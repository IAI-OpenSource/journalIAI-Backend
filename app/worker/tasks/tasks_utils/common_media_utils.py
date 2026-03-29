"""Utilitaires communs pour le traitement des médias vidéo et image."""

from logging import getLogger
from typing import Optional
from uuid import UUID

from app.cache.helpers.base import CacheWrapper
from app.db.models.enums import MediaType, PostType
from app.db.models.post import Post
from app.db.models.post_media import PostMedia
from app.db.session import AsyncSessionLocal
from app.schemas.post_upload_schemas import CreateMediaUploadIntentFullData
from app.storage.minio_config import BucketName
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
    user_id: str,
    post_data: CreateMediaUploadIntentFullData,
    post_type: PostType,
    media_type: MediaType,
    media_url: str,
    thumbnail_url: str,
    file_size: int,
    width: int,
    height: int,
    duration: int = None,
    blur_hash: str = None,
    stored_bucket_name: str = None,
) -> ProcessingResult[str]:
    """
    Crée et enregistre un post avec ses métadonnées médias en base de données.
    
    Fonction générique pour créer un post vidéo ou image et l'enregistrer en BD.
    
    Args:
        cache: Cache pour accès à Redis.
        user_id: ID de l'utilisateur auteur.
        post_data: Données du post (contenu, club, event, etc.).
        post_type: Type du post (VIDEO, IMAGE, TEXT, etc.).
        media_type: Type du média (VIDEO, IMAGE).
        media_url: URL du média dans MinIO.
        thumbnail_url: URL de la miniature dans MinIO.
        file_size: Taille du fichier original en bytes.
        width: Largeur du média.
        height: Hauteur du média.
        duration: Durée du média en secondes (pour vidéo).
        blur_hash: Hash de flou pour la prévisualisation (optionnel).
        stored_bucket_name: Nom du bucket où est stocké le média (optionnel).
        
    Returns:
        ProcessingResult(True, post_id) en succès, ProcessingResult(False, error) en échec.
    """
    from app.services.media_upload_service import MediaUploadsService

    try:
        async with AsyncSessionLocal() as session:
            service = MediaUploadsService(cache, session)

            # Créer le post
            definitive_post = Post(
                author_id=UUID(user_id),
                event_id=post_data.event_id,
                club_id=post_data.club_id,
                academic_year_id=post_data.academic_year_id,
                target_classe_id=post_data.classe_id,
                content=post_data.content,
            )
            definitive_post.post_type = post_type

            # Déterminer le bucket si non fourni
            if not stored_bucket_name:
                stored_bucket_name = BucketName.POSTS_PERMANENT_CONTENT.value

            # Créer la média
            definitive_post_media = PostMedia(
                post_id=definitive_post.id,
                media_type=media_type,
                media_url=media_url,
                thumbnail_url=thumbnail_url,
                file_size=file_size,
                duration=duration,
                width=width,
                height=height,
                blur_hash=blur_hash,
                stored_bucket_name=stored_bucket_name,
            )
            definitive_post_media.is_processed = True

            # Sauvegarder
            res = await service.worker_service_save_processed_media_post_in_bd(
                definitive_post, definitive_post_media
            )

            if res.is_error():
                logger.error(f"Erreur lors de la sauvegarde en BD: {res.error}")
                return ProcessingResult.error_response(res.error)

            logger.info(f"Post {media_type.value} créé avec succès: {res.data}")
            return ProcessingResult.ok_response(res.data)

    except Exception as e:
        logger.exception(
            f"Erreur inattendue lors de la création du post en BD: {e}",
            exc_info=e,
        )
        return ProcessingResult.error_response(f"Erreur lors de la sauvegarde en base de données")


