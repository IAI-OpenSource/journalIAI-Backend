import secrets
from logging import getLogger
from time import time
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status, WebSocket, WebSocketDisconnect

from app.cache.helpers.base import CacheWrapper
from app.cache.uploads_cache import MediaUploadsCache
from app.db.models.post import Post
from app.db.models.post_media import PostMedia
from app.db.models.user import User
from app.globals.messages import Messages
from app.globals.others_constants import OtherConstants
from app.repositories.post_video_repository import PostRepository
from app.schemas.post_upload_schemas import CreateMediaUploadIntent, UploadURLSchema, MediaUploadCompleteSchema, \
    WsPostProcessingInfoSchema, WsPostProcessingInfoSchemaSteps, CreateMediaUploadIntentFullData, FileInUploadURLSchema, \
    AvailableUploadMethod
from app.services import ServiceResult
from app.storage.post_video_storage import PostUploadStorage
from app.worker.celery_app import celery_app
from app.worker.tasks.workers_task_names import WorkersTaskNames

logger = getLogger(__name__)


def generate_random_intent_id(longueur: int) -> str:
    """Genere un ID unique pour un intent d'upload média."""
    return secrets.token_hex(longueur)

def get_mock_data() -> tuple[UUID, UUID]:
    """Génére des données mock pour les tests"""
    return UUID("5f594ab3-2560-4e5b-adbe-f20e5dd8e193"), UUID("74910788-e47d-483d-b24f-750c7b24e3d6")

