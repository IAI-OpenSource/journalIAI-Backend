import os
import subprocess
from typing import Any
from uuid import uuid4

from celery import shared_task
from minio.datatypes import Object

from app.storage.bucket_files_utils import BucketFilesUtils
from app.storage.minio_client import MinioClientFactory
from app.storage.minio_config import BucketName
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.workers_task_names import WorkersTaskNames
import magic

# TODO: Remplacer tous les retours de fonctions en tuple ResultPattern
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

def download_file_from_bucket(bucket_name: str, file_path_in_bucket : str, file_destination_path: str) -> InternalResultPatern:
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
            "-acodec", "aac", "-ba", "128k",
            "-vf", "scale=-2:720",  # Redimensionne à 720p en gardant l'aspect ratio
            output_path
        ]

        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return True, output_path
    except Exception as e:
        return False, f"Erreur ({e.__class__.__name__}) lors du traitement de la vidéo avec ffmpeg : {e}"

@shared_task(name=WorkersTaskNames.PROCESS_VIDEO)
def process_video_task(raw_object: Object, intent_id: str) -> None:
    """
    Tâche pour traiter un fichier video, Normalise une vidéo brute en MP4 standard (720p, H.264/AAC).
    Args:
        raw_object: Le fichier video dans MinIo
        intent_id: L'id de l'intent d'upload video associé à ce fichier,
         utilisé pour faire le lien entre le fichier traité et l'intent d'upload qui a été créé pour ce fichier

    Returns:
        Que dalle, c'est une tâche pour traiter une vidéo, le résultat du traitement (la vidéo normalisée)
        est uploadé dans le bucket Minio et lié à l'intent d'upload video grâce à l'id de l'intent fourni en argument
    """
    local_raw_path = f"/tmp/{uuid4()}_raw"
    local_processed_path = f"/tmp/{uuid4()}_processed.mp4"
    final_bucket_object_key = BucketFilesUtils.generate_object_name_for_processed_video(intent_id, raw_object.object_name)
    # TODO: Ajouter la logique Redis Stream
    try:
        down_res = download_file_from_bucket(raw_object.bucket_name, raw_object.object_name, local_raw_path)

        if not down_res[0]:
            return

        if not verify_file_is_video(local_raw_path)[0]:
            return

        video_processed = process_video_file_with_ffmpeg(input_path=local_raw_path, output_path=local_processed_path)

        if not video_processed[0]:
            return

        upload_res = upload_processed_file_to_bucket(
            bucket_name=BucketName.POSTS_PERMANENT_CONTENT.value,
            file_path_in_bucket=local_processed_path,
            file_local_path=local_processed_path
        )

        if not upload_res[0]:
            return

        del_result = delete_file_from_bucket(raw_object.bucket_name, raw_object.object_name)

        if not del_result[0]:
            pass



        # TODO: Ajouter la logique ajout bd et cache Redis pour marquer l'intent d'upload video
        #  comme traité et stocker les infos de la vidéo traitée (url dans le bucket Minio,
        #  métadonnées, etc.) pour que le frontend puisse les récupérer et afficher le post vidéo traité
        #  à l'utilisateur
    except Exception as e:
        pass
    finally:
        if os.path.exists(local_raw_path):
            os.remove(local_raw_path)
        if os.path.exists(local_processed_path):
            os.remove(local_processed_path)



