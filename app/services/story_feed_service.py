"""
Service pour la gestion du feed de stories.
Contient la logique métier pour récupérer et formater le feed paginé de stories.
"""

import logging
import time
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.cache.helpers.base import CacheWrapper
from app.cache.story_cache import StoryCache
from app.core.stream_token import create_stream_token
from app.db.models.enums import MediaType, StoryGroupsType, ClubMembersType, UserRole
from app.db.models.story_groups import StoryGroups
from app.globals.messages import Messages
from app.repositories.story_repository import StoryRepository
from app.schemas.global_schemas import StringMessage
from app.schemas.story_schemas import (
    StoryRead, StoryGroupRead, StoryAuthorSchema, StoryClubSchema, StoryClasseSchema, StoryGroupListResult,
)
from app.schemas.user_schemas import ReadUser
from app.services import ServiceResult
from app.services.club_member_service import ClubMemberService
from app.storage.media_read_storage import MediaReadStorage

logger = logging.getLogger(__name__)


# TODO : Ajouter une logique  journaliere pour supprimer les stories expirées
class StoryFeedService:
    """Service pour gérer le feed de stories."""

    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self._db = db
        self._cache = cache
        self.story_repo = StoryRepository(db)
        self.story_cache = StoryCache(cache)

    @staticmethod
    def _format_story_group(group: StoryGroups, user_id: str, viewed_story_ids: set[UUID]) -> StoryGroupRead:
        """
        Formate un groupe de stories brut de la DB en schéma StoryGroupRead.

        Args:
            group: Le groupe de stories depuis la DB.
            user_id: ID de l'utilisateur courant (pour les URLs avec token).
            viewed_story_ids: Set des IDs de stories vues par l'utilisateur.

        Returns:
            StoryGroupRead formaté avec URLs complètes et infos de vues.
        """
        # Formater l'auteur si présent (pour USER_GROUP)
        author_info: Optional[StoryAuthorSchema] = None
        if group.author:
            author_info = StoryAuthorSchema(
                **group.author.__dict__,
            )

        # Formater les infos du club si présentes (pour CLUB_GROUP)
        club_info: Optional[StoryClubSchema] = None
        if group.club:
            club_info = StoryClubSchema(
                **group.club.__dict__,
            )

        # Formater les infos de la classe si présentes (pour CLASSE_GROUP)
        target_classe_info: Optional[StoryClasseSchema] = None
        if group.classe:
            target_classe_info = StoryClasseSchema(
                **group.classe.__dict__,
            )

        # Formater chaque story du groupe
        stories_list: List[StoryRead] = []
        viewed_index_in_group: List[int] = []

        if group.stories:
            for i, story in enumerate(group.stories):
                prefix_path, key = story.media_url.split("/", 1)

                hls_url = None
                image_medium_url = None
                image_high_url = None

                if story.media_type == MediaType.VIDEO:
                    hls_url = MediaReadStorage.generate_story_read_hls_url(
                        key, create_stream_token(key, user_id, prefix_path),
                    )
                else:
                    image_medium_url = MediaReadStorage.generate_story_medium_post_image_url(
                        key, create_stream_token(key, user_id, prefix_path),
                    )

                    image_high_url = MediaReadStorage.generate_story_high_quality_post_image_url(
                        key, create_stream_token(key, user_id, prefix_path),
                    )

                # Vérifier si la story a été vue
                already_viewed = story.id in viewed_story_ids
                logger.warning(f"Valeur des vues bd : {story.views}")
                if already_viewed:
                    viewed_index_in_group.append(i)

                story_author_info = StoryAuthorSchema(
                    id=story.author.id,
                    username=story.author.username,
                    first_name=story.author.first_name,
                    last_name=story.author.last_name,
                    avatar_url=story.author.avatar_url,
                    role=story.author.role,
                    executive_role=story.author.executive_role,
                )

                story_read = StoryRead(
                    id=story.id,
                    author_id=story.author_id,
                    author=story_author_info,
                    media_type=story.media_type,
                    thumbnail_url=story.thumbnail_url,
                    hls_master_url=hls_url,
                    image_medium_url=image_medium_url,
                    image_high_url=image_high_url,
                    legend=story.legend,
                    width=story.width,
                    height=story.height,
                    blur_hash=story.blur_hash,
                    duration_seconds=story.duration_seconds,
                    already_viewed=already_viewed,
                    created_at=story.created_at,
                    expires_at=story.expires_at,
                )
                stories_list.append(story_read)

        return StoryGroupRead(
            id=group.id,
            group_type=group.group_type,
            author_id=group.author_id,
            author=author_info,
            club_id=group.club_id,
            club_info=club_info,
            target_classe_id=group.target_classe_id,
            target_classe_info=target_classe_info,
            stories=stories_list,
            stories_count=len(stories_list),
            viewed_index_in_group=viewed_index_in_group,
            updated_at=group.updated_at,
            expires_at=group.expires_at,
        )

    async def service_get_stories_feed(
        self,
        user_id: UUID,
        cursor: str | None = None,
        page_size: int = 20,
        user_classe_id: Optional[UUID] = None,
    ) -> ServiceResult[StoryGroupListResult]:
        """
        Récupère un feed paginé de groupes de stories.

        Args:
            user_id: ID de l'utilisateur courant.
            cursor: Curseur opaque de pagination.
            page_size: Nombre de groupes par page (0-20 max).
            user_classe_id: Classe de l'utilisateur

        Returns:
            ServiceResult avec le feed paginé ou une erreur.
        """

        # Récupérer les stories vues depuis le cache
        redis_seen_story_ids: List[UUID] = await self.story_cache.get_daily_seen_story_ids(user_id=user_id) or []

        userid_str = str(user_id)

        s = time.perf_counter()
        result = await self.story_repo.get_story_groups_feed(
            user_id=user_id,
            cursor=cursor,
            page_size=page_size,
            user_classe_id=user_classe_id,
        )

        logger.warning("Temps de réponse BD (stories feed) : %s secondes", time.perf_counter() - s)

        if result.is_error():
            logger.error("Erreur récupération feed de stories : %s", result.error)
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=Messages.STORY_SERVICE,
            )

        items = result.data["items"]
        s = time.perf_counter()

        viewed_story_ids_set = set(redis_seen_story_ids)  # Transformation en set parce que c'est plus rapideee

        viewed_story_ids_set.update(result.data["user_viewed_story_ids"])

        feed_result = StoryGroupListResult(
            items=[self._format_story_group(group, userid_str, viewed_story_ids_set) for group in items],
            next_cursor=result.data["next_cursor"],
            has_more=result.data["has_more"],
        )
        logger.warning("Temps de génération de liens dynamiques (stories) : %s secondes", time.perf_counter() - s)

        return ServiceResult.service_success(
            data=feed_result,
            status_code=result.status_code,
            service_name=Messages.STORY_SERVICE,
        )

    async def service_record_story_views(
        self, story_ids: List[UUID], user_id: UUID,
    ) -> ServiceResult[str]:
        """
        Enregistre des vues de stories — opération idempotente.

        Args:
            story_ids: IDs des stories vues.
            user_id: ID de l'utilisateur.

        Returns:
            ServiceResult avec succès ou erreur.
        """
        result = await self.story_cache.mark_stories_as_viewed(
            user_id=user_id,
            story_ids=story_ids,
        )

        if result and result > 0:
            await self.story_cache.add_user_to_daily_seen_stories(user_id)
            logger.info("Stories marquées comme vues user=%s count=%d", user_id, result)

        return ServiceResult.service_success(
            data="ok",
            status_code=status.HTTP_200_OK,
            service_name=Messages.STORY_SERVICE,
        )

    async def service_delete_story(
        self, story_id: UUID, story_group_id: UUID, user_obj: ReadUser
    ) -> ServiceResult[StringMessage]:
        """
        Supprime une story si l'utilisateur est l'auteur.

        Args:
            story_id: ID de la story à supprimer.
            story_group_id: ID du groupe de story auquel appartient la story
            user_obj: Infos sur l'utilisateur courant

        Returns:
            ServiceResult avec succès ou erreur.
        """
        verif_res = await self._verify_user_can_modify_story(
            story_id=story_id, user_obj=user_obj, group_id=story_group_id
        )

        if verif_res.is_error():
            return ServiceResult.service_error(
                message=verif_res.error,
                status_code=verif_res.status_code,
                service_name=Messages.STORY_SERVICE,
            )

        group_with_story = verif_res.data

        nb_stories = len(group_with_story.stories)
        if nb_stories <= 1:
            # Si c'est la dernière story du groupe, on supprime tout le groupe (cascade)
            delete_res = await self.story_repo.delete_story_group(group_with_story.id)
        else:
            # Sinon, on supprime juste la story ciblée
            delete_res = await self.story_repo.delete_story(story_id)

        return ServiceResult.service_success(
            data=StringMessage(message="Story supprimée avec succès."),
            status_code=status.HTTP_200_OK,
            service_name=Messages.STORY_SERVICE,
        )

    async def _verify_user_can_modify_story(
        self, group_id: UUID, user_obj: ReadUser, story_id: UUID,
    ) -> ServiceResult[StoryGroups]:
        """
        Vérifie si l'utilisateur peut modifier la storie, donc implicitement la group story.

        Args:
            group_id: ID du groupe de stories.
            user_obj: Infos sur l'utilisateur courant
            story_id: Id de la story.

        Returns:
            ServiceResult avec le groupe de stories ou une erreur d'autorisation.
        """

        group_result = await self.story_repo.get_story_group_by_id(group_id)

        if group_result.is_error():
            return ServiceResult.service_error(
                message=group_result.error,
                status_code=group_result.status_code,
                service_name=Messages.STORY_SERVICE,
            )

        group = group_result.data

        for sto in group.stories:
            if sto.id == story_id:
                break
        else:
            return ServiceResult.service_error(
                message="La story spécifiée n'appartient pas à ce groupe.",
                status_code=status.HTTP_404_NOT_FOUND,
                service_name=Messages.STORY_SERVICE,
            )

        can_modify = False
        match group.group_type:
            case StoryGroupsType.USER_GROUP:
                if group.author_id == user_obj.id:
                    can_modify = True
            case StoryGroupsType.CLUB_GROUP:
                club_member_svc = ClubMemberService(self._db, self._cache)
                if not group.club_id:
                    logger.warning(
                        f"CAS INCOHERENT : Groupe de story de type CLUB_GROUP sans club_id, group_id={group.id}"
                    )
                else:
                    res = await club_member_svc.service_check_membership(group.club_id, user_obj.id)
                    if res.is_error():
                        return ServiceResult.service_error(
                            message=res.error,
                            status_code=res.status_code,
                            service_name=Messages.STORY_SERVICE,
                        )

                    # Un membre simple de club ne peut pas y poster
                    if res.data.role_in_club != ClubMembersType.SIMPLE_MEMBER:
                        can_modify = True
            case StoryGroupsType.CLASSE_GROUP:
                if user_obj.can_post and user_obj.role == UserRole.DELEGATE and user_obj.classe and \
                        user_obj.classe.id == group.target_classe_id:

                    can_modify = True

        if not can_modify:
            return ServiceResult.service_error(
                message=Messages.USER_CANNOT_MODIFY_STORY,
                status_code=status.HTTP_403_FORBIDDEN,
                service_name=Messages.STORY_SERVICE,
            )

        return ServiceResult.service_success(
            data=group,
            status_code=status.HTTP_200_OK,
            service_name=Messages.STORY_SERVICE,
        )
