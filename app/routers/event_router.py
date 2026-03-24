from fastapi import APIRouter, Depends, Response
from app.cache.helpers.base import get_redis
from app.globals.api_tags import ApiTags
from app.services.events_services import EventService
from app.schemas.events_schemas import EventCreate, EventUpdate, EventInfo,ApiEventListReponse
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional, Any
from app.db.models.enums import EventStatus  # corrigé : vient de enums

routeur = APIRouter(prefix="/events", tags=[ApiTags.EVENT])


# IMPORTANT : les routes statiques (/paginated, /status, /) doivent être déclarées
# AVANT les routes dynamiques (/{event_id}) pour éviter les conflits FastAPI


@routeur.get("/", name="Récupérer tous les events.", response_model=ApiEventListReponse)
async def get_all_events(
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis)
) -> Any:
    """Endpoint pour récupérer tous les events.

    Args:
        db (AsyncSession): La session de base de données, injectée par FastAPI.

    Returns:
        EventRead: La liste de tous les events.
    """
    event_service = EventService(db, redis)
    result = await event_service.service_find_all_event()
    return result.to_HTTP_api_base_response(reponse)


@routeur.get("/paginated/", name="Récupérer les events avec pagination",response_model=ApiEventListReponse)
async def get_events_paginated(
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    cursor: Optional[UUID] = None,
    limit: int = 10
) -> Any:
    """Endpoint pour récupérer les events avec pagination par curseur.

    Args:
        cursor (Optional[UUID]): L'identifiant du dernier event récupéré.
        limit (int): Le nombre maximum d'events à récupérer.
        db (AsyncSession): La session de base de données, injectée par FastAPI.

    Returns:
        EventListReponse: La liste des events avec le curseur suivant.
    """
    event_service = EventService(db, redis)
    result = await event_service.service_get_events_paginated(cursor=cursor, limit=limit)
    return result.to_HTTP_api_base_response(reponse)


@routeur.get("/status/{statut}", name="Récupérer les events par statut",response_model=ApiEventListReponse)
async def get_events_by_statut(
    statut: EventStatus,
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis)
) -> Any:
    """Endpoint pour récupérer les events par statut.

    Args:
        statut (EventStatus): Le statut des events à récupérer.
        db (AsyncSession): La session de base de données, injectée par FastAPI.

    Returns:
        EventRead: La liste des events correspondant au statut.
    """
    event_service = EventService(db, redis)
    result = await event_service.service_find_event_by_statut(statut=statut)
    return result.to_HTTP_api_base_response(reponse)


@routeur.get("/{event_id}", name="Récupérer un event par son ID", response_model=EventInfo)
async def get_event_by_id(
    event_id: UUID,
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis)
) -> Any:
    """Endpoint pour récupérer un event par son ID.

    Args:
        event_id (UUID): L'identifiant de l'event à récupérer.
        db (AsyncSession): La session de base de données, injectée par FastAPI.

    Returns:
        EventRead: Les données de l'event ou une erreur si l'event n'est pas trouvé.
    """
    event_service = EventService(db, redis)
    result = await event_service.service_find_event_by_id(event_id=event_id)
    return result.to_HTTP_api_base_response(reponse)


@routeur.post("/", name="Créer un event", response_model=EventInfo)
async def create_event(
    payload: EventCreate,
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis)
) -> Any:
    """Endpoint pour créer un event.

    Args:
        payload (EventCreate): Les données de l'event à créer.
        db (AsyncSession): La session de base de données, injectée par FastAPI.

    Returns:
        EventRead: Les données de l'event créé.
    """
    event_service = EventService(db, redis)
    result = await event_service.service_create_event(event_data=payload)
    return result.to_HTTP_api_base_response(reponse)


@routeur.put("/{event_id}", name="Mettre à jour un event", response_model=EventInfo)
async def update_event(
    event_id: UUID,
    payload: EventUpdate,
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis)
) -> Any:
    """Endpoint pour mettre à jour un event.

    Args:
        event_id (UUID): L'identifiant de l'event à mettre à jour.
        payload (EventUpdate): Les données de l'event à mettre à jour.
        db (AsyncSession): La session de base de données, injectée par FastAPI.

    Returns:
        EventRead: Les données de l'event mis à jour.
    """
    event_service = EventService(db, redis)
    result = await event_service.service_update_event(event_id=event_id, event_data=payload)
    return result.to_HTTP_api_base_response(reponse)


@routeur.delete("/{event_id}", name="Supprimer un event")
async def delete_event(
    event_id: UUID,
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis)
) -> Any:
    """Endpoint pour supprimer un event (soft delete).

    Args:
        event_id (UUID): L'identifiant de l'event à supprimer.
        db (AsyncSession): La session de base de données, injectée par FastAPI.

    Returns:
        None: Une réponse vide avec un code de statut indiquant le résultat.
    """
    event_service = EventService(db, redis)
    result = await event_service.service_delete_event(event_id=event_id)
    return result.to_HTTP_api_base_response(reponse)