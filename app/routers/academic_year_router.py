from typing import Annotated

from fastapi import APIRouter, Depends, Response, Path, Query

from app.auth.role_depends import RoleDepends
from app.cache.helpers.base import get_redis, CacheWrapper
from app.globals.api_tags import ApiTags
from app.schemas import ApiBaseResponse
from app.schemas.global_schemas import GlobalStringMessage
from app.services.academic_year_service import AcademicYearService
from app.schemas.academic_year_schemas import AcademicYearCreateRequest, AcademicYearResponse, AcademicYearUpdateRequest, AcademicYearListResponse
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

router = APIRouter(
    prefix="/academic-years", tags=[ApiTags.ACADEMIC_YEAR],
    dependencies=[Depends(RoleDepends.all_authorize)]
)
def get_academic_year_service(
    bd: Annotated[AsyncSession, Depends(get_db)], redis: Annotated[CacheWrapper, Depends(get_redis)]
) -> AcademicYearService:
    return AcademicYearService(bd, redis)


@router.get("/active", response_model=ApiBaseResponse[AcademicYearResponse])
async def get_active_academic_year(
    reponse: Response, academic_year_service: Annotated[AcademicYearService, Depends(get_academic_year_service)]
) -> ApiBaseResponse[AcademicYearResponse]:
    """Endpoint pour récupérer l'année académique active."""
    result = await academic_year_service.get_active_academic_year()
    return result.to_HTTP_api_base_response(reponse)

@router.get(
    "/{academic_year_id}",
    response_model=ApiBaseResponse[AcademicYearResponse],
    dependencies=[Depends(RoleDepends.only_admin_authorize)],
)
async def get_academic_year_by_id(
    academic_year_id: Annotated[UUID, Path(description="L'id de l'année academique à recup")], reponse: Response,
    academic_year_service: Annotated[AcademicYearService, Depends(get_academic_year_service)]
) -> ApiBaseResponse[AcademicYearResponse]:
    """Endpoint pour récupérer une année académique par son ID."""
    result = await academic_year_service.get_academic_year_by_id(academic_year_id)
    return result.to_HTTP_api_base_response(reponse)

@router.get(
"/", response_model=ApiBaseResponse[AcademicYearListResponse],
    dependencies=[Depends(RoleDepends.only_admin_authorize)]
)
async def get_all_academic_years(
    reponse: Response, academic_year_service: Annotated[AcademicYearService, Depends(get_academic_year_service)],
    page: Annotated[int, Query(description="La page à récuperer")] = 1,
    page_size: Annotated[int, Query(description="La taille de la page à  récup")] = 20
):
    """Endpoint pour lister tous les années académiques avec pagination et filtrage par statut actif/inactif."""
    result = await academic_year_service.get_all_academic_years(page=page, page_size=page_size)
    return result.to_HTTP_api_base_response(reponse)

@router.post(
"/", response_model=ApiBaseResponse[AcademicYearResponse],
    dependencies=[Depends(RoleDepends.only_admin_authorize)]
)
async def create_academic_year(
    payload:AcademicYearCreateRequest, reponse:Response,
    academic_year_service: Annotated[AcademicYearService, Depends(get_academic_year_service)]
) -> ApiBaseResponse[AcademicYearResponse]:
    """Endpoint pour créer une année académique"""
    result = await academic_year_service.create_academic_year(payload)
    return result.to_HTTP_api_base_response(reponse)

@router.put(
    "/{academic_year_id}",
    response_model=ApiBaseResponse[AcademicYearResponse],
    dependencies=[Depends(RoleDepends.only_admin_authorize)]
)
async def update_academic_year(
    academic_year_id: Annotated[UUID, Path(..., description="L'id de l'année académique à update")],
    payload: AcademicYearUpdateRequest,
    reponse: Response, academic_year_service: Annotated[AcademicYearService, Depends(get_academic_year_service)]
) -> ApiBaseResponse[AcademicYearResponse]:
    """Endpoint pour mettre à jour une année académique"""
    result = await academic_year_service.update_academic_year(academic_year_id, payload)
    return result.to_HTTP_api_base_response(reponse)

@router.delete(
    "/{academic_year_id}",
    response_model=GlobalStringMessage,
    dependencies=[Depends(RoleDepends.only_admin_authorize)]
)
async def delete_academic_year(
    academic_year_id: Annotated[UUID, Path(..., description="L'id de l'année académique à supprimer")],
    reponse: Response,
    academic_year_service: Annotated[AcademicYearService, Depends(get_academic_year_service)]
):
    """Endpoint pour supprimer une année académique"""
    result = await academic_year_service.soft_delete_academic_year(academic_year_id)
    return result.to_HTTP_api_base_response(reponse)