# TODO: Ajouter des commentaires clairs pour se retrouver après
class MediaUploadsService:

    def __init__(self, cache: CacheWrapper, bd: AsyncSession):
        self._cache = MediaUploadsCache(cache)
        self._bd = PostRepository(bd)


    async def service_process_media_upload_intent(
        self, current_user: User, intent_data: CreateMediaUploadIntent
    ) -> ServiceResult[UploadURLSchema]:
        """
        Logique métier pour process un intent d'upload média
        Args:
            current_user: L'utilisateur courant
            intent_data: Le données de l'intent d'upload à enregistrer, conformes au schéma CreateMediaUploadIntent

        Returns:
            ServiceResult indiquant le succès ou l'échec de l'opération, avec un message approprié
        """
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
                upload_url = PostUploadStorage.get_video_upload_intent_presigned_upload_url(
                    random_intent_id, file.file_name
                )
            else:
                upload_url = PostUploadStorage.get_image_upload_intent_presigned_upload_url(
                    random_intent_id, file.file_name
                )
            if not upload_url:
                logger.error(f"Erreur lors de la génération de l'URL d'upload pour l'intent d'upload {random_intent_id}")
                continue

            files_to_upload.append(
                FileInUploadURLSchema(upload_url=upload_url, method=AvailableUploadMethod.PUT)
            )

        if not files_to_upload:
            logger.error("Liste des fichiers à UPload vide")
            return ServiceResult.service_error(message=Messages.ERROR_UPLOAD_URL_GENERATION, status_code=500)

        logger.info(f"URLs d'upload générées avec succès pour l'intent d'upload {random_intent_id}")


        # TODO: Revoir ces mocks data et cette logique apres
        # TODO: Verifier la véracité des données quand AnneeAcademique et Club seront pret
        full_data = CreateMediaUploadIntentFullData.model_validate(intent_data.model_dump(), from_attributes=True)
        if full_data.club_id:
            full_data.academic_year_id, full_data.classe_id = None, None     # Sécurisation

        elif full_data.only_for_a_class:
            # Alors on doit mettre l'année académique et la classe
            # On recupere la classe et lannée
            full_data.academic_year_id, full_data.classe_id = get_mock_data()
            full_data.club_id = None        # Sécurisation

        elif full_data.for_current_academic_year:
            full_data.academic_year_id = get_mock_data()[0]     # Mock de l'année académique courante
            full_data.classe_id = None        # Sécurisation

        else:
            full_data.academic_year_id = None
            full_data.classe_id = None

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
            await self._bd.bd_session.rollback()
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

            await self._bd.bd_session.commit()
            return ServiceResult.service_success(data="Ok")     # nsm

        except Exception as e:
            await self._bd.bd_session.rollback()
            error = f"Exception {e.__class__.__name__} lors de la sauvegarde du post traité en base de données : {e}"
            logger.exception(error)
            return ServiceResult.service_error(message=error, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


    async def service_verify_complete_media_upload(self, current_user: User, intent_id: str) -> ServiceResult[MediaUploadCompleteSchema]:
        """
        Logique métier pour finaliser un upload de média et lancer une tache de traitement dans le worker
        Args:
            current_user: L'utilisateur courant
            intent_id: Id de l'intent d'upload media
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
                intent_file_metadata = PostUploadStorage.get_video_upload_intent_file_info(intent_id, file.file_name)
            else:
                intent_file_metadata = PostUploadStorage.get_image_upload_intent_file_info(intent_id, file.file_name)

            if not intent_file_metadata:
                return ServiceResult.service_error(
                    message=Messages.ERROR_FILE_NOT_UPLOADED.format(file_name=file.file_name),
                    status_code=status.HTTP_404_NOT_FOUND, service_name= Messages.POST_SERVICE
                )

        await self._cache.add_upload_event_in_a_stream(
            user_id=user_id_str, intent_id=intent_id,
            data=WsPostProcessingInfoSchema(
               step=WsPostProcessingInfoSchemaSteps.IN_QUEUE,
               progress=0,
               timestamp=time(),
               error_message=None
           ),
            must_add_ttl=True
        )
        try:
            celery_app.send_task(
                name=WorkersTaskNames.PROCESS_MEDIAS_UPLOAD,
                kwargs={
                    "intent_id": intent_id,
                    "user_id": user_id_str,
                    "post_data": intent_data.model_dump_json()
                }
            )
        except Exception as e:
            logger.error(f"Erreur {e.__class__.__name__} lors de l'envoi de la tâche de post-traitement du média uploadé dans le worker : {e}")
            await self._cache.delete_upload_progress_stream(user_id_str, intent_id)   # Nettoyage du stream en cas d'erreur pour éviter les fuites de mémoire
            return ServiceResult.service_error(
                message=Messages.INTERNAL_SERVER_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, service_name=Messages.POST_SERVICE
            )

        await self._cache.delete_media_upload_intent(user_id_str, intent_id)  # Marque comme déja en cours de process

        return ServiceResult.service_success(
            data=MediaUploadCompleteSchema(
                job_id=intent_id
            )
        )


    async def service_listen_media_processing_intent(self, current_user: User, intent_id: str, ws: WebSocket) -> None:
        """
        Suis l'avancée d'un intent d'upload de média en écoutant les messages de progression du post-traitement du
        média dans le cache, et retourne les infos de progression à l'utilisateur via le websocket
        Args:
            current_user: L'utilisateur courant
            intent_id: Id de l'intent d'upload média
            ws: Websocket de suivi

        Returns:
            Jsp encore
        """
        user_id_str = str(current_user.id)
        verification = await self._cache.verify_a_upload_is_in_processing(user_id_str, intent_id)

        try:
            if not verification:
                logger.info(f"Aucun upload en cours de post-traitement trouvé pour l'intent d'upload média avec id {intent_id} et user_id {user_id_str}")
                await ws.send_text(
                    WsPostProcessingInfoSchema(
                        progress=0,
                        step=WsPostProcessingInfoSchemaSteps.UNKNOWN,
                        timestamp=0,
                        error_message=Messages.ERROR_MEDIA_UPLOAD_INTENT_NOT_FOUND
                    ).model_dump_json()
                )
                return

            last_id = None
            MAX_WAIT_ATEMPT = 10        # 10 minut
            attempts = 0
            has_finished = False

            while attempts < MAX_WAIT_ATEMPT and not has_finished:
                res = await self._cache.read_upload_progress_event_in_a_stream(user_id_str, intent_id, last_id)

                progress_data = res[0]

                if progress_data is None:
                    attempts+=1
                    logger.debug(f"Aucun nouvel événement de progression trouvé pour l'intent d'upload média avec id {intent_id} et user_id {user_id_str}, tentative {attempts+1}/{MAX_WAIT_ATEMPT}")
                    continue

                last_id = res[1]
                logger.info(f"Nouvel événement de progression trouvé pour l'intent d'upload média avec id {intent_id} et user_id {user_id_str}, étape: {res[0].step}, progression: {res[0].progress}%, timestamp: {res[0].timestamp}, message d'erreur: {res[0].error_message}")


                await ws.send_json(progress_data.model_dump_json())

                if progress_data.step == WsPostProcessingInfoSchemaSteps.COMPLETED or progress_data.error_message is not None:
                    has_finished = True
                    break

            if has_finished:
                logger.info(f"Traitement de l'intent d'upload média avec id {intent_id} et user_id {user_id_str} terminé, fermeture du websocket")
                await self._cache.delete_upload_progress_stream(user_id_str, intent_id)   # Nettoyage du stream après la fin du suivi

            else:
                logger.error(f"Nombre maximum de tentatives atteint pour la lecture su stream d'upload média avec id {intent_id} et user_id {user_id_str}, fermeture du websocket")
                await ws.send_json(
                    WsPostProcessingInfoSchema(
                        progress=0,
                        step=WsPostProcessingInfoSchemaSteps.UNKNOWN,
                        timestamp=0,
                        error_message=Messages.INTERNAL_SERVER_ERROR
                    ).model_dump_json()
                )

        except WebSocketDisconnect:
            logger.info(f"Websocket de suivi de l'intent d'upload média avec id {intent_id} et user_id {user_id_str} déconnecté par le client")
            raise
        except Exception as e:
            logger.exception(f"Exception {e.__class__.__name__} lors de l'écoute du websocket de suivi de l'intent d'upload média avec id {intent_id} et user_id {user_id_str} : {e}", exc_info=e)
            try:
                await ws.send_json(
                    WsPostProcessingInfoSchema(
                        progress=0,
                        step=WsPostProcessingInfoSchemaSteps.UNKNOWN,
                        timestamp=0,
                        error_message=Messages.INTERNAL_SERVER_ERROR
                    ).model_dump_json()
                )
            except WebSocketDisconnect:
                return
        finally:
            try:
                await ws.close()
            except WebSocketDisconnect:
                pass






