import asyncio
import concurrent.futures
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Optional, TypeVar
from uuid import UUID

import magic
from minio.datatypes import Object

from app.cache.helpers.base import CacheWrapper
from app.cache.uploads_cache import MediaUploadsCache
from app.db.models.enums import PostType, MediaType
from app.db.models.post import Post
from app.db.models.post_media import PostMedia
from app.db.session import AsyncSessionLocal
from app.schemas.post_upload_schemas import WsPostProcessingInfoSchema, CreateMediaUploadIntentFullData

from app.storage.minio_client import MinioClientFactory
from app.storage.minio_config import BucketName
from app.worker.tasks.async_loop_manager import task_async_loop_manager

T = TypeVar("T")
InternalResultPatern  = tuple[bool, T | str]  # (success, data) ou (success, error_message)


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


def upload_processed_file_to_bucket(
        bucket_name: str, file_path_in_bucket: str, file_local_path: str, c_type: str
) -> InternalResultPatern[str]:
    """
    Upload un fichier traité depuis le stockage local vers le bucket Minio
    Args:
        bucket_name: Le nom du bucket Minio
        file_path_in_bucket: Le chemin du fichier dans le bucket Minio où stocker le fichier traité
        file_local_path: Le chemin local du fichier traité à uploader
        c_type: Le content_type du fichier à upload

    Returns:
        Que dalle, c'est une fonction pour uploader un fichier traité vers le bucket Minio, le résultat de l'upload
        est que le fichier traité est stocké dans le bucket Minio à l'emplacement spécifié par file_path_in_bucket
    """
    try:
        minio_client = MinioClientFactory.get_backend_client()

        res = minio_client.fput_object(bucket_name, file_path_in_bucket, file_local_path, content_type=c_type)

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

        # Extraction du flux vidéo
        video_stream = next(s for s in data['streams'] if s['codec_type'] == 'video')

        # Vérification de la présence d'un flux audio
        has_audio = any(s for s in data['streams'] if s['codec_type'] == 'audio')

        # La durée peut être dans format ou dans le stream (on prend format par sécurité)
        duration = float(data['format'].get('duration', 0))

        to_return = {
            "width": int(video_stream['width']),
            "height": int(video_stream['height']),
            "bitrate": int(data['format'].get('bit_rate', 0)),
            "duration": duration,
            "has_audio": has_audio
        }

        return True, to_return
    except (StopIteration, KeyError):
        return False, "Impossible de trouver un flux vidéo valide dans le fichier."
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


def generate_thumbnail(local_raw_path: str, output_dir: str, ss_time: int) -> Optional[str]:
    """Génère une miniature WebP optimisée à partir de la vidéo."""

    thumbnail_path = os.path.join(output_dir, "thumbnail.webp")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(ss_time),
        "-i", local_raw_path,
        # On retire 'format=webp' d'ici
        "-vf", "scale=w=1280:h=720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
        "-vframes", "1",
        "-c:v", "libwebp",  # On spécifie explicitement le codec WebP
        "-lossless", "0",  # 0 pour compression avec perte (plus léger)
        "-compression_level", "4",
        "-q:v", "75",
        thumbnail_path
    ]

    try:
        # Exécution synchrone (c'est rapide, quelques millisecondes)
        subprocess.run(cmd, capture_output=True, check=True)
        return thumbnail_path
    except subprocess.CalledProcessError as e:
        print(f"Erreur FFMPEG stderr lors de la génération du thumbnail mais on continue : {e.stderr}")


def generate_hls_command(local_raw_path: str, output_dir: str, qualities: list, has_audio: bool = True) -> list[str]:
    """Construit la commande FFmpeg fMP4 avec dossiers nommés et gestion audio intelligente."""

    if isinstance(qualities, str):
        qualities = json.loads(qualities)

    nb_hls = len(qualities)
    nb_total = nb_hls + 1

    # 1. Filtres vidéo (inchangés)
    split_labels = "".join([f"[v_split_{i}]" for i in range(nb_total)])
    filters = [f"[0:v]split={nb_total}{split_labels}"]
    for i, q in enumerate(qualities):
        filters.append(f"[v_split_{i}]scale=w=-2:h={q['height']}[v{i}out]")
        os.makedirs(os.path.join(output_dir, q['name']), exist_ok=True)
    filters.append(f"[v_split_{nb_hls}]scale=w=-2:h=720[v_mp4]")

    # 2. Construction de la base de la commande
    cmd = ["ffmpeg", "-y", "-i", local_raw_path]

    # OPTIMISATION : On n'ajoute la source lavfi que si on n'a pas d'audio
    if not has_audio:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])

    cmd.extend(["-filter_complex", ";".join(filters)])

    # 3. Définition du mapping audio selon la disponibilité
    # Si audio présent : on mappe la piste de l'input 0
    # Si audio absent : on mappe la piste de l'input 1 (le silence qu'on vient d'ajouter)
    audio_map = "0:a" if has_audio else "1:a"

    # 4. Sortie MP4 Download
    cmd.extend([
        "-map", "[v_mp4]", "-map", audio_map,
        "-c:v", "libx264", "-crf", "23", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "128k", "-shortest",
        f"{output_dir}/download_720p.mp4"
    ])

    # 5. Sorties HLS
    for i, q in enumerate(qualities):
        cmd.extend([
            "-map", f"[v{i}out]", "-map", audio_map,
            f"-c:v:{i}", "libx264", "-preset", "veryfast",
            "-crf", str(q['crf']), f"-b:v:{i}", q['vrate'],
            f"-c:a:{i}", "aac", f"-b:a:{i}", "128k"
        ])

    # 6. Configuration HLS + m4s
    var_map = " ".join([f"v:{i},a:{i},name:{q['name']}" for i, q in enumerate(qualities)])

    cmd.extend([
        "-f", "hls", "-hls_time", "6", "-hls_playlist_type", "vod",
        "-hls_segment_type", "fmp4", "-master_pl_name", "master.m3u8",
        "-var_stream_map", var_map,
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
                elif p.suffix == ".webp":
                    continue        # Sautes mouton, je geres çà séparemment
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


async def send_data_to_progress_stream(cache: MediaUploadsCache, user_id: str, intent_id: str, data: WsPostProcessingInfoSchema) -> None:
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


async def add_processed_things_in_db(
    cache: CacheWrapper, user_id: str, post_data: CreateMediaUploadIntentFullData, minio_video_url: str,
    minio_thumnail_url: str, file_size: int, duration: int, w: int, h:int
) -> InternalResultPatern[str]:
    """Enregistre le post et la video en bd"""
    from app.services.media_upload_service import MediaUploadsService

    async with AsyncSessionLocal() as session:
        service = MediaUploadsService(cache, session)

        definitive_post = Post(
            author_id=UUID(user_id),
            event_id=post_data.event_id,
            club_id=post_data.club_id,
            academic_year_id=post_data.academic_year_id,
            target_classe_id=post_data.classe_id,
            content=post_data.content
        )

        definitive_post.post_type = PostType.VIDEO


        definitive_post_media = PostMedia(
            post_id=definitive_post.id,
            media_type=MediaType.VIDEO,
            media_url=minio_video_url,
            thumbnail_url=minio_thumnail_url,
            file_size=file_size,
            duration=duration,
            width=w,
            height=h,
        )

        definitive_post_media.is_processed = True

        res = await service.worker_service_save_processed_video_post_in_bd(definitive_post, definitive_post_media)
        if res.is_error():
            return False, res.error

        return True, res.data
