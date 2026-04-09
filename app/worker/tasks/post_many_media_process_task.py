from logging import getLogger
from uuid import UUID

from celery import shared_task
from minio.datatypes import Object

from app.cache.helpers.base import cache_manager
from app.cache.post_cache import PostCache
from app.db.models.post import Post
from app.db.models.post_media import PostMedia
from app.globals.others_constants import OtherConstants
from app.schemas.post_upload_schemas import CreateMediaUploadIntentFullData
from app.storage.minio_config import BucketName
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.tasks_utils.base import ProcessingContext, ProcessingStep
from app.worker.tasks.tasks_utils.common_media_utils import create_post_and_media
from app.worker.tasks.tasks_utils.handlers import CleanupHandler, ProgressHandler
from app.worker.tasks.tasks_utils.medias_process_helper import MediasProcessHelper
from app.worker.tasks.tasks_utils.minio import MinIOManager
from app.worker.tasks.workers_task_names import WorkersTaskNames

logger = getLogger(__name__)


@shared_task(name=WorkersTaskNames.PROCESS_MEDIAS_UPLOAD, queue=OtherConstants.MEDIA_PROCESSING_WORKER_QUEUE_NAME)
def process_media_upload_task(
    intent_id: str,
    user_id: str,
    post_data: str
) -> None:
    """
    Tache pour traiter plusieurs médias d'un post et l'ajouter en bd
    Args:
        user_id: ID de l'utilisateur propriétaire.
        intent_id: ID de l'intent d'upload image.
        post_data: JSON string contenant les données du post.
    """

    def send_error_to_user(error: str) -> None:
        try:
            task_async_loop_manager.run_async(progress_handler.error(error))
        except Exception as ee:
            logger.error(f"Erreur {ee.__class__.__name__} envoi message d'erreur au stream pour {intent_id}: {ee}")

    try:
        post_data_obj: CreateMediaUploadIntentFullData = CreateMediaUploadIntentFullData.model_validate_json(post_data)
    except Exception as e:
        logger.error(f"Erreur validation JSON du post_data pour intent {intent_id}: {e}")
        return

    redis_cache = cache_manager.get_redis_connection_from_pool()
    upload_cache = PostCache(redis_cache)

    # Contexte et handlers
    context = ProcessingContext(
        user_id=user_id,
        intent_id=intent_id,
        post_data=post_data_obj,
        cache=redis_cache,
        upload_cache=upload_cache,
    )

    progress_handler = ProgressHandler(context)
    helper = MediasProcessHelper(progress_handler, intent_id, logger)
    cleanup_handler = CleanupHandler()
    cleanup_handler.register_many_files(context.get_all_raw_paths())
    cleanup_handler.register_many_directories(context.get_all_processed_dirs_paths())

    current_step = ProcessingStep.VERIFICATION
    downloads_res: dict[str, Object] | None = None
    uploaded_files_to_cleanup: list[tuple[str, str]] = []  # [(bucket_name, object_path), ...]
    post_object: Post | None = None

    try:
        downloads_res: dict[str, Object] = {}

        for media in post_data_obj.files:
            down_res = helper.verify_file_existing_and_download(
                step=current_step, local_raw_path=context.get_local_raw_path(media.file_name),
                media_progress_weight= context.get_file_progress_weight(media.file_name), file_info=media
            )

            if down_res.is_error():
                send_error_to_user(down_res.error)
                return
            downloads_res[media.file_name] = down_res.data

        current_step = ProcessingStep.COMPRESSING

        compress_process_res: dict[str, tuple[str | None, int, int, int | None ]] = {}     # des tuples: local_thumbnail_path, height, width, duration

        for media in post_data_obj.files:
            compress_res = helper.compress_file(
                step=current_step, local_raw_path=context.get_local_raw_path(media.file_name),
                media_progress_weight= context.get_file_progress_weight(media.file_name),
                file_info=media, output_dir=context.get_local_processed_dir(media.file_name)
            )
            if compress_res.is_error():
                send_error_to_user(compress_res.error)
                return

            compress_process_res[media.file_name] = compress_res.data

        current_step = ProcessingStep.CREATING

        uploads_res: dict[str, tuple[str, str | None]] = {}     # des tuples: minio_media_url et minio_thumbnail_url

        for media in post_data_obj.files:
            upload_res = helper.upload_files_to_minio(
                step=current_step, file_info=media, media_progress_weight= context.get_file_progress_weight(media.file_name),
                output_dir=context.get_local_processed_dir(media.file_name),
                thumbnail_path=compress_process_res[media.file_name][0], is_story=False
            )
            if upload_res.is_error():
                send_error_to_user(upload_res.error)
                return

            uploads_res[media.file_name] = upload_res.data

            media_url, thumbnail_url = upload_res.data

            if media_url:
                uploaded_files_to_cleanup.append((BucketName.POSTS_PERMANENT_CONTENT.value, media_url))
            if thumbnail_url:
                uploaded_files_to_cleanup.append((BucketName.USER_IDENTITY_ASSETS.value, thumbnail_url))


        post_object = Post(
            author_id=UUID(user_id), club_id=post_data_obj.club_id, event_id=post_data_obj.event_id,
            academic_year_id=post_data_obj.academic_year_id, target_classe_id=post_data_obj.classe_id,
            content=post_data_obj.content
        )

        post_medias: list[PostMedia] = []

        for i, media in enumerate(post_data_obj.files):
            media_object = helper.create_post_media_object(
                post_id=post_object.id, duration=compress_process_res[media.file_name][3],
                file_size=downloads_res[media.file_name].size, file_info=media,
                width=compress_process_res[media.file_name][2], height=compress_process_res[media.file_name][1],
                bucket_media_url=uploads_res[media.file_name][0], bucket_thumbnail_path=uploads_res[media.file_name][1],
                local_thumbnail_path=compress_process_res[media.file_name][0], index=i
            )

            if media_object.is_error():
                send_error_to_user(media_object.error)
                return

            post_medias.append(media_object.data)

        db_result = task_async_loop_manager.run_async(create_post_and_media(redis_cache, post_object, post_medias, logger))

        if db_result.is_error():
            send_error_to_user(db_result.error)
            return

        task_async_loop_manager.run_async(progress_handler.complete())

    except Exception as e:
        logger.exception(f"Exception {e.__class__.__name__} inattendue lors du traitement médias: {e}")
        task_async_loop_manager.run_async(progress_handler.error())
    finally:
        # Nettoyage
        if downloads_res is not None:
            for media in downloads_res.values():
                MinIOManager.delete_file(media.bucket_name, media.object_name)


        if post_object is None and uploaded_files_to_cleanup:
            for bucket_name, object_path in uploaded_files_to_cleanup:
                del_res = MinIOManager.delete_file(bucket_name, object_path)
                if del_res.is_error():
                    logger.error(f"Erreur suppression upload orphelin MinIO {bucket_name}/{object_path}: {del_res.error}")
                else:
                    logger.info(f"Nettoyage upload orphelin MinIO: {bucket_name}/{object_path}")

        
        try:
            task_async_loop_manager.run_async(redis_cache.close())
        except Exception as e:
            logger.error(f"Erreur fermeture Redis: {e}")
        
        cleanup_handler.cleanup_all()



