from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import logging
from sqlalchemy import select, update, func, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.notification import Notification
from app.repositories import CRUDResult
from app.repositories.repositories_utils import RepositoriesUtils
from app.schemas.notification_schemas import NotificationCreate
from app.globals.messages import Messages as msg

logger = logging.getLogger(__name__)



@dataclass
class NotificationRepository:
    """Repository pour gérer les notifications."""

    db: AsyncSession

    async def create_notification(self, data: NotificationCreate) -> CRUDResult[Notification]:
        try:
            stmt = (
                insert(Notification)
                .values(**data.model_dump())
                .returning(Notification)
            )
            result = await self.db.execute(stmt)
            notif = result.scalar_one()
            await self.db.commit()

            logger.info(f"Notification créée pour user {data.user_id}")
            return CRUDResult.crud_success(notif, 201)

        except IntegrityError as e:
            return await RepositoriesUtils.traiter_integrity_error(e, self.db, logger, Notification)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def mark_as_read(self, notification_id: UUID, user_id: UUID) -> CRUDResult[Notification]:
        try:
            stmt = (
                update(Notification)
                .where(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,  # sécurité : un user ne peut lire que ses notifs
                    Notification.deleted_at.is_(None)
                )
                .values(is_read=True, read_at=datetime.now(timezone.utc))
                .returning(Notification)
            )
            result = await self.db.execute(stmt)
            notif = result.scalar_one_or_none()

            if notif is None:
                return CRUDResult.crud_error(msg.NOT_FOUND, 404)

            await self.db.commit()
            return CRUDResult.crud_success(notif)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def mark_all_as_read(self, user_id: UUID) -> CRUDResult[int]:
        """Retourne le nombre de notifs marquées."""
        try:
            stmt = (
                update(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                    Notification.deleted_at.is_(None)
                )
                .values(is_read=True, read_at=datetime.now(timezone.utc))
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return CRUDResult.crud_success(result.rowcount)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def count_unread(self, user_id: UUID) -> CRUDResult[int]:
        try:
            stmt = (
                select(func.count(Notification.id))
                .where(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                    Notification.deleted_at.is_(None)
                )
            )
            result = await self.db.execute(stmt)
            count = result.scalar_one()
            return CRUDResult.crud_success(count)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
        
    async def get_notifications_paginated(
        self,
        user_id: UUID,
        cursor_id: Optional[UUID] = None,      
        cursor_date: Optional[datetime] = None, 
        limit: int = 20,
    ) -> CRUDResult[dict]:
        """
        Récupère les notifications d'un user, du plus récent au plus ancien.
        Le curseur est composé de (created_at, id) pour gérer les égalités de date.
        """
        try:
            query = (
                select(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.deleted_at.is_(None)
                )
                .order_by(Notification.created_at.desc(), Notification.id.desc())
            )

            
            if cursor_id and cursor_date:
                query = query.where(
                    (Notification.created_at < cursor_date)
                    | (
                        (Notification.created_at == cursor_date)
                        & (Notification.id < cursor_id)
                    )
                )

            query = query.limit(limit + 1)  # +1 pour détecter has_more

            result = await self.db.execute(query)
            items = list(result.scalars().all())

            has_more = len(items) > limit
            page = items[:limit]

            return CRUDResult.crud_success({
                "items": page,
                "has_more": has_more,
                "last": page[-1] if page else None  # pour construire le next_cursor
            })

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)