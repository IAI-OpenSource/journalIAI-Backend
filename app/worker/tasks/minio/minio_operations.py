"""Manager centralisé pour les opérations MinIO."""

from logging import getLogger
from pathlib import Path

from minio.datatypes import Object

from app.storage.minio_client import MinioClientFactory
from app.worker.tasks.base.processing_result import ProcessingResult

logger = getLogger(__name__)


class MinIOManager:
    """
    Manager centralisé pour toutes les opérations MinIO.
    
    Encapsule les opérations de téléchargement, upload, suppression et métadonnées
    pour une réutilisation cohérente entre vidéo et image.
    """

    @staticmethod
    def get_file_metadata(bucket_name: str, object_path: str) -> ProcessingResult[Object]:
        """
        Récupère les métadonnées d'un fichier dans MinIO.
        
        Args:
            bucket_name: Nom du bucket MinIO.
            object_path: Chemin du fichier dans le bucket.
            
        Returns:
            ProcessingResult avec objet Object si succès, erreur sinon.
        """
        try:
            minio_client = MinioClientFactory.get_backend_client()
            metadata = minio_client.stat_object(bucket_name, object_path)
            return ProcessingResult.ok_response(metadata)
        except Exception as e:
            logger.error(
                f"Erreur lors de la récupération des métadonnées MinIO "
                f"({e.__class__.__name__}): {e}"
            )
            return ProcessingResult.error_response(f"Impossible de récupérer les métadonnées du fichier")

    @staticmethod
    def download_file(
        bucket_name: str, object_path: str, local_destination: str
    ) -> ProcessingResult[str]:
        """
        Télécharge un fichier depuis MinIO vers le système local.
        
        Args:
            bucket_name: Nom du bucket MinIO.
            object_path: Chemin du fichier dans le bucket.
            local_destination: Chemin local de destination.
            
        Returns:
            ProcessingResult avec chemin local si succès, erreur sinon.
        """
        try:
            minio_client = MinioClientFactory.get_backend_client()
            minio_client.fget_object(bucket_name, object_path, local_destination)
            return ProcessingResult.ok_response(local_destination)
        except Exception as e:
            logger.error(
                f"Erreur lors du téléchargement depuis MinIO "
                f"({e.__class__.__name__}): {e}"
            )
            return ProcessingResult.error_response(f"Impossible de télécharger le fichier")

    @staticmethod
    def upload_file(
        bucket_name: str,
        object_path: str,
        local_file_path: str,
        content_type: str = "application/octet-stream",
    ) -> ProcessingResult[str]:
        """
        Upload un fichier vers MinIO.
        
        Args:
            bucket_name: Nom du bucket MinIO.
            object_path: Chemin de destination dans le bucket.
            local_file_path: Chemin local du fichier à uploader.
            content_type: Type MIME du fichier.
            
        Returns:
            ProcessingResult avec nom de l'objet si succès, erreur sinon.
        """
        try:
            minio_client = MinioClientFactory.get_backend_client()
            result = minio_client.fput_object(
                bucket_name, object_path, local_file_path, content_type=content_type
            )
            return ProcessingResult.ok_response(result.object_name)
        except Exception as e:
            logger.error(
                f"Erreur lors de l'upload vers MinIO "
                f"({e.__class__.__name__}): {e}"
            )
            return ProcessingResult.error_response(f"Impossible d'uploader le fichier")

    @staticmethod
    def delete_file(bucket_name: str, object_path: str) -> ProcessingResult:
        """
        Supprime un fichier depuis MinIO.
        
        Args:
            bucket_name: Nom du bucket MinIO.
            object_path: Chemin du fichier à supprimer.
            
        Returns:
            ProcessingResult(True) si succès, ProcessingResult(False, error) sinon.
        """
        try:
            minio_client = MinioClientFactory.get_backend_client()
            minio_client.remove_object(bucket_name, object_path)
            return ProcessingResult.ok_response(None)
        except Exception as e:
            logger.error(
                f"Erreur lors de la suppression depuis MinIO "
                f"({e.__class__.__name__}): {e}"
            )
            return ProcessingResult.error_response(f"Impossible de supprimer le fichier")

    @staticmethod
    def get_content_type_for_file(file_path: str) -> str:
        """
        Détermine le content-type approprié basé sur l'extension du fichier.
        
        Args:
            file_path: Chemin du fichier.
            
        Returns:
            Le content-type approprié.
        """
        suffix = Path(file_path).suffix.lower()

        content_types = {
            ".m3u8": "application/x-mpegURL",
            ".m4s": "video/iso.segment",
            ".mp4": "video/mp4",
            ".webp": "image/webp",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
        }

        return content_types.get(suffix, "application/octet-stream")


