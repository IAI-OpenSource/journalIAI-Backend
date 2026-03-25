import asyncio
import concurrent.futures
import json
import os
import shutil
import subprocess
from logging import getLogger
from pathlib import Path
from time import time
from typing import Any, TypeVar
from uuid import uuid4

from celery import shared_task
from minio.datatypes import Object

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

T = TypeVar("T")
InternalResultPatern  = tuple[bool, T | str]  # (success, data) ou (success, error_message)

# TODO: refactor tout ce spaghethi après

def verify_file_is_video(file_path : str) -> InternalResultPatern[None]:
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
        return False, f"Le fichier n'est pas une vidéo valide, type MIME détecté : {buffer_type}, veuillez envoyer un fichier vidéo valide"

def download_file_from_minio(bucket_name: str, file_path_in_bucket : str, file_destination_path: str) -> InternalResultPatern[str]:
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

def get_file_metadata_from_minio(bucket_name: str, file_path_in_bucket : str) -> InternalResultPatern[Object]:
    try:
        minio_client = MinioClientFactory.get_backend_client()

        res = minio_client.stat_object(bucket_name, file_path_in_bucket)
        return True, res
    except Exception as e:
        return False, f"Erreur ({e.__class__.__name__}) lors du StatObject du fichier depuis le bucket Minio : {e}"

def upload_processed_file_to_bucket(bucket_name: str, file_path_in_bucket: str, file_local_path: str) -> InternalResultPatern[str]:
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

def delete_file_from_bucket(bucket_name: str, file_path_in_bucket: str) -> InternalResultPatern[None]:
    """Tout est dans le nom de la fonction"""
    try:
        minio_client = MinioClientFactory.get_backend_client()

        minio_client.remove_object(bucket_name, file_path_in_bucket)
        return True, None
    except Exception as e:
        return False, f"Erreur ({e.__class__.__name__}) lors de la suppression du fichier depuis le bucket Minio : {e}"

def process_video_file_with_ffmpeg(ffmpeg_cmd: list[str]) -> InternalResultPatern[None]:
    """Tout est dans le nom"""
    try:
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return True, None
    except subprocess.CalledProcessError as e:
        return False, f"Erreur FFMPEG stderr lors du traitement de la vidéo avec ffmpeg : {e.stderr}"
    except Exception as e:
        return False, f"Erreur ({e.__class__.__name__}) lors du traitement de la vidéo avec ffmpeg : {e}"


def get_video_metadata(local_path: str) -> InternalResultPatern[dict[str, Any]]:
    """Récupère la résolution et le bitrate de la vidéo source via ffprobe."""

    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-show_format", local_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        video_stream = next(s for s in data['streams'] if s['codec_type'] == 'video')
        to_return = {
            "width": int(video_stream['width']),
            "height": int(video_stream['height']),
            "bitrate": int(data['format'].get('bit_rate', 0))
        }
        return True, to_return
    except subprocess.CalledProcessError as e:
        return False, f"Erreur FFPROBE stderr lors de l'obtention des qualités de la vidéo avec ffprobe : {e.stderr}"
    except Exception as e:
        return False, f"Erreur ({e.__class__.__name__}) lors de l'obtention des qualités de la vidéo avec ffprobe : {e}"


def get_target_qualities(height: int) -> list[dict]:
    """Retourne la liste des paliers HLS à générer selon la source."""
    all_qualities = [
        {"name": "360p", "height": 360, "vrate": "800k", "crf": 28},
        {"name": "480p", "height": 480, "vrate": "1400k", "crf": 26},
        {"name": "720p", "height": 720, "vrate": "2800k", "crf": 23},
        {"name": "1080p", "height": 1080, "vrate": "5000k", "crf": 20},
    ]

    # On ne garde que les qualités inférieures ou égales à la source
    to_return = [q for q in all_qualities if q['height'] <= height]

    # On prends seulement les deux meilleurs qualités parce que c'est comme çà, c'est moi qui décide
    # to_return = to_return[-2:]

    # Finalementy on prend une seule qualité
    to_return = to_return[-1:]

    # On retourne la qualité la plus basse au cas ou y'a 0 match
    return to_return or all_qualities[0]


def generate_hls_command(local_raw_path: str, output_dir: str, qualities: list) -> list[str]:
    """Construit la commande FFmpeg pour fMP4 (m4s) avec dossiers par résolution."""

    if isinstance(qualities, str):
        qualities = json.loads(qualities)

    nb_hls = len(qualities)
    nb_total = nb_hls + 1

    # 1. Construction des filtres vidéo
    split_labels = "".join([f"[v_split_{i}]" for i in range(nb_total)])
    filters = [f"[0:v]split={nb_total}{split_labels}"]

    for i, q in enumerate(qualities):
        filters.append(f"[v_split_{i}]scale=w=-2:h={q['height']}[v{i}out]")
        # On crée des dossiers explicites (ex: v720p)
        os.makedirs(os.path.join(output_dir, q['name']), exist_ok=True)

    filters.append(f"[v_split_{nb_hls}]scale=w=-2:h=720[v_mp4]")

    # 2. Base de la commande avec source audio de secours
    cmd = [
        "ffmpeg", "-y",
        "-i", local_raw_path,
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-filter_complex", ";".join(filters)
    ]

    # 3. Sortie MP4 Download (Standard MP4 pour compatibilité max)
    cmd.extend([
        "-map", "[v_mp4]", "-map", "0:a?", "-map", "1:a",
        "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "128k", "-shortest",
        f"{output_dir}/download_720p.mp4"
    ])

    # 4. Sorties HLS (Définition des codecs et bitrates)
    for i, q in enumerate(qualities):
        cmd.extend([
            "-map", f"[v{i}out]", "-map", "0:a?", "-map", "1:a",
            f"-c:v:{i}", "libx264", "-preset", "veryfast",
            "-crf", str(q['crf']), f"-b:v:{i}", q['vrate'],
            f"-c:a:{i}", "aac", f"-b:a:{i}", "128k"
        ])

    # 5. Configuration HLS + m4s (fMP4)
    # On définit le var_stream_map avec des noms personnalisés (ex: name:720p)
    # La syntaxe "name:XYZ" définit le nom du dossier et du fichier m3u8
    var_map_list = []
    for i, q in enumerate(qualities):
        var_map_list.append(f"v:{i},a:{i},name:{q['name']}")

    var_map = " ".join(var_map_list)

    cmd.extend([
        "-f", "hls",
        "-hls_time", "6",
        "-hls_playlist_type", "vod",
        "-hls_segment_type", "fmp4",  # <--- PASSAGE EN m4s
        "-master_pl_name", "master.m3u8",
        "-var_stream_map", var_map,
        # Chemin : dossier_qualité/segment_numéro.m4s
        "-hls_segment_filename", f"{output_dir}/%v/seg_%d.m4s",
        "-shortest",
        f"{output_dir}/%v/index.m3u8"
    ])

    return cmd


