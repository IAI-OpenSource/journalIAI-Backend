import os
import subprocess
from logging import getLogger
from time import time
from typing import Any
from uuid import uuid4

from celery import shared_task

from app.cache.helpers.base import cache_manager
from app.cache.uploads_cache import VideoUploadsCache
from app.globals.messages import Messages
from app.schemas.upload_schemas import WsPostProcessingInfoSchema, WsPostProcessingInfoSchemaSteps
from app.storage.bucket_files_utils import BucketFilesUtils
from app.storage.minio_client import MinioClientFactory
from app.storage.minio_config import BucketName
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.workers_task_names import WorkersTaskNames
import magic
logger = getLogger(__name__)

InternalResultPatern  = tuple[bool, Any]  # (success, data) ou (success, error_message)

def verify_file_is_video(file_path : str) -> InternalResultPatern:
    """
    Vérifie si le fichier à traiter est bien une vidéo en utilisant la bibliothèque python-magic
    Args:
        file_path: Le chemin du fichier à vérifier

    Returns:
        True si le fichier est une vidéo, False sinon
    """

    # Analyse par buffer du fichier pour déterminer son type MIME
    with open(file_path, "rb") as file:
        buffer_type = magic.from_buffer(file.read(2048), mime=True)
        if buffer_type and buffer_type.startswith("video/"):
            return True, None
        return False, None

def download_file_from_minio(bucket_name: str, file_path_in_bucket : str, file_destination_path: str) -> InternalResultPatern:
    """
    Télécharge un fichier depuis le bucket Minio et le stocke localement pour traitement
    Args:
        bucket_name: Le nom du bucket Minio
        file_path_in_bucket: Le chemin du fichier dans le bucket Minio
        file_destination_path: Le chemin local où stocker le fichier téléchargé pour traitement

    Returns:
        Le chemin local du fichier téléchargé
    """
    try:
        minio_client = MinioClientFactory.get_backend_client()

        minio_client.fget_object(bucket_name, file_path_in_bucket, file_destination_path)
        return True, file_destination_path
    except Exception as e:
        return False, f"Erreur ({e.__class__.__name__}) lors du téléchargement du fichier depuis le bucket Minio : {e}"

def get_file_metadata_from_minio(bucket_name: str, file_path_in_bucket : str) -> InternalResultPatern:
    try:
        minio_client = MinioClientFactory.get_backend_client()

        res = minio_client.stat_object(bucket_name, file_path_in_bucket)
        return True, res
    except Exception as e:
        return False, f"Erreur ({e.__class__.__name__}) lors du StatObject du fichier depuis le bucket Minio : {e}"

def upload_processed_file_to_bucket(bucket_name: str, file_path_in_bucket: str, file_local_path: str) -> InternalResultPatern:
    """
    Upload un fichier traité depuis le stockage local vers le bucket Minio
    Args:
        bucket_name: Le nom du bucket Minio
        file_path_in_bucket: Le chemin du fichier dans le bucket Minio où stocker le fichier traité
        file_local_path: Le chemin local du fichier traité à uploader

    Returns:
        Que dalle, c'est une fonction pour uploader un fichier traité vers le bucket Minio, le résultat de l'upload
        est que le fichier traité est stocké dans le bucket Minio à l'emplacement spécifié par file_path_in_bucket
    """
    try:
        minio_client = MinioClientFactory.get_backend_client()

        res = minio_client.fput_object(bucket_name, file_path_in_bucket, file_local_path)

        return True, res.object_name
    except Exception as e:
        return False, f"Erreur ({e.__class__.__name__}) lors de l'upload du fichier traité vers le bucket Minio : {e}"

def delete_file_from_bucket(bucket_name: str, file_path_in_bucket: str) -> InternalResultPatern:
    """Tout est dans le nom de la fonction"""
    try:
        minio_client = MinioClientFactory.get_backend_client()

        minio_client.remove_object(bucket_name, file_path_in_bucket)
        return True, None
    except Exception as e:
        return False, f"Erreur ({e.__class__.__name__}) lors de la suppression du fichier depuis le bucket Minio : {e}"

def process_video_file_with_ffmpeg(input_path: str, output_path: str) -> InternalResultPatern:
    """Tout est dans le nom"""
    try:
        # On force 720p (HD) pour économiser la bande passante internet du serveur et accélérer les temps de traitement,
        # tout en gardant une qualité correcte pour un post
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vcodec", "libx264", "-crf", "23",  # Bon compromis poids/qualité
            "-preset", "medium",
            "-acodec", "aac", "-b:a", "128k",
            "-vf", "scale='bitand(oh*dar,65534)':720",  # Redimensionne à 720p en gardant l'aspect ratio
            output_path
        ]

        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return True, output_path
    except subprocess.CalledProcessError as e:
        return False, f"Erreur FFMPEG stderr lors du traitement de la vidéo avec ffmpeg : {e.stderr}"
    except Exception as e:
        return False, f"Erreur ({e.__class__.__name__}) lors du traitement de la vidéo avec ffmpeg : {e}"

