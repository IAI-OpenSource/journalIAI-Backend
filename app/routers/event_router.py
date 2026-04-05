from fastapi import APIRouter, Depends, Response, Query, Path

from app.auth.role_depends import RoleDepends
from app.cache.helpers.base import get_redis, CacheWrapper
from app.globals.api_tags import ApiTags
from app.schemas.global_schemas import GlobalStringMessage
from app.services.events_services import EventService
from app.schemas.events_schemas import EventCreate, EventUpdate, EventInfo, ApiPaginatedEventListReponse, \
    ApiEventListReponse
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Any, Annotated, Optional
from app.db.models.enums import EventStatus  # corrigé : vient de enums

routeur = APIRouter(prefix="/events", tags=[ApiTags.EVENT], dependencies=[Depends(RoleDepends.all_authorize)])


# IMPORTANT : les routes statiques (/paginated, /status, /) doivent être déclarées
# AVANT les routes dynamiques (/{event_id}) pour éviter les conflits FastAPI

def get_event_service(
    bd: Annotated[AsyncSession, Depends(get_db)], redis: Annotated[CacheWrapper, Depends(get_redis)]
) -> EventService:
    return EventService(bd, redis)

@routeur.get("/", name="Récupérer tous les events.", response_model=ApiEventListReponse, deprecated=True)
async def get_all_events(
    reponse: Response,
    event_service: Annotated[EventService, Depends(get_event_service)]
) -> Any:
    """Endpoint pour récupérer tous les events, PRIORISER LA REQUETE AVEC PAGINATION"""
    result = await event_service.service_find_all_event()
    return result.to_HTTP_api_base_response(reponse)

# TODO: Corriger toute cette route (la pagination est mal faite)
@routeur.get("/paginated/", name="Récupérer les events avec pagination", response_model=ApiPaginatedEventListReponse)
async def get_events_paginated(
    reponse: Response,
    event_service: Annotated[EventService, Depends(get_event_service)],
    cursor: Annotated[Optional[UUID], Query(description="L'identifiant du dernier event récupéré (Optionnel)")] = None,
    limit: Annotated[int, Query(description="Le nombre maximum d'events à récupérer, par défaut à 10", gt=0, le=100)] = 10
) -> Any:
    """Endpoint pour récupérer les events avec pagination par curseur. Le client peut fournir un `cursor`
     (ID du dernier event récupéré) et une `limit` pour contrôler le nombre d'events retournés. Si aucun cursor n'est fourni, la pagination commence depuis le début de la liste."""
    result = await event_service.service_get_events_paginated(cursor=cursor, limit=limit)
    return result.to_HTTP_api_base_response(reponse)


@routeur.get("/status/{statut}", name="Récupérer les events par statut", response_model=ApiEventListReponse)
async def get_events_by_statut(
    statut: Annotated[EventStatus, Path(description="Le statut par lequel filtrer les events")],
    reponse: Response,
    event_service: Annotated[EventService, Depends(get_event_service)]
) -> Any:
    """Endpoint pour récupérer les events en filtrant par statut."""
    result = await event_service.service_find_event_by_statut(statut=statut)
    return result.to_HTTP_api_base_response(reponse)


@routeur.get("/{event_id}", name="Récupérer un event par son ID", response_model=EventInfo)
async def get_event_by_id(
    event_id: Annotated[UUID, Path(description="L'identifiant de l'event à récupérer")],
    reponse: Response,
    event_service: Annotated[EventService, Depends(get_event_service)]
) -> Any:
    """Endpoint pour récupérer un event par son ID.    """
    result = await event_service.service_find_event_by_id(event_id=event_id)
    return result.to_HTTP_api_base_response(reponse)


@routeur.post(
    "/", name="Créer un event", response_model=EventInfo,
    dependencies=[Depends(RoleDepends.only_admin_authorize)]
)
async def create_event(
    payload: EventCreate,
    reponse: Response,
    event_service: Annotated[EventService, Depends(get_event_service)]

) -> Any:
    """Endpoint pour créer un event."""
    result = await event_service.service_create_event(event_data=payload)
    return result.to_HTTP_api_base_response(reponse)


@routeur.put("/{event_id}", name="Mettre à jour un event", response_model=EventInfo)
async def update_event(
    event_id: Annotated[UUID, Path(description="L'identifiant de l'event à mettre à jour")],
    payload: EventUpdate,
    reponse: Response,
    event_service: Annotated[EventService, Depends(get_event_service)]
) -> Any:
    """Endpoint pour mettre à jour un event."""
    result = await event_service.service_update_event(event_id=event_id, event_data=payload)
    return result.to_HTTP_api_base_response(reponse)


@routeur.delete("/{event_id}", name="Supprimer un event", response_model=GlobalStringMessage)
async def delete_event(
    event_id: Annotated[UUID, Path(description="L'identifiant de l'event à supprimer")],
    reponse: Response,
    event_service: Annotated[EventService, Depends(get_event_service)]
) -> Any:
    """Endpoint pour supprimer un event (soft delete)."""
    result = await event_service.service_delete_event(event_id=event_id)
    return result.to_HTTP_api_base_response(reponse)