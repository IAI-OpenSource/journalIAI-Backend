from typing import Annotated
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


from fastapi import APIRouter, Depends, File, Form, Response, UploadFile

from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas import ApiBaseResponse
from app.schemas.global_schemas import GlobalStringMessage
from app.schemas.registration_schemas import CreateRegistration, ReadRegistration, RegistrationInfos
from app.services.registration_service import RegistrationService


router = APIRouter(prefix="/registration", tags=[ApiTags.JETON_ENREGISTREMENT])


## function global pour creer une instance de 
# RegistrationService pour le fichier. Comme c'est une simple fonction pas besoins
# de deplacer ça 
def get_registration_service(db: AsyncSession = Depends(get_db)) -> RegistrationService:
  return RegistrationService(db=db)



@router.post(
  "/add",
  response_model=GlobalStringMessage,
  tags=[ApiTags.ADMIN_MODERATEUR]
)
async def create_registration(
  response: Response,
  reg_data: CreateRegistration,
  reg_service: Annotated[RegistrationService, Depends(get_registration_service)]):
  """Route pour créer 1 seul jeton"""
  
  db_reg = await reg_service.service_create_registration(registration_data=reg_data)
  
  if db_reg.is_error():
    return ApiBaseResponse.error_response(
      error_message=db_reg.error, 
      response=response, 
      status_code=db_reg.status_code
    )

  return ApiBaseResponse.success_response(
    f"Jeton céer pour l'étudiant {db_reg.data.last_name}", 
    response=response, 
    status_code=db_reg.status_code
  )



@router.get(
  "/one",
  response_model=RegistrationInfos,
  tags=[ApiTags.ADMIN_MODERATEUR]
)
async def create_registration(
  response: Response,
  find_reg_data: CreateRegistration,
  reg_service: Annotated[RegistrationService, Depends(get_registration_service)]):
  """Route pour récupérer 1 seul jeton"""
  
  db_reg = await reg_service.service_get_registration_by_jeton(find_registration_data=find_reg_data)
  
  return db_reg.to_HTTP_api_base_response(response)


@router.post(
  "/students/import",
  response_model=GlobalStringMessage,
  tags=[ApiTags.ADMIN_MODERATEUR]
)
async def imports_students(
  response: Response,
  classe_id: Annotated[UUID, Form(..., description="ID de la classe concernée")],
  excel_file: Annotated[UploadFile, File(..., description="le fichier excel")],
  reg_service: Annotated[RegistrationService, Depends(get_registration_service)]
):
  """Roue pour créer des jetons pour plusieurs étudiants(en chargeant un fichier excel)"""
  
  result = await reg_service.service_imports_reg_data(
    file=excel_file,
    classe_id=classe_id
  )
  
  return result.to_HTTP_api_base_response(response)
