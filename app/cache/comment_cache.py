from typing import Optional
from uuid import UUID
from logging import getLogger
import redis
from pydantic import BaseModel

from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.cache_keys import CacheKey
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.schemas.comment_schemas import CommentRead, PaginatedCommentListResponse

logger = getLogger(__name__)


class CommentCache:
    def __init__(self, cache: CacheWrapper):
        self.comment_cache = cache
        self.message: Optional[str] = None

    # -------------------------------------------------------------------------
    # Clés de cache
    # -------------------------------------------------------------------------
    @staticmethod
    def create_comment_cache_key(comment_id: UUID) -> CacheKey:
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.COMMENT_OBJECT
        ).set_arguments(id=str(comment_id))

    @staticmethod
    def create_comment_list_cache_key(post_id: UUID, cursor: Optional[UUID], limit: int) -> CacheKey:
        composite_id = f"{str(post_id)}_{str(cursor) if cursor else 'start'}_{limit}"
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.POST_COMMENTS
        ).set_arguments(id=composite_id)

    @staticmethod
    def create_replies_list_cache_key(parent_comment_id: UUID, cursor: Optional[UUID], limit: int) -> CacheKey:
        composite_id = f"{str(parent_comment_id)}_{str(cursor) if cursor else 'start'}_{limit}"
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.COMMENT_REPLIES
        ).set_arguments(id=composite_id)

    # -------------------------------------------------------------------------
    # Cache : commentaire unique
    # -------------------------------------------------------------------------

    async def set_comment_in_cache(self, comment_id: UUID, comment: CommentRead, ttl: int) -> None:
        try:
            cache_key = self.create_comment_cache_key(comment_id)
            await self.comment_cache.save_pydantic_model_in_cache(
                key=cache_key,
                model_instance=comment,
                expire_seconds=int(ttl)
            )
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la mise en cache du commentaire {comment_id}")
        except Exception as e:
            logger.exception(f"Erreur lors de la mise en cache du commentaire {comment_id} : {e}")

    async def get_comment_from_cache(self, comment_id: UUID) -> BaseModel | None:
        try:
            cache_key = self.create_comment_cache_key(comment_id)
            return await self.comment_cache.get_pydantic_model_from_cache(
                key=cache_key,
                model_class=CommentRead
            )
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la récupération du commentaire {comment_id}")
            return None
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération du commentaire {comment_id} : {e}")
            return None

    async def delete_comment_from_cache(self, comment_id: UUID) -> None:
        try:
            cache_key = self.create_comment_cache_key(comment_id)
            await self.comment_cache.delete_in_cache(key=cache_key)
            logger.info(f"Commentaire {comment_id} supprimé du cache avec succès")
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la suppression du commentaire {comment_id}")
        except Exception as e:
            logger.exception(f"Erreur lors de la suppression du commentaire {comment_id} du cache : {e}")

    async def update_comment_in_cache(self, comment_id: UUID, comment: CommentRead, ttl: int) -> None:
        try:
            await self.delete_comment_from_cache(comment_id)
            await self.set_comment_in_cache(comment_id, comment, int(ttl))
            logger.info(f"Commentaire {comment_id} mis à jour dans le cache avec succès")
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la mise à jour du commentaire {comment_id}")
        except Exception as e:
            logger.exception(f"Erreur lors de la mise à jour du commentaire {comment_id} dans le cache : {e}")

    async def comment_exists_in_cache(self, comment_id: UUID) -> bool:
        try:
            cache_key = self.create_comment_cache_key(comment_id)
            return await self.comment_cache.exists_in_cache(key=cache_key)
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la vérification du commentaire {comment_id}")
            return False
        except Exception as e:
            logger.exception(f"Erreur lors de la vérification du commentaire {comment_id} dans le cache : {e}")
            return False

    # -------------------------------------------------------------------------
    # Cache : liste paginée de commentaires (par post)
    # -------------------------------------------------------------------------

    async def set_comments_paginated_in_cache(
        self, post_id: UUID, cursor: Optional[UUID], limit: int,
        data: PaginatedCommentListResponse, ttl: int
    ) -> None:
        try:
            cache_key = self.create_comment_list_cache_key(post_id, cursor, limit)
            await self.comment_cache.save_pydantic_model_in_cache(
                key=cache_key,
                model_instance=data,
                expire_seconds=int(ttl)
            )
            logger.info(f"Liste paginée de commentaires (post={post_id}, cursor={cursor}) mise en cache avec succès")
        except redis.ConnectionError:
            logger.exception("Erreur de connexion Redis lors de la mise en cache de la liste paginée de commentaires")
        except Exception as e:
            logger.exception(f"Erreur lors de la mise en cache de la liste paginée de commentaires : {e}")

    async def get_comments_paginated_from_cache(
        self, post_id: UUID, cursor: Optional[UUID], limit: int
    ) -> BaseModel | None:
        try:
            cache_key = self.create_comment_list_cache_key(post_id, cursor, limit)
            return await self.comment_cache.get_pydantic_model_from_cache(
                key=cache_key,
                model_class=PaginatedCommentListResponse
            )
        except redis.ConnectionError:
            logger.exception("Erreur de connexion Redis lors de la récupération de la liste paginée de commentaires")
            return None
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération de la liste paginée de commentaires depuis le cache : {e}")
            return None

    async def delete_comments_paginated_from_cache(
        self, post_id: UUID, cursor: Optional[UUID], limit: int
    ) -> None:
        try:
            cache_key = self.create_comment_list_cache_key(post_id, cursor, limit)
            await self.comment_cache.delete_in_cache(key=cache_key)
            logger.info(f"Cache liste paginée de commentaires (post={post_id}, cursor={cursor}) supprimé avec succès")
        except redis.ConnectionError:
            logger.exception("Erreur de connexion Redis lors de la suppression du cache liste paginée de commentaires")
        except Exception as e:
            logger.exception(f"Erreur lors de la suppression du cache liste paginée de commentaires : {e}")

    # -------------------------------------------------------------------------
    # Cache : liste paginée de réponses (par commentaire parent)
    # -------------------------------------------------------------------------

    async def set_replies_paginated_in_cache(
        self, parent_comment_id: UUID, cursor: Optional[UUID], limit: int,
        data: PaginatedCommentListResponse, ttl: int
    ) -> None:
        try:
            cache_key = self.create_replies_list_cache_key(parent_comment_id, cursor, limit)
            await self.comment_cache.save_pydantic_model_in_cache(
                key=cache_key,
                model_instance=data,
                expire_seconds=int(ttl)
            )
            logger.info(f"Liste paginée de réponses (parent={parent_comment_id}, cursor={cursor}) mise en cache avec succès")
        except redis.ConnectionError:
            logger.exception("Erreur de connexion Redis lors de la mise en cache des réponses paginées")
        except Exception as e:
            logger.exception(f"Erreur lors de la mise en cache des réponses paginées : {e}")

    async def get_replies_paginated_from_cache(
        self, parent_comment_id: UUID, cursor: Optional[UUID], limit: int
    ) -> BaseModel | None:
        try:
            cache_key = self.create_replies_list_cache_key(parent_comment_id, cursor, limit)
            return await self.comment_cache.get_pydantic_model_from_cache(
                key=cache_key,
                model_class=PaginatedCommentListResponse
            )
        except redis.ConnectionError:
            logger.exception("Erreur de connexion Redis lors de la récupération des réponses paginées")
            return None
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération des réponses paginées depuis le cache : {e}")
            return None

    async def delete_replies_paginated_from_cache(
        self, parent_comment_id: UUID, cursor: Optional[UUID], limit: int
    ) -> None:
        try:
            cache_key = self.create_replies_list_cache_key(parent_comment_id, cursor, limit)
            await self.comment_cache.delete_in_cache(key=cache_key)
            logger.info(f"Cache réponses paginées (parent={parent_comment_id}) supprimé avec succès")
        except redis.ConnectionError:
            logger.exception("Erreur de connexion Redis lors de la suppression du cache des réponses paginées")
        except Exception as e:
            logger.exception(f"Erreur lors de la suppression du cache des réponses paginées : {e}")