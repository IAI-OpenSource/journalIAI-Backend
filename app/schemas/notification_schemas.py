from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from app.schemas import ApiBaseResponse


class NotificationCreate(BaseModel):
    """Schéma pour la création d'une notification."""

    user_id: UUID
    type: str = Field(..., max_length=50, description="Ex: 'new_post', 'event_published', 'club_update'")
    title: str = Field(..., max_length=255)
    message: str
    resource_type: Optional[str] = Field(None, max_length=50, description="Ex: 'post', 'event', 'club'")
    resource_id: Optional[UUID] = None

class NotificationRead(BaseModel):
    """Schéma pour la lecture d'une notification."""

    model_config = {"from_attributes": True}
    
    id: UUID
    type: str
    title: str
    message: str
    resource_type: Optional[str] = None
    resource_id: Optional[UUID] = None
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None

class NotificationListResponse(ApiBaseResponse):
    """Schéma pour la liste des notifications."""

    items: list[NotificationRead]
    next_cursor: Optional[str] = Field(
        None,
        description="Curseur opaque pour la page suivante. NULL si c'est la dernière page."
    )
    has_more: bool
    unread_count: int = Field(description="Nombre de notifs non lues — utile pour le badge")



class NotificationInfo(ApiBaseResponse):
    result: Optional[NotificationRead] = None

class NotificationListInfo(ApiBaseResponse):
    result: Optional[NotificationListResponse] = None