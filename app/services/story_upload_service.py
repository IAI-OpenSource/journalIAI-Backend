"""
Service pour la gestion des uploads de médias pour les stories.
Contient la logique métier pour initialiser les uploads, générer les URLs, et finaliser le traitement.
"""

import secrets
from datetime import datetime, timedelta
from logging import getLogger
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status
from app.cache.helpers.base import CacheWrapper
from app.cache.processing_cache import ProcessingCache
from app.cache.story_cache import StoryCache
from app.db.models.enums import ClubMembersType, UserRole, StoryGroupsType
from app.db.models.stories import Story
from app.globals.messages import Messages
from app.repositories.story_repository import StoryRepository
from app.schemas.post_upload_schemas import AvailableUploadMethod
from app.schemas.story_upload_schemas import (
    CreateStoryUploadIntent, StoryUploadURLSchema, MediaUploadCompleteSchema, CreateStoryUploadIntentFullData,
    FileInUploadURLSchema
)
from app.schemas.user_schemas import ReadUser
from app.services import ServiceResult
from app.services.club_member_service import ClubMemberService
from app.storage.media_upload_storage import MediaUploadStorage
from app.worker.tasks.workers_task_names import WorkersTaskNames
from app.globals.others_constants import OtherConstants
from app.services.processing_service import ProcessingService

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
        self._processing_cache = ProcessingCache(cache)

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
            )

        random_intent_id = generate_random_intent_id(16)

        # Vérifier la taille du fichier
        file = intent_data.file
        if file.file_size >= OtherConstants.MAX_UPLOAD_FILE_SIZE:
            return ServiceResult.service_error(
                message=f"Le fichier {file.file_name} dépasse la taille maximale autorisée (100Mo), taille : {file.file_size} octets",
                status_code=status.HTTP_400_BAD_REQUEST,
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
            )

        # Ajouter un événement de progression initial
        processing_serv = ProcessingService(self._raw_cache)
        task_res = await processing_serv.send_processing_task(
            user_id=user_id_str,
            intent_id=intent_id,
            task_name=WorkersTaskNames.PROCESS_STORY_UPLOAD,
            queue_name=OtherConstants.MEDIA_PROCESSING_WORKER_QUEUE_NAME,
            task_kwargs={
                "intent_id": intent_id,
                "user_id": user_id_str,
                "story_data": intent_data.model_dump_json()
            }
        )

        if task_res.is_error():
            return ServiceResult.service_error(
                message=task_res.error, status_code=task_res.status_code, service_name= Messages.POST_SERVICE
            )

        # Supprimer l'intent du cache (marqué comme en cours de traitement)
        await self._cache.delete_media_upload_intent(user_id_str, intent_id)

        return ServiceResult.service_success(
            data=MediaUploadCompleteSchema(job_id=intent_id)
        )


    async def worker_service_save_processed_story_in_bd(
        self, user_id: str, intent_info: CreateStoryUploadIntentFullData,
        minio_url: str, thumbnail_url: str | None, height: int | None, width: int | None,
        duration: int | None, f_size: int | None, intent_id: str
    ) -> ServiceResult[str]:
        """
        Service appelé par le worker de traitement de story pour sauvegarder la story traitée
        dans la base de données.
        """
        try:
            logger.info(f"Début de la sauvegarde de la story traitée pour l'intent d'upload {intent_id} et user_id {user_id}")
            group_res = await self._bd.get_or_create_active_story_group(
                user_id=UUID(user_id),
                infos=intent_info,
                in_transaction=True
            )

            if group_res.is_error():
                logger.error(
                    f"Erreur lors de la récupération ou création du groupe de story pour l'intent d'upload"
                    f" {intent_id} et user_id {user_id} : {group_res.error}"
                )
                return ServiceResult.service_error(
                    message=group_res.error,
                    status_code=group_res.status_code,
                )
            logger.info(f"Groupe de story récupéré ou créé avec succès pour l'intent d'upload {intent_id} et user_id {user_id}, id du groupe : {group_res.data.id}")
            sto_group = group_res.data

            story_expire = datetime.now() + timedelta(hours=intent_info.story_duration_hours)

            story = Story(
                author_id=UUID(user_id),
                group_id=sto_group.id,
                expires_at=story_expire,
                media_type=intent_info.file.media_type,
                media_url=minio_url,
                thumbnail_url=thumbnail_url,
                duration_seconds=duration,
                width=width,
                height=height,
                file_size=f_size,
                legend=intent_info.legend,
            )
            logger.info(
                f"Story à sauvegarder créée pour l'intent d'upload {intent_id} et user_id {user_id},"
                f" media_url : {story.media_url}, thumbnail_url : {story.thumbnail_url}"
            )
            story_res = await self._bd.save_story(story, in_transaction=True)

            if story_res.is_error():
                logger.error(
                    f"Erreur lors de la sauvegarde de la story pour l'intent d'upload {intent_id} et"
                    f" user_id {user_id} : {story_res.error}"
                )
                return ServiceResult.service_error(
                    message=story_res.error,
                    status_code=story_res.status_code
                )

            sto = story_res.data
            if sto_group.expires_at < sto.expires_at:
                logger.info(f"Expiration du groupe de story {sto_group.id} mise à jour de {sto_group.expires_at} à {sto.expires_at} pour l'intent d'upload {intent_info} et user_id {user_id}")
                sto_group.expires_at = sto.expires_at

            sto_group.updated_at = datetime.now()
            
            logger.info(
                f"Commit des changements en cours pour la story traitée de l'intent d'upload {intent_id} et user_id {user_id}"
            )

            await self._raw_bd.commit()

            return ServiceResult.service_success(data="ok", status_code=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception(
                f"Exception {e.__class__.__name__} lors de la sauvegarde de la story traitée pour"
                f" l'intent : {intent_id}: {e}", exc_info=e
            )

            return ServiceResult.service_error(
                message=Messages.INTERNAL_SERVER_ERROR,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

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
        club_member_svc = ClubMemberService(self._raw_bd, self._raw_cache)

        # Vérifier les permissions du club
        if data.club_id:
            data.target_classe_id = None

            res = await club_member_svc.service_check_membership(data.club_id, user_obj.id)
            if res.is_error():
                return ServiceResult.service_error(
                    message=res.error,
                    status_code=res.status_code,
                )

            # Un membre simple de club ne peut pas y poster
            if res.data.role_in_club == ClubMembersType.SIMPLE_MEMBER:
                return ServiceResult.service_error(
                    message=Messages.USER_CANNOT_POST_IN_CLUB,
                    status_code=status.HTTP_403_FORBIDDEN,
                )

            data.target_group_type = StoryGroupsType.CLUB_GROUP

        # Vérifier les permissions de classe
        elif data.only_for_a_class:
            data.club_id = None

            if user_obj.role != UserRole.DELEGATE or not user_obj.classe:
                return ServiceResult.service_error(
                    message=Messages.USER_CANNOT_POST_IN_CLASSE,
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            data.target_classe_id = user_obj.classe.id
            data.target_group_type = StoryGroupsType.CLASSE_GROUP

        else:
            data.target_group_type = StoryGroupsType.USER_GROUP

        return ServiceResult.service_success(data="ok", status_code=status.HTTP_200_OK)

