from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response, Path
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user
from app.auth.role_depends import RoleDepends
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas.notification_schemas import NotificationInfo, NotificationListInfo
from app.schemas.user_schemas import ReadUser
from app.services.notification_service import NotificationService

router = APIRouter(
    prefix="/notifications",
    tags=["Routes Notifications"],
    dependencies=[Depends(RoleDepends.all_authorize)]
)


def get_notification_service(db: Annotated[AsyncSession, Depends(get_db)]) -> NotificationService:
    return NotificationService(db)


@router.get("/", response_model=NotificationListInfo)
async def get_my_notifications(
    response: Response,
    current_user: Annotated[ReadUser, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    cursor: Annotated[Optional[str], Query(description="Curseur de pagination")] = None,
    limit: Annotated[int, Query(gt=0, le=50)] = 20,
):
    """Récupère les notifications de l'utilisateur connecté, du plus récent au plus ancien."""
    result = await service.get_my_notifications(current_user.id, cursor, limit)
    return result.to_HTTP_api_base_response(response)


@router.patch("/{notification_id}/read", response_model=NotificationInfo)
async def mark_as_read(
    notification_id: Annotated[UUID, Path()],
    response: Response,
    current_user: Annotated[ReadUser, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
):
    """Marque une notification spécifique comme lue."""
    result = await service.mark_as_read(notification_id, current_user.id)
    return result.to_HTTP_api_base_response(response)


@router.patch("/read-all", response_model=None, status_code=200)
async def mark_all_as_read(
    response: Response,
    current_user: Annotated[ReadUser, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
):
    """Marque toutes les notifications comme lues."""
    result = await service.mark_all_as_read(current_user.id)
    return result.to_HTTP_api_base_response(response)