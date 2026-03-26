from fastapi import APIRouter, Depends, Response
from app.cache.helpers.base import get_redis
from app.globals.api_tags import ApiTags
from app.services.club_service import ClubService
from app.schemas.clubs_schemas import ClubCreateRequest, ClubResponse, ClubUpdateRequest, ClubsListResponse
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

router = APIRouter(prefix="/clubs", tags=[ApiTags.CLUB])

@router.get("/{club_id}")
async def get_club_by_id(club_id: UUID, reponse: Response , db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ClubResponse:
    """Endpoint pour récupérer un club par son ID.
    """
    club_service = ClubService(db, redis)
    result = await club_service.get_club(club_id)
    return result.to_HTTP_api_base_response(reponse)
    
    
@router.get("/slug/{slug}")
async def get_club_by_slug(slug: str, reponse: Response , db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ClubResponse:
    """Endpoint pour récupérer un club par son slug.
    """
    club_service = ClubService(db, redis)
    result = await club_service.get_club_by_slug(slug)
    return result.to_HTTP_api_base_response(reponse)

@router.get("/")
async def get_all_clubs(reponse: Response , db: AsyncSession = Depends(get_db), redis = Depends(get_redis), page:int = 1, page_size: int = 20, is_active: bool = False, ) -> ClubsListResponse:
    """Endpoint pour lister tous les clubs.
    
    Args:
        page (int): Le numéro de la page à récupérer.
        page_size (int): Le nombre de clubs à récupérer par page.
        is_active (bool): Filtrer les clubs par statut actif.
        db (AsyncSession): La session de base de données, injectée par FastAPI.
        
    Returns:
        ClubsListResponse: La liste des clubs.
    """
    club_service = ClubService(db, redis)
    result = await club_service.get_all_clubs(page=page, page_size=page_size, is_active=is_active)
    return result.to_HTTP_api_base_response(reponse)


@router.post("/")
async def create_club(payload:ClubCreateRequest, reponse:Response, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ClubResponse:
    """Endpoint pour créer un club.
    
    Args:
        payload (ClubCreateRequest): Les données du club à créer.
        db (AsyncSession): La session de base de données, injectée par FastAPI.
        
    Returns:
        ClubResponse: Les données du club créé ou une erreur si la création échoue.
    """
    club_service = ClubService(db, redis)
    result = await club_service.create_club(payload)
    return result.to_HTTP_api_base_response(reponse)


@router.put("/{club_id}")
async def update_club(club_id: UUID, payload: ClubUpdateRequest, reponse: Response, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ClubResponse:
    """Endpoint pour mettre à jour un club.
    
    Args:
        club_id (UUID): L'identifiant du club à mettre à jour.
        payload (ClubUpdateRequest): Les données du club à mettre à jour.
        db (AsyncSession): La session de base de données, injectée par FastAPI.
        
    Returns:
        ClubResponse: Les données du club mis à jour ou une erreur si la mise à jour échoue.
    """
    club_service = ClubService(db, redis)
    result = await club_service.update_club(club_id, payload)
    return result.to_HTTP_api_base_response(reponse)

@router.delete("/{club_id}")
async def delete_club(club_id: UUID, reponse: Response, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> None:
    """Endpoint pour supprimer un club.
    
    Args:
        club_id (UUID): L'identifiant du club à supprimer.
        db (AsyncSession): La session de base de données, injectée par FastAPI.
        
    Returns:
        None: Une réponse vide avec un code de statut indiquant le résultat de l'opération.
    """
    club_service = ClubService(db, redis)
    result = await club_service.delete_club(club_id)
    return result.to_HTTP_api_base_response(reponse)