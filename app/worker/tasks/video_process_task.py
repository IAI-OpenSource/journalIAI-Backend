import os
import shutil
from logging import getLogger
from time import time
from uuid import uuid4

from celery import shared_task

from app.cache.helpers.base import cache_manager
from app.cache.uploads_cache import VideoUploadsCache
from app.globals.messages import Messages
from app.schemas.upload_schemas import WsPostProcessingInfoSchema, WsPostProcessingInfoSchemaSteps, \
     CreateVideoUploadIntentFullData
from app.storage.bucket_files_utils import BucketFilesUtils
from app.storage.minio_config import BucketName
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.tasks_utils.video_process_task_utils import verify_file_is_video, download_file_from_minio, \
    get_file_metadata_from_minio, upload_processed_file_to_bucket, delete_file_from_bucket, \
    process_video_file_with_ffmpeg, get_video_metadata, get_target_qualities, generate_thumbnail, generate_hls_command, \
    upload_hls_to_minio, send_data_to_progress_stream, add_processed_things_in_db
from app.worker.tasks.workers_task_names import WorkersTaskNames

logger = getLogger(__name__)


# TODO: refactor tout ce spaghethi après

@shared_task(name=WorkersTaskNames.PROCESS_VIDEO)
def process_video_task(
        raw_bucket_name: str, raw_object_name: str, user_id: str, intent_id: str, post_data : str
) -> None:
    """
    Tâche pour traiter un fichier video, Normalise une vidéo brute en MP4 standard (720p, H.264/AAC).
    Args:
        raw_bucket_name: Le bucket du fichier brut dans MinIo
        raw_object_name: Le fichier video dans MinIo
        user_id: L'id de l'utilisateur à qui appartient le fichier video à traiter, utilisé pour faire le lien entre le fichier traité et l'utilisateur
        intent_id: L'id de l'intent d'upload video associé à ce fichier,
         utilisé pour faire le lien entre le fichier traité et l'intent d'upload qui a été créé pour ce fichier
        post_data: Un Json String contenant les données du post à ajouter

    Returns:
        Que dalle, c'est une tâche pour traiter une vidéo, le résultat du traitement (la vidéo normalisée)
        est uploadé dans le bucket Minio et lié à l'intent d'upload video grâce à l'id de l'intent fourni en argument
    """

    post_data: CreateVideoUploadIntentFullData = CreateVideoUploadIntentFullData.model_validate_json(post_data)
    local_raw_path = f"/tmp/{uuid4()}_raw"
    local_processed_dir = f"/tmp/{uuid4()}_processed_files"
    os.makedirs(local_processed_dir, exist_ok=True)
    final_bucket_objects_path = BucketFilesUtils.generate_objects_path_for_processed_video(intent_id)
    final_bucket_thumbnail_path = BucketFilesUtils.generate_objects_path_for_video_thumbnail(intent_id)
    local_thumbnail_path = None
    redis_cache = cache_manager.get_redis_connection_from_pool()
    upload_cache = VideoUploadsCache(redis_cache)
    global_progress_pourcentage = 0

    progression = WsPostProcessingInfoSchema(
        step=WsPostProcessingInfoSchemaSteps.UNKNOWN, progress=global_progress_pourcentage, timestamp=time(), error_message=None
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

        file_verification = verify_file_is_video(local_raw_path)
        if not file_verification[0]:
            logger.error(file_verification[1])
            error_update_progress(error_message=file_verification[1])
            return

        video_metadat_res = get_video_metadata(local_raw_path)
        if not video_metadat_res[0]:
            logger.error(video_metadat_res[1])
            error_update_progress()
            return

        update_progress(WsPostProcessingInfoSchemaSteps.COMPRESSING, 10)

        qualities = get_target_qualities(video_metadat_res[1]['height'])

        logger.info(f"Qualities utilisées : {qualities}")
        process_command = generate_hls_command(
            local_raw_path=local_raw_path,
            qualities=qualities,
            output_dir=local_processed_dir,
            has_audio=video_metadat_res[1]['has_audio']
        )

        video_processed = process_video_file_with_ffmpeg(process_command)

        if not video_processed[0]:
            logger.error(video_processed[1])
            error_update_progress()
            return
        try:
            local_thumbnail_path = generate_thumbnail(
                local_raw_path, local_processed_dir,
                ss_time=max(int(video_metadat_res[1]['duration'] * 0.1), 1)  # On prend une frame à 10% de la vidéo, fallback 1 seconde
            )
        except Exception as e:
            logger.error(f"Erreur {e.__class__.__name__} lors de la génération du thumbnail mais on continue : {e}")

        update_progress(WsPostProcessingInfoSchemaSteps.CREATING, 40)

        upload_res = task_async_loop_manager.run_async(
            upload_hls_to_minio(local_processed_dir, final_bucket_objects_path))

        if not upload_res[0]:
            logger.error(upload_res[1])
            error_update_progress()
            return

        # Upload de la miniature
        if local_thumbnail_path:
            upload_processed_file_to_bucket(
                BucketName.USER_IDENTITY_ASSETS.value,
                final_bucket_thumbnail_path,
                local_thumbnail_path,
                c_type="image/webp"
            )


        update_progress(WsPostProcessingInfoSchemaSteps.FINALIZING, 15)

        db_add_res = task_async_loop_manager.run_async(
            add_processed_things_in_db(
                cache=redis_cache,
                file_size=raw_object.size,
                duration=video_metadat_res[1]['duration'],
                user_id=user_id,
                post_data=post_data,
                minio_video_url=final_bucket_objects_path,
                minio_thumnail_url=final_bucket_thumbnail_path,
                h=video_metadat_res[1]['height'],
                w=video_metadat_res[1]['width'],
            )
        )
        if not db_add_res[0]:
            logger.error(db_add_res[1])
            error_update_progress()
            return

        update_progress(WsPostProcessingInfoSchemaSteps.COMPLETED, 15)
    except Exception as e:
        logger.exception(f"Exception {e.__class__.__name__} inattendue lors du traitement de la vidéo : {e}", exc_info=e)
        error_update_progress()
    finally:

        delete_file_from_bucket(raw_object.bucket_name, raw_object.object_name)

        task_async_loop_manager.run_async(redis_cache.close())
        if os.path.exists(local_raw_path):
            os.remove(local_raw_path)
        if os.path.exists(local_processed_dir):
            shutil.rmtree(local_processed_dir)


