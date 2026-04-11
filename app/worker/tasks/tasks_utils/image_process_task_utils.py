import asyncio
import concurrent.futures
import os
from logging import getLogger
from pathlib import Path
from typing import Any

from PIL import Image

from app.globals.messages import Messages
from app.storage.minio_client import MinioClientFactory
from app.storage.minio_config import BucketName
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.tasks_utils.base import ProcessingResult

logger = getLogger(__name__)


def get_image_metadata(local_path: str) -> ProcessingResult[dict[str, Any]]:
    """
    Récupère les métadonnées d'une image (résolution, format, taille).
    
    Args:
        local_path: Le chemin local de l'image à analyser.

    Returns:
        ProcessingResult avec dict contenant width, height, format et file_size.
    """
    try:
        with Image.open(local_path) as img:
            width, height = img.size
            image_format = img.format or "UNKNOWN"
            file_size = os.path.getsize(local_path)
            
            metadata = {
                "width": width,
                "height": height,
                "format": image_format,
                "file_size": file_size
            }
            return ProcessingResult.ok_response(metadata)
    except Exception as e:
        logger.exception(f"Erreur lors de la lecture des métadonnées de l'image: {e}")
        return ProcessingResult.error_response(f"Erreur lors de la lecture des métadonnées")


def process_image_with_pillow(
    local_raw_path: str, output_dir: str
) -> ProcessingResult[dict[str, str]]:
    """
    Traite une image en créant 3 variantes WebP : thumbnail, medium et full.
    
    Variantes :
    - thumbnail: 300x300 (prévisualisation)
    - medium: 720x720 (affichage normal)
    - full: 1920x1920 max (visualisation complète)
    
    Args:
        local_raw_path: Chemin local de l'image brute.
        output_dir: Répertoire de sortie pour les images traitées.

    Returns:
        ProcessingResult avec dict des chemins : {thumbnail_path, medium_path, full_path}.
    """
    try:
        variants = {
            "thumbnail": {"size": (300, 300), "quality": 80},
            "medium": {"size": (720, 720), "quality": 85},
            "full": {"size": (1920, 1920), "quality": 95}
        }
        
        result_paths = {}
        
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
                img.thumbnail(variant_config["size"], Image.Resampling.LANCZOS)
                
                # Créer une image de la taille exacte avec fond blanc
                variant_img = Image.new("RGB", variant_config["size"], (255, 255, 255))
                offset = (
                    (variant_config["size"][0] - img.size[0]) // 2,
                    (variant_config["size"][1] - img.size[1]) // 2
                )
                variant_img.paste(img, offset)
                
                # Sauvegarder en WebP
                variant_img.save(
                    variant_path,
                    format="WEBP",
                    quality=variant_config["quality"],
                    method=6
                )
            
            result_paths[variant_name] = variant_path
        
        return ProcessingResult.ok_response(result_paths)
    
    except Exception as e:
        logger.exception(f"Erreur lors du traitement de l'image avec Pillow: {e}")
        return ProcessingResult.error_response(f"Erreur lors du traitement: {e}")


async def upload_images_to_minio(local_dir: str, remote_path: str, is_story: bool) -> ProcessingResult[dict[str, str]]:
    """
    Upload les images traitées (les 3 variantes WebP) vers MinIO en parallèle.
    
    Args:
        local_dir: Répertoire local contenant les images traitées.
        remote_path: Chemin de base dans le bucket MinIO.
        is_story: Indique si les images sont destinées à une story (affecte le bucket de destination).

    Returns:
        ProcessingResult avec dict des URLs distantes des 3 variantes.
    """
    try:
        if not os.path.exists(local_dir) or not os.listdir(local_dir):
            logger.error("Le dossier local est vide ou inexistant.")
            return ProcessingResult.error_response(Messages.INTERNAL_SERVER_ERROR)

        files = []
        for p in Path(local_dir).rglob("*.webp"):
            if p.is_file():
                if p.name.startswith("thumb"):
                    continue    # Saute mouton, Les thumbnails sont traités à part, dans un autre bucket

                rel_path = p.relative_to(local_dir)
                remote_file_path = f"{remote_path}/{rel_path}"
                files.append((str(p), remote_file_path))
        
        if not files:
            logger.error("Aucune image WebP n'a été trouvée après traitement.")
            return ProcessingResult.error_response(Messages.INTERNAL_SERVER_ERROR)
        
        minio_client = MinioClientFactory.get_backend_client()
        remote_urls = {}
        
        # Upload en parallèle
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            tasks = [
                task_async_loop_manager.get_loop().run_in_executor(
                    executor,
                    minio_client.fput_object,
                    BucketName.STORIES_EPHEMERAL_CONTENT.value if is_story else BucketName.POSTS_PERMANENT_CONTENT.value,
                    r_path,
                    l_path,
                    "image/webp"
                )
                for l_path, r_path in files
            ]
            await asyncio.gather(*tasks)
        
        # Construire le dictionnaire avec les chemins des variantes
        for l_path, r_path in files:
            variant_name = Path(l_path).stem
            remote_urls[variant_name] = r_path
        
        return ProcessingResult.ok_response(remote_urls)
    
    except Exception as err:
        logger.exception(f"Erreur lors de l'upload des images vers MinIO: {err}")
        return ProcessingResult.error_response(Messages.INTERNAL_SERVER_ERROR)



