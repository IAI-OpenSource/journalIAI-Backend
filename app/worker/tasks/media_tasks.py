## Tâche Celery pour le traitement des médias images après upload MinIO.
## Convertit JPG/JPEG → WebP, génère un thumbnail WebP,
## déplace raw → permanent, met à jour PostMedia en base.

import logging
import os
import subprocess
import tempfile
from uuid import UUID

from celery import shared_task

from app.db.models.enums import MediaType
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.workers_task_names import WorkersTaskNames

logger = logging.getLogger(__name__)

# Qualité WebP (0-100). 82 = bon compromis taille/qualité
WEBP_QUALITY = 82
# Dimensions max du thumbnail (largeur × hauteur)
THUMBNAIL_WIDTH = 400
THUMBNAIL_HEIGHT = 400


@shared_task(
    name=WorkersTaskNames.PROCESS_MEDIA,
    # Retry automatique 3 fois si le worker plante (réseau MinIO, ffmpeg absent…)
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,         # délai exponentiel entre les retries
    retry_backoff_max=60,
)
def task_process_media(
    media_id: str,
    post_id: str,
    raw_key: str,
    media_type: str,
) -> None:
    """Convertit une image uploadée en WebP + thumbnail WebP.

    Flow :
    1. Télécharge le fichier brut depuis posts-raw-uploads
    2. Convertit en WebP avec FFmpeg (qualité configurable)
    3. Génère un thumbnail WebP (400×400 max, sans déformation)
    4. Upload WebP + thumbnail dans posts-permanent-content
    5. Déplace la référence raw → permanent dans MinIO
    6. Met à jour PostMedia en base (thumbnail_url, is_processed=True)

    Args:
        media_id: UUID du PostMedia à mettre à jour en base.
        post_id: UUID du post parent (pour construire la clé permanente).
        raw_key: Clé objet dans posts-raw-uploads.
        media_type: Valeur de l'enum MediaType (ex: "IMAGE").
    """
    task_async_loop_manager.run_async(
        _async_process_media(
            media_id=UUID(media_id),
            post_id=UUID(post_id),
            raw_key=raw_key,
            media_type=MediaType(media_type),
        )
    )


async def _async_process_media(
    media_id: UUID,
    post_id: UUID,
    raw_key: str,
    media_type: MediaType,
) -> None:
    """Coroutine principale du traitement — exécutée via AsyncLoopManager."""

    #from app.storage.post_storage_repository import PostStorageRepository
    #storage = PostStorageRepository()
    from app.storage.minio_config import BucketName
    from app.repositories.post_repository import PostRepository
    from app.db.session import get_db  # context manager async session

    # Répertoire temporaire local pour les fichiers intermédiaires
    # Tout sera nettoyé automatiquement à la fin du bloc with
    with tempfile.TemporaryDirectory() as tmp_dir:

        raw_local_path = os.path.join(tmp_dir, "raw_input")
        webp_local_path = os.path.join(tmp_dir, "output.webp")
        thumb_local_path = os.path.join(tmp_dir, "thumbnail.webp")

        # ----------------------------------------------------------
        # 1. Téléchargement du fichier brut depuis MinIO
        # ----------------------------------------------------------
        from minio.commonconfig import CopySource
        from app.storage.minio_client import MinioClientFactory

        private_client = MinioClientFactory.get_backend_client()

        logger.info("Téléchargement raw_key=%s", raw_key)
        private_client.fget_object(
            BucketName.POSTS_RAW_UPLOADS.value,
            raw_key,
            raw_local_path,
        )

        # 2. Conversion en WebP avec FFmpeg
        logger.info("Conversion WebP media_id=%s", media_id)
        _convert_to_webp(
            input_path=raw_local_path,
            output_path=webp_local_path,
            quality=WEBP_QUALITY,
        )

        # 3. Génération du thumbnail WebP
        logger.info("Génération thumbnail media_id=%s", media_id)
        _generate_thumbnail(
            input_path=raw_local_path,
            output_path=thumb_local_path,
            max_width=THUMBNAIL_WIDTH,
            max_height=THUMBNAIL_HEIGHT,
        )

        # 4. Upload WebP + thumbnail dans posts-permanent-content
        from datetime import date

        date_prefix = date.today().strftime("%Y/%m")
        base_key = f"images/{date_prefix}/{post_id}/{media_id}"
        webp_permanent_key = f"{base_key}.webp"
        thumb_permanent_key = f"{base_key}_thumb.webp"

        logger.info("Upload WebP permanent key=%s", webp_permanent_key)
        private_client.fput_object(
            BucketName.POSTS_PERMANENT_CONTENT.value,
            webp_permanent_key,
            webp_local_path,
            content_type="image/webp",
        )

        logger.info("Upload thumbnail key=%s", thumb_permanent_key)
        private_client.fput_object(
            BucketName.POSTS_PERMANENT_CONTENT.value,
            thumb_permanent_key,
            thumb_local_path,
            content_type="image/webp",
        )

        # ----------------------------------------------------------
        # 5. Suppression du fichier brut dans posts-raw-uploads
        #    (le lifecycle de 7j le ferait aussi, mais on libère
        #    l'espace immédiatement après traitement réussi)
        # ----------------------------------------------------------
        private_client.remove_object(
            BucketName.POSTS_RAW_UPLOADS.value,
            raw_key,
        )
        logger.info("Fichier brut supprimé raw_key=%s", raw_key)

    # ----------------------------------------------------------
    # 6. Mise à jour PostMedia en base
    #    (hors du with tmp_dir : les fichiers locaux sont déjà supprimés)
    # ----------------------------------------------------------
    async with get_db() as db:
        repo = PostRepository(db)
        result = await repo.mark_media_as_processed(
            media_id=media_id,
            thumbnail_url=thumb_permanent_key,
        )

        if result.is_error():
            logger.error(
                "Erreur mise à jour PostMedia media_id=%s : %s",
                media_id,
                result.error,
            )
            # On lève une exception pour déclencher le retry Celery
            raise RuntimeError(
                f"Impossible de marquer media_id={media_id} comme traité : {result.error}"
            )

    logger.info(
        "Traitement terminé avec succès media_id=%s webp=%s thumb=%s",
        media_id,
        webp_permanent_key,
        thumb_permanent_key,
    )


