import asyncio
import concurrent.futures
import os
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

import magic
from PIL import Image

from app.cache.helpers.base import CacheWrapper
from app.db.models.enums import PostType, MediaType
from app.db.models.post import Post
from app.db.models.post_media import PostMedia
from app.db.session import AsyncSessionLocal
from app.schemas.post_upload_schemas import CreateMediaUploadIntentFullData

from app.storage.minio_client import MinioClientFactory
from app.storage.minio_config import BucketName
from app.worker.tasks.async_loop_manager import task_async_loop_manager

T = TypeVar("T")
InternalResultPatern = tuple[bool, T | str]  # (success, data) ou (success, error_message)


def verify_file_is_image(file_path: str) -> InternalResultPatern[None]:
    """
    Vérifie si le fichier à traiter est bien une image en utilisant la bibliothèque python-magic.
    
    Args:
        file_path: Le chemin du fichier à vérifier.

    Returns:
        Tuple (True, None) si le fichier est une image valide, (False, error_message) sinon.
    """
    try:
        with open(file_path, "rb") as file:
            buffer_type = magic.from_buffer(file.read(2048), mime=True)
            if buffer_type and buffer_type.startswith("image/"):
                return True, None
            return False, f"Le fichier n'est pas une image valide, type MIME détecté : {buffer_type}, veuillez envoyer une image valide"
    except Exception as e:
        return False, f"Erreur ({e.__class__.__name__}) lors de la vérification du type de fichier : {e}"


def get_image_metadata(local_path: str) -> InternalResultPatern[dict[str, Any]]:
    """
    Récupère les métadonnées d'une image (résolution, format, taille).
    
    Args:
        local_path: Le chemin local de l'image à analyser.

    Returns:
        Dictionnaire contenant width, height, format et file_size, ou un message d'erreur.
    """
    try:
        with Image.open(local_path) as img:
            # Conversion en RGB si l'image n'est pas en RGB (pour éviter les problèmes WebP)
            width, height = img.size
            image_format = img.format or "UNKNOWN"
            
            # Obtenir la taille du fichier
            file_size = os.path.getsize(local_path)
            
            return True, {
                "width": width,
                "height": height,
                "format": image_format,
                "file_size": file_size
            }
    except Exception as e:
        return False, f"Erreur ({e.__class__.__name__}) lors de la lecture des métadonnées de l'image : {e}"


def process_image_with_pillow(
    local_raw_path: str, output_dir: str
) -> InternalResultPatern[dict[str, str]]:
    """
    Traite une image en créant 3 variantes WebP : thumbnail, medium et original/full.
    
    Les variantes ont les résolutions suivantes :
    - thumbnail: 300x300 (pour la prévisualisation rapide)
    - medium: 720x720 (pour l'affichage normal)
    - full: 1920x1920 max (pour la visualisation complète)
    
    Args:
        local_raw_path: Le chemin local de l'image brute.
        output_dir: Le répertoire de sortie pour les images traitées.

    Returns:
        Dictionnaire avec les chemins locaux des 3 variantes : {thumbnail_path, medium_path, full_path}.
    """
    try:
        variants = {
            "thumbnail": {"size": (300, 300), "quality": 80},
            "medium": {"size": (720, 720), "quality": 85},
            "full": {"size": (1920, 1920), "quality": 95}
        }
        
        result_paths = {}
        
        # Ouvrir l'image source
        with Image.open(local_raw_path) as original_img:
            # Convertir en RGB si nécessaire (PNG avec alpha, etc.)
            if original_img.mode in ("RGBA", "LA", "P"):
                # Créer un fond blanc pour les images avec transparence
                bg = Image.new("RGB", original_img.size, (255, 255, 255))
                if original_img.mode == "P":
                    original_img = original_img.convert("RGBA")
                bg.paste(original_img, mask=original_img.split()[-1] if original_img.mode == "RGBA" else None)
                original_img = bg
            elif original_img.mode != "RGB":
                original_img = original_img.convert("RGB")
        
        # Créer les 3 variantes
        for variant_name, variant_config in variants.items():
            variant_path = os.path.join(output_dir, f"{variant_name}.webp")
            
            with Image.open(local_raw_path) as img:
                # Convertir en RGB si nécessaire
                if img.mode in ("RGBA", "LA", "P"):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    bg.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                
                # Redimensionner en conservant le ratio d'aspect
                # On utilise LANCZOS pour une meilleure qualité
                img.thumbnail(variant_config["size"], Image.Resampling.LANCZOS)
                
                # Créer une image de la taille exacte avec fond blanc si nécessaire
                variant_img = Image.new("RGB", variant_config["size"], (255, 255, 255))
                offset = (
                    (variant_config["size"][0] - img.size[0]) // 2,
                    (variant_config["size"][1] - img.size[1]) // 2
                )
                variant_img.paste(img, offset)
                
                # Sauvegarder en WebP avec compression optimisée
                variant_img.save(
                    variant_path,
                    format="WEBP",
                    quality=variant_config["quality"],
                    method=6  # Compression maximale (0-6)
                )
            
            result_paths[variant_name] = variant_path
        
        return True, result_paths
    
    except Exception as e:
        return False, f"Erreur ({e.__class__.__name__}) lors du traitement de l'image avec Pillow : {e}"


