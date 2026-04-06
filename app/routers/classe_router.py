from typing import Annotated
from uuid import UUID
 
from fastapi import APIRouter, Depends, Response, Path, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.role_depends import RoleDepends
from app.cache.helpers.base import CacheWrapper, get_redis
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas.classe_schemas import (ClasseApiResponse,ClasseCreateRequest,ClasseUpdateRequest,ClassesListApiResponse)
from app.schemas.global_schemas import GlobalStringMessage
from app.services.classe_service import ClasseService
 
router = APIRouter(prefix="/classes", tags=[ApiTags.CLASSE], dependencies=[Depends(RoleDepends.all_authorize)])
 
def get_classe_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[CacheWrapper, Depends(get_redis)]
) -> ClasseService:
    return ClasseService(db, redis)

@router.get("/", response_model=ClassesListApiResponse, status_code=200)
async def get_all_classes(
    reponse: Response, service: Annotated[ClasseService, Depends(get_classe_service)],
    page: Annotated[int, Query(description="La page à récuperer")] = 1,
    page_size: Annotated[int, Query(description="La taille de la page à  récup")] = 20
):
    """Liste toutes les classes avec pagination."""
    result = await service.get_all_classes(page=page, page_size=page_size)
    return result.to_HTTP_api_base_response(reponse)
 
 
@router.get("/{classe_id}", response_model=ClasseApiResponse, status_code=200)
async def get_classe_by_id(
    classe_id: Annotated[UUID, Path(description="Id de la classe à get")],
    reponse: Response, service: Annotated[ClasseService, Depends(get_classe_service)]
):
    """Récupère une classe par son ID."""
    result = await service.get_classe_by_id(classe_id)
    return result.to_HTTP_api_base_response(reponse)
 
 
@router.post("/", response_model=ClasseApiResponse, dependencies=[Depends(RoleDepends.only_admin_authorize)])
async def create_classe(
    payload: ClasseCreateRequest,
    reponse: Response, service: Annotated[ClasseService, Depends(get_classe_service)]
):
    """Crée une nouvelle classe."""
    result = await service.create_classe(payload)
    return result.to_HTTP_api_base_response(reponse)
 
 
@router.put(
"/{classe_id}", response_model=ClasseApiResponse, dependencies=[Depends(RoleDepends.only_admin_authorize)]
)
async def update_classe(
    classe_id: Annotated[UUID, Path()], payload: ClasseUpdateRequest, reponse: Response,
    service: Annotated[ClasseService, Depends(get_classe_service)]
):
    """Met à jour une classe existante."""
    result = await service.update_classe(classe_id, payload)
    return result.to_HTTP_api_base_response(reponse)
 
 
@router.delete(
    "/{classe_id}",
    response_model=GlobalStringMessage,
    dependencies=[Depends(RoleDepends.only_admin_authorize)]
)
async def delete_classe(
    classe_id: Annotated[UUID, Path()],
    reponse: Response,
    service: Annotated[ClasseService, Depends(get_classe_service)]
):
    """Supprime une classe (soft delete)."""
    result = await service.delete_classe(classe_id)
    return result.to_HTTP_api_base_response(reponse)