# ------------------------------------------------------------------
# Helpers FFmpeg (appels subprocess)
# ------------------------------------------------------------------

def _convert_to_webp(input_path: str, output_path: str, quality: int) -> None:
    """Convertit une image JPG/JPEG/PNG en WebP via FFmpeg.

    Utilise le codec libwebp. Le filtre scale=-1:-1 préserve les
    proportions d'origine sans redimensionner.

    Args:
        input_path: Chemin local du fichier source.
        output_path: Chemin local de destination .webp.
        quality: Qualité WebP 0-100.

    Raises:
        RuntimeError: Si FFmpeg retourne un code d'erreur non nul.
    """
    cmd = [
        "ffmpeg",
        "-y",                        # écraser sans confirmation
        "-i", input_path,            # fichier source
        "-c:v", "libwebp",           # codec WebP
        "-quality", str(quality),    # qualité
        "-vf", "scale=-1:-1",        # préserve les proportions
        output_path,
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,                 # timeout 2 min max
    )

    if result.returncode != 0:
        error_output = result.stderr.decode("utf-8", errors="replace")
        logger.error("FFmpeg conversion échouée : %s", error_output)
        raise RuntimeError(f"FFmpeg conversion échouée : {error_output[:300]}")


def _generate_thumbnail(
    input_path: str,
    output_path: str,
    max_width: int,
    max_height: int,
) -> None:
    """Génère un thumbnail WebP sans déformation (letterbox-free).

    Utilise le filtre scale FFmpeg avec force_original_aspect_ratio=decrease
    puis pad pour obtenir exactement max_width×max_height si nécessaire.
    En pratique on utilise juste le scale avec contain pour garder
    les proportions — pas de bandes noires.

    Args:
        input_path: Chemin local du fichier source.
        output_path: Chemin local du thumbnail .webp généré.
        max_width: Largeur maximale du thumbnail.
        max_height: Hauteur maximale du thumbnail.

    Raises:
        RuntimeError: Si FFmpeg retourne un code d'erreur non nul.
    """
    # scale avec force_original_aspect_ratio=decrease :
    # réduit l'image pour qu'elle tienne dans max_width×max_height
    # sans jamais l'agrandir ni la déformer
    scale_filter = (
        f"scale={max_width}:{max_height}:"
        f"force_original_aspect_ratio=decrease"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-c:v", "libwebp",
        "-quality", "75",            # qualité réduite pour les thumbnails
        "-vf", scale_filter,
        output_path,
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )

    if result.returncode != 0:
        error_output = result.stderr.decode("utf-8", errors="replace")
        logger.error("FFmpeg thumbnail échoué : %s", error_output)
        raise RuntimeError(f"FFmpeg thumbnail échoué : {error_output[:300]}")
