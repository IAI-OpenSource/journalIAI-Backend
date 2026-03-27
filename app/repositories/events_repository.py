from sqlalchemy.ext.asyncio import AsyncSession
import logging
from sqlalchemy import select, update, insert
from app.db.models.event import Event
from app.db.models.enums import EventStatus  # corrigé : vient de enums
from app.repositories.repositories_utils import RepositoriesUtils
from app.schemas.events_schemas import EventCreate, EventUpdate, ApiEventListReponse, EventInfo
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from . import CRUDResult
from app.globals.messages import Messages as msg
from dataclasses import dataclass
from sqlalchemy.exc import IntegrityError


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
            CRUDResult[List[Event]]: Liste des événements trouvés.
        """
        try:
            stmt = select(Event).where(Event.deleted_at == None).order_by(Event.start_date)
            result = await self.db.execute(stmt)
            events = result.scalars().all()

            logger.info("Events récupérés avec succès !")
            return CRUDResult.crud_success(events)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def get_event_by_id(self, event_id: UUID) -> CRUDResult[Event]:
        """
        Récupère un événement par son identifiant.

        Args:
            event_id (UUID): Identifiant unique de l'événement.

        Returns:
            CRUDResult[Event]: L'événement trouvé.
        """
        try:
            stmt = select(Event).where(Event.id == event_id).where(Event.deleted_at == None)
            result = await self.db.execute(stmt)
            event_by_id = result.scalar_one_or_none()

            if event_by_id is None:
                logger.info(f"Aucun event trouvé pour l'id {event_id}")
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=404)

            logger.info("Event récupéré avec succès !")
            return CRUDResult.crud_success(event_by_id)

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
            CRUDResult[List[Event]]: Liste des événements correspondant au statut.
        """
        try:
            stmt = (
                select(Event)
                .where(Event.status == status)
                .where(Event.deleted_at == None)
                .order_by(Event.start_date)
            )
            result = await self.db.execute(stmt)
            events = result.scalars().all()

            logger.info("Events récupérés avec succès !")
            return CRUDResult.crud_success(events)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def create_event(self, event_data: EventCreate) -> CRUDResult[Event]:
        """
        Crée un nouvel événement.

        Args:
            event_data (EventCreate): Données de l'événement à créer.

        Returns:
            CRUDResult[Event]: L'événement créé.
        """
        try:
            stmt = (
                insert(Event)
                .values(**event_data.model_dump())
                .returning(Event)
            )
            result = await self.db.execute(stmt)
            db_event = result.scalar_one_or_none()

            if db_event is None:
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=500)

            await self.db.commit()

            logger.info("Event créé avec succès !")
            return CRUDResult.crud_success(db_event)

        except IntegrityError as ie:
            await self.db.rollback() 
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)
        except Exception as e:
            await self.db.rollback()  
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def update_event(self, event_id: UUID, data: EventUpdate) -> CRUDResult[Event]:
        """
        Met à jour un événement existant.

        Args:
            event_id (UUID): Identifiant de l'événement à mettre à jour.
            data (EventUpdate): Données à mettre à jour.

        Returns:
            CRUDResult[Event]: L'événement mis à jour.
        """
        try:
            stmt = (
                update(Event)
                .where(Event.id == event_id)
                .where(Event.deleted_at == None)  # corrigé : on ne met pas à jour un event supprimé
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

    async def soft_delete_event(self, event_id: UUID) -> CRUDResult[Event]:
        """
        Supprime logiquement un événement (soft delete).

        Args:
            event_id (UUID): Identifiant de l'événement à supprimer.

        Returns:
            CRUDResult[Event]: L'événement supprimé.
        """
        try:
            stmt = (
                update(Event)
                .where(Event.id == event_id)
                .where(Event.deleted_at == None)  # corrigé : on ne supprime pas deux fois
                .values(deleted_at=datetime.now(timezone.utc))  # corrigé : utcnow() déprécié
                .returning(Event)
            )
            result = await self.db.execute(stmt)
            deleted_event = result.scalar_one_or_none()  # corrigé : on récupère le résultat

            if deleted_event is None:
                logger.info(f"Event {event_id} introuvable pour la suppression")
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=404)

            await self.db.commit()

            logger.info(f"Event {event_id} supprimé avec succès !")
            return CRUDResult.crud_success(deleted_event)  # corrigé : retourne un CRUDResult

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def get_events_paginated(self, cursor: Optional[UUID] = None, limit: int = 10) -> CRUDResult[List[Event]]:
        """
        Récupère les événements avec pagination basée sur un curseur.

        Args:
            cursor (Optional[UUID]): Identifiant du dernier événement récupéré.
            limit (int): Nombre maximum d'événements à récupérer.

        Returns:
            CRUDResult: dict avec events et next_cursor.
        """
        try:
            query = select(Event).where(Event.deleted_at == None).order_by(Event.id)

            if cursor:
                query = query.where(Event.id > cursor)

            query = query.limit(limit)

            result = await self.db.execute(query)
            events = result.scalars().all()

            next_cursor = events[-1].id if events else None

            logger.info("Événements paginés récupérés avec succès !")
            return CRUDResult.crud_success({
                "events": events,           # corrigé : on retourne les objets Event bruts
                "next_cursor": next_cursor  # le service s'occupe de la validation Pydantic
            })

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def get_event_by_title_and_date(self, title: str, start_date: datetime) -> CRUDResult[Event]:
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

            if event is None:
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=404)

            return CRUDResult.crud_success(event)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Event)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)