async def send_data_to_progress_stream(cache: VideoUploadsCache, user_id: str, intent_id: str, data: WsPostProcessingInfoSchema) -> None:
    """
    Envoie une mise à jour de progression du post-traitement de la vidéo dans le stream Redis dédié à cet effet
    Args:
        data: La donnée de progression à envoyer, contenant les informations sur l'étape actuelle du post-traitement,
        le pourcentage de progression, un timestamp, et éventuellement un message d'erreur en cas de problème

        user_id: Id de l'utilisateur à qui appartient l'intent d'upload video pour lequel on envoie la mise à jour de progression

        intent_id: Id de l'intent d'upload video

        cache: Le cache Redis pour accéder au stream de progression des uploads

    Returns:
        Que dalle, c'est une fonction pour envoyer une mise à jour de progression dans le stream Redis, le résultat de cette fonction
        est que la mise à jour de progression est ajoutée dans le stream Redis pour que le frontend puisse la récupérer et afficher l'avancée du post-traitement à l'utilisateur
    """
    await cache.add_upload_event_in_a_stream(user_id, intent_id, data, enum_compatible=True)



@shared_task(name=WorkersTaskNames.PROCESS_VIDEO)
def process_video_task(raw_bucket_name: str, raw_object_name: str, user_id: str, intent_id: str) -> None:
    """
    Tâche pour traiter un fichier video, Normalise une vidéo brute en MP4 standard (720p, H.264/AAC).
    Args:
        raw_bucket_name: Le bucket du fichier brut dans MinIo
        raw_object_name: Le fichier video dans MinIo
        user_id: L'id de l'utilisateur à qui appartient le fichier video à traiter, utilisé pour faire le lien entre le fichier traité et l'utilisateur
        intent_id: L'id de l'intent d'upload video associé à ce fichier,
         utilisé pour faire le lien entre le fichier traité et l'intent d'upload qui a été créé pour ce fichier

    Returns:
        Que dalle, c'est une tâche pour traiter une vidéo, le résultat du traitement (la vidéo normalisée)
        est uploadé dans le bucket Minio et lié à l'intent d'upload video grâce à l'id de l'intent fourni en argument
    """
    raw_object = get_file_metadata_from_minio(raw_bucket_name, raw_object_name)

    if not raw_object[0]:
        logger.error(raw_object[1])
        return
    raw_object = raw_object[1]

    local_raw_path = f"/tmp/{uuid4()}_raw"
    local_processed_path = f"/tmp/{uuid4()}_processed.mp4"
    final_bucket_object_key = BucketFilesUtils.generate_object_name_for_processed_video(intent_id, raw_object.object_name)
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

    def error_update_progress():
        nonlocal progression
        update_progress(progression.step, 0, Messages.INTERNAL_SERVER_ERROR)

    # TODO: Ajouter la logique Redis Stream
    try:
        update_progress(WsPostProcessingInfoSchemaSteps.VERIFICATION, 10)

        down_res = download_file_from_minio(raw_object.bucket_name, raw_object.object_name, local_raw_path)

        if not down_res[0]:
            logger.error(down_res[1])
            error_update_progress()
            return

        update_progress(WsPostProcessingInfoSchemaSteps.PROCESSING, 10)

        if not verify_file_is_video(local_raw_path)[0]:
            logger.error(f"Le fichier {raw_object.object_name} n'est pas une vidéo valide")
            error_update_progress()
            return

        update_progress(WsPostProcessingInfoSchemaSteps.COMPRESSING, 10)

        video_processed = process_video_file_with_ffmpeg(input_path=local_raw_path, output_path=local_processed_path)

        if not video_processed[0]:
            logger.error(video_processed[1])
            error_update_progress()
            return

        update_progress(WsPostProcessingInfoSchemaSteps.CREATING, 40)

        upload_res = upload_processed_file_to_bucket(
            bucket_name=BucketName.POSTS_PERMANENT_CONTENT.value,
            file_path_in_bucket=local_processed_path,
            file_local_path=local_processed_path
        )


        if not upload_res[0]:
            logger.error(upload_res[1])
            error_update_progress()
            return

        update_progress(WsPostProcessingInfoSchemaSteps.CREATING, 10)


        del_result = delete_file_from_bucket(raw_object.bucket_name, raw_object.object_name)

        if not del_result[0]:
            pass

        # TODO: Ajouter la logique ajout bd et cache Redis pour marquer l'intent d'upload video
        #  comme traité et stocker les infos de la vidéo traitée (url dans le bucket Minio,
        #  métadonnées, etc.) pour que le frontend puisse les récupérer et afficher le post vidéo traité
        #  à l'utilisateur
    except Exception as e:
        logger.exception(f"Exception {e.__class__.__name__} inattendue lors du traitement de la vidéo : {e}", exc_info=e)
        error_update_progress()
    finally:
        #TODO: Marquer la tache comme processed dans le cache et supprimer tout ce qui va avec
        task_async_loop_manager.run_async(redis_cache.close())
        if os.path.exists(local_raw_path):
            os.remove(local_raw_path)
        if os.path.exists(local_processed_path):
            os.remove(local_processed_path)




