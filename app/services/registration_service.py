## fichier contenant le service/logique métier de la table session
## vous y trouverez les appels fonctions de repository


import base64
from dataclasses import dataclass
from io import BytesIO
import logging
import traceback
from typing import Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.registration_repository import RegistrationRepository
from app.schemas.registration_schemas import CreateMultileRegistration, CreateRegistration, FindRegistration, ReadRegistration
from app.globals.messages import Messages as msg
from app.utils.jetons_utils import JetonUtils

from . import ServiceResult


logger = logging.getLogger(__name__)


class RegistrationService:
  
  def __init__(self, db: AsyncSession):
    self.db = db
    self.resgistration_repo = RegistrationRepository(self.db)

  
  async def service_create_registration(self, registration_data: CreateRegistration) -> ServiceResult[ReadRegistration]:
      """Logique Métier pour la création d'une régistration de jeton"""

      reg_repo = await self.resgistration_repo.insert_registration(reg_data=registration_data)
      
      if reg_repo.is_success():
        return ServiceResult.service_success(
          data=reg_repo.data,
          status_code=reg_repo.status_code,
          service_name=msg.REGISTRATION_JETON
        )
      
      return ServiceResult.service_error(
        message=reg_repo.error,
        status_code=reg_repo.status_code,
        service_name=msg.REGISTRATION_JETON
      )
      
  
  async def service_get_registration_by_jeton(
    self, 
    find_registration_data: FindRegistration
  ) -> ServiceResult[ReadRegistration]:
    """Logique métier pour récupérer une régistration de jeton""" 
    
    repo_reg = await self.resgistration_repo.get_registration_by_jeton(find_registration_data)       

    if repo_reg.is_error():
      return ServiceResult.service_error(
        message=repo_reg.error,
        status_code=repo_reg.status_code,
        service_name=msg.READ_REGISTRATION
      )
      
    return ServiceResult.service_success(
      data=repo_reg.data,
      status_code=repo_reg.status_code,
      service_name=msg.READ_REGISTRATION
    )
    
    
  async def service_imports_reg_data(self, file_base: str, classe_id: UUID) -> ServiceResult[str]:
    """Logique métier pour générer plusieurs jeton en meme temps
      (à partir d'un fichier excel)"""

    file_bytes = base64.b64decode(file_base)
    file_like = BytesIO(file_bytes)

    res_import = await JetonUtils.read_excel_file(file_like)
    
    valide_data = res_import["data"]

    for row in valide_data:
      row["classe_id"] = classe_id
      row["jeton"] = JetonUtils.generate_code_jeton(8)
        
    if valide_data:
      result = await self.resgistration_repo.multiple_registration(valide_data)

      if result.is_success():
        return ServiceResult.service_success(
          data=result.data,
          status_code=result.status_code,
          service_name=msg.REGISTRATION_JETON
        )
      
      return ServiceResult.service_error(
        message=result.error,
        status_code=result.status_code,
        service_name=msg.READ_REGISTRATION
      )
      
    return ServiceResult.service_error(
      message=f'Les erreurs: {res_import["errors"]}',
    )
      
    
        
        
    