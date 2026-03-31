"""Utilitaires communs pour le traitement des médias vidéo et image."""

from logging import getLogger, Logger
from typing import Optional, List
from app.cache.helpers.base import CacheWrapper
from app.db.models.enums import MediaType, PostType
from app.db.models.post import Post
from app.db.models.post_media import PostMedia
from app.db.session import AsyncSessionLocal
from app.worker.tasks.tasks_utils.base import ProcessingResult
from blurhash import encode
from PIL import Image

logger = getLogger(__name__)

def generate_blurhash_str(
    image_path: str
) -> Optional[str]:
    """
    Génère une chaîne de blurhash pour une image ou une vidéo.

    Args:
        image_path: Chemin local de l'image

    Returns:
        Chaîne de blurhash générée ou None
    """
    if not image_path:
        return None
    try:
        with Image.open(image_path) as img:
            img = img.convert("RGB")
            img.thumbnail((100, 100))
            blur_hash_str = encode(img, x_components=7, y_components=6)
            return blur_hash_str
    except Exception as e:
        logger.error(f"Erreur {e.__class__.__name__} lors de la génération du blurhash: {e}")
        return None

async def create_post_and_media(
    cache: CacheWrapper,
    post_object: Post,
    post_medias: List[PostMedia],
    custom_logger: Logger
) -> ProcessingResult[str]:
    """
    Crée et enregistre un post avec ses métadonnées médias en base de données.
    
    Fonction générique pour créer un post vidéo ou image et l'enregistrer en BD.
    
    Args:
        cache: Cache pour accès à Redis.
        post_object: Instance de Post à créer.
        post_medias: Le medias à inserer
        custom_logger: Logger spécifique à la tâche appelante pour des logs contextualisés.

    Returns:
        ProcessingResult(True, post_id) en succès, ProcessingResult(False, error) en échec.
    """
    from app.services.media_upload_service import MediaUploadsService

    try:
        async with AsyncSessionLocal() as session:
            service = MediaUploadsService(cache, session)
            post_type = PostType.CAROUSSEL
            if len(post_medias) == 1:
                if post_medias[0].media_type == MediaType.VIDEO:
                    post_type = PostType.VIDEO
                else:
                    post_type = PostType.IMAGE

            post_object.post_type = post_type


            # Sauvegarder
            res = await service.worker_service_save_processed_media_post_in_bd(
                post_object, post_medias
            )

            if res.is_error():
                custom_logger.error(f"Erreur lors de la sauvegarde en BD: {res.error}")
                return ProcessingResult.error_response(res.error)

            custom_logger.info(f"Post inséré en base de données avec succès")

            return ProcessingResult.ok_response(res.data)

    except Exception as e:
        custom_logger.exception(
            f"Erreur inattendue lors de la création du post en BD: {e}",
            exc_info=e,
        )
        return ProcessingResult.error_response(f"Erreur lors de la sauvegarde en base de données")


