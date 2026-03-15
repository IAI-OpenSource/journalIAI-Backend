from dataclasses import dataclass
import logging
import traceback
from typing import Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.events_repository import EventRepository
from app.schemas.events_schemas import EventCreate, EventRead
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
                """Logique metier de recuperation tout les events"""


                
