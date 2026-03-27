import os
import shutil
from logging import getLogger
from time import time
from uuid import uuid4

from celery import shared_task

from app.cache.helpers.base import cache_manager
from app.cache.uploads_cache import MediaUploadsCache
from app.globals.messages import Messages
from app.schemas.post_upload_schemas import CreateMediaUploadIntentFullData, WsPostProcessingInfoSchema, \
    WsPostProcessingInfoSchemaSteps
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.tasks_utils.video_process_task_utils import send_data_to_progress_stream, \
    get_file_metadata_from_minio, delete_file_from_bucket, download_file_from_minio
from app.worker.tasks.tasks_utils.image_process_task_utils import verify_file_is_image, \
    get_image_metadata, process_image_with_pillow, upload_images_to_minio, add_processed_image_in_db
from app.worker.tasks.workers_task_names import WorkersTaskNames
from app.storage.bucket_files_utils import BucketFilesUtils

logger = getLogger(__name__)
#TODO: Refactor après

#TODO: Ajouter le BlurHash

@shared_task(name=WorkersTaskNames.PROCESS_IMAGE)
def process_image_task(
    raw_bucket_name: str, raw_object_name: str, user_id: str, intent_id: str, post_data: str
):
    """
    Tâche pour traiter un fichier image, Normalise une image brute en Webp.
    Args:
        raw_bucket_name: Le bucket du fichier brut dans MinIo
        raw_object_name: L'image brute dans MinIo
        user_id: L'id de l'utilisateur à qui appartient l'image à traiter, utilisé pour faire le lien entre le fichier traité et l'utilisateur
        intent_id: L'id de l'intent d'upload image associé à ce fichier,
         utilisé pour faire le lien entre le fichier traité et l'intent d'upload qui a été créé pour ce fichier
        post_data: Un Json String contenant les données du post à ajouter

    Returns:
        Que dalle, c'est une tâche pour traiter une image, le résultat du traitement (l'image normalisée)
        est uploadé dans le bucket Minio et lié à l'intent d'upload image grâce à l'id de l'intent fourni en argument
    """

    post_data: CreateMediaUploadIntentFullData = CreateMediaUploadIntentFullData.model_validate_json(post_data)
    local_raw_path = f"/tmp/{uuid4()}_raw"
    local_processed_dir = f"/tmp/{uuid4()}_processed_files"
    os.makedirs(local_processed_dir, exist_ok=True)
    final_bucket_objects_path = BucketFilesUtils.generate_objects_path_for_processed_image(intent_id)
    local_thumbnail_path = None
    redis_cache = cache_manager.get_redis_connection_from_pool()
    upload_cache = MediaUploadsCache(redis_cache)
    global_progress_pourcentage = 0

    progression = WsPostProcessingInfoSchema(
        step=WsPostProcessingInfoSchemaSteps.UNKNOWN, progress=global_progress_pourcentage, timestamp=time(),
        error_message=None
    )

    def update_progress(step: WsPostProcessingInfoSchemaSteps, progress_increment: int, error_message: str = None):
        nonlocal global_progress_pourcentage
        nonlocal progression

        if not error_message:
            global_progress_pourcentage += progress_increment

        progression.progress = min(global_progress_pourcentage, 100)
        progression.step = step
        progression.error_message = error_message
        progression.timestamp = time()

        task_async_loop_manager.run_async(send_data_to_progress_stream(upload_cache, user_id, intent_id, progression))

    def error_update_progress(error_message: str = None):
        nonlocal progression
        update_progress(progression.step, 0, error_message or Messages.INTERNAL_SERVER_ERROR)

    raw_object = get_file_metadata_from_minio(raw_bucket_name, raw_object_name)

    if not raw_object[0]:
        logger.error(raw_object[1])
        return

    raw_object = raw_object[1]

    try:
        update_progress(WsPostProcessingInfoSchemaSteps.VERIFICATION, 10)

        down_res = download_file_from_minio(raw_object.bucket_name, raw_object.object_name, local_raw_path)

        if not down_res[0]:
            logger.error(down_res[1])
            error_update_progress()
            return

        update_progress(WsPostProcessingInfoSchemaSteps.VERIFICATION, 10)

        file_verification = verify_file_is_image(local_raw_path)
        if not file_verification[0]:
            logger.error(file_verification[1])
            error_update_progress(error_message=file_verification[1])
            return

        image_metadata_res = get_image_metadata(local_raw_path)
        if not image_metadata_res[0]:
            logger.error(image_metadata_res[1])
            error_update_progress()
            return

        image_metadata = image_metadata_res[1]
        logger.info(f"Métadonnées de l'image : {image_metadata}")

        update_progress(WsPostProcessingInfoSchemaSteps.COMPRESSING, 20)

        # TODO: Changez la génération des qualités (on va faire pplutot un truc
        #  Génération de 3 tailles (Small, Medium, Large) en WebP)
        process_res = process_image_with_pillow(local_raw_path, local_processed_dir)
        if not process_res[0]:
            logger.error(process_res[1])
            error_update_progress()
            return

        processed_images_paths = process_res[1]
        logger.info(f"Images traitées créées : {list(processed_images_paths.keys())}")

        update_progress(WsPostProcessingInfoSchemaSteps.CREATING, 40)

        # TODO: Ramenez le thumbnail vers le bucket public
        upload_res = task_async_loop_manager.run_async(
            upload_images_to_minio(local_processed_dir, final_bucket_objects_path)
        )

        if not upload_res[0]:
            logger.error(upload_res[1])
            error_update_progress()
            return

        minio_urls = upload_res[1]
        logger.info(f"Images uploadées vers MinIO : {list(minio_urls.keys())}")

        update_progress(WsPostProcessingInfoSchemaSteps.FINALIZING, 15)

        db_add_res = task_async_loop_manager.run_async(
            add_processed_image_in_db(
                cache=redis_cache,
                user_id=user_id,
                post_data=post_data,
                minio_urls=minio_urls,
                file_size=image_metadata['file_size'],
                width=image_metadata['width'],
                height=image_metadata['height'],
            )
        )

        if not db_add_res[0]:
            logger.error(db_add_res[1])
            error_update_progress()
            return

        update_progress(WsPostProcessingInfoSchemaSteps.COMPLETED, 15)

    except Exception as e:
        logger.exception(f"Exception {e.__class__.__name__} inattendue lors du traitement de la photo : {e}",
                         exc_info=e)
        error_update_progress()
    finally:

        delete_file_from_bucket(raw_object.bucket_name, raw_object.object_name)

        task_async_loop_manager.run_async(redis_cache.close())
        if os.path.exists(local_raw_path):
            os.remove(local_raw_path)
        if os.path.exists(local_processed_dir):
            shutil.rmtree(local_processed_dir)

