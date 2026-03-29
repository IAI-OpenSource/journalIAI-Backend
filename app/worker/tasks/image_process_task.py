"""Tâche Celery pour le traitement des images."""

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
from app.worker.tasks.tasks_utils.image_process_task_utils import (
    get_image_metadata,
    process_image_with_pillow,
    upload_images_to_minio,
)
from app.worker.tasks.workers_task_names import WorkersTaskNames
from app.worker.tasks.validation.file_validator import FileValidator

logger = getLogger(__name__)


@shared_task(name=WorkersTaskNames.PROCESS_IMAGE)
def process_image_task(
    raw_bucket_name: str, raw_object_name: str, user_id: str, intent_id: str, post_data: str
) -> None:
    """
    Tâche pour traiter un fichier image.
    
    Normalise une image brute en 3 variantes WebP (thumbnail, medium, full).
    
    Args:
        raw_bucket_name: Bucket MinIO du fichier brut.
        raw_object_name: Nom du fichier brut dans MinIO.
        user_id: ID de l'utilisateur propriétaire.
        intent_id: ID de l'intent d'upload image.
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
        validation_result = FileValidator.validate_image(context.local_raw_path)
        if validation_result.is_error():
            send_error_to_user(validation_result.error)
            return

        # Extraire métadonnées image
        metadata_result = get_image_metadata(context.local_raw_path)
        if metadata_result.is_error():
            send_error_to_user(metadata_result.error)
            return

        image_metadata = metadata_result.data
        logger.info(f"Métadonnées image: {image_metadata}")

        task_async_loop_manager.run_async(
            progress_handler.update_step(ProcessingStep.COMPRESSING, 20)
        )

        # Traiter l'image
        process_result = process_image_with_pillow(context.local_raw_path, context.local_processed_dir)
        if process_result.is_error():
            send_error_to_user(process_result.error)
            return

        processed_images_paths = process_result.data
        logger.info(f"Images traitées créées: {list(processed_images_paths.keys())}")

        local_thumbnail_path = processed_images_paths.get("thumbnail")

        task_async_loop_manager.run_async(
            progress_handler.update_step(ProcessingStep.CREATING, 40)
        )

        # Upload vers MinIO
        final_bucket_objects_path = BucketFilesUtils.generate_objects_path_for_processed_image(intent_id)
        upload_result = task_async_loop_manager.run_async(
            upload_images_to_minio(context.local_processed_dir, final_bucket_objects_path)
        )


        if upload_result.is_error():
            send_error_to_user(upload_result.error)
            return

        minio_urls = upload_result.data

        final_bucket_thumbnail_path = None
        if local_thumbnail_path:
            final_bucket_thumbnail_path = BucketFilesUtils.generate_objects_path_for_image_thumbnail(intent_id)
            res = MinIOManager.upload_file(
                BucketName.USER_IDENTITY_ASSETS.value,
                final_bucket_thumbnail_path,
                local_thumbnail_path,
                content_type="image/webp"
            )
            if res.is_error():
                logger.error(f"Erreur upload miniature mais lets go on continue: {res.error}")
                final_bucket_thumbnail_path = None

        logger.info(f"Images uploadées vers MinIO: {list(minio_urls.keys())}")

        task_async_loop_manager.run_async(
            progress_handler.update_step(ProcessingStep.FINALIZING, 15)
        )

        db_result = task_async_loop_manager.run_async(
            create_post_and_media(
                cache=redis_cache,
                user_id=user_id,
                post_data=post_data_obj,
                post_type=PostType.IMAGE,
                media_type=MediaType.IMAGE,
                media_url=final_bucket_objects_path,
                thumbnail_url=final_bucket_thumbnail_path,
                file_size=image_metadata['file_size'],
                width=image_metadata['width'],
                height=image_metadata['height'],
                blur_hash=generate_blurhash_str(context.local_raw_path)
            )
        )

        if db_result.is_error():
            send_error_to_user(db_result.error)
            return

        task_async_loop_manager.run_async(progress_handler.complete())

    except Exception as e:
        logger.exception(f"Exception inattendue lors du traitement image: {e}")
        task_async_loop_manager.run_async(progress_handler.error())
    finally:
        # Supprimer le fichier brut
        MinIOManager.delete_file(raw_object.bucket_name, raw_object.object_name)
        
        # Nettoyage
        task_async_loop_manager.run_async(redis_cache.close())
        task_async_loop_manager.run_async(cleanup_handler.cleanup_all())


