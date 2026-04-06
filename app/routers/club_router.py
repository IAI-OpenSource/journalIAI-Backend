from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.auth.role_depends import RoleDepends
from app.cache.helpers.base import get_redis, CacheWrapper
from app.globals.api_tags import ApiTags
from app.schemas import ApiBaseResponse
from app.schemas.global_schemas import GlobalStringMessage
from app.services.club_service import ClubService
from app.schemas.club_schemas import ClubCreateRequest, ClubResponse, ClubUpdateRequest, ClubsListResponse
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

router = APIRouter(prefix="/clubs", tags=[ApiTags.CLUB], dependencies=[Depends(RoleDepends.all_authorize)])

def get_club_service(
    db: Annotated[AsyncSession, Depends(get_db)], redis: Annotated[CacheWrapper, Depends(get_redis)]
) -> ClubService:
    return ClubService(db, redis)


#TODO: Ajouter une pagination cursor-based
@router.get("/{club_id}", response_model=ApiBaseResponse[ClubResponse], status_code=200)
async def get_club_by_id(
    club_id: UUID, reponse: Response, club_service: Annotated[ClubService, Depends(get_club_service)]
) -> ApiBaseResponse[ClubResponse]:
    """Endpoint pour récupérer un club par son ID."""
    result = await club_service.get_club(club_id)
    return result.to_HTTP_api_base_response(reponse)
    
    
@router.get("/slug/{slug}", response_model=ApiBaseResponse[ClubResponse], status_code=200)
async def get_club_by_slug(
    slug: str, reponse: Response,
    club_service: Annotated[ClubService, Depends(get_club_service)]
) -> ApiBaseResponse[ClubResponse]:
    """Endpoint pour récupérer un club par son slug.
    """
    result = await club_service.get_club_by_slug(slug)
    return result.to_HTTP_api_base_response(reponse)

#TODO: Mettre en cache cette les réponses de cette pagination dans le service
@router.get("/", response_model=ApiBaseResponse[ClubsListResponse], status_code=200)
async def get_all_clubs(
    reponse: Response,
    club_service: Annotated[ClubService, Depends(get_club_service)],
    page:int = 1, page_size: int = 20, is_active: bool = False
) -> ApiBaseResponse[ClubsListResponse]:
    """Endpoint pour lister tous les clubs avec pagination et filtrage par statut actif/inactif."""
    result = await club_service.get_all_clubs(page=page, page_size=page_size, is_active=is_active)
    return result.to_HTTP_api_base_response(reponse)


@router.post(
"/", response_model=ApiBaseResponse[ClubResponse], dependencies=[Depends(RoleDepends.only_admin_authorize)]
)
async def create_club(
    payload: ClubCreateRequest, reponse:Response,
    club_service: Annotated[ClubService, Depends(get_club_service)]
) -> ApiBaseResponse[ClubResponse]:
    """Endpoint pour créer un club"""
    result = await club_service.create_club(payload)
    return result.to_HTTP_api_base_response(reponse)


@router.put(
"/{club_id}", response_model=ApiBaseResponse[ClubResponse],
    dependencies=[Depends(RoleDepends.only_admin_authorize)]
)
async def update_club(
    club_id: UUID, payload: ClubUpdateRequest, reponse: Response,
    club_service: Annotated[ClubService, Depends(get_club_service)]
) -> ApiBaseResponse[ClubResponse]:
    """Endpoint pour mettre à jour un club"""
    result = await club_service.update_club(club_id, payload)
    return result.to_HTTP_api_base_response(reponse)

@router.delete(
"/{club_id}", response_model=GlobalStringMessage, dependencies=[Depends(RoleDepends.only_admin_authorize)]
)
async def delete_club(
    club_id: UUID, reponse: Response,
    club_service: Annotated[ClubService, Depends(get_club_service)]
) -> ApiBaseResponse[None]:
    """Endpoint pour supprimer un club"""
    result = await club_service.delete_club(club_id)
    return result.to_HTTP_api_base_response(reponse)