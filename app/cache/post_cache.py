from logging import getLogger
from typing import Optional

from app.cache.cache_utils import CacheUtils
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.globals.cache_duration import CacheDurartion
from app.schemas.post_upload_schemas import WsMediasProcessingInfoSchema, CreateMediaUploadIntentFullData

logger = getLogger(__name__)

class PostCache:
    """Classe pour toutes les opérations de cache liées aux uploads de fichiers, comme la gestion des intents d'upload pour les utilisateurs"""

    def __init__(self, cache: CacheWrapper):
        self._cache = cache

    async def save_media_upload_intent(self, user_id: str, intent_id: str, intent_data: CreateMediaUploadIntentFullData) -> None:
        """
        Enregistre un intent d'upload de nmédia dans le cache pour les utilisateurs
        Args:
            user_id: Id de l'utilisateur
            intent_id: Id de l'intent d'upload medias
            intent_data: Le données de l'intent d'upload à enregistrer, conformes au schéma CreateMediaUploadIntentFullData

        Returns:
            Rien du tout, mais l'intent d'upload est enregistré dans le cache pour une utilisation ultérieure
        """

        cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.FILE_UPLOAD_INTENT_KEY).set_arguments(
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
        Supprime l'intent du cache
        Args:
            user_id: Id de l'utilisateur
            intent_id: Id de l'intent d'upload média

        Returns:
            Rien du tout
        """
        try:
            cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.FILE_UPLOAD_INTENT_KEY).set_arguments(
                user_id=user_id, intent_id=intent_id
            )
            await self._cache.delete_in_cache(cache_key)
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)

    async def get_media_upload_intent(self, user_id: str, intent_id: str) -> Optional[CreateMediaUploadIntentFullData]:
        """
        Recupere l'intent d'upload média depuis le cache pour les utilisateurs, en utilisant l'user_id et l'intent_id
        pour construire la clé de cache correspondante, et retourne les données de l'intent d'upload si elles existent et sont valides, ou None sinon
        Args:
            user_id: Id de l'utilisateur
            intent_id: Id de l'intent d'upload média

        Returns:
            Les données de l'intent d'upload média récupérées du cache, conformes au schéma CreateMediaUploadIntentFullData,
            ou None si l'intent n'existe pas ou a expiré
        """

        cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.FILE_UPLOAD_INTENT_KEY).set_arguments(
            user_id=user_id, intent_id=intent_id
        )

        try:
            data = await self._cache.get_pydantic_model_from_cache(cache_key, CreateMediaUploadIntentFullData)
            return data
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None