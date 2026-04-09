"""
Service pour la gestion des uploads de médias pour les stories.
Contient la logique métier pour initialiser les uploads, générer les URLs, et finaliser le traitement.
"""

import secrets
from logging import getLogger
from time import time

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status, WebSocket, WebSocketDisconnect

from app.cache.helpers.base import CacheWrapper
from app.cache.story_cache import StoryCache
from app.db.models.enums import ClubMembersType, UserRole
from app.globals.messages import Messages
from app.repositories.story_repository import StoryRepository
from app.schemas.post_upload_schemas import AvailableUploadMethod, WsMediasProcessingInfoSchema, \
    WsMediasProcessingInfoSchemaSteps
from app.schemas.story_upload_schemas import (
    CreateStoryUploadIntent, StoryUploadURLSchema, MediaUploadCompleteSchema, CreateStoryUploadIntentFullData,
    FileInUploadURLSchema
)
from app.schemas.user_schemas import ReadUser
from app.services import ServiceResult
from app.services.academic_year_service import AcademicYearService
from app.services.club_member_service import ClubMemberService
from app.storage.media_upload_storage import MediaUploadStorage
from app.worker.celery_app import celery_app
from app.worker.tasks.workers_task_names import WorkersTaskNames
from app.globals.others_constants import OtherConstants

logger = getLogger(__name__)


def generate_random_intent_id(longueur: int) -> str:
    """Génère un ID unique pour un intent d'upload média story."""
    return secrets.token_hex(longueur)


