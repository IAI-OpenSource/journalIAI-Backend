import secrets
from datetime import timedelta
from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.helpers.base import CacheWrapper
from app.cache.uploads_cache import VideoUploadsCache
from app.globals.cache_duration import CacheDurartion
from app.globals.messages import Messages
from app.schemas.upload_schemas import CreateVideoUploadIntent, UploadURLSchema
from app.services import ServiceResult
from app.storage.minio_client import MinioClientFactory
from app.storage.minio_config import BucketName
from app.utils.bucket_files_utils import BucketFilesUtils

logger = getLogger(__name__)


def generate_random_intent_id(longueur: int) -> str:
    """Genere un ID unique pour un intent d'upload video."""
    return secrets.token_hex(longueur)

class VideoUploadsService:

    def __init__(self, cache: CacheWrapper, bd: AsyncSession):
        self._cache = VideoUploadsCache(cache)
        self._bd = bd




    async def save_video_upload_intent(self, user_id: str, intent_data: CreateVideoUploadIntent) -> ServiceResult[UploadURLSchema]:
        """
        Logique métier pour enregistrer un intent d'upload video dans le cache pour les utilisateurs
        Args:
            user_id: Id de l'utilisateur
            intent_data: Le données de l'intent d'upload à enregistrer, conformes au schéma CreateVideoUploadIntent

        Returns:
            ServiceResult indiquant le succès ou l'échec de l'opération, avec un message approprié
        """
        random_intent_id = generate_random_intent_id(16)

        bucket_object_key = BucketFilesUtils.generate_object_name_for_raw_video(
            intent_id=random_intent_id,
            filename=intent_data.file_name
        )

        minio_client = MinioClientFactory.get_public_client()

        upload_url = minio_client.presigned_put_object(
            BucketName.POSTS_RAW_UPLOADS.value,
            bucket_object_key,
            timedelta(seconds=CacheDurartion.VIDEO_UPLOAD_INTENT_DURATION.value)
        )

        if not upload_url:
            logger.info("Erreur lors de la génération de l'URL d'upload pour l'intent d'upload video")
            return ServiceResult.service_error(message=Messages.ERROR_UPLOAD_URL_GENERATION, status_code=500)

        logger.info(f"URL d'upload générée avec succès pour l'intent d'upload video générée avec succès")

        await self._cache.save_video_upload_intent(user_id, random_intent_id, intent_data)

        data_to_return = UploadURLSchema(upload_url=upload_url, intent_id=random_intent_id)

        return ServiceResult.service_success(data=data_to_return)