async def upload_images_to_minio(local_dir: str, remote_path: str) -> InternalResultPatern[dict[str, str]]:
    """
    Upload les images traitées (les 3 variantes WebP) vers MinIO en parallèle.
    
    Args:
        local_dir: Le répertoire local contenant les images traitées.
        remote_path: Le chemin de base dans le bucket MinIO où uploader les images.

    Returns:
        Dictionnaire avec les URLs distantes des 3 variantes ou un message d'erreur.
    """
    try:
        if not os.path.exists(local_dir) or not os.listdir(local_dir):
            return False, "Le dossier local est vide ou inexistant. Le traitement a probablement échoué."
        
        files = []
        for p in Path(local_dir).rglob("*.webp"):
            if p.is_file():
                rel_path = p.relative_to(local_dir)
                remote_file_path = f"{remote_path}/{rel_path}"
                files.append((str(p), remote_file_path))
        
        if not files:
            return False, "Aucune image WebP n'a été trouvée après traitement."
        
        minio_client = MinioClientFactory.get_backend_client()
        remote_urls = {}
        
        # Upload en parallèle avec un executor
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            tasks = [
                task_async_loop_manager.get_loop().run_in_executor(
                    executor,
                    minio_client.fput_object,
                    BucketName.POSTS_PERMANENT_CONTENT.value,
                    r_path,  # Destination dans le bucket
                    l_path,  # Fichier source sur le disque
                    "image/webp"
                )
                for l_path, r_path in files
            ]
            await asyncio.gather(*tasks)
        
        # Construire le dictionnaire avec les chemins des variantes
        # Les fichiers sont nommés thumbnail.webp, medium.webp, full.webp
        for l_path, r_path in files:
            variant_name = Path(l_path).stem  # thumbnail, medium, full
            remote_urls[variant_name] = r_path
        
        return True, remote_urls
    
    except Exception as err:
        return False, f"Erreur ({err.__class__.__name__}) lors de l'upload des images vers le bucket Minio : {err}"


async def add_processed_image_in_db(
    cache: CacheWrapper,
    user_id: str,
    post_data: CreateMediaUploadIntentFullData,
    minio_urls: dict[str, str],
    file_size: int,
    width: int,
    height: int
) -> InternalResultPatern[str]:
    """
    Enregistre le post image et les métadonnées en base de données.
    
    Args:
        cache: Le cache pour accéder à Redis.
        user_id: L'ID de l'utilisateur auteur du post.
        post_data: Les données du post (contenu, club, event, etc.).
        minio_urls: Dictionnaire des URLs des 3 variantes (thumbnail, medium, full).
        file_size: La taille du fichier original en bytes.
        width: La largeur de l'image originale.
        height: La hauteur de l'image originale.

    Returns:
        Tuple (True, data) en cas de succès, (False, error_message) en cas d'erreur.
    """
    from app.services.media_upload_service import MediaUploadsService
    
    async with AsyncSessionLocal() as session:
        service = MediaUploadsService(cache, session)
        
        # Créer le post
        definitive_post = Post(
            author_id=UUID(user_id),
            event_id=post_data.event_id,
            club_id=post_data.club_id,
            academic_year_id=post_data.academic_year_id,
            target_classe_id=post_data.classe_id,
            content=post_data.content
        )
        
        definitive_post.post_type = PostType.IMAGE
        
        # Utiliser la variante "full" comme URL principale (pour les accès directs)
        # et stocker la variante "thumbnail" comme thumbnail
        main_url = minio_urls.get("full", "")
        thumbnail_url = minio_urls.get("thumbnail", "")
        
        definitive_post_media = PostMedia(
            post_id=definitive_post.id,
            media_type=MediaType.IMAGE,
            media_url=main_url,
            thumbnail_url=thumbnail_url,
            file_size=file_size,
            duration=None,
            width=width,
            height=height,
        )
        
        definitive_post_media.is_processed = True
        
        # Utiliser le service pour sauvegarder (similaire aux vidéos)
        res = await service.worker_service_save_processed_media_post_in_bd(definitive_post, definitive_post_media)
        if res.is_error():
            return False, res.error
        
        return True, res.data

