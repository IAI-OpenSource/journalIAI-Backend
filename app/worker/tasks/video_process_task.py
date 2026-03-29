"""Tâche Celery pour le traitement des vidéos."""
from logging import getLogger

from celery import shared_task

from app.cache.helpers.base import cache_manager
from app.cache.uploads_cache import MediaUploadsCache
from app.db.models.enums import MediaType, PostType
from app.schemas.post_upload_schemas import CreateMediaUploadIntentFullData
from app.storage.bucket_files_utils import BucketFilesUtils
from app.storage.minio_config import BucketName
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.base.processing_context import ProcessingContext
from app.worker.tasks.base.processing_step import ProcessingStep
from app.worker.tasks.handlers.cleanup_handler import CleanupHandler
from app.worker.tasks.handlers.progress_handler import ProgressHandler
from app.worker.tasks.minio.minio_operations import MinIOManager
from app.worker.tasks.tasks_utils.common_media_utils import create_post_and_media, generate_blurhash_str
from app.worker.tasks.tasks_utils.video_process_task_utils import (
    generate_hls_command,
    generate_thumbnail,
    get_target_qualities,
    get_video_metadata,
    process_video_file_with_ffmpeg,
    upload_hls_to_minio,
)
from app.worker.tasks.workers_task_names import WorkersTaskNames
from app.worker.tasks.validation.file_validator import FileValidator

logger = getLogger(__name__)


