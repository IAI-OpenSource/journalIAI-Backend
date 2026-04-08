import urllib.parse
import base64
import logging
from typing import Annotated, Optional, Union
from uuid import UUID

from fastapi.responses import StreamingResponse
from app.auth.role_depends import RoleDepends
from app.db.models.enums import CeleryStatus, DownloadFormat
from app.utils.pdf_utils import PDFExportUtils
from app.worker.celery_app import celery_app
from sqlalchemy.ext.asyncio import AsyncSession


from fastapi import APIRouter, Depends, File, Form, Path, Query, Response, UploadFile

from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas import ApiBaseResponse
from app.schemas.global_schemas import GlobalStringMessage, StringMessage
from app.schemas.registration_schemas import CreateRegistration, ExcelReadSuccess, ExcelSuccessInfos, ExcelUploadResponse, FindRegistration, JetonUpdateData, ListRegistrationInfos, ExcelUploadInfos, RegistrationInfos
from app.services.registration_service import RegistrationService
from app.worker.tasks.excel_task import import_students_task


router = APIRouter(prefix="/registration", tags=[ApiTags.JETON_ENREGISTREMENT])
logger = logging.getLogger(__name__)


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
  response_model=ExcelUploadInfos,
)
async def imports_students(
  response: Response,
  classe_id: Annotated[UUID, Form(..., description="ID de la classe concernée")],
  excel_file: Annotated[UploadFile, File(..., description="le fichier excel")],
):
  """Roue pour créer des jetons pour plusieurs étudiants(en chargeant un fichier excel)"""
  
  file_bytes = await excel_file.read()

  file_base64 = base64.b64encode(file_bytes).decode("utf-8")

  task = import_students_task.delay(file_base64=file_base64, classe_id=classe_id)
  
  return ExcelUploadInfos.success_response(
    data=ExcelUploadResponse(
      message="Importation lancée. Accéder à l'ID de la tache pou suivre sont état/statut",
      task_id=task.id  
    ), 
    response=response
  )



@router.get(
  "/import/status/{task_id}",
  response_model=ExcelSuccessInfos
)
async def check_status(
  response: Response,
  task_id: Annotated[str, Path(description="ID de la tache que vous avez récupéré")]
  ):
  """Route pour checker l'etat/statut du chargement du fichier excel"""
  task_result = import_students_task.AsyncResult(task_id)
  
  if task_result.state == CeleryStatus.PENDING.value:
    return ExcelSuccessInfos.error_response(
      error_message="Ajout de jetons en cours ...",
      response=response
    )
  elif task_result.state == CeleryStatus.SUCCESS:
      return ExcelSuccessInfos.success_response(
        data=ExcelReadSuccess(
          status=CeleryStatus.SUCCESS,
          message="Plusieurs jetons ajoutée avec succès !"
        ),
        response=response
      )
  elif task_result.state == CeleryStatus.FAILURE:
      # C'est ici que le meta data de ton update_state apparaîtra
      logger.error(str(task_result.info))
      return ExcelSuccessInfos.error_response(
      error_message="Ajout de jetons échoué. Veuillez réessayer",
      response=response
    )
  

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



@router.get(
  "/export/jetons/{classe_id}/{format}",
  response_model=None
)
async def export_pdf_jetons(
    classe_id: Annotated[UUID, Path(description="ID de la classe")],
    response: Response,
    format: Annotated[DownloadFormat, Path(description="Format de téléchargement")],
    reg_service: Annotated[RegistrationService, Depends(get_registration_service)]
  ):
    """Route pour exporter les jetons en pdf"""
    service_result = await reg_service.service_get_all_jetons_by_classe(classe_id) 

    if service_result.is_error():
      return ApiBaseResponse.error_response(
        error_message=service_result.error,
        response=response
      )
    
    if not service_result.data:
      return ApiBaseResponse.error_response(
        error_message="Aucun jetons trouvé pour cette classe",
        response=response
      )
      
    if format == DownloadFormat.JSON:
      return ApiBaseResponse.success_response(
        data=[s.model_dump(exclude={'role', 'executive_role', 'used_at', 'added_at'}) for s in service_result.data],
        response=response
      )

    pdf_buffer = PDFExportUtils.generate_jetons_pdf(
      service_result.data
      , f"Classe {service_result.data[0].classe.classe_prefix.value if service_result.data[0].classe else None} {service_result.data[0].classe.classe_suffix.upper() if service_result.data[0].classe else None}")

    filename = f"Jetons_IAI_Classe_{classe_id}.pdf"
    
    encoded_filename = urllib.parse.quote(filename)

    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        "Content-Type": "application/pdf"
    }

    return StreamingResponse(
        pdf_buffer, 
        headers=headers, 
        media_type="application/pdf"
    )