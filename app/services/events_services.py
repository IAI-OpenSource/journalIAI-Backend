from dataclasses import dataclass
import logging
import traceback
from typing import Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.events_repository import EventRepository
from app.schemas.events_schemas import EventCreate, EventRead, EventUpdate
from app.db.models.event import EventStatus
from app.globals.messages import Messages as msg 

from . import ServiceResult


logger = logging.getLogger(__name__)

class EventService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.event_repo = EventRepository(self.db)


    async def service_find_event_by_id(self, event_id: UUID) -> ServiceResult[EventRead]:
        """Logique metier de recuperation d'un event par son ID"""

        event = await self.event_repo.get_event_by_id(event_id=event_id)

        if event.is_error():
            logger.error(f"Erreur: {event.error}")
            return ServiceResult.service_error(
               message=event.error,
               status_code=event.status_code,
               service_name=msg.EVENT_SERVICE
            )
        
        if EventRead.model_validate(event.data).is_deleted():
            logger.error(f"Erreur: {msg.DELETED_EVENT}")
            return ServiceResult.service_error(
                message=f"Erreur: {msg.DELETED_EVENT}",
                status_code=400,
                service_name=msg.EVENT_SERVICE
            )
        return ServiceResult.service_success(event.data, status_code=event.status_code)
    


    async def service_find_event_by_statut(self, statut: EventStatus) -> ServiceResult[EventRead]:
                """Logique metier de recuperation un event par son statut"""
                
                event = await self.event_repo.get_events_by_status(statut=statut)

                if event.is_error():
                    logger.error(f"Erreur: {event.error}")
                    return ServiceResult.service_error(
                    message=event.error,
                    status_code=event.status_code,
                    service_name=msg.EVENT_SERVICE
                    )


                active_events = [e for e in event.data if not EventRead.model_validate(e).is_deleted()]

                if not active_events:
                    logger.error(f"Erreur: {msg.DELETED_EVENT}")
                    return ServiceResult.service_error(
                        message=f"Erreur: {msg.DELETED_EVENT}",
                        status_code=404,
                        service_name=msg.EVENT_SERVICE
                        )

                return ServiceResult.service_success(active_events, status_code=event.status_code)


    async def service_find_all_event(self) -> ServiceResult[EventRead]:
                """Logique metier de recuperation tout les events"""

                events = await self.event_repo.get_event()

                if events.is_error():
                    logger.error(f"Erreur: {events.error}")
                    return ServiceResult.service_error(
                    message=events.error,
                    status_code=events.status_code,
                    service_name=msg.EVENT_SERVICE
                    )
                

                active_events = [e for e in events.data if not EventRead.model_validate(e).is_deleted()]

                if not active_events:
                    logger.warning(f"Erreur: {msg.EVENTS_NOT_FOUND}")
                    return ServiceResult.service_error(
                        message=f"Erreur: {msg.EVENTS_NOT_FOUND}",
                        status_code=404,
                        service_name=msg.EVENT_SERVICE
                    )

                return ServiceResult.service_success(
                    data=active_events,
                    service_name=msg.EVENT_SERVICE
                )
            

    async def service_create_event(self, event_data: EventCreate) -> ServiceResult[EventRead]:
        """Logique metier pour creer un event"""

        existing = await self.event_repo.get_event_by_title_and_date(
            title=event_data.title,
            start_date=event_data.start_date
        )

        if existing.is_error():
            logger.error(f"Erreur vérification doublon: {existing.error}")
            return ServiceResult.service_error(
                message=existing.error,
                status_code=existing.status_code,
                service_name=msg.EVENT_SERVICE
            )

        if existing.data is not None:
            logger.warning(f"Event déjà existant: {event_data.title} - {event_data.start_date}")
            return ServiceResult.service_error(
                message=msg.EVENT_ALREADY_EXISTS,
                status_code=409,  # Conflict
                service_name=msg.EVENT_SERVICE
            )

        event_obj = await self.event_repo.create_event(event_data=event_data)

        if event_obj.is_error():
            logger.error(f"Erreur création event: {event_obj.error}")
            return ServiceResult.service_error(
                message=event_obj.error,
                status_code=event_obj.status_code,
                service_name=msg.EVENT_SERVICE
            )

        try:
            created_event = EventRead.model_validate(event_obj.data)
        except Exception as e:
            logger.error(f"Erreur validation event créé: {e}")
            return ServiceResult.service_error(
                message=str(e),
                status_code=500,
                service_name=msg.EVENT_SERVICE
            )

        logger.info(f"Event créé avec succès: {created_event.id}")
        return ServiceResult.service_success(
            data=created_event,
            status_code=201,
            service_name=msg.EVENT_SERVICE
        )
        

    async def service_update_event(self, event_id: UUID, event_data: EventUpdate) -> ServiceResult[EventRead]:
        """Logique metier pour mettre a jour un event"""

        existing = await self.event_repo.get_event_by_id(event_id=event_id)

        if existing.is_error():
            logger.error(f"Erreur: {existing.error}")
            return ServiceResult.service_error(
                message=existing.error,
                status_code=existing.status_code,
                service_name=msg.EVENT_SERVICE
            )

        if EventRead.model_validate(existing.data).is_deleted():
            logger.error(f"Erreur: {msg.DELETED_EVENT}")
            return ServiceResult.service_error(
                message=f"Erreur: {msg.DELETED_EVENT}",
                status_code=400,
                service_name=msg.EVENT_SERVICE
            )

        updated = await self.event_repo.update_event(event_id=event_id, data=event_data)

        if updated.is_error():
            logger.error(f"Erreur mise à jour event {event_id}: {updated.error}")
            return ServiceResult.service_error(
                message=updated.error,
                status_code=updated.status_code,
                service_name=msg.EVENT_SERVICE
            )

        logger.info(f"Event mis à jour avec succès: {event_id}")
        return ServiceResult.service_success(
            data=updated.data,
            status_code=200,
            service_name=msg.EVENT_SERVICE
        )
    


    async def service_delete_event(self, event_id: UUID) -> ServiceResult[EventRead]:
        """Logique metier pour supprimer un event (soft delete)"""

        # 1. Vérifier que l'event existe et n'est pas déjà supprimé
        existing = await self.event_repo.get_event_by_id(event_id=event_id)

        if existing.is_error():
            logger.error(f"Erreur: {existing.error}")
            return ServiceResult.service_error(
                message=existing.error,
                status_code=existing.status_code,
                service_name=msg.EVENT_SERVICE
            )

        # 2. Vérifier qu'il n'est pas déjà supprimé
        if EventRead.model_validate(existing.data).is_deleted():
            logger.warning(f"Event {event_id} déjà supprimé")
            return ServiceResult.service_error(
                message=msg.DELETED_EVENT,
                status_code=400,
                service_name=msg.EVENT_SERVICE
            )

        # 3. Effectuer le soft delete
        deleted = await self.event_repo.soft_delete_event(event_id=event_id)

        if deleted is None or (hasattr(deleted, "is_error") and deleted.is_error()):
            logger.error(f"Erreur suppression event {event_id}")
            return ServiceResult.service_error(
                message=msg.DELETE_FAILED,
                status_code=500,
                service_name=msg.EVENT_SERVICE
            )

        logger.info(f"Event supprimé avec succès: {event_id}")
        return ServiceResult.service_success(
            data=None,
            status_code=204,
            service_name=msg.EVENT_SERVICE
        )