@shared_task(name=WorkersTaskNames.PROCESS_VIDEO)
def process_video_task(
    raw_bucket_name: str, raw_object_name: str, user_id: str, intent_id: str, post_data: str
) -> None:
    """
    Tâche pour traiter un fichier vidéo.
    
    Normalise une vidéo brute en HLS (fMP4) avec multiple qualités et génère une miniature.
    
    Args:
        raw_bucket_name: Bucket MinIO du fichier brut.
        raw_object_name: Nom du fichier brut dans MinIO.
        user_id: ID de l'utilisateur propriétaire.
        intent_id: ID de l'intent d'upload vidéo.
        post_data: JSON string contenant les données du post.
    """

    def send_error_to_user(error: str) -> None:
        task_async_loop_manager.run_async(progress_handler.error(error))

    post_data_obj: CreateMediaUploadIntentFullData = CreateMediaUploadIntentFullData.model_validate_json(post_data)
    redis_cache = cache_manager.get_redis_connection_from_pool()
    upload_cache = MediaUploadsCache(redis_cache)
    
    # Contexte et handlers
    context = ProcessingContext(
        raw_bucket_name=raw_bucket_name,
        raw_object_name=raw_object_name,
        user_id=user_id,
        intent_id=intent_id,
        post_data=post_data_obj,
        cache=redis_cache,
        upload_cache=upload_cache,
    )
    
    progress_handler = ProgressHandler(context)
    cleanup_handler = CleanupHandler()

    # Enregistrer les chemins pour nettoyage
    cleanup_handler.register_file(context.local_raw_path)
    cleanup_handler.register_directory(context.local_processed_dir)

    raw_object_result = MinIOManager.get_file_metadata(raw_bucket_name, raw_object_name)
    if raw_object_result.is_error():
        send_error_to_user(raw_object_result.error)
        return

    raw_object = raw_object_result.data

    try:
        # Récupérer métadonnées MinIO
        task_async_loop_manager.run_async(
            progress_handler.update_step(ProcessingStep.VERIFICATION, 10)
        )


        # Télécharger le fichier
        download_result = MinIOManager.download_file(
            raw_object.bucket_name, raw_object.object_name, context.local_raw_path
        )

        if download_result.is_error():
            send_error_to_user(download_result.error)
            return

        task_async_loop_manager.run_async(
            progress_handler.update_step(ProcessingStep.VERIFICATION, 10)
        )

        # Valider le fichier
        validation_result = FileValidator.validate_video(context.local_raw_path)

        if validation_result.is_error():
            send_error_to_user(validation_result.error)
            return

        # Extraire métadonnées vidéo
        metadata_result = get_video_metadata(context.local_raw_path)
        if metadata_result.is_error():
            send_error_to_user(metadata_result.error)
            return

        video_metadata = metadata_result.data
        logger.info(f"Métadonnées vidéo: {video_metadata}")

        task_async_loop_manager.run_async(
            progress_handler.update_step(ProcessingStep.COMPRESSING, 20)
        )

        # Traiter la vidéo
        qualities = get_target_qualities(video_metadata['height'])
        logger.info(f"Qualités utilisées: {qualities}")

        hls_command = generate_hls_command(
            local_raw_path=context.local_raw_path,
            qualities=qualities,
            output_dir=context.local_processed_dir,
            has_audio=video_metadata['has_audio']
        )

        process_result = process_video_file_with_ffmpeg(hls_command)

        if process_result.is_error():
            send_error_to_user(process_result.error)
            return

        # Générer miniature
        try:
            thumbnail_path = generate_thumbnail(
                context.local_raw_path,
                context.local_processed_dir,
                ss_time=max(int(video_metadata['duration'] * 0.1), 1)
            )
            if thumbnail_path:
                cleanup_handler.register_file(thumbnail_path)
        except Exception as e:
            logger.warning(f"Génération miniature échouée mais on continue: {e}")
            thumbnail_path = None

        task_async_loop_manager.run_async(
            progress_handler.update_step(ProcessingStep.CREATING, 40)
        )

        # Upload HLS vers MinIO
        final_bucket_objects_path = BucketFilesUtils.generate_objects_path_for_processed_video(intent_id)
        upload_result = task_async_loop_manager.run_async(
            upload_hls_to_minio(context.local_processed_dir, final_bucket_objects_path)
        )

        if upload_result.is_error():
            send_error_to_user(upload_result.error)
            return

        # Upload miniature
        final_bucket_thumbnail_path = None

        if thumbnail_path:
            final_bucket_thumbnail_path = BucketFilesUtils.generate_objects_path_for_video_thumbnail(intent_id)
            res = MinIOManager.upload_file(
                BucketName.USER_IDENTITY_ASSETS.value,
                final_bucket_thumbnail_path,
                thumbnail_path,
                content_type="image/webp"
            )
            if res.is_error():
                logger.error(f"Erreur upload miniature mais lets go on continue: {res.error}")
                final_bucket_thumbnail_path = None

        task_async_loop_manager.run_async(
            progress_handler.update_step(ProcessingStep.FINALIZING, 15)
        )

        # Enregistrer en BD
        db_result = task_async_loop_manager.run_async(
            create_post_and_media(
                cache=redis_cache,
                user_id=user_id,
                post_data=post_data_obj,
                post_type=PostType.VIDEO,
                media_type=MediaType.VIDEO,
                media_url=final_bucket_objects_path,
                thumbnail_url=final_bucket_thumbnail_path,
                file_size=raw_object.size,
                width=video_metadata['width'],
                height=video_metadata['height'],
                duration=int(video_metadata['duration']),
                blur_hash=generate_blurhash_str(thumbnail_path)
            )
        )

        if db_result.is_error():
            logger.error(db_result.error)
            task_async_loop_manager.run_async(progress_handler.error(db_result.error))
            return

        task_async_loop_manager.run_async(progress_handler.complete())

    except Exception as e:
        logger.exception(f"Exception {e.__class__.__name__} inattendue lors du traitement vidéo: {e}")
        task_async_loop_manager.run_async(progress_handler.error())
    finally:
        # Supprimer le fichier brut
        MinIOManager.delete_file(raw_object.bucket_name, raw_object.object_name)
        
        # Nettoyage
        task_async_loop_manager.run_async(redis_cache.close())
        task_async_loop_manager.run_async(cleanup_handler.cleanup_all())



