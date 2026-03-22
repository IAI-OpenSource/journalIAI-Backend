from typing import Optional, List
from uuid import UUID
from logging import getLogger
import redis
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.cache_keys import CacheKey
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.schemas.events_schemas import EventRead, EventListReponse
from app.db.models.enums import EventStatus  # corrigé : vient de enums

logger = getLogger(__name__)


class EventCache:
    def __init__(self, cache: CacheWrapper):
        self.event_cache = cache
        self.message: Optional[str] = None

    # -------------------------------------------------------------------------
    # Clés de cache
    # -------------------------------------------------------------------------

    def create_event_cache_key(self, id: UUID) -> CacheKey:
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.EVENT_OBJECT
        ).set_arguments(id=id)

    def create_event_list_cache_key(self, cursor: Optional[UUID], limit: int) -> CacheKey:
        composite_id = f"{str(cursor) if cursor else 'start'}_{limit}"
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.EVENT_LIST
        ).set_arguments(id=composite_id)

    def create_event_status_cache_key(self, status: EventStatus) -> CacheKey:
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.EVENT_BY_STATUS
        ).set_arguments(id=status.value)

    # -------------------------------------------------------------------------
    # Cache : événement unique
    # -------------------------------------------------------------------------

    async def set_event_in_cache(self, event_id: UUID, event: EventRead, ttl: int) -> None:
        try:
            cache_key = self.create_event_cache_key(event_id)
            await self.event_cache.save_pydantic_model_in_cache(
                key=cache_key,
                model_instance=event,
                expire_seconds=ttl
            )
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la mise en cache de l'événement {event_id}")
        except Exception:
            logger.exception(f"Erreur lors de la mise en cache de l'événement {event_id}")

    async def get_event_from_cache(self, event_id: UUID) -> Optional[EventRead]:
        try:
            cache_key = self.create_event_cache_key(event_id)
            return await self.event_cache.get_pydantic_model_from_cache(
                key=cache_key,
                model_class=EventRead
            )
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la récupération de l'événement {event_id}")
            return None
        except Exception:
            logger.exception(f"Erreur lors de la récupération de l'événement {event_id}")
            return None

    async def delete_event_from_cache(self, event_id: UUID) -> None:
        try:
            cache_key = self.create_event_cache_key(event_id)
            await self.event_cache.delete_from_cache(key=cache_key)
            logger.info(f"Événement {event_id} supprimé du cache avec succès")
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la suppression de l'événement {event_id}")
        except Exception:
            logger.exception(f"Erreur lors de la suppression de l'événement {event_id} du cache")

    async def update_event_in_cache(self, event_id: UUID, event: EventRead, ttl: int) -> None:
        try:
            await self.delete_event_from_cache(event_id)
            await self.set_event_in_cache(event_id, event, ttl)
            logger.info(f"Événement {event_id} mis à jour dans le cache avec succès")
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la mise à jour de l'événement {event_id}")
        except Exception:
            logger.exception(f"Erreur lors de la mise à jour de l'événement {event_id} dans le cache")

    async def event_exists_in_cache(self, event_id: UUID) -> bool:
        try:
            cache_key = self.create_event_cache_key(event_id)
            return await self.event_cache.exists_in_cache(key=cache_key)
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la vérification de l'événement {event_id}")
            return False
        except Exception:
            logger.exception(f"Erreur lors de la vérification de l'événement {event_id} dans le cache")
            return False

    # -------------------------------------------------------------------------
    # Cache : liste paginée
    # -------------------------------------------------------------------------

    async def set_events_paginated_in_cache(
        self,
        cursor: Optional[UUID],
        limit: int,
        data: EventListReponse,
        ttl: int
    ) -> None:
        try:
            cache_key = self.create_event_list_cache_key(cursor, limit)
            await self.event_cache.save_pydantic_model_in_cache(
                key=cache_key,
                model_instance=data,
                expire_seconds=ttl
            )
            logger.info(f"Liste paginée (cursor={cursor}, limit={limit}) mise en cache avec succès")
        except redis.ConnectionError:
            logger.exception("Erreur de connexion Redis lors de la mise en cache de la liste paginée")
        except Exception:
            logger.exception("Erreur lors de la mise en cache de la liste paginée")

    async def get_events_paginated_from_cache(
        self,
        cursor: Optional[UUID],
        limit: int
    ) -> Optional[EventListReponse]:
        try:
            cache_key = self.create_event_list_cache_key(cursor, limit)
            return await self.event_cache.get_pydantic_model_from_cache(
                key=cache_key,
                model_class=EventListReponse
            )
        except redis.ConnectionError:
            logger.exception("Erreur de connexion Redis lors de la récupération de la liste paginée")
            return None
        except Exception:
            logger.exception("Erreur lors de la récupération de la liste paginée depuis le cache")
            return None

    async def delete_events_paginated_from_cache(
        self,
        cursor: Optional[UUID],
        limit: int
    ) -> None:
        try:
            cache_key = self.create_event_list_cache_key(cursor, limit)
            await self.event_cache.delete_from_cache(key=cache_key)
            logger.info(f"Cache liste paginée (cursor={cursor}, limit={limit}) supprimé avec succès")
        except redis.ConnectionError:
            logger.exception("Erreur de connexion Redis lors de la suppression du cache liste paginée")
        except Exception:
            logger.exception("Erreur lors de la suppression du cache liste paginée")

    # -------------------------------------------------------------------------
    # Cache : événements par statut
    # -------------------------------------------------------------------------

    async def set_events_by_status_in_cache(
        self,
        status: EventStatus,
        events: List[EventRead],
        ttl: int
    ) -> None:
        try:
            cache_key = self.create_event_status_cache_key(status)
            await self.event_cache.save_json_in_cache(
                key=cache_key,
                data=[e.model_dump(mode="json") for e in events],
                expire_seconds=ttl
            )
            logger.info(f"Événements avec statut '{status.value}' mis en cache avec succès")
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la mise en cache des événements statut {status.value}")
        except Exception:
            logger.exception(f"Erreur lors de la mise en cache des événements statut {status.value}")

    async def get_events_by_status_from_cache(
        self,
        status: EventStatus
    ) -> Optional[List[EventRead]]:
        try:
            cache_key = self.create_event_status_cache_key(status)
            raw = await self.event_cache.get_json_from_cache(key=cache_key)
            if raw is None:
                return None
            return [EventRead(**item) for item in raw]
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la récupération du statut {status.value}")
            return None
        except Exception:
            logger.exception(f"Erreur lors de la récupération des événements statut {status.value} depuis le cache")
            return None

    async def delete_events_by_status_from_cache(self, status: EventStatus) -> None:
        try:
            cache_key = self.create_event_status_cache_key(status)
            await self.event_cache.delete_from_cache(key=cache_key)
            logger.info(f"Cache statut '{status.value}' supprimé avec succès")
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la suppression du cache statut {status.value}")
        except Exception:
            logger.exception(f"Erreur lors de la suppression du cache statut {status.value}")