async def upload_hls_to_minio(local_dir: str, remote_path: str) -> InternalResultPatern[None]:
    """Upload le dossier HLS (fMP4) complet en parallèle vers MinIO."""
    try:
        if not os.path.exists(local_dir) or not os.listdir(local_dir):
            return False, "Le dossier local est vide ou inexistant. FFmpeg a probablement échoué."

        files = []
        for p in Path(local_dir).rglob('*'):
            if p.is_file():
                # 1. Détermination du Content-Type (Crucial pour m4s)
                if p.suffix == ".m3u8":
                    content_type = "application/x-mpegURL"
                elif p.suffix == ".m4s":
                    content_type = "video/iso.segment"
                elif p.suffix == ".mp4":
                    content_type = "video/mp4"  # Gère init.mp4 et download_720p.mp4
                else:
                    content_type = "application/octet-stream"

                rel_path = p.relative_to(local_dir)
                # On prépare (Source locale, Destination distante, Type MIME)
                files.append((str(p), f"{remote_path}/{rel_path}", content_type))

        minio_client = MinioClientFactory.get_backend_client()

        # 2. Utilisation de l'executor pour les appels bloquants de minio-py
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            tasks = [
                task_async_loop_manager.get_loop().run_in_executor(
                    executor,
                    minio_client.fput_object,
                    BucketName.POSTS_PERMANENT_CONTENT.value,
                    r_path,  # Destination dans le bucket
                    l_path,  # Fichier source sur le disque
                    cont_type
                )
                for l_path, r_path, cont_type in files
            ]
            await asyncio.gather(*tasks)

        return True, None

    except Exception as err:
        return False, f"Erreur ({err.__class__.__name__}) lors de l'upload du dossier HLS vers le bucket Minio : {err}"
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
    await cache.add_upload_event_in_a_stream(user_id, intent_id, data)



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
    local_processed_dir = f"/tmp/{uuid4()}_processed_files"
    os.makedirs(local_processed_dir, exist_ok=True)
    final_bucket_objects_path = BucketFilesUtils.generate_objects_path_for_processed_video(intent_id)
    redis_cache = cache_manager.get_redis_connection_from_pool()
    upload_cache = VideoUploadsCache(redis_cache)
    task_async_loop_manager.run_async(upload_cache.delete_video_upload_intent(user_id, intent_id))
    global_progress_pourcentage = 0
    has_successfully_processed = False
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

    # TODO: Ajouter la logique Redis Stream
    try:
        update_progress(WsPostProcessingInfoSchemaSteps.VERIFICATION, 10)

        down_res = download_file_from_minio(raw_object.bucket_name, raw_object.object_name, local_raw_path)

        if not down_res[0]:
            logger.error(down_res[1])
            error_update_progress()
            return

        update_progress(WsPostProcessingInfoSchemaSteps.PROCESSING, 10)

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
        )

        video_processed = process_video_file_with_ffmpeg(process_command)

        if not video_processed[0]:
            logger.error(video_processed[1])
            error_update_progress()
            return

        update_progress(WsPostProcessingInfoSchemaSteps.CREATING, 40)

        upload_res = task_async_loop_manager.run_async(upload_hls_to_minio(local_processed_dir, final_bucket_objects_path))

        if not upload_res[0]:
            logger.error(upload_res[1])
            error_update_progress()
            return

        update_progress(WsPostProcessingInfoSchemaSteps.COMPLETED, 10)

        has_successfully_processed = True

        # TODO: Ajouter la logique ajout bd et cache Redis pour marquer l'intent d'upload video
        #  comme traité et stocker les infos de la vidéo traitée (url dans le bucket Minio,
        #  métadonnées, etc.) pour que le frontend puisse les récupérer et afficher le post vidéo traité
        #  à l'utilisateur
    except Exception as e:
        logger.exception(f"Exception {e.__class__.__name__} inattendue lors du traitement de la vidéo : {e}", exc_info=e)
        error_update_progress()
    finally:
        #TODO: Marquer la tache comme processed dans le cache et supprimer tout ce qui va avec
        if has_successfully_processed:
            delete_file_from_bucket(raw_object.bucket_name, raw_object.object_name)

        task_async_loop_manager.run_async(redis_cache.close())
        if os.path.exists(local_raw_path):
            os.remove(local_raw_path)
        if os.path.exists(local_processed_dir):
            shutil.rmtree(local_processed_dir)


