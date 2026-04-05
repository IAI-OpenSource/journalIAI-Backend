import base64
from typing import Annotated, Optional
from uuid import UUID
from app.auth.role_depends import RoleDepends
from app.worker.celery_app import celery_app
from sqlalchemy.ext.asyncio import AsyncSession


from fastapi import APIRouter, Depends, File, Form, Path, Query, Response, UploadFile

from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas import ApiBaseResponse
from app.schemas.global_schemas import GlobalStringMessage, StringMessage
from app.schemas.registration_schemas import CreateRegistration, FindRegistration, JetonUpdateData, ListRegistrationInfos, ReadRegistration, RegistrationInfos
from app.services.registration_service import RegistrationService
from app.worker.tasks.excel_task import import_students_task


router = APIRouter(prefix="/registration", tags=[ApiTags.JETON_ENREGISTREMENT])


## function global pour creer une instance de 
# RegistrationService pour le fichier. Comme c'est une simple fonction pas besoins
# de deplacer ça 
def get_registration_service(db: AsyncSession = Depends(get_db)) -> RegistrationService:
  return RegistrationService(db=db)



@router.post(
  "/add",
  dependencies=[Depends(RoleDepends.only_managers_authorize)],
  response_model=RegistrationInfos,
)
async def create_registration(
  response: Response,
  reg_data: CreateRegistration,
  reg_service: Annotated[RegistrationService, Depends(get_registration_service)]):
  """Route pour créer 1 seul jeton"""
  
  db_reg = await reg_service.service_create_registration(registration_data=reg_data)
  
  return db_reg.to_HTTP_api_base_response(response)



@router.post(
  "/one",
  dependencies=[Depends(RoleDepends.only_managers_authorize)],
  response_model=RegistrationInfos,
)
async def get_registration(
  response: Response,
  find_reg_data: FindRegistration,
  reg_service: Annotated[RegistrationService, Depends(get_registration_service)]):
  """Route pour récupérer 1 seul jeton"""
  
  db_reg = await reg_service.service_get_registration_by_jeton(find_registration_data=find_reg_data)
  
  return db_reg.to_HTTP_api_base_response(response)



@router.post(
  "/update/{reg_id}",
  dependencies=[Depends(RoleDepends.only_managers_authorize)],
  response_model=GlobalStringMessage,
)
async def update_registration(
  response: Response,
  reg_id: Annotated[UUID, Path(..., description="Id du jeton a mettre à jour")],
  update_reg_data: JetonUpdateData,
  reg_service: Annotated[RegistrationService, Depends(get_registration_service)]):
  """Route pour récupérer 1 seul jeton"""
  
  db_reg = await reg_service.service_update_registration(reg_id=reg_id, reg_update_data=update_reg_data)
  
  return db_reg.to_HTTP_api_base_response(response)



@router.post(
  "/students/import",
  dependencies=[Depends(RoleDepends.only_managers_authorize)],
  response_model=GlobalStringMessage,
)
async def imports_students(
  response: Response,
  classe_id: Annotated[UUID, Form(..., description="ID de la classe concernée")],
  excel_file: Annotated[UploadFile, File(..., description="le fichier excel")],
):
  """Roue pour créer des jetons pour plusieurs étudiants(en chargeant un fichier excel)"""
  
  file_bytes = await excel_file.read()

  file_base64 = base64.b64encode(file_bytes).decode("utf-8")

  import_students_task.delay(file_base64=file_base64, classe_id=classe_id)
  
  return GlobalStringMessage.success_response(data=StringMessage(message="Lecture du fichier en arrière plan"), response=response)



@router.get(
  "/all",
  dependencies=[Depends(RoleDepends.only_managers_authorize)],
  response_model=ListRegistrationInfos,
)
async def all_jetons(
  response: Response,
  reg_service: Annotated[RegistrationService, Depends(get_registration_service)],
  for_back: Annotated[Optional[str], Query(description="ce paramètre concerne le backend. vous pouvez forget")] = None
):
  """Route pour avoir tout les jetons de la db"""

  service_result = await reg_service.service_get_all_jetons(for_back=for_back)

  if service_result.is_error():
    return ListRegistrationInfos.error_response(
      error_message=service_result.error,
      status_code=service_result.status_code,
      response=response
    )
    
  return ListRegistrationInfos.success_response(
    data=service_result.data,
    status_code=service_result.status_code,
    response=response,
  )
  
  
  
@router.get(
  "/all/by-classe/{classe_id}",
  dependencies=[Depends(RoleDepends.only_managers_authorize)],
  response_model=ListRegistrationInfos,
)
async def all_jetons_by_classe(
  response: Response,
  reg_service: Annotated[RegistrationService, Depends(get_registration_service)],
  classe_id: Annotated[UUID, Path(..., description="Id de la classe. celui çi est obligatoire")],
  for_back: Annotated[Optional[str], Query(description="ce paramètre concerne le backend. vous pouvez forget")] = None
):
  """Route pour avoir tout les jetons de la db"""

  service_result = await reg_service.service_get_all_jetons_by_classe(classe_id=classe_id, for_back=for_back)

  if service_result.is_error():
    return ListRegistrationInfos.error_response(
      error_message=service_result.error,
      status_code=service_result.status_code,
      response=response
    )
    
  return ListRegistrationInfos.success_response(
    data=service_result.data,
    status_code=service_result.status_code,
    response=response,
  )