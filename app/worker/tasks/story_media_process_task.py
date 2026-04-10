"""
Tâche Celery pour traiter l'upload d'une story.
Gère le traitement d'un seul média (image ou vidéo) avec compression et upload.
"""

from logging import getLogger

from celery import shared_task
from minio.datatypes import Object

from app.cache.helpers.base import cache_manager, CacheWrapper
from app.cache.processing_cache import ProcessingCache
from app.cache.story_cache import StoryCache
from app.db.session import AsyncSessionLocal

from app.globals.others_constants import OtherConstants
from app.schemas.story_upload_schemas import CreateStoryUploadIntentFullData
from app.services.story_upload_service import StoryMediaUploadsService
from app.storage.minio_config import BucketName
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.tasks_utils.base import ProcessingContext, ProcessingStep, ProcessingResult
from app.worker.tasks.tasks_utils.common_media_utils import generate_blurhash_str
from app.worker.tasks.tasks_utils.handlers import CleanupHandler, ProgressHandler
from app.worker.tasks.tasks_utils.medias_process_helper import MediasProcessHelper
from app.worker.tasks.tasks_utils.minio import MinIOManager
from app.worker.tasks.workers_task_names import WorkersTaskNames

logger = getLogger(__name__)



@shared_task(name=WorkersTaskNames.PROCESS_STORY_UPLOAD, queue=OtherConstants.MEDIA_PROCESSING_WORKER_QUEUE_NAME)
def process_story_upload_task(
    intent_id: str,
    user_id: str,
    story_data: str
) -> None:
    """
    Tâche pour traiter un seul média d'une story et l'ajouter en BD.

    Args:
        user_id: ID de l'utilisateur propriétaire
        intent_id: ID de l'intent d'upload
        story_data: JSON string contenant les données de la story
    """

    def send_error_to_user(error: str) -> None:
        """Envoie un message d'erreur au client via le stream de progression."""
        try:
            task_async_loop_manager.run_async(progress_handler.error(error))
        except Exception as ee:
            logger.error(f"Erreur {ee.__class__.__name__} lors de l'envoi du message d'erreur pour {intent_id}: {ee}")

    try:
        story_data_obj: CreateStoryUploadIntentFullData = CreateStoryUploadIntentFullData.model_validate_json(story_data)
    except Exception as e:
        logger.error(f"Erreur validation JSON du story_data pour intent {intent_id}: {e}")
        return

    redis_cache = cache_manager.get_redis_connection_from_pool()
    upload_cache = StoryCache(redis_cache)

    # Créer un contexte compatible avec ProcessingContext (utilisant upload_cache qui accepte StoryCache)
    context = ProcessingContext(
        user_id=user_id,
        intent_id=intent_id,
        post_data=story_data_obj,
        cache=redis_cache,
        upload_cache=upload_cache,
        processing_cache=ProcessingCache(redis_cache)
    )

    progress_handler = ProgressHandler(context)
    helper = MediasProcessHelper(progress_handler, intent_id, logger)
    cleanup_handler = CleanupHandler()
    cleanup_handler.register_many_files(context.get_all_raw_paths())
    cleanup_handler.register_many_directories(context.get_all_processed_dirs_paths())

    current_step = ProcessingStep.VERIFICATION
    downloaded_file: Object | None = None
    uploaded_files_to_cleanup: list[tuple[str, str]] = []  # [(bucket_name, object_path), ...]
    has_success = False
    try:
        file = story_data_obj.file

        down_res = helper.verify_file_existing_and_download(
            step=current_step,
            local_raw_path=context.get_local_raw_path(file.file_name),
            media_progress_weight=1.0,
            file_info=file
        )

        if down_res.is_error():
            send_error_to_user(down_res.error)
            return

        downloaded_file = down_res.data

        current_step = ProcessingStep.COMPRESSING

        compress_res: ProcessingResult[tuple[str | None, int, int, int | None, str | None ]] = helper.compress_file(
            step=current_step,
            local_raw_path=context.get_local_raw_path(file.file_name),
            media_progress_weight=1.0,
            file_info=file,
            output_dir=context.get_local_processed_dir(file.file_name),
            is_story=True
        )

        if compress_res.is_error():
            send_error_to_user(compress_res.error)
            return

        local_thumbnail_path, height, width, duration, blur_hash = compress_res.data


        current_step = ProcessingStep.CREATING

        upload_res = helper.upload_files_to_minio(
            step=current_step,
            file_info=file,
            media_progress_weight=1.0,
            output_dir=context.get_local_processed_dir(file.file_name),
            thumbnail_path=local_thumbnail_path,
            is_story=True
        )

        if upload_res.is_error():
            send_error_to_user(upload_res.error)
            return

        media_url, thumbnail_url = upload_res.data

        if media_url:
            uploaded_files_to_cleanup.append((BucketName.STORIES_EPHEMERAL_CONTENT.value, media_url))
        if thumbnail_url:
            uploaded_files_to_cleanup.append((BucketName.USER_IDENTITY_ASSETS.value, thumbnail_url))


        # Save en Bd
        db_result = task_async_loop_manager.run_async(
            _save_result_to_bd(
                user_id=user_id, thumbnail_url=thumbnail_url, minio_url=media_url,
                height=height, width=width, intent_info=story_data_obj, file_size=downloaded_file.size,
                duration=duration, cache=redis_cache, intent_id=intent_id,
                blur_hash=blur_hash
            )
        )

        if db_result.is_error():
            send_error_to_user(db_result.error)
            return

        has_success = True

        task_async_loop_manager.run_async(progress_handler.complete())

        logger.info(f"Traitement de la story terminé avec succès pour l'intent {intent_id}")

    except Exception as e:
        error_msg = f"Exception {e.__class__.__name__} lors du traitement de la story {intent_id}: {e}"
        logger.exception(error_msg)
        task_async_loop_manager.run_async(progress_handler.error())


    finally:

        # Nettoyage des fichiers locaux
        cleanup_handler.cleanup_all()

        if downloaded_file:
            MinIOManager.delete_file(BucketName.MEDIAS_RAW_UPLOADS.value, downloaded_file.object_name)

        if uploaded_files_to_cleanup and not has_success:
            for file in uploaded_files_to_cleanup:
                MinIOManager.delete_file(file[0], file[1])

        task_async_loop_manager.run_async(redis_cache.close())


async def _save_result_to_bd(
        user_id: str,
        cache: CacheWrapper,
        intent_info: CreateStoryUploadIntentFullData,
        thumbnail_url: str | None,
        minio_url: str,
        height: int,
        width: int,
        duration: int | None,
        file_size: int | None,
        intent_id: str,
        blur_hash: str | None,
) -> ProcessingResult[str]:
    async with AsyncSessionLocal() as sess:
        repo = StoryMediaUploadsService(cache, sess)
        res = await repo.worker_service_save_processed_story_in_bd(
            user_id=user_id,
            minio_url=minio_url,
            intent_info=intent_info,
            thumbnail_url=thumbnail_url,
            height=height,
            width=width,
            duration=duration,
            f_size=file_size,
            intent_id=intent_id,
            blur_hash=blur_hash
        )
        if res.is_error():
            return ProcessingResult.error_response(res.error)

        return ProcessingResult.ok_response(res.data)