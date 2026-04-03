## fichier contenant le service/logique métier des posts
## vous y trouverez les appels aux repositories (DB + Storage)

import logging
import time
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.globals.messages import Messages
from app.repositories.post_repository import PostRepository
from app.schemas.post_schemas import (
    CreatePost,
    ReadPost,
    ReadPostList, PostClubSchema, PostEventSchema, PostAuthorSchema, PostMediaSchema,
)

from . import ServiceResult
from ..cache.feed_cache import FeedCache
from ..cache.helpers.base import CacheWrapper
from ..core.stream_token import create_stream_token
from ..db.models.enums import MediaType
from ..db.models.post import Post
from ..storage.post_read_storage import MediaReadStorage

logger = logging.getLogger(__name__)


class PostService:

    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.db = db
        self.post_repo = PostRepository(self.db)
        self.feed_cache = FeedCache(cache)

    # Création d'un post

    async def service_create_post(
        self,
        author_id: UUID,
        post_data: CreatePost,
    ) -> ServiceResult[ReadPost]:
        """Crée un post en base de données.

        author_id et academic_year_id sont injectés depuis le token JWT
        et le contexte académique actif — jamais depuis le body client.
        """
        # TODO: Changer ce mock
        result = await self.post_repo.insert_post(
            author_id=author_id,
            academic_year_id=UUID("5f594ab3-2560-4e5b-adbe-f20e5dd8e193"),
            post_data=post_data,
        )

        if result.is_error():
            logger.error("Erreur création post : %s", result.error)
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=Messages.POST_SERVICE,
            )

        post_read = ReadPost.model_validate(result.data)
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



    async def service_get_post(self, post_id: UUID, user_id: UUID, user_class_id: Optional[UUID] = None,) -> ServiceResult[ReadPost]:
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
        
        seen_post_ids: List[UUID] = await self.feed_cache.get_daily_seen_post_ids(user_id=user_id)
        userid_str = str(user_id)
        # TODO: Changer ce mock
        s = time.perf_counter()
        result = await self.post_repo.get_feed(
            academic_year_id=UUID("5f594ab3-2560-4e5b-adbe-f20e5dd8e193"),
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

    
    async def service_count_new_posts(
        self,
        academic_year_id: UUID,
        since: datetime,
    ) -> ServiceResult[dict]:
        """COUNT(*) posts créés depuis `since`. Appelé toutes les 60s.
 
        Retourne {"new_count": N}.
        Requête ultra-légère utilisant l'index sur created_at.
        """
        result = await self.post_repo.count_new_posts_since(
            academic_year_id=academic_year_id,
            since=since,
        )
        if result.is_error():
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=Messages.POST_SERVICE,
            )
        return ServiceResult.service_success(
            data={"new_count": result.data},
            status_code=result.status_code,)


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
