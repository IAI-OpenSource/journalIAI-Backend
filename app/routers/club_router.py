from fastapi import APIRouter, Depends, Response
from app.cache.helpers.base import get_redis
from app.globals.api_tags import ApiTags
from app.schemas import ApiBaseResponse
from app.schemas.global_schemas import GlobalStringMessage
from app.services.club_service import ClubService
from app.schemas.club_schemas import ClubCreateRequest, ClubResponse, ClubUpdateRequest, ClubsListResponse
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

router = APIRouter(prefix="/clubs", tags=[ApiTags.CLUB])

#TODO: Ajouter une pagination cursor-based
@router.get("/{club_id}", response_model=ApiBaseResponse[ClubResponse], status_code=200)
async def get_club_by_id(club_id: UUID, reponse: Response , db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ApiBaseResponse[ClubResponse]:
    """Endpoint pour récupérer un club par son ID."""
    club_service = ClubService(db, redis)
    result = await club_service.get_club(club_id)
    return result.to_HTTP_api_base_response(reponse)
    
    
@router.get("/slug/{slug}", response_model=ApiBaseResponse[ClubResponse], status_code=200)
async def get_club_by_slug(slug: str, reponse: Response , db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ApiBaseResponse[ClubResponse]:
    """Endpoint pour récupérer un club par son slug.
    """
    club_service = ClubService(db, redis)
    result = await club_service.get_club_by_slug(slug)
    return result.to_HTTP_api_base_response(reponse)

#TODO: Mettre en cache cette les réponses de cette pagination dans le service
@router.get("/", response_model=ApiBaseResponse[ClubsListResponse], status_code=200)
async def get_all_clubs(reponse: Response , db: AsyncSession = Depends(get_db), redis = Depends(get_redis), page:int = 1, page_size: int = 20, is_active: bool = False, ) -> ApiBaseResponse[ClubsListResponse]:
    """Endpoint pour lister tous les clubs avec pagination et filtrage par statut actif/inactif."""
    club_service = ClubService(db, redis)
    result = await club_service.get_all_clubs(page=page, page_size=page_size, is_active=is_active)
    return result.to_HTTP_api_base_response(reponse)


@router.post("/", response_model=ApiBaseResponse[ClubResponse], status_code=201, )
async def create_club(payload:ClubCreateRequest, reponse:Response, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ApiBaseResponse[ClubResponse]:
    """Endpoint pour créer un club"""
    club_service = ClubService(db, redis)
    result = await club_service.create_club(payload)
    return result.to_HTTP_api_base_response(reponse)


@router.put("/{club_id}", response_model=ApiBaseResponse[ClubResponse], status_code=200)
async def update_club(club_id: UUID, payload: ClubUpdateRequest, reponse: Response, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ApiBaseResponse[ClubResponse]:
    """Endpoint pour mettre à jour un club"""
    club_service = ClubService(db, redis)
    result = await club_service.update_club(club_id, payload)
    return result.to_HTTP_api_base_response(reponse)

@router.delete("/{club_id}", response_model=GlobalStringMessage, status_code=200)
async def delete_club(club_id: UUID, reponse: Response, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ApiBaseResponse[None]:
    """Endpoint pour supprimer un club"""
    club_service = ClubService(db, redis)
    result = await club_service.delete_club(club_id)
    return result.to_HTTP_api_base_response(reponse)