from datetime import timedelta
from logging import getLogger
from typing import Optional

from minio.datatypes import Object

from app.globals.cache_duration import CacheDurartion
from app.storage.bucket_files_utils import BucketFilesUtils
from app.storage.minio_client import MinioClientFactory
from app.storage.minio_config import BucketName

logger = getLogger(__name__)

class PostUploadStorage:

    @staticmethod
    def get_video_upload_intent_presigned_upload_url(intent_id: str, filename: str) -> Optional[str]:
        """
        Crée une url présignée d'upload pour un intent d'upload video.
        Args:
            intent_id: Id de l'intent
            filename: Le nom du fichier
        Returns:
            L'url d'upload, None est cas d'erreur
        """
        try:
            bucket_object_key = BucketFilesUtils.generate_object_name_for_raw_video(
                intent_id=intent_id,
                filename=filename
            )

            minio_client = MinioClientFactory.get_public_client()

            upload_url = minio_client.presigned_put_object(
                BucketName.POSTS_RAW_UPLOADS.value,
                bucket_object_key,
                timedelta(seconds=CacheDurartion.UPLOAD_INTENT_DURATION.value)
            )
            return upload_url

        except Exception as e:
            logger.exception(
                f"Exception {e.__class__.__name__} lors de la génération de l'URL d'upload pour un intent d'upload video : {e}",
                exc_info=e
            )
            return None

    @staticmethod
    def get_image_upload_intent_presigned_upload_url(intent_id: str, filename: str) -> Optional[str]:
        """
        Crée une url présignée d'upload pour un intent d'upload image.
        Args:
            intent_id: Id de l'intent
            filename: Le nom du fichier
        Returns:
            L'url d'upload, None est cas d'erreur
        """
        try:
            bucket_object_key = BucketFilesUtils.generate_object_path_for_raw_image(
                intent_id=intent_id,
                filename=filename
            )

            minio_client = MinioClientFactory.get_public_client()

            upload_url = minio_client.presigned_put_object(
                BucketName.POSTS_RAW_UPLOADS.value,
                bucket_object_key,
                timedelta(seconds=CacheDurartion.UPLOAD_INTENT_DURATION.value)
            )
            return upload_url

        except Exception as e:
            logger.exception(
                f"Exception {e.__class__.__name__} lors de la génération de l'URL d'upload pour un intent d'upload image : {e}",
                exc_info=e
            )
            return None
    @staticmethod
    def get_video_upload_intent_file_info(intent_id: str, filename: str) -> Optional[Object]:
        """
        Verifie si le fichier video de l'intent est bien existant et le retourne
        Args:
            intent_id: Id de l'intent
            filename: Le nom du fichier
        Returns:
            Les métadonnées du fichier s'il existe
        """
        try:
            bucket_object_key = BucketFilesUtils.generate_object_name_for_raw_video(
                intent_id=intent_id,
                filename=filename
            )

            minio_client = MinioClientFactory.get_backend_client()

            file_metadata = minio_client.stat_object(BucketName.POSTS_RAW_UPLOADS.value, bucket_object_key)

            return file_metadata

        except Exception as e:
            logger.exception(
                f"Exception {e.__class__.__name__} lors de la récupération d'un intent d'upload video : {e}",
                exc_info=e
            )
            return None




