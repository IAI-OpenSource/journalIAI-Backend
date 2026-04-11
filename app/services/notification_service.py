import base64
import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.globals.messages import Messages as msg
from app.globals.status_codes import StatusCode as status
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification_schemas import NotificationCreate, NotificationRead, NotificationListResponse
from app.services import ServiceResult

logger = logging.getLogger(__name__)


def _encode_cursor(created_at: datetime, notif_id: UUID) -> str:
    """Encode le curseur en base64 — même pattern que post_repository."""
    payload = {"created_at": created_at.isoformat(), "id": str(notif_id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        data = json.loads(raw)
        return datetime.fromisoformat(data["created_at"]), UUID(data["id"])
    except Exception:
        raise ValueError("Curseur de pagination invalide.")


class NotificationService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = NotificationRepository(db)

    
    async def create_notification(self, data: NotificationCreate) -> ServiceResult[NotificationRead]:
        result = await self.repo.create_notification(data)

        if result.is_error():
            return ServiceResult.service_error(result.error, result.status_code)

        return ServiceResult.service_success(
            NotificationRead.model_validate(result.data),
            status._201_STATUS_CREATED,
        )

    
    async def get_my_notifications(
        self,
        user_id: UUID,
        cursor: Optional[str] = None,
        limit: int = 20,
    ) -> ServiceResult[NotificationListResponse]:

        
        cursor_id, cursor_date = None, None
        if cursor:
            try:
                cursor_date, cursor_id = _decode_cursor(cursor)
            except ValueError as e:
                return ServiceResult.service_error(str(e), 400)

        
        notifs_result = await self.repo.get_notifications_paginated(
            user_id, cursor_id, cursor_date, limit
        )
        count_result = await self.repo.count_unread(user_id)

        if notifs_result.is_error():
            return ServiceResult.service_error(notifs_result.error, notifs_result.status_code)

        data = notifs_result.data
        items = [NotificationRead.model_validate(n) for n in data["items"]]
        unread_count = count_result.data if count_result.is_success() else 0

        
        next_cursor = None
        if data["has_more"] and data["last"]:
            last = data["last"]
            next_cursor = _encode_cursor(last.created_at, last.id)

        return ServiceResult.service_success(
            NotificationListResponse(
                items=items,
                next_cursor=next_cursor,
                has_more=data["has_more"],
                unread_count=unread_count,
            ),
            status._200_STATUS_SUCCESS,
        )

    
    async def mark_as_read(
        self, notification_id: UUID, user_id: UUID
    ) -> ServiceResult[NotificationRead]:
        result = await self.repo.mark_as_read(notification_id, user_id)

        if result.is_error():
            return ServiceResult.service_error(result.error, result.status_code)

        return ServiceResult.service_success(
            NotificationRead.model_validate(result.data),
            status._200_STATUS_SUCCESS,
        )

    
    async def mark_all_as_read(self, user_id: UUID) -> ServiceResult[dict]:
        result = await self.repo.mark_all_as_read(user_id)

        if result.is_error():
            return ServiceResult.service_error(result.error, result.status_code)

        return ServiceResult.service_success(
            {"marked_count": result.data},
            status._200_STATUS_SUCCESS,
        )