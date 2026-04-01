## fichier contenant le service/logique métier des posts
## vous y trouverez les appels aux repositories (DB + Storage)

import logging
from typing import List
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.globals.messages import Messages
from app.repositories.post_repository import PostRepository
from app.schemas.post_schemas import (
    CreatePost,
    ReadPost,
    ReadPostList,
)

from . import ServiceResult
from ..cache.feed_cache import FeedCache
from ..cache.helpers.base import CacheWrapper

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
        academic_year_id: UUID,
        post_data: CreatePost,
    ) -> ServiceResult[ReadPost]:
        """Crée un post en base de données.

        author_id et academic_year_id sont injectés depuis le token JWT
        et le contexte académique actif — jamais depuis le body client.
        """
        result = await self.post_repo.insert_post(
            author_id=author_id,
            academic_year_id=academic_year_id,
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

    # Récupération d'un post par ID

    async def service_get_post(self, post_id: UUID) -> ServiceResult[ReadPost]:
        """Récupère un post par son ID avec ses médias."""
        result = await self.post_repo.get_post_by_id(post_id=post_id)

        if result.is_error():
            logger.error("Erreur récupération post id=%s : %s", post_id, result.error)
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

    # Feed paginé


    async def service_get_feed(
        self,
        user_id: UUID,
        academic_year_id: UUID,
        cursor: str | None = None,
        page_size: int = 20,
    ) -> ServiceResult[ReadPostList]:
        """Retourne une page du feed (cursor-based pagination)."""
        
        seen_post_ids: List[UUID] = await self.feed_cache.get_seen_post_ids(user_id=user_id)
        if seen_post_ids is None:
            logger.warning(
                "Redis indisponible — fallback PostgreSQL user=%s", user_id
            )
            fallback = await self.post_repo.get_seen_post_ids_from_db(user_id=user_id)
            # Si PostgreSQL aussi en erreur → feed sans exclusion (dégradé fonctionnel)
            seen_post_ids = fallback.data if not fallback.is_error() else []
            
        result = await self.post_repo.get_feed(
            academic_year_id=academic_year_id,
            seen_post_ids=seen_post_ids,
            cursor=cursor,
            page_size=page_size,
        )    
        
        if result.is_error():
            logger.error("Erreur récupération feed : %s", result.error)
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=Messages.POST_SERVICE,
            )
        items = result.data["items"]

        feed = ReadPostList(
            items=[ReadPost.model_validate(p) for p in items],
            next_cursor=result.data["next_cursor"],
            has_more=result.data["has_more"],
        )
        return ServiceResult.service_success(
            data=feed,
            status_code=result.status_code,
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
        self, post_id: UUID, user_id: UUID
    ) -> ServiceResult[None]:
        """Enregistre la vue d'un post — opération idempotente."""
        result = await self.post_repo.insert_post_view(
            post_id=post_id,
            user_id=user_id,
        )

        if result.is_error():
            logger.error("Erreur enregistrement vue : %s", result.error)
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=Messages.POST_SERVICE,
            )

        return ServiceResult.service_success(
            data=None,
            status_code=result.status_code,
        )
