from logging import getLogger

from app.cache.cache_utils import CacheUtils
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.globals.cache_duration import CacheDurartion
from app.schemas.upload_schemas import CreateVideoUploadIntent

logger = getLogger(__name__)

class VideoUploadsCache:
    """Classe pour toutes les opérations de cache liées aux uploads de fichiers, comme la gestion des intents d'upload pour les utilisateurs"""

    def __init__(self, cache: CacheWrapper):
        self._cache = cache

    async def save_video_upload_intent(self, user_id: str, intent_data: CreateVideoUploadIntent) -> None:
        """
        Enregistre un intent d'upload video dans le cache pour les utilisateurs
        Args:
            user_id: Id de l'utilisateur
            intent_data: Le données de l'intent d'upload à enregistrer, conformes au schéma CreateVideoUploadIntent

        Returns:
            Rien du tout, mais l'intent d'upload est enregistré dans le cache pour une utilisation ultérieure
        """

        cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.FILE_UPLOAD_INTENT_KEY).set_arguments(
            user_id=user_id, file_name=intent_data.file_name
        )

        try:
            await self._cache.save_pydantic_model_in_cache(
                cache_key,
                intent_data,
                CacheDurartion.VIDEO_UPLOAD_INTENT_DURATION.value
            )
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)