## fichier contenant le service/logique métier des posts
## vous y trouverez les appels aux repositories (DB + Storage)

import logging
import time
from typing import List, Optional, Union
from uuid import UUID
from datetime import datetime

from fastapi import status

from sqlalchemy.ext.asyncio import AsyncSession

from app.globals.messages import Messages
from app.repositories.post_repository import PostRepository
from app.schemas.post_schemas import (
    CreatePost,
    ReadPost,
    ReadPostList, PostClubSchema, PostEventSchema, PostAuthorSchema, PostMediaSchema, CreatePostFullData,
)

from . import ServiceResult
from .academic_year_service import AcademicYearService
from .club_member_service import ClubMemberService
from .events_services import EventService
from ..cache.feed_cache import FeedCache
from ..cache.helpers.base import CacheWrapper
from ..core.stream_token import create_stream_token
from ..db.models.enums import MediaType, ClubMembersType, UserRole
from ..db.models.post import Post
from ..schemas.post_upload_schemas import CreateMediaUploadIntentFullData
from ..schemas.user_schemas import ReadUser
from ..storage.media_read_storage import MediaReadStorage

logger = logging.getLogger(__name__)


class PostService:

    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.db = db
        self._cache = cache
        self.post_repo = PostRepository(self.db)
        self.feed_cache = FeedCache(cache)

    @staticmethod
    async def verify_post_can_been_processed(
        bd_session: AsyncSession, cache: CacheWrapper,
        data_to_vrify: Union[CreatePostFullData, CreateMediaUploadIntentFullData], user_obj: ReadUser
    ) -> ServiceResult[str]:
        """Vérifie que l'utilisateur a le droit de faire un post avec les données fournies"""
        academic_year_svc = AcademicYearService(bd_session, cache)
        club_member_svc = ClubMemberService(bd_session, cache)

        if data_to_vrify.for_current_academic_year:
            res = await academic_year_svc.get_active_academic_year()
            if res.is_error():
                return ServiceResult.service_error(
                    message=res.error,
                    status_code=res.status_code,
                    service_name=Messages.POST_SERVICE
                )
            data_to_vrify.academic_year_id = res.data.id

        if data_to_vrify.club_id:
            # Alors classe_id doit etre nul
            data_to_vrify.classe_id = None

            # On doit aussi vérifier si l'user peut post dans le club
            res = await club_member_svc.service_check_membership(data_to_vrify.club_id, user_obj.id)
            if res.is_error():
                return ServiceResult.service_error(
                    message=res.error,
                    status_code=res.status_code,
                    service_name=Messages.POST_SERVICE
                )
            # Un membre simple ne peut pas post
            if res.data.role_in_club == ClubMembersType.SIMPLE_MEMBER:
                return ServiceResult.service_error(
                    message=Messages.USER_CANNOT_POST_IN_CLUB,
                    status_code=status.HTTP_403_FORBIDDEN,
                    service_name=Messages.POST_SERVICE
                )

        elif data_to_vrify.only_for_a_class:
            # On doit récuperer la class dans laquelle l'utilisateur est déléguée

            data_to_vrify.club_id = None

            if user_obj.role != UserRole.DELEGATE or not user_obj.classe:
                return ServiceResult.service_error(
                    message=Messages.USER_CANNOT_POST_IN_CLASSE,
                    status_code=status.HTTP_403_FORBIDDEN,
                    service_name=Messages.POST_SERVICE
                )
            data_to_vrify.classe_id = user_obj.classe.id

            # On doit aussi mettre l'année académique si pas encore mis
            if not data_to_vrify.academic_year_id:
                res = await academic_year_svc.get_active_academic_year()
                if res.is_error():
                    return ServiceResult.service_error(
                        message=res.error,
                        status_code=res.status_code,
                        service_name=Messages.POST_SERVICE
                    )
                data_to_vrify.academic_year_id = res.data.id

        # Si il y'a un evenement on doit verifier s'il existe
        if data_to_vrify.event_id:
            evt = await EventService(bd_session, cache).service_find_event_by_id(data_to_vrify.event_id)
            if evt.is_error():
                return ServiceResult.service_error(
                    message=evt.error,
                    status_code=evt.status_code,
                    service_name=Messages.POST_SERVICE
                )
        return ServiceResult.service_success(data="ok", status_code=status.HTTP_200_OK, service_name=Messages.POST_SERVICE)

    async def service_create_text_post(
        self,
        user: ReadUser,
        post_data: CreatePost,
    ) -> ServiceResult[ReadPost]:
        """Crée un post textuel en base de données"""

        post_full_data = CreatePostFullData.model_validate(post_data, from_attributes=True)

        verif = await self.verify_post_can_been_processed(self.db, self._cache, post_full_data, user)

        if verif.is_error():
            return ServiceResult.service_error(
                message=verif.error,
                status_code=verif.status_code,
                service_name=Messages.POST_SERVICE
            )


        result = await self.post_repo.insert_text_post(user.id, post_full_data)

        if result.is_error():
            logger.error("Erreur création post : %s", result.error)
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=Messages.POST_SERVICE,
            )
        post = result.data
        author_schema = PostAuthorSchema.model_validate(user)
        author_schema.avatar_url = MediaReadStorage.generate_read_public_asset(user.avatar_url)
        post_read = ReadPost(**post.__dict__, author_info=author_schema)

        return ServiceResult.service_success(
            data=post_read,
            status_code=result.status_code,
        )

    @staticmethod
    def _format_post_infos(post : Post, user_id: str) -> ReadPost:
        """Formate les données d'un post model brut de la DB en le schéma réponse ReadPost"""
        club_info: Optional[PostClubSchema] = None
        event_info: Optional[PostEventSchema] = None
        user_info: Optional[PostAuthorSchema] = None
        medias_list: list[PostMediaSchema] = []

        if post.club:
            club_info = PostClubSchema(
                **post.club.__dict__
            )
            club_info.logo_url = MediaReadStorage.generate_read_public_asset(post.club.logo_url)
        if post.event:
            event_info = PostEventSchema.model_validate(post.event, from_attributes=True)
        if post.author:
            user_info = PostAuthorSchema(
                **post.author.__dict__
            )
            user_info.avatar_url=MediaReadStorage.generate_read_public_asset(post.author.avatar_url)
        if post.medias:
            for media in post.medias:
                bucket, key = media.media_url.split("/", 1)
                medias_list.append(
                    PostMediaSchema(
                        id=media.id,
                        thumbnail_url=MediaReadStorage.generate_read_public_asset(media.thumbnail_url),
                        width=media.width,
                        media_type=media.media_type,
                        blur_hash=media.blur_hash,
                        duration=media.duration,
                        created_at=media.created_at,
                        display_order=media.display_order,
                        hls_master_url=None if media.media_type == MediaType.IMAGE else
                        MediaReadStorage.generate_read_hls_url(key, create_stream_token(key, user_id, bucket)),
                        height=media.height,
                        image_medium_url= None if media.media_type == MediaType.VIDEO else
                        MediaReadStorage.generate_medium_post_image_url(key, create_stream_token(key, user_id, bucket)),
                        image_high_url= None if media.media_type == MediaType.VIDEO else
                        MediaReadStorage.generate_high_quality_post_image_url(key, create_stream_token(key, user_id, bucket))
                    )
                )

        return ReadPost(
            created_at=post.created_at,
            id=post.id,
            club_id=post.club_id,
            event_id=post.event_id,
            author_id=post.author_id,
            content=post.content,
            target_classe_id=post.target_classe_id,
            academic_year_id=post.academic_year,
            post_type=post.post_type,
            club_info=club_info,
            event_info=event_info,
            author_info=user_info,
            medias=medias_list,
            is_pinned=post.is_pinned,
            like_count=post.like_count,
            updated_at=post.updated_at,
            comment_count=post.comment_count
        )



    async def service_get_post(
        self, post_id: UUID, user_id: UUID, user_class_id: Optional[UUID] = None
    ) -> ServiceResult[ReadPost]:
        """Récupère un post par son ID avec ses médias."""
        result = await self.post_repo.get_post_by_id(post_id=post_id)

        if result.is_error():
            logger.error("Erreur récupération post id=%s : %s", post_id, result.error)
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=Messages.POST_SERVICE,
            )
        target_classe_id = result.data.target_classe_id

        if target_classe_id and user_class_id and  target_classe_id != user_class_id:
            logger.warning("Accès non autorisé au post id=%s pour user_class_id=%s", post_id, user_class_id)
            return ServiceResult.service_error(
                message="Accès non autorisé à ce post",
                status_code=403,
                service_name=Messages.POST_SERVICE,
            )

        post_read = self._format_post_infos(result.data, user_id=str(user_id))
        return ServiceResult.service_success(
            data=post_read,
            status_code=result.status_code,
            service_name=Messages.POST_SERVICE
        )

    # Feed paginé


    async def service_get_feed(
        self,
        user_id: UUID,
        cursor: str | None = None,
        page_size: int = 20,
        user_classe_id: Optional[UUID] = None,
    ) -> ServiceResult[ReadPostList]:
        """Retourne une page du feed (cursor-based pagination)."""
        
        current_academic_year_request = await AcademicYearService(self.db, self._cache).get_active_academic_year()
        if current_academic_year_request.is_error():
            return ServiceResult.service_error(
                message=current_academic_year_request.error,
                status_code=current_academic_year_request.status_code,
                service_name=Messages.POST_SERVICE
            )

        seen_post_ids: List[UUID] = await self.feed_cache.get_daily_seen_post_ids(user_id=user_id) or []
        userid_str = str(user_id)
        s = time.perf_counter()
        result = await self.post_repo.get_feed(
            academic_year_id=current_academic_year_request.data.id,
            seen_post_ids=seen_post_ids,
            cursor=cursor,
            page_size=page_size,
            user_id=user_id,
            classe_id=user_classe_id
        )
        logger.warning("Temps de réponse BD : %s secondes", time.perf_counter() - s)
        
        if result.is_error():
            logger.error("Erreur récupération feed : %s", result.error)
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=Messages.POST_SERVICE,
            )
        items = result.data["items"]
        s = time.perf_counter()
        feed = ReadPostList(
            items=[self._format_post_infos(p, userid_str) for p in items],
            next_cursor=result.data["next_cursor"],
            has_more=result.data["has_more"],
        )
        logger.warning("Temps de génération de liens dynamiqye : %s secondes", time.perf_counter() - s)


        return ServiceResult.service_success(
            data=feed,
            status_code=result.status_code,
            service_name=Messages.POST_SERVICE
        )



    # Enregistrement d'une vue

    async def service_record_view(
        self, post_ids: List[UUID], user_id: UUID
    ) -> ServiceResult[str]:
        """Enregistre des vues de posts — opération idempotente."""

        result = await self.feed_cache.mark_posts_as_seen(
            user_id=user_id,
            post_ids=post_ids
        )
        if result and result > 0:
            await self.feed_cache.add_user_to_daily_seen_posts(user_id)

        return ServiceResult.service_success(
            data="ok",
            status_code=200,service_name=Messages.POST_SERVICE,
        )
