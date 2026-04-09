from logging import getLogger
from typing import Optional

from app.cache.cache_utils import CacheUtils
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.globals.cache_duration import CacheDurartion
from app.schemas.post_upload_schemas import WsMediasProcessingInfoSchema
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

    async def verify_a_upload_is_in_processing(self, user_id: str, intent_id: str) -> bool:
        """
        Vérifie si un upload de story est en cours de post-traitement.

        Args:
            user_id: ID de l'utilisateur
            intent_id: ID de l'intent d'upload

        Returns:
            True si le post-traitement est en cours, False sinon
        """

        cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.STORY_FILE_UPLOAD_PROGRESS_STREAM_KEY).set_arguments(
            user_id=user_id, intent_id=intent_id
        )

        try:
            exists = await self._cache.exists_in_cache(cache_key)
            return exists
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return False

    async def add_upload_event_in_a_stream(
        self, user_id: str, intent_id: str, data: WsMediasProcessingInfoSchema, must_add_ttl: bool = False
    ) -> None:
        """
        Ajoute un événement de progression dans le stream de suivi d'un upload de story.

        Args:
            user_id: ID de l'utilisateur
            intent_id: ID de l'intent d'upload
            data: Données de progression
            must_add_ttl: Si True, ajoute un TTL au stream

        Returns:
            None
        """

        def ensure_compatibility(schema: WsMediasProcessingInfoSchema) -> dict:
            to_return = {
                "step": schema.step.value,
                "progress": schema.progress,
                "timestamp": schema.timestamp,
            }

            if schema.error_message:
                to_return["error_message"] = schema.error_message
            return to_return

        cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.STORY_FILE_UPLOAD_PROGRESS_STREAM_KEY).set_arguments(
            user_id=user_id, intent_id=intent_id
        )

        try:
            ttl = CacheDurartion.UPLOAD_PROGRESS_STREAM_DURATION.value if must_add_ttl else None
            await self._cache.add_data_in_stream(cache_key, data.model_dump_json(), ttl)
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def read_upload_progress_event_in_a_stream(
        self, user_id: str, intent_id: str, last_id: str | None
    ) -> tuple[Optional[WsMediasProcessingInfoSchema], str | None]:
        """
        Lit un événement de progression depuis le stream de suivi d'un upload de story.

        Args:
            user_id: ID de l'utilisateur
            intent_id: ID de l'intent d'upload
            last_id: Dernier ID d'événement lu

        Returns:
            Tuple (données de progression ou None, nouveau last_id)
        """
        cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.STORY_FILE_UPLOAD_PROGRESS_STREAM_KEY).set_arguments(
            user_id=user_id, intent_id=intent_id
        )

        try:
            res = await self._cache.read_from_stream(cache_key, last_id, 1)
            if not res or not res[0]:
                return None, last_id

            event_data = res[0][1]
            new_last_id = res[0][0]
            data = WsMediasProcessingInfoSchema.model_validate_json(event_data)
            return data, new_last_id
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None, last_id

    async def delete_upload_progress_stream(self, user_id: str, intent_id: str) -> None:
        """
        Supprime le stream de suivi d'un upload de story.

        Args:
            user_id: ID de l'utilisateur
            intent_id: ID de l'intent d'upload

        Returns:
            None
        """
        cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.STORY_FILE_UPLOAD_PROGRESS_STREAM_KEY).set_arguments(
            user_id=user_id, intent_id=intent_id
        )

        try:
            await self._cache.delete_in_cache(cache_key)
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

