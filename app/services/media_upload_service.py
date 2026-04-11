import secrets
from logging import getLogger
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.cache.helpers.base import CacheWrapper
from app.cache.post_cache import PostCache
from app.cache.processing_cache import ProcessingCache
from app.db.models.post import Post
from app.db.models.post_media import PostMedia
from app.globals.messages import Messages
from app.globals.others_constants import OtherConstants
from app.repositories.post_repository import PostRepository
from app.schemas.post_upload_schemas import CreateMediaUploadIntent, UploadURLSchema, MediaUploadCompleteSchema, \
    CreateMediaUploadIntentFullData, FileInUploadURLSchema, \
    AvailableUploadMethod
from app.schemas.user_schemas import ReadUser
from app.services import ServiceResult
from app.services.post_service import PostService
from app.services.processing_service import ProcessingService
from app.storage.media_upload_storage import MediaUploadStorage
from app.worker.tasks.workers_task_names import WorkersTaskNames

logger = getLogger(__name__)


def generate_random_intent_id(longueur: int) -> str:
    """Genere un ID unique pour un intent d'upload média."""
    return secrets.token_hex(longueur)


# TODO: Ajouter des commentaires clairs pour se retrouver après
class MediaUploadsService:

    def __init__(self, cache: CacheWrapper, bd: AsyncSession):
        self._raw_bd = bd
        self._raw_cache = cache
        self._cache = PostCache(cache)
        self._bd = PostRepository(bd)
        self._processing_cache = ProcessingCache(cache)


    async def service_process_media_upload_intent(
        self, current_user: ReadUser, intent_data: CreateMediaUploadIntent
    ) -> ServiceResult[UploadURLSchema]:
        """
        Logique métier pour process un intent d'upload média
        Args:
            current_user: L'utilisateur courant
            intent_data: Le données de l'intent d'upload à enregistrer, conformes au schéma CreateMediaUploadIntent

        Returns:
            ServiceResult indiquant le succès ou l'échec de l'opération, avec un message approprié
        """

        full_data = CreateMediaUploadIntentFullData.model_validate(intent_data.model_dump(), from_attributes=True)

        verif = await PostService.verify_post_can_been_processed(
            self._raw_bd, self._raw_cache, full_data, current_user
        )

        if verif.is_error():
            return ServiceResult.service_error(
                message=verif.error,
                status_code=verif.status_code,
                service_name=Messages.POST_SERVICE
            )

        random_intent_id = generate_random_intent_id(16)

        files_to_upload: List[FileInUploadURLSchema] = []

        for file in intent_data.files:
            if file.file_size >= OtherConstants.MAX_UPLOAD_FILE_SIZE:
                return ServiceResult.service_error(
                    message=f"Le fichier {file.file_name} dépasse la taille totale autorisée (100Mo), taille du fichier : {file.file_size} octets",
                    status_code=status.HTTP_400_BAD_REQUEST,
                    service_name=Messages.POST_SERVICE
                )
            if file.is_video:
                upload_url = MediaUploadStorage.get_video_upload_intent_presigned_upload_url(
                    random_intent_id, file.file_name
                )
            else:
                upload_url = MediaUploadStorage.get_image_upload_intent_presigned_upload_url(
                    random_intent_id, file.file_name
                )
            if not upload_url:
                logger.error(f"Erreur lors de la génération de l'URL d'upload pour l'intent d'upload {random_intent_id}")
                continue

            files_to_upload.append(
                FileInUploadURLSchema(
                    upload_url=upload_url, method=AvailableUploadMethod.PUT,
                    media_type=file.media_type, file_name=file.file_name
                )
            )

        if not files_to_upload:
            logger.error("Liste des fichiers à UPload vide")
            return ServiceResult.service_error(message=Messages.ERROR_UPLOAD_URL_GENERATION, status_code=500)

        logger.info(f"URLs d'upload générées avec succès pour l'intent d'upload {random_intent_id}")

        await self._cache.save_media_upload_intent(str(current_user.id), random_intent_id, full_data)

        data_to_return = UploadURLSchema(intent_id=random_intent_id, files=files_to_upload)

        return ServiceResult.service_success(data=data_to_return)


    async def worker_service_save_processed_media_post_in_bd(self, post_object: Post, medias: List[PostMedia]) -> ServiceResult[str]:
        """
        Logique métier pour sauvegarder les informations du post média traité dans la base de données
        Args:
            post_object: Le post à save
            medias: La liste des médias liés au post

        Returns:
            ServiceResult indiquant le succès ou l'échec de l'opération, avec un message approprié
        """
        async def error_return(error_message: str):
            await self._bd.db.rollback()
            logger.error(error_message)
            return ServiceResult.service_error(message=error_message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            res = await self._bd.save_post(post_object, in_transaction=True)

            if res.is_error():
                error = f"Erreur lors de la sauvegarde du post traité en base de données : {res.error}"
                return await error_return(error)

            for media in medias:
                media.post_id = res.data.id

            res2 = await self._bd.save_many_post_media(medias, in_transaction=True)

            if res2.is_error():
                error = f"Erreur lors de la sauvegarde du média du post traité en base de données : {res2.error}"
                return await error_return(error)

            await self._bd.db.commit()
            return ServiceResult.service_success(data="Ok")     # nsm

        except Exception as e:
            await self._bd.db.rollback()
            error = f"Exception {e.__class__.__name__} lors de la sauvegarde du post traité en base de données : {e}"
            logger.exception(error)
            return ServiceResult.service_error(message=error, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


    async def service_verify_complete_media_upload(self, current_user: ReadUser, intent_id: str) -> ServiceResult[MediaUploadCompleteSchema]:
        """
        Logique métier pour finaliser un upload de média et lancer une tache de traitement dans le worker
        Args:
            current_user: L'utilisateur courant
            intent_id: Id de l'intent d'upload medias
        Returns:
            ServiceResult indiquant le succès ou l'échec de l'opération, avec un message approprié
        """

        user_id_str = str(current_user.id)

        intent_data = await self._cache.get_media_upload_intent(user_id_str, intent_id)

        if not intent_data:
            return ServiceResult.service_error(
                message=Messages.ERROR_MEDIA_UPLOAD_INTENT_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND, service_name= Messages.POST_SERVICE
            )

        for file in intent_data.files:
            if file.is_video:
                intent_file_metadata = MediaUploadStorage.get_video_upload_intent_file_info(intent_id, file.file_name)
            else:
                intent_file_metadata = MediaUploadStorage.get_image_upload_intent_file_info(intent_id, file.file_name)

            if not intent_file_metadata:
                return ServiceResult.service_error(
                    message=Messages.ERROR_FILE_NOT_UPLOADED.format(file_name=file.file_name),
                    status_code=status.HTTP_404_NOT_FOUND, service_name= Messages.POST_SERVICE
                )

        processing_serv = ProcessingService(self._raw_cache)
        task_res = await processing_serv.send_processing_task(
            user_id=user_id_str,
            intent_id=intent_id,
            task_name=WorkersTaskNames.PROCESS_MEDIAS_UPLOAD,
            queue_name=OtherConstants.MEDIA_PROCESSING_WORKER_QUEUE_NAME,
            task_kwargs={
                "intent_id": intent_id,
                "user_id": user_id_str,
                "post_data": intent_data.model_dump_json()
            }
        )

        if task_res.is_error():
            return ServiceResult.service_error(
                message=task_res.error, status_code=task_res.status_code, service_name= Messages.POST_SERVICE
            )

        await self._cache.delete_media_upload_intent(user_id_str, intent_id)  # Marque comme déja en cours de process

        return ServiceResult.service_success(
            data=MediaUploadCompleteSchema(
                job_id=intent_id
            )
        )


