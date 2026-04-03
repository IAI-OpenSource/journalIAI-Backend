from fastapi import APIRouter, Depends, Response, Query, Path

from app.cache.helpers.base import get_redis
from app.globals.api_tags import ApiTags
from app.schemas.global_schemas import GlobalStringMessage
from app.services.club_member_service import ClubMemberService
from app.schemas.club_member_schema import (
    ClubMemberCreate,
    ClubMemberUpdate,
    ClubMemberInfo,
    ApiClubMemberListResponse,
    ApiPaginatedClubMemberListResponse,
)
from app.db.session import get_db
from app.db.models.enums import ClubMembersType
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Any, Annotated, Optional

routeur = APIRouter(prefix="/clubs/{club_id}/members", tags=[ApiTags.CLUB_MEMBER])


# IMPORTANT : les routes statiques (/paginated, /role) doivent être déclarées
# AVANT les routes dynamiques (/{member_id}) pour éviter les conflits FastAPI


@routeur.get(
    "/",
    name="Récupérer tous les membres d'un club",
    response_model=ApiClubMemberListResponse,
)
async def get_members_by_club(
    club_id: Annotated[UUID, Path(description="L'identifiant du club")],
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> Any:
    """Endpoint pour récupérer tous les membres actifs d'un club."""
    service = ClubMemberService(db, redis)
    result = await service.service_get_members_by_club(club_id=club_id)
    return result.to_HTTP_api_base_response(reponse)


@routeur.get(
    "/paginated/",
    name="Récupérer les membres d'un club avec pagination",
    response_model=ApiPaginatedClubMemberListResponse,
)
async def get_members_paginated(
    club_id: Annotated[UUID, Path(description="L'identifiant du club")],
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
    cursor: Annotated[
        Optional[UUID],
        Query(description="L'identifiant du dernier membre récupéré (Optionnel)"),
    ] = None,
    limit: Annotated[
        int,
        Query(description="Le nombre maximum de membres à récupérer, par défaut à 10", gt=0, le=100),
    ] = 10,
) -> Any:
    """Endpoint pour récupérer les membres d'un club avec pagination par curseur.
    Le client peut fournir un `cursor` (ID du dernier membre récupéré) et une `limit`
    pour contrôler le nombre de membres retournés. Si aucun cursor n'est fourni,
    la pagination commence depuis le début de la liste."""
    service = ClubMemberService(db, redis)
    result = await service.service_get_members_paginated(club_id=club_id, cursor=cursor, limit=limit)
    return result.to_HTTP_api_base_response(reponse)


@routeur.get(
    "/role/{role}",
    name="Récupérer les membres d'un club par rôle",
    response_model=ApiClubMemberListResponse,
)
async def get_members_by_role(
    club_id: Annotated[UUID, Path(description="L'identifiant du club")],
    role: Annotated[ClubMembersType, Path(description="Le rôle par lequel filtrer les membres")],
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> Any:
    """Endpoint pour récupérer les membres d'un club en filtrant par rôle."""
    service = ClubMemberService(db, redis)
    result = await service.service_get_members_by_role(club_id=club_id, role=role)
    return result.to_HTTP_api_base_response(reponse)


@routeur.get(
    "/{member_id}",
    name="Récupérer un membre par son ID",
    response_model=ClubMemberInfo,
)
async def get_member_by_id(
    club_id: Annotated[UUID, Path(description="L'identifiant du club")],
    member_id: Annotated[UUID, Path(description="L'identifiant du membre à récupérer")],
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> Any:
    """Endpoint pour récupérer un membre par son ID."""
    service = ClubMemberService(db, redis)
    result = await service.service_get_member_by_id(member_id=member_id)
    return result.to_HTTP_api_base_response(reponse)


@routeur.post(
    "/",
    name="Ajouter un membre à un club",
    response_model=ClubMemberInfo,
    status_code=201,
)
async def add_member(
    club_id: Annotated[UUID, Path(description="L'identifiant du club")],
    payload: ClubMemberCreate,
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> Any:
    """Endpoint pour ajouter un membre à un club.
    Le club_id est toujours celui de l'URL — le champ éventuel dans le body est ignoré."""
    service = ClubMemberService(db, redis)
    payload = payload.model_copy(update={"club_id": club_id})
    result = await service.service_add_member(member_data=payload)
    return result.to_HTTP_api_base_response(reponse)


@routeur.put(
    "/{member_id}",
    name="Mettre à jour le rôle d'un membre",
    response_model=ClubMemberInfo,
)
async def update_member_role(
    club_id: Annotated[UUID, Path(description="L'identifiant du club")],
    member_id: Annotated[UUID, Path(description="L'identifiant du membre à mettre à jour")],
    payload: ClubMemberUpdate,
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> Any:
    """Endpoint pour mettre à jour le rôle d'un membre dans un club."""
    service = ClubMemberService(db, redis)
    result = await service.service_update_member_role(club_id=club_id, member_id=member_id, data=payload)
    return result.to_HTTP_api_base_response(reponse)


@routeur.delete(
    "/{member_id}",
    name="Retirer un membre d'un club",
    response_model=GlobalStringMessage,
)
async def remove_member(
    club_id: Annotated[UUID, Path(description="L'identifiant du club")],
    member_id: Annotated[UUID, Path(description="L'identifiant du membre à retirer")],
    reponse: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> Any:
    """Endpoint pour retirer un membre d'un club (soft delete)."""
    service = ClubMemberService(db, redis)
    result = await service.service_remove_member(club_id=club_id, member_id=member_id)
    return result.to_HTTP_api_base_response(reponse)