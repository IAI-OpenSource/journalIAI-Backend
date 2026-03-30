import asyncio
import concurrent.futures
import json
import os
import subprocess
from logging import getLogger
from pathlib import Path
from typing import Any, Optional

from app.globals.messages import Messages
from app.globals.others_constants import OtherConstants
from app.storage.minio_client import MinioClientFactory
from app.storage.minio_config import BucketName
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.tasks_utils.base import ProcessingResult

logger = getLogger(__name__)

def process_video_file_with_ffmpeg(ffmpeg_cmd: list[str]) -> ProcessingResult:
    """
    Exécute une commande FFmpeg pour traiter une vidéo.
    
    Args:
        ffmpeg_cmd: Commande FFmpeg à exécuter (liste d'arguments).
        
    Returns:
        ProcessingResult(True) en succès, ProcessingResult(False, error) sinon.
    """
    try:
        subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return ProcessingResult.ok_response(None)
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur FFMPEG lors du traitement de la vidéo: {e.stderr}")
        return ProcessingResult.error_response(Messages.INTERNAL_SERVER_ERROR)
    except Exception as e:
        error_msg = f"Erreur ({e.__class__.__name__}) lors du traitement FFMPEG: {e}"
        logger.error(error_msg)
        return ProcessingResult.error_response(Messages.INTERNAL_SERVER_ERROR)


def get_video_metadata(local_path: str) -> ProcessingResult[dict[str, Any]]:
    """
    Récupère les métadonnées d'une vidéo via ffprobe.
    
    Extrait la résolution, la durée, le bitrate et la présence d'audio.
    
    Args:
        local_path: Chemin local du fichier vidéo.
        
    Returns:
        ProcessingResult avec dict contenant width, height, bitrate, duration, has_audio.
    """
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

        metadata = {
            "width": int(video_stream['width']),
            "height": int(video_stream['height']),
            "bitrate": int(data['format'].get('bit_rate', 0)),
            "duration": duration,
            "has_audio": has_audio
        }

        return ProcessingResult.ok_response(metadata)
    except (StopIteration, KeyError) as e:
        logger.error(f"Format vidéo invalide: {e}")
        return ProcessingResult.error_response("Impossible de trouver un flux vidéo valide dans le fichier, fichier vidéo Invalide")
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur FFPROBE: {e.stderr}")
        return ProcessingResult.error_response("Erreur lors de l'extraction des métadonnées vidéo, fichier vidéo Invalide")
    except Exception as e:
        logger.exception(f"Erreur lors de l'extraction des métadonnées vidéo: {e}")
        return ProcessingResult.error_response(
            f"Erreur lors de l'extraction des métadonnées vidéo, , fichier vidéo Invalide"
        )


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
        "-threads", "2",                                        # 2 threads
        "-c:a", "aac", "-b:a", "128k", "-shortest",
        f"{output_dir}/{OtherConstants.HLS_DOWNLOAD_FILE_NAME}"
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
        "-f", "hls", "-hls_time", str(OtherConstants.HLS_SEGMENTS_DURATION), "-hls_playlist_type", "vod",
        "-hls_segment_type", "fmp4", "-master_pl_name", OtherConstants.HLS_PLAYLIST_MASTER_NAME,
        "-var_stream_map", var_map,
        "-hls_segment_filename", f"{output_dir}/%v/seg_%d.m4s",
        "-shortest",
        f"{output_dir}/%v/index.m3u8"
    ])

    return cmd


async def upload_hls_to_minio(local_dir: str, remote_path: str) -> ProcessingResult[None]:
    """
    Upload le dossier HLS (fMP4) complet en parallèle vers MinIO.
    
    Args:
        local_dir: Répertoire local contenant les fichiers HLS.
        remote_path: Chemin de base dans MinIO pour les uploads.
        
    Returns:
        ProcessingResult(True) en succès, ProcessingResult(False, error) sinon.
    """
    try:
        if not os.path.exists(local_dir) or not os.listdir(local_dir):
            return ProcessingResult.error_response(
                "Le dossier local est vide ou inexistant. FFmpeg a probablement échoué.")

        files = []
        for p in Path(local_dir).rglob('*'):
            if p.is_file():
                # Détermination du Content-Type (Crucial pour m4s)
                if p.suffix == ".m3u8":
                    content_type = "application/x-mpegURL"
                elif p.suffix == ".m4s":
                    content_type = "video/iso.segment"
                elif p.suffix == ".mp4":
                    content_type = "video/mp4"
                elif p.suffix == ".webp":
                    continue        # Sautes mouton, je geres çà séparemment
                else:
                    content_type = "application/octet-stream"

                rel_path = p.relative_to(local_dir)
                files.append((str(p), f"{remote_path}/{rel_path}", content_type))

        minio_client = MinioClientFactory.get_backend_client()

        # Upload en parallèle avec un executor
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            tasks = [
                task_async_loop_manager.get_loop().run_in_executor(
                    executor,
                    minio_client.fput_object,
                    BucketName.POSTS_PERMANENT_CONTENT.value,
                    r_path,
                    l_path,
                    cont_type
                )
                for l_path, r_path, cont_type in files
            ]
            await asyncio.gather(*tasks)

        return ProcessingResult.ok_response(None)

    except Exception as err:
        error_msg = f"Erreur ({err.__class__.__name__}) lors de l'upload HLS vers MinIO: {err}"
        logger.exception(error_msg)
        return ProcessingResult.error_response(Messages.INTERNAL_SERVER_ERROR)



