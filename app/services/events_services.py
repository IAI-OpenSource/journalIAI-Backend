from dataclasses import dataclass
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.events_repository import EventRepository
from app.cache.event_cache import EventCache
from app.cache.helpers.base import CacheWrapper
from app.globals.cache_duration import CacheDurartion 
from app.schemas.events_schemas import EventCreate, EventRead, EventUpdate, EventListReponse
from app.db.models.event import EventStatus
from app.globals.messages import Messages as msg

from . import ServiceResult

logger = logging.getLogger(__name__)


class EventService:
    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.db = db
        self.event_repo = EventRepository(self.db)
        self.event_cache = EventCache(cache)

    # -------------------------------------------------------------------------
    # Helpers d'invalidation
    # -------------------------------------------------------------------------

    async def _invalidate_all_caches(self, event_id: UUID, status: Optional[EventStatus] = None) -> None:
        """Invalide tous les caches liés à un événement après une mutation."""
        await self.event_cache.delete_event_from_cache(event_id)
        await self.event_cache.delete_events_paginated_from_cache(cursor=None, limit=10)
        if status:
            await self.event_cache.delete_events_by_status_from_cache(status)

    # -------------------------------------------------------------------------
    # Lecture
    # -------------------------------------------------------------------------

    async def service_find_event_by_id(self, event_id: UUID) -> ServiceResult[EventRead]:
        """Récupère un event par son ID — cache en priorité."""

        # 1. Vérifier le cache
        cached = await self.event_cache.get_event_from_cache(event_id)
        if cached is not None:
            logger.info(f"Event {event_id} trouvé en cache")
            if cached.is_deleted():
                return ServiceResult.service_error(
                    message=msg.DELETED_EVENT,
                    status_code=400,
                    service_name=msg.EVENT_SERVICE
                )
            return ServiceResult.service_success(cached, status_code=200)

        # 2. Sinon, aller en base
        event = await self.event_repo.get_event_by_id(event_id=event_id)

        if event.is_error():
            logger.error(f"Erreur: {event.error}")
            return ServiceResult.service_error(
                message=event.error,
                status_code=event.status_code,
                service_name=msg.EVENT_SERVICE
            )

        validated = EventRead.model_validate(event.data)

        if validated.is_deleted():
            return ServiceResult.service_error(
                message=msg.DELETED_EVENT,
                status_code=400,
                service_name=msg.EVENT_SERVICE
            )

        # 3. Mettre en cache
        await self.event_cache.set_event_in_cache(event_id, validated, CacheDurartion.EVENT_DURATION)

        return ServiceResult.service_success(validated, status_code=200)

    async def service_find_event_by_statut(self, statut: EventStatus) -> ServiceResult:
        """Récupère les events par statut — cache en priorité."""

        # 1. Vérifier le cache
        cached = await self.event_cache.get_events_by_status_from_cache(statut)
        if cached is not None:
            logger.info(f"Events statut '{statut.value}' trouvés en cache")
            return ServiceResult.service_success(cached, status_code=200)

        # 2. Sinon, aller en base
        event = await self.event_repo.get_events_by_status(statut=statut)

        if event.is_error():
            logger.error(f"Erreur: {event.error}")
            return ServiceResult.service_error(
                message=event.error,
                status_code=event.status_code,
                service_name=msg.EVENT_SERVICE
            )

        active_events = [
            EventRead.model_validate(e) for e in event.data
            if not EventRead.model_validate(e).is_deleted()
        ]

        if not active_events:
            return ServiceResult.service_error(
                message=msg.DELETED_EVENT,
                status_code=404,
                service_name=msg.EVENT_SERVICE
            )

        # 3. Mettre en cache
        await self.event_cache.set_events_by_status_in_cache(statut, active_events, CacheDurartion.EVENT_DURATION)

        return ServiceResult.service_success(active_events, status_code=200)

    async def service_find_all_event(self) -> ServiceResult:
        """Récupère tous les events."""

        events = await self.event_repo.get_event()

        if events.is_error():
            logger.error(f"Erreur: {events.error}")
            return ServiceResult.service_error(
                message=events.error,
                status_code=events.status_code,
                service_name=msg.EVENT_SERVICE
            )

        active_events = [
            e for e in events.data
            if not EventRead.model_validate(e).is_deleted()
        ]

        if not active_events:
            return ServiceResult.service_error(
                message=msg.EVENTS_NOT_FOUND,
                status_code=404,
                service_name=msg.EVENT_SERVICE
            )

        return ServiceResult.service_success(data=active_events, service_name=msg.EVENT_SERVICE)

    async def service_get_events_paginated(
        self, cursor: Optional[UUID] = None, limit: int = 10
    ) -> ServiceResult:
        """Récupère les events avec pagination — cache en priorité."""

        # 1. Vérifier le cache
        cached = await self.event_cache.get_events_paginated_from_cache(cursor, limit)
        if cached is not None:
            logger.info(f"Liste paginée (cursor={cursor}) trouvée en cache")
            return ServiceResult.service_success(cached.model_dump(), status_code=200)

        # 2. Sinon, aller en base
        events = await self.event_repo.get_events_paginated(cursor=cursor, limit=limit)

        if events.is_error():
            logger.error(f"Erreur pagination: {events.error}")
            return ServiceResult.service_error(
                message=events.error,
                status_code=events.status_code,
                service_name=msg.EVENT_SERVICE
            )

        try:
            paginated_data = events.data
            validated_events = [EventRead.model_validate(e) for e in paginated_data["events"]]
        except Exception as e:
            logger.error(f"{msg.EVENT_PAGINATION_ERROR}: {e}")
            return ServiceResult.service_error(
                message=str(e),
                status_code=500,
                service_name=msg.EVENT_SERVICE
            )

        # 3. Mettre en cache
        response = EventListReponse(
            events=validated_events,
            next_cursor=paginated_data["next_cursor"]
        )
        await self.event_cache.set_events_paginated_in_cache(cursor, limit, response, CacheDurartion.EVENT_DURATION)

        logger.info(f"Events récupérés — count: {len(validated_events)}")
        return ServiceResult.service_success(
            data={
                "events": validated_events,
                "next_cursor": paginated_data["next_cursor"],
                "count": len(validated_events)
            },
            status_code=200,
            service_name=msg.EVENT_SERVICE
        )

    # -------------------------------------------------------------------------
    # Mutations
    # -------------------------------------------------------------------------

    async def service_create_event(self, event_data: EventCreate) -> ServiceResult[EventRead]:
        """Crée un event et invalide les caches liste/statut."""

        existing = await self.event_repo.get_event_by_title_and_date(
            title=event_data.title,
            start_date=event_data.start_date
        )

        if existing.is_error():
            return ServiceResult.service_error(
                message=existing.error,
                status_code=existing.status_code,
                service_name=msg.EVENT_SERVICE
            )

        if existing.data is not None:
            return ServiceResult.service_error(
                message=msg.EVENT_ALREADY_EXISTS,
                status_code=409,
                service_name=msg.EVENT_SERVICE
            )

        event_obj = await self.event_repo.create_event(event_data=event_data)

        if event_obj.is_error():
            return ServiceResult.service_error(
                message=event_obj.error,
                status_code=event_obj.status_code,
                service_name=msg.EVENT_SERVICE
            )

        try:
            created_event = EventRead.model_validate(event_obj.data)
        except Exception as e:
            return ServiceResult.service_error(message=str(e), status_code=500, service_name=msg.EVENT_SERVICE)

        # Invalider liste paginée + cache statut
        await self.event_cache.delete_events_paginated_from_cache(cursor=None, limit=10)
        await self.event_cache.delete_events_by_status_from_cache(created_event.status)

        logger.info(f"{msg.EVENT_CREATE_SUCCES}: {created_event.id}")
        return ServiceResult.service_success(data=created_event, status_code=201, service_name=msg.EVENT_SERVICE)

    async def service_update_event(self, event_id: UUID, event_data: EventUpdate) -> ServiceResult[EventRead]:
        """Met à jour un event et invalide tous ses caches."""

        existing = await self.event_repo.get_event_by_id(event_id=event_id)

        if existing.is_error():
            return ServiceResult.service_error(
                message=existing.error,
                status_code=existing.status_code,
                service_name=msg.EVENT_SERVICE
            )

        validated_existing = EventRead.model_validate(existing.data)

        if validated_existing.is_deleted():
            return ServiceResult.service_error(
                message=msg.DELETED_EVENT,
                status_code=400,
                service_name=msg.EVENT_SERVICE
            )

        updated = await self.event_repo.update_event(event_id=event_id, data=event_data)

        if updated.is_error():
            return ServiceResult.service_error(
                message=updated.error,
                status_code=updated.status_code,
                service_name=msg.EVENT_SERVICE
            )

        # Invalider tous les caches liés
        await self._invalidate_all_caches(event_id, status=validated_existing.status)

        logger.info(f"{msg.EVENT_UPDATE_SUCCES}: {event_id}")
        return ServiceResult.service_s