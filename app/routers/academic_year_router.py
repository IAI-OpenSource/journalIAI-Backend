from fastapi import APIRouter, Depends, Response
from app.cache.helpers.base import get_redis
from app.globals.api_tags import ApiTags
from app.schemas import ApiBaseResponse
from app.schemas.global_schemas import GlobalStringMessage
from app.services.academic_year_service import AcademicYearService
from app.schemas.academic_year_schemas import AcademicYearCreateRequest, AcademicYearResponse, AcademicYearUpdateRequest, AcademicYearListResponse
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

router = APIRouter(prefix="/academic-years", tags=[ApiTags.ACADEMIC_YEAR])


@router.get("/active", response_model=ApiBaseResponse[AcademicYearResponse], status_code=200)
async def get_active_academic_year(reponse: Response , db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ApiBaseResponse[AcademicYearResponse]:
    """Endpoint pour récupérer l'année académique active."""
    academic_year_service = AcademicYearService(db, redis)
    result = await academic_year_service.get_active_academic_year()
    return result.to_HTTP_api_base_response(reponse)

@router.get("/{academic_year_id}", response_model=ApiBaseResponse[AcademicYearResponse], status_code=200)
async def get_academic_year_by_id(academic_year_id: UUID, reponse: Response , db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ApiBaseResponse[AcademicYearResponse]:
    """Endpoint pour récupérer une année académique par son ID."""
    academic_year_service = AcademicYearService(db, redis)
    result = await academic_year_service.get_academic_year_by_id(academic_year_id)
    return result.to_HTTP_api_base_response(reponse)

@router.get("/", response_model=ApiBaseResponse[AcademicYearListResponse], status_code=200)
async def get_all_academic_years(reponse: Response , db: AsyncSession = Depends(get_db), redis = Depends(get_redis), page:int = 1, page_size: int = 20) -> ApiBaseResponse[AcademicYearListResponse]:
    """Endpoint pour lister tous les années académiques avec pagination et filtrage par statut actif/inactif."""
    academic_year_service = AcademicYearService(db, redis)
    result = await academic_year_service.get_all_academic_years(page=page, page_size=page_size)
    return result.to_HTTP_api_base_response(reponse)

@router.post("/", response_model=ApiBaseResponse[AcademicYearResponse], status_code=201)
async def create_academic_year(payload:AcademicYearCreateRequest, reponse:Response, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ApiBaseResponse[AcademicYearResponse]:
    """Endpoint pour créer une année académique"""
    academic_year_service = AcademicYearService(db, redis)
    result = await academic_year_service.create_academic_year(payload)
    return result.to_HTTP_api_base_response(reponse)

@router.put("/{academic_year_id}", response_model=ApiBaseResponse[AcademicYearResponse], status_code=200)
async def update_academic_year(academic_year_id: UUID, payload: AcademicYearUpdateRequest, reponse: Response, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ApiBaseResponse[AcademicYearResponse]:
    """Endpoint pour mettre à jour une année académique"""
    academic_year_service = AcademicYearService(db, redis)
    result = await academic_year_service.update_academic_year(academic_year_id, payload)
    return result.to_HTTP_api_base_response(reponse)

@router.delete("/{academic_year_id}", response_model=GlobalStringMessage, status_code=200)
async def delete_academic_year(academic_year_id: UUID, reponse: Response, db: AsyncSession = Depends(get_db), redis = Depends(get_redis)) -> ApiBaseResponse[None]:
    """Endpoint pour supprimer une année académique"""
    academic_year_service = AcademicYearService(db, redis)
    result = await academic_year_service.soft_delete_academic_year(academic_year_id)
    return result.to_HTTP_api_base_response(reponse)