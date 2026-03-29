from uuid import UUID
 
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
 
from app.cache.helpers.base import CacheWrapper, get_redis
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas import ApiBaseResponse
from app.schemas.classe_schemas import (ClasseApiResponse,ClasseCreateRequest,ClasseListResponse,ClasseUpdateRequest,ClassesListApiResponse)
from app.schemas.global_schemas import GlobalStringMessage
from app.services.classe_service import ClasseService
 
router = APIRouter(prefix="/classes", tags=[ApiTags.CLASSE])
 
 
@router.get("/", response_model=ClassesListApiResponse, status_code=200)
async def get_all_classes(reponse: Response,db: AsyncSession = Depends(get_db),redis: CacheWrapper = Depends(get_redis),page: int = 1,page_size: int = 20):
    """Liste toutes les classes avec pagination."""
    service = ClasseService(db, redis)
    result = await service.get_all_classes(page=page, page_size=page_size)
    return result.to_HTTP_api_base_response(reponse)
 
 
@router.get("/{classe_id}", response_model=ClasseApiResponse, status_code=200)
async def get_classe_by_id(classe_id: UUID,reponse: Response,db: AsyncSession = Depends(get_db),redis: CacheWrapper = Depends(get_redis)):
    """Récupère une classe par son ID."""
    service = ClasseService(db, redis)
    result = await service.get_classe_by_id(classe_id)
    return result.to_HTTP_api_base_response(reponse)
 
 
@router.post("/", response_model=ClasseApiResponse, status_code=201)
async def create_classe(payload: ClasseCreateRequest,reponse: Response,db: AsyncSession = Depends(get_db),redis: CacheWrapper = Depends(get_redis)):
    """Crée une nouvelle classe."""
    service = ClasseService(db, redis)
    result = await service.create_classe(payload)
    return result.to_HTTP_api_base_response(reponse)
 
 
@router.put("/{classe_id}", response_model=ClasseApiResponse, status_code=200)
async def update_classe(classe_id: UUID,payload: ClasseUpdateRequest,reponse: Response,db: AsyncSession = Depends(get_db),redis: CacheWrapper = Depends(get_redis)):
    """Met à jour une classe existante."""
    service = ClasseService(db, redis)
    result = await service.update_classe(classe_id, payload)
    return result.to_HTTP_api_base_response(reponse)
 
 
@router.delete("/{classe_id}", response_model=GlobalStringMessage, status_code=200)
async def delete_classe(classe_id: UUID,reponse: Response,db: AsyncSession = Depends(get_db),redis: CacheWrapper = Depends(get_redis)):
    """Supprime une classe (soft delete)."""
    service = ClasseService(db, redis)
    result = await service.delete_classe(classe_id)
    return result.to_HTTP_api_base_response(reponse)