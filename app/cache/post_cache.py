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

    async def verify_a_upload_is_in_processing(self, user_id: str, intent_id: str) -> bool:
        """
        Verifie dans le cache si un upload est en cours de post-traitement pour un intent d'upload video donné, en vérifiant l'existence d'une clé spécifique pour cet état
        Args:
            user_id: Id de l'utilisateur
            intent_id: Id de l'intent d'upload video

        Returns:
            True si le post-traitement de l'upload est en cours pour cet intent d'upload video, False sinon ou en cas d'erreur
        """

        cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.FILE_UPLOAD_PROGRESS_STREAM_KEY).set_arguments(
            user_id=user_id, intent_id=intent_id
        )

        try:
            return await self._cache.exists_in_cache(cache_key)
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return False

    async def add_upload_event_in_a_stream(
        self, user_id: str, intent_id: str, data: WsMediasProcessingInfoSchema,
        must_add_ttl: bool = False
    ) -> Optional[str]:
        """
        Ajoute un evenement dans le stream redis qui gère l'avancée des uploads
        Args:
            user_id: Id de l'utilisateur
            intent_id: Id de l'intent d'upload
            data:  La donnée à envoyer
            must_add_ttl: Indique si on doit mettre une expiration sur le stream, a utilisé seulement lors du premier
             ajout

        Returns:
            La clé généré automatiquement par Redis pour l'evenement ajouté
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

        cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.FILE_UPLOAD_PROGRESS_STREAM_KEY).set_arguments(
            user_id=user_id, intent_id=intent_id
        )

        try:
            res = await self._cache.stream_add(
                cache_key,
                ensure_compatibility(data)
            )

            if must_add_ttl:
                await self._cache.expire_in_cache(
                    cache_key, CacheDurartion.UPLOAD_PROGRESS_STREAM_DURATION.value
                )

            return res
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None

    async def read_upload_progress_event_in_a_stream(self, user_id: str, intent_id: str, last_id: str = None) -> tuple[Optional[WsMediasProcessingInfoSchema], Optional[str]]:
        """
            Lit les événements du stream redis qui gère l'avancée des uploads
        Args:
            user_id: L'id de l'utilisateur
            intent_id: Le id de l'intent d'upload
            last_id: Le id du dernier événement lu, pour ne lire que les événements suivants. Si None, lit le prochain événement disponible
        Returns:
            Un tuple contenant les données de l'événement lu, converties en objet WsMediasProcessingInfoSchema,
            et le id de cet événement dans le stream. Si une erreur survient ou si aucun événement n'est
            disponible, retourne (None, None)
        """

        cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.FILE_UPLOAD_PROGRESS_STREAM_KEY).set_arguments(
            user_id=user_id, intent_id=intent_id
        )

        try:
            event = await self._cache.stream_read(cache_key, last_id=last_id if last_id else "0-0", count=1, block=60000)

            if not event:
                return None, None

            # On convertit la donnée de l'événement en objet WsMediasProcessingInfoSchema
            progress_info = WsMediasProcessingInfoSchema.model_validate(event[0][1])

            return progress_info, event[0][0]
        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
            return None, None

    async def delete_upload_progress_stream(self, user_id: str, intent_id: str) -> None:
        """
        Supprimer le stream de suivi d'upload
        Args:
            user_id: L'id de l'utilisateur
            intent_id: Le id de l'intent d'upload

        Returns:
            None
        """
        cache_key = CacheKeysFactory.get_cache_key(AvailableCacheKeys.FILE_UPLOAD_PROGRESS_STREAM_KEY).set_arguments(
            user_id=user_id, intent_id=intent_id
        )

        try:

            await self._cache.delete_in_cache(cache_key)

        except Exception as e:
            CacheUtils.traiter_exceptions(e, logger)