class StoryMediaUploadsService:
    """Service pour gérer les uploads de médias pour les stories."""

    def __init__(self, cache: CacheWrapper, bd: AsyncSession):
        self._raw_bd = bd
        self._raw_cache = cache
        self._cache = StoryCache(cache)
        self._bd = StoryRepository(bd)

    async def service_process_media_upload_intent(
        self, current_user: ReadUser, intent_data: CreateStoryUploadIntent
    ) -> ServiceResult[StoryUploadURLSchema]:
        """
        Logique métier pour traiter un intent d'upload média story.

        Args:
            current_user: L'utilisateur courant
            intent_data: Les données de l'intent d'upload

        Returns:
            ServiceResult avec l'URL d'upload ou une erreur
        """

        full_data = CreateStoryUploadIntentFullData.model_validate(intent_data.model_dump(), from_attributes=True)

        # Vérifier que l'utilisateur peut créer une story avec les données fournies
        verif = await self._verify_story_can_been_processed(full_data, current_user)

        if verif.is_error():
            return ServiceResult.service_error(
                message=verif.error,
                status_code=verif.status_code,
                service_name=Messages.POST_SERVICE
            )

        random_intent_id = generate_random_intent_id(16)

        # Vérifier la taille du fichier
        file = intent_data.file
        if file.file_size >= OtherConstants.MAX_UPLOAD_FILE_SIZE:
            return ServiceResult.service_error(
                message=f"Le fichier {file.file_name} dépasse la taille maximale autorisée (100Mo), taille : {file.file_size} octets",
                status_code=status.HTTP_400_BAD_REQUEST,
                service_name=Messages.POST_SERVICE
            )

        # Générer l'URL d'upload selon le type de fichier
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
            return ServiceResult.service_error(message=Messages.ERROR_UPLOAD_URL_GENERATION, status_code=500)

        logger.info(f"URL d'upload générée avec succès pour l'intent d'upload {random_intent_id}")

        # Sauvegarder l'intent dans le cache
        await self._cache.save_media_upload_intent(str(current_user.id), random_intent_id, full_data)

        file_to_upload = FileInUploadURLSchema(
            upload_url=upload_url,
            method=AvailableUploadMethod.PUT,
            media_type=file.media_type,
            file_name=file.file_name
        )

        data_to_return = StoryUploadURLSchema(intent_id=random_intent_id, file=file_to_upload)

        return ServiceResult.service_success(data=data_to_return)

    async def service_verify_complete_media_upload(
        self, current_user: ReadUser, intent_id: str
    ) -> ServiceResult[MediaUploadCompleteSchema]:
        """
        Logique métier pour finaliser un upload de média story et lancer le traitement.

        Args:
            current_user: L'utilisateur courant
            intent_id: ID de l'intent d'upload

        Returns:
            ServiceResult avec l'ID du job de traitement
        """

        user_id_str = str(current_user.id)

        # Récupérer l'intent depuis le cache
        intent_data = await self._cache.get_media_upload_intent(user_id_str, intent_id)

        if not intent_data:
            return ServiceResult.service_error(
                message=Messages.ERROR_MEDIA_UPLOAD_INTENT_NOT_FOUND,
                status_code=status.HTTP_404_NOT_FOUND,
                service_name=Messages.POST_SERVICE
            )

        # Vérifier que le fichier a bien été uploadé
        file = intent_data.file
        if file.is_video:
            intent_file_metadata = MediaUploadStorage.get_video_upload_intent_file_info(intent_id, file.file_name)
        else:
            intent_file_metadata = MediaUploadStorage.get_image_upload_intent_file_info(intent_id, file.file_name)

        if not intent_file_metadata:
            return ServiceResult.service_error(
                message=Messages.ERROR_FILE_NOT_UPLOADED.format(file_name=file.file_name),
                status_code=status.HTTP_404_NOT_FOUND,
                service_name=Messages.POST_SERVICE
            )

        # Ajouter un événement de progression initial
        await self._cache.add_upload_event_in_a_stream(
            user_id=user_id_str,
            intent_id=intent_id,
            data=WsMediasProcessingInfoSchema(
                step=WsMediasProcessingInfoSchemaSteps.IN_QUEUE,
                progress=0,
                timestamp=time(),
                error_message=None
            ),
            must_add_ttl=True
        )

        try:
            # Envoyer la tâche de traitement au worker
            celery_app.send_task(
                name=WorkersTaskNames.PROCESS_STORY_UPLOAD,
                kwargs={
                    "intent_id": intent_id,
                    "user_id": user_id_str,
                    "story_data": intent_data.model_dump_json()
                },
                queue=OtherConstants.MEDIA_PROCESSING_WORKER_QUEUE_NAME
            )
        except Exception as e:
            logger.error(f"Erreur {e.__class__.__name__} lors de l'envoi de la tâche de traitement de story : {e}")
            await self._cache.delete_upload_progress_stream(user_id_str, intent_id)
            return ServiceResult.service_error(
                message=Messages.INTERNAL_SERVER_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                service_name=Messages.POST_SERVICE
            )

        # Supprimer l'intent du cache (marqué comme en cours de traitement)
        await self._cache.delete_media_upload_intent(user_id_str, intent_id)

        return ServiceResult.service_success(
            data=MediaUploadCompleteSchema(job_id=intent_id)
        )

    async def service_listen_media_processing_intent(
        self, current_user: ReadUser, intent_id: str, ws: WebSocket
    ) -> None:
        """
        Suit l'avancée du traitement d'une story en écoutant les événements du cache via WebSocket.

        Args:
            current_user: L'utilisateur courant
            intent_id: ID de l'intent d'upload
            ws: WebSocket de suivi
        """
        user_id_str = str(current_user.id)
        verification = await self._cache.verify_a_upload_is_in_processing(user_id_str, intent_id)

        try:
            if not verification:
                logger.info(f"Aucun upload de story en cours pour l'intent {intent_id} et user_id {user_id_str}")
                await ws.send_text(
                    WsMediasProcessingInfoSchema(
                        progress=0,
                        step=WsMediasProcessingInfoSchemaSteps.UNKNOWN,
                        timestamp=0,
                        error_message=Messages.ERROR_MEDIA_UPLOAD_INTENT_NOT_FOUND
                    ).model_dump_json()
                )
                return

            last_id = None
            MAX_WAIT_ATEMPT = 10  # 10 minutes
            attempts = 0
            has_finished = False

            while attempts < MAX_WAIT_ATEMPT and not has_finished:
                res = await self._cache.read_upload_progress_event_in_a_stream(user_id_str, intent_id, last_id)

                progress_data = res[0]

                if progress_data is None:
                    attempts += 1
                    logger.debug(f"Aucun nouvel événement pour l'intent {intent_id}, tentative {attempts+1}/{MAX_WAIT_ATEMPT}")
                    continue

                last_id = res[1]
                logger.info(f"Événement de progression: étape={progress_data.step}, progression={progress_data.progress}%")

                await ws.send_json(progress_data.model_dump_json())

                if progress_data.step == WsMediasProcessingInfoSchemaSteps.COMPLETED or progress_data.error_message is not None:
                    has_finished = True
                    break

            if has_finished:
                logger.info(f"Traitement de la story terminé pour l'intent {intent_id}")
                await self._cache.delete_upload_progress_stream(user_id_str, intent_id)
            else:
                logger.error(f"Nombre maximum de tentatives atteint pour l'intent {intent_id}")
                await ws.send_json(
                    WsMediasProcessingInfoSchema(
                        progress=0,
                        step=WsMediasProcessingInfoSchemaSteps.UNKNOWN,
                        timestamp=0,
                        error_message=Messages.INTERNAL_SERVER_ERROR
                    ).model_dump_json()
                )

        except WebSocketDisconnect:
            logger.info(f"Websocket de suivi pour la story {intent_id} déconnecté par le client")
            raise
        except Exception as e:
            logger.exception(f"Exception {e.__class__.__name__} lors du suivi de la story : {e}", exc_info=e)
            try:
                await ws.send_json(
                    WsMediasProcessingInfoSchema(
                        progress=0,
                        step=WsMediasProcessingInfoSchemaSteps.UNKNOWN,
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

    async def worker_service_save_processed_story_in_bd(self):
        pass

    async def _verify_story_can_been_processed(
        self, data: CreateStoryUploadIntentFullData, user_obj: ReadUser
    ) -> ServiceResult[str]:
        """
        Vérifie que l'utilisateur peut créer une story avec les données fournies.

        Args:
            data: Données complètes de la story
            user_obj: Utilisateur courant

        Returns:
            ServiceResult indiquant si la création est autorisée
        """
        academic_year_svc = AcademicYearService(self._raw_bd, self._raw_cache)
        club_member_svc = ClubMemberService(self._raw_bd, self._raw_cache)

        # Vérifier l'année académique si spécifiée
        if not data.academic_year_id:
            res = await academic_year_svc.get_active_academic_year()
            if res.is_error():
                return ServiceResult.service_error(
                    message=res.error,
                    status_code=res.status_code,
                    service_name=Messages.POST_SERVICE
                )
            data.academic_year_id = res.data.id

        # Vérifier les permissions du club
        if data.club_id:
            data.target_classe_id = None

            res = await club_member_svc.service_check_membership(data.club_id, user_obj.id)
            if res.is_error():
                return ServiceResult.service_error(
                    message=res.error,
                    status_code=res.status_code,
                    service_name=Messages.POST_SERVICE
                )

            # Un membre simple ne peut pas poster
            if res.data.role_in_club == ClubMembersType.SIMPLE_MEMBER:
                return ServiceResult.service_error(
                    message=Messages.USER_CANNOT_POST_IN_CLUB,
                    status_code=status.HTTP_403_FORBIDDEN,
                    service_name=Messages.POST_SERVICE
                )

        # Vérifier les permissions de classe
        elif data.only_for_a_class:
            data.club_id = None

            if user_obj.role != UserRole.DELEGATE or not user_obj.classe:
                return ServiceResult.service_error(
                    message=Messages.USER_CANNOT_POST_IN_CLASSE,
                    status_code=status.HTTP_403_FORBIDDEN,
                    service_name=Messages.POST_SERVICE
                )
            data.target_classe_id = user_obj.classe.id

        return ServiceResult.service_success(data="ok", status_code=status.HTTP_200_OK, service_name=Messages.POST_SERVICE)

