from logging import getLogger
from typing import Optional
from uuid import UUID

from app.cache.cache_utils import CacheUtils
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.cache_keys import CacheKey
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.globals.cache_duration import CacheDurartion
from app.schemas.story_upload_schemas import CreateStoryUploadIntentFullData

logger = getLogger(__name__)


def _seen_stories_key(user_id: UUID) -> CacheKey:
    """Génère la clé Redis pour les stories vues par un utilisateur."""
    return CacheKeysFactory.get_cache_key(AvailableCacheKeys.USER_DAILY_POST_SEEN).set_arguments(id=str(user_id))


class StoryCache:
    """Classe pour toutes les opérations de cache liées aux uploads de fichiers pour les stories."""

    def __init__(self, cache: CacheWrapper):
        self._cache = cache

    async def save_media_upload_intent(self, user_id: str, intent_id: str, intent_data: CreateStoryUploadIntentFullData) -> None:
        """
        Enregistre un intent d'upload de média story dans le cache.

        Args:
            user_id: ID de l'utilisateur
            intent_id: ID de l'intent d'upload
            intent_data: Données de l'intent d'upload

        Returns:
            None - l'intent d'upload est enregistré dans le cache
        """

        cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.STORY_FILE_UPLOAD_INTENT_KEY).set_arguments(
            user_id=user_id, intent_id=intent_id
        )

        try:
            await self._cache.save_pydantic_model_in_cache(
                cache_key,
                intent_data,
                CacheDurartion.UPLOAD_INTENT_DURATION.value
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def delete_media_upload_intent(self, user_id: str, intent_id: str) -> None:
        """
        Supprime l'intent du cache.

        Args:
            user_id: ID de l'utilisateur
            intent_id: ID de l'intent d'upload

        Returns:
            None
        """
        try:
            cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.STORY_FILE_UPLOAD_INTENT_KEY).set_arguments(
                user_id=user_id, intent_id=intent_id
            )
            await self._cache.delete_in_cache(cache_key)
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def get_media_upload_intent(self, user_id: str, intent_id: str) -> Optional[CreateStoryUploadIntentFullData]:
        """
        Récupère l'intent d'upload média story depuis le cache.

        Args:
            user_id: ID de l'utilisateur
            intent_id: ID de l'intent d'upload

        Returns:
            Les données de l'intent d'upload ou None si inexistant/expiré
        """

        cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.STORY_FILE_UPLOAD_INTENT_KEY).set_arguments(
            user_id=user_id, intent_id=intent_id
        )

        try:
            data = await self._cache.get_pydantic_model_from_cache(cache_key, CreateStoryUploadIntentFullData)
            return data
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None

    async def get_daily_seen_story_ids(self, user_id: UUID) -> list[UUID] | None:
        """Récupère la liste des UUIDs de stories déjà vues par l'utilisateur.

        Commande Redis : SMEMBERS user:{user_id}:seen_stories

        Returns:
            Liste de strings (UUIDs) si Redis répond, None si Redis crash.
            None déclenche le fallback PostgreSQL dans le service.
        """
        try:
            key = _seen_stories_key(user_id)
            members = await self._cache.get_from_a_set(key)
            result = [UUID(m) for m in members]
            logger.debug(
                "Cache hit seen_stories user=%s count=%d", user_id, len(result)
            )
            return result
        except Exception as e:
            logger.warning(
                "Redis unavailable (get_seen_stories) user=%s : %s — fallback PostgreSQL",
                user_id, e,
            )
            return None

    async def mark_stories_as_viewed(self, user_id: UUID, story_ids: list[UUID]) -> int | None:
        """Marque une liste de stories comme vues dans Redis.

        Opérations :
        1. SADD batch (un seul appel pour N stories)
        2. EXPIRE pour renouveler le TTL à 7 jours

        Args:
            user_id: ID de l'utilisateur.
            story_ids: Liste des stories à marquer comme vues.
        """
        if not story_ids:
            return None

        try:
            key = _seen_stories_key(user_id)

            str_ids = [str(sid) for sid in story_ids]

            res = await self._cache.add_to_a_set(key, *str_ids)

            logger.debug(
                "Stories marquées comme vues user=%s total_set=%d",
                user_id, res
            )
            return res

        except Exception as e:
            logger.error(f"Erreur lors du marquage d'une story comme vue user_id = {user_id}, story_ids = {story_ids}")
            CacheUtils.traiter_exceptions(e, logger)
            return None

    async def clear_daily_seen_stories_for_user(self, user_id: UUID) -> None:
        """Supprime complètement le SET des stories vues.

        Rarement utilisé — préférer mark_stories_as_viewed qui est idempotent.
        """
        try:
            key = _seen_stories_key(user_id)
            await self._cache.delete_in_cache(key)
            logger.info("SET seen_stories supprimé avec succès user=%s", user_id)
        except Exception as e:
            logger.warning(
                "Redis unavailable (clear_seen_stories) user=%s : %s", user_id, e
            )

