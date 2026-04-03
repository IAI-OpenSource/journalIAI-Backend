import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.events_repository import EventRepository
from app.cache.event_cache import EventCache
from app.cache.helpers.base import CacheWrapper
from app.globals.cache_duration import CacheDurartion
from app.schemas.events_schemas import EventCreate, EventUpdate, PaginatedEventListReponse, EventRead, \
    SimpleEventListResponse
from app.db.models.enums import EventStatus  # corrigé : vient de enums
from app.globals.messages import Messages as msg

from . import ServiceResult
from ..schemas.global_schemas import StringMessage

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

    async def service_find_event_by_statut(self, statut: EventStatus) -> ServiceResult[SimpleEventListResponse]:
        """Récupère les events par statut — cache en priorité."""

        # 1. Vérifier le cache
        cached = await self.event_cache.get_events_by_status_from_cache(statut)
        if cached is not None:
            logger.info(f"Events statut '{statut.value}' trouvés en cache")

            try:
                validated_cache = PaginatedEventListReponse(events=cached)
                return ServiceResult.service_success(validated_cache, status_code=200)
            except Exception as e:
                logger.warning(f"Cache corrompu pour la pagination: {e}. On force la lecture DB.")

        # 2. Sinon, aller en base
        events = await self.event_repo.get_events_by_status(status=statut)

        if events.is_error():
            logger.error(f"Erreur: {events.error}")
            return ServiceResult.service_error(
                message=events.error,
                status_code=events.status_code,
                service_name=msg.EVENT_SERVICE
            )

       

        validated = [EventRead.model_validate(e) for e in events.data]
        response = SimpleEventListResponse(events=validated)
        

        # 3. Mettre en cache
        await self.event_cache.set_events_by_status_in_cache(statut, validated, int(CacheDurartion.EVENT_DURATION))

        return ServiceResult.service_success(data=response, status_code=200)

   

    async def service_find_all_event(self) -> ServiceResult[SimpleEventListResponse]:
        """Récupère tous les events."""

        events = await self.event_repo.get_event()

        if events.is_error():
            logger.error(f"Erreur: {events.error}")
            return ServiceResult.service_error(
                message=events.error,
                status_code=events.status_code,
                service_name=msg.EVENT_SERVICE
            )
        
        validated = [EventRead.model_validate(e) for e in events.data]
        response = SimpleEventListResponse(events=validated)

        return ServiceResult.service_success(data=response, status_code=200, service_name=msg.EVENT_SERVICE)

    async def service_get_events_paginated(
        self, cursor: Optional[UUID] = None, limit: int = 10
    ) -> ServiceResult[PaginatedEventListReponse]:

        # 1. Vérifier le cache
        cached = await self.event_cache.get_events_paginated_from_cache(cursor, limit)
        if cached is not None:
            logger.info(f"Liste paginée (cursor={cursor}) trouvée en cache")
            return ServiceResult.service_success(cached, status_code=200)

        # 2. Sinon, aller en base
        events = await self.event_repo.get_events_paginated(cursor=cursor, limit=limit)

        if events.is_error():
            logger.error(f"Erreur pagination: {events.error}")
            return ServiceResult.service_error(
                message=msg.INTERNAL_SERVER_ERROR,
                status_code=events.status_code,
                service_name=msg.EVENT_SERVICE
            )

        try:
            paginated_data = events.data
            validated_events = [EventRead.model_validate(e) for e in paginated_data["events"]]
        except Exception as e:
            logger.error(f"{msg.EVENT_PAGINATION_ERROR}: {e}")
            return ServiceResult.service_error(
                message=msg.INTERNAL_SERVER_ERROR,
                status_code=500,
                service_name=msg.EVENT_SERVICE
            )

        # 3. Construire uniquement PaginatedEventListReponse — pas ApiPaginatedEventListReponse
        list_response = PaginatedEventListReponse(
            events=validated_events,
            next_cursor=paginated_data["next_cursor"]
        )

        # 4. Mettre en cache + cast int pour Redis
        await self.event_cache.set_events_paginated_in_cache(
            cursor, limit, list_response, int(CacheDurartion.EVENT_DURATION)
        )

        logger.info(f"Events récupérés — count: {len(validated_events)}")
        return ServiceResult.service_success(data=list_response, status_code=200)

    # -------------------------------------------------------------------------
    # Mutations
    # -------------------------------------------------------------------------

    async def service_create_event(self, event_data: EventCreate) -> ServiceResult[EventRead]:
        """Crée un event et invalide les caches associés."""

        # 1. Appel au repository
        event_obj = await self.event_repo.create_event(event_data=event_data)

        # 2. Gestion des erreurs du repo (ex: IntegrityError/Slug déjà existant)
        if event_obj.is_error():
            return ServiceResult.service_error(
                message=event_obj.error,
                status_code=event_obj.status_code,
                service_name=msg.EVENT_SERVICE
            )

        # 3. Validation Pydantic
        try:
            # created_event est maintenant une instance de EventRead
            created_event = EventRead.model_validate(event_obj.data)
        except Exception as e:
            logger.error(f"Erreur de validation Pydantic: {str(e)}")
            return ServiceResult.service_error(
                message=msg.INTERNAL_SERVER_ERROR,
                status_code=500, 
                service_name=msg.EVENT_SERVICE
            )

        # 4. Invalidation des caches
        # Utilisation du helper interne. Notez : created_event.status (pas .data.status)
        await self._invalidate_all_caches(
            event_id=created_event.id, 
            status=created_event.status
        )

        logger.info(f"{msg.EVENT_CREATE_SUCCES}: {created_event.id}")
        
        return ServiceResult.service_success(
            data=created_event, 
            status_code=201, 
            service_name=msg.EVENT_SERVICE
        )

    async def service_update_event(self, event_id: UUID, event_data: EventUpdate) -> ServiceResult[EventRead]:
        """Met à jour un event et invalide tous ses caches."""

        existing = await self.event_repo.get_event_by_id(event_id=event_id)

        if existing.is_error():
            return ServiceResult.service_error(
                message=existing.error,
                status_code=existing.status_code,
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
        await self._invalidate_all_caches(event_id, status=existing.data.status)
        created_event = EventRead.model_validate(updated.data)

        logger.info(f"{msg.EVENT_UPDATE_SUCCES}: {event_id}")
        return ServiceResult.service_success(data=created_event, status_code=200, service_name=msg.EVENT_SERVICE)

    async def service_delete_event(self, event_id: UUID) -> ServiceResult[StringMessage]:
        """Supprime (soft delete) un event et invalide tous ses caches."""

        existing = await self.event_repo.get_event_by_id(event_id=event_id)

        if existing.is_error():
            return ServiceResult.service_error(
                message=existing.error,
                status_code=existing.status_code,
                service_name=msg.EVENT_SERVICE
            )

        deleted = await self.event_repo.soft_delete_event(event_id=event_id)

        if deleted.is_error():  # corrigé : soft_delete_event retourne maintenant un CRUDResult
            return ServiceResult.service_error(
                message=msg.DELETE_FAILED,
                status_code=500,
                service_name=msg.EVENT_SERVICE
            )

        # Invalider tous les caches liés
        await self._invalidate_all_caches(event_id, status=existing.data.status)

        logger.info(f"{msg.EVENT_DELETE_SUCCESS}: {event_id}")
        return ServiceResult.service_success(
            data=StringMessage(message=msg.EVENT_DELETE_SUCCESS),
            status_code=200,  # corrigé : 204 ne renvoie pas de body, on met 200
            service_name=msg.EVENT_SERVICE
        )