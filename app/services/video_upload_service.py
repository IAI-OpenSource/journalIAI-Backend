import secrets
from logging import getLogger

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from app.cache.helpers.base import CacheWrapper
from app.cache.uploads_cache import VideoUploadsCache
from app.globals.messages import Messages
from app.schemas.upload_schemas import CreateVideoUploadIntent, UploadURLSchema, VideoUploadCompleteSchema
from app.services import ServiceResult

from app.storage.post_video_storage import PostVideoStorage

logger = getLogger(__name__)


def generate_random_intent_id(longueur: int) -> str:
    """Genere un ID unique pour un intent d'upload video."""
    return secrets.token_hex(longueur)

class VideoUploadsService:

    def __init__(self, cache: CacheWrapper, bd: AsyncSession):
        self._cache = VideoUploadsCache(cache)
        self._bd = bd

    async def service_process_video_upload_intent(
        self, user_id: str, intent_data: CreateVideoUploadIntent
    ) -> ServiceResult[UploadURLSchema]:
        """
        Logique métier pour process un intent d'upload video
        Args:
            user_id: Id de l'utilisateur
            intent_data: Le données de l'intent d'upload à enregistrer, conformes au schéma CreateVideoUploadIntent

        Returns:
            ServiceResult indiquant le succès ou l'échec de l'opération, avec un message approprié
        """
        random_intent_id = generate_random_intent_id(16)

        upload_url = PostVideoStorage.get_video_upload_intent_presigned_upload_url(random_intent_id,
                                                                                   intent_data.file_name)

        if not upload_url:
            logger.error("Erreur lors de la génération de l'URL d'upload pour l'intent d'upload video")
            return ServiceResult.service_error(message=Messages.ERROR_UPLOAD_URL_GENERATION, status_code=500)

        logger.info(f"URL d'upload générée avec succès pour l'intent d'upload video générée avec succès")

        await self._cache.save_video_upload_intent(user_id, random_intent_id, intent_data)

        data_to_return = UploadURLSchema(upload_url=upload_url, intent_id=random_intent_id)

        return ServiceResult.service_success(data=data_to_return)

    async def service_verify_complete_video_upload(self, user_id: str, intent_id: str) -> ServiceResult[VideoUploadCompleteSchema]:
        """
        Logique métier pour finaliser un upload de vidéo et lancer une tache de traitement dans le worker
        Args:
            user_id: Id de l'utilisateur
            intent_id: Id de l'intent d'upload video
        Returns:
            ServiceResult indiquant le succès ou l'échec de l'opération, avec un message approprié
        """
        intent_data = await self._cache.get_video_upload_intent(user_id, intent_id)

        if not intent_data:
            return ServiceResult.service_error(message=Messages.ERROR_VIDEO_UPLOAD_INTENT_NOT_FOUND, status_code=status.HTTP_404_NOT_FOUND)

        intent_file_metadata = PostVideoStorage.get_video_upload_intent_file_info(intent_id, intent_data.file_name)

        if not intent_file_metadata:
            return ServiceResult.service_error(message=Messages.ERROR_VIDEO_UPLOAD_INTENT_NOT_FOUND, status_code=status.HTTP_404_NOT_FOUND)


        return ServiceResult.service_success(
            data=VideoUploadCompleteSchema(
                job_id=intent_id
            )
        )

