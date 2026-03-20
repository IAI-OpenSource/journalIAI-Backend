from alembic.util import status
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from sqlalchemy import select, update, insert
from app.db.models.event import Event, EventStatus
from app.repositories.repositories_utils import RepositoriesUtils
from app.schemas.events_schemas import EventCreate, EventUpdate, EventListReponse, EventRead
from typing import List
from uuid import UUID
from datetime import datetime
from . import CRUDResult
from app.globals.messages import Messages as msg
from dataclasses import dataclass
from sqlalchemy.exc import IntegrityError
import traceback
from typing import Optional






logger = logging.getLogger(__name__)



@dataclass
class EventRepository:
    """
    Repository gérant les opérations liées aux événements.

    Fournit des méthodes CRUD et de récupération des événements
    avec support de pagination et filtrage.
    """

    db: AsyncSession

    
    async def get_event(self) -> CRUDResult[List[Event]]:
        """
        Récupère la liste de tous les événements non supprimés.

        Returns:
            List[Event]: Liste des événements trouvés.

        Raises:
            CRUDResult.crud_error:
                - NOT_FOUND si aucun événement n'est trouvé.
                - INTERNAL_SERVER_ERROR en cas d'erreur de base de données.
        """

        try: 
            stmt = select(Event).where(Event.deleted_at == None).order_by(Event.start_date)
            result = await self.db.execute(stmt)
            events = result.scalars().all()
           
            
            if events is None:
                logger.info("Aucun events Trouve")
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=status._404_STATUS_NOT_FOUND.value)
            
            logger.info("Events recuperer avec succes !")
            return CRUDResult.crud_success(events)
        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)


    
    async def get_event_by_id(self, event_id: UUID) -> CRUDResult[EventRead]:
        """
        Récupère un événement par son identifiant.

        Args:
            event_id (UUID): Identifiant unique de l'événement.

        Returns:
            Event: L'événement trouvé.

        Raises:
            CRUDResult.crud_error:
                - NOT_FOUND si l'événement n'existe pas.
                - INTERNAL_SERVER_ERROR en cas d'erreur.
        """
        try:
            stmt = select(Event).where(Event.id == event_id).where(Event.deleted_at == None)
            result = await self.db.execute(stmt)
            event_ById = result.scalar_one_or_none()

            if event_ById is None:
                logger.info("Aucun event Trouve")
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=status._404_STATUS_NOT_FOUND.value)
            
            logger.info("Evens recuperer avec succes !")
            return CRUDResult.crud_success(event_ById)
        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

            


   
    async def get_events_by_status(self, status: EventStatus) -> CRUDResult[List[Event]]:
        """
        Récupère les événements filtrés par statut.

        Args:
            status (EventStatus): Statut des événements à récupérer.

        Returns:
            List[Event]: Liste des événements correspondant au statut.

        Raises:
            CRUDResult.crud_error:
                - NOT_FOUND si aucun événement n'est trouvé.
                - INTERNAL_SERVER_ERROR en cas d'erreur.
        """
        try:
            stmt = select(Event).where(Event.status == status).where(Event.deleted_at == None).order_by(Event.start_date)
            result = await self.db.execute(stmt)
            events = result.scalars().all()
            
            if events is None:
                    logger.info("Aucun event Trouve")
                    return CRUDResult.crud_error(msg.NOT_FOUND, status_code=status._404_STATUS_NOT_FOUND.value)
                    z
            logger.info("Events recuperer avec succes !")
            return CRUDResult.crud_success(events)
        
        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)


    
    async def create_event(self, event_data: EventCreate):
        """
        Crée un nouvel événement.

        Args:
            event_data (EventCreate): Données de l'événement à créer.

        Returns:
            Event: L'événement créé.

        Raises:
            CRUDResult.crud_error:
                - INTERNAL_SERVER_ERROR en cas d'erreur.
        """
        try:

            stmt = (
            insert(Event).values(**event_data
            .model_dump())
            .returning(Event)
            )
            result = await self.db.execute(stmt)
            db_event = result.scalar_one_or_none()
            if db_event is None:
                return CRUDResult.crud_error("Event not created")
            await self.db.commit()

            logger.info("Event ajoutée avec succès !")
            return CRUDResult.crud_success(db_event)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)



   
    async def update_event(self, event_id: UUID, data: EventUpdate):
        """
        Met à jour un événement existant.

        Args:
            event_id (UUID): Identifiant de l'événement à mettre à jour.
            data (EventUpdate): Données à mettre à jour.

        Returns:
            CRUDResult: L'événement mis à jour.

        Raises:
            CRUDResult.crud_error:
                - NOT_FOUND si l'événement n'existe pas.
                - INTERNAL_SERVER_ERROR en cas d'erreur.
        """
        try:
            stmt = (
                update(Event)
                .where(Event.id == event_id)
                .values(**data.model_dump(exclude_unset=True))
                .returning(Event)  
            )
            result = await self.db.execute(stmt)
            updated_event = result.scalar_one_or_none()

            if updated_event is None:
                logger.info(f"Event {event_id} introuvable pour la mise à jour")
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=404)

            await self.db.commit()

            logger.info(f"Event {event_id} mis à jour avec succès !")
            return CRUDResult.crud_success(updated_event)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)




    
    async def soft_delete_event(self, event_id: UUID):
        """
        Supprime logiquement un événement (soft delete).

        Args:
            event_id (UUID): Identifiant de l'événement à supprimer.

        Returns:
            CRUDResult: Résultat de l'opération.

        Raises:
            CRUDResult.crud_error:
                - INTERNAL_SERVER_ERROR en cas d'erreur.
        """
        try:
            await self.db.execute(
                update(Event)
                .where(Event.id == event_id)
                .values(deleted_at=datetime.utcnow())
                .returning(Event) 
            )
            await self.db.commit()

            logger.info("Event supprimer avec succès !")

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)


    
    async def get_events_paginated(self, cursor: Optional[UUID] = None, limit: int = 10) -> CRUDResult[EventRead]:
        """
        Récupère les événements avec pagination basée sur un curseur.

        Args:
            cursor (Optional[UUID]): Identifiant du dernier événement
                récupéré. Les résultats seront retournés après ce curseur.
            limit (int): Nombre maximum d'événements à récupérer.

        Returns:
            dict:
                - events (List[Event]): Liste des événements.
                - next_cursor (Optional[UUID]): Curseur pour la prochaine requête.

        Raises:
            CRUDResult.crud_error:
                - NOT_FOUND si aucun événement n'est trouvé.
                - INTERNAL_SERVER_ERROR en cas d'erreur.
        """
        try:
            query = select(Event).where(Event.deleted_at == None).order_by(Event.id)

            if cursor:
                query = query.where(Event.id > cursor)

            query = query.limit(limit)

            result = await self.db.execute(query)
            events = result.scalars().all()

            if not events:
                logger.info("Aucun événement trouvé")
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=404)

            next_cursor = events[-1].id if events else None

            logger.info("Événements récupérés avec succès !") 
            response = EventListReponse(
                events=events,
                next_cursor=next_cursor
            )
            return CRUDResult.crud_success(response.model_dump())

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)



async def get_event_by_title_and_date(self, title: str, start_date: datetime) -> CRUDResult:
    """
    Vérifie si un événement avec le même titre et la même date existe déjà.

    Args:
        title (str): Titre de l'événement.
        start_date (datetime): Date de début de l'événement.

    Returns:
        CRUDResult: L'événement trouvé ou None.
    """
    try:
        stmt = (
            select(Event)
            .where(Event.title == title)
            .where(Event.start_date == start_date)
            .where(Event.deleted_at == None)
        )
        result = await self.db.execute(stmt)
        event = result.scalar_one_or_none()

        return CRUDResult.crud_success(event)

    except IntegrityError as ie:
        return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)

    except Exception as e:
        return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
    


