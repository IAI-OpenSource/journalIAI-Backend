from logging import getLogger
from typing import Optional

from app.cache.cache_utils import CacheUtils
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.globals.cache_duration import CacheDurartion
from app.schemas.story_upload_schemas import CreateStoryUploadIntentFullData

logger = getLogger(__name__)


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