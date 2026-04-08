## fichier contenant le service/logique métier de la table session
## vous y trouverez les appels fonctions de repository


import base64
from dataclasses import dataclass
from io import BytesIO
import logging
import traceback
from typing import Optional, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import UserRole
from app.repositories.registration_repository import RegistrationRepository
from app.schemas.global_schemas import StringMessage
from app.schemas.registration_schemas import CreateRegistration, FindRegistration, JetonUpdateData, ReadRegistration
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
          data=ReadRegistration.model_validate(reg_repo.data),
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
      data=ReadRegistration.model_validate(repo_reg.data),
      status_code=repo_reg.status_code,
      service_name=msg.READ_REGISTRATION
    )
    
    
  async def service_imports_reg_data(self, file_base: str, classe_id: UUID) -> ServiceResult[StringMessage]:
    """Logique métier pour générer plusieurs jeton en meme temps
      (à partir d'un fichier excel)"""

    file_bytes = base64.b64decode(file_base)
    file_like = BytesIO(file_bytes)

    res_import = await JetonUtils.read_excel_file(file_like)
    
    if res_import.is_error():
      return ServiceResult.service_error(
        message=res_import.error,
        status_code=res_import.status_code,
        service_name=res_import.service_name
      )
      
    if res_import.data["data"]:

      for row in res_import.data["data"]:
        row["classe_id"] = classe_id
        row["role"] = UserRole.STUDENT.value
        row["jeton"] = JetonUtils.generate_code_jeton(8)
          
      result = await self.resgistration_repo.multiple_registration(res_import.data["data"])

      if result.is_success():
        return ServiceResult.service_success(
          data=StringMessage(message=result.data),
          status_code=result.status_code,
          service_name=msg.REGISTRATION_JETON
        )
      
      return ServiceResult.service_error(
        message=result.error,
        status_code=result.status_code,
        service_name=msg.READ_REGISTRATION
      )
      
    return ServiceResult.service_error(
      message=f'Les erreurs: {res_import.data["errors"]}',
    )
      
  
  async def service_update_registration(self, reg_id: UUID, reg_update_data: JetonUpdateData) -> ServiceResult[StringMessage]:
    """Logique métier pour mettre à jour le role d'un jeton"""

    repo_result = await self.resgistration_repo.update_registration_jeton(reg_id=reg_id, reg_update_data=reg_update_data)

    if repo_result.is_error():
      return ServiceResult.service_error(
        message=repo_result.error,
        status_code=repo_result.status_code
      )
        
    return ServiceResult.service_success(
      data=StringMessage(message="Jeton mis à jour avec succès"),
      status_code=repo_result.status_code,
      service_name=msg.REGISTRATION_JETON
    )
    
    
  async def service_get_all_jetons(self, for_back: Optional[str] = None) -> ServiceResult[list[ReadRegistration]]:
    """Logique métier pour gérer la récupération de tous les jetons"""

    reg_repo = await self.resgistration_repo.get_all_jetons(for_back=for_back)

    if reg_repo.is_error():
      return ServiceResult.service_error(
        message=reg_repo.error,
        status_code=reg_repo.status_code,
        service_name=msg.REGISTRATION_JETON
      )
      
    ##TODO: implémeter le cache et filtrer la liste via le soft delete. Je veux tester les dependance de role d'abord

    return ServiceResult.service_success(
      data=[ReadRegistration.model_validate(jeton) for jeton in reg_repo.data],
      status_code=reg_repo.status_code,
      service_name=msg.REGISTRATION_JETON
    )
    
  
  async def service_get_all_jetons_by_classe(self, classe_id: UUID, for_back: Optional[str] = None) -> ServiceResult[list[ReadRegistration]]:
    """Logique métier pour gérer la récupération de tous les jetons d'une classe donnée"""

    reg_repo = await self.resgistration_repo.get_all_jetons_by_classe(classe_id=classe_id, for_back=for_back)

    if reg_repo.is_error():
      return ServiceResult.service_error(
        message=reg_repo.error,
        status_code=reg_repo.status_code,
        service_name=msg.REGISTRATION_JETON
      )
      
    ##TODO: implémeter le cache et filtrer la liste via le soft delete. Je veux tester les dependance de role d'abord

    return ServiceResult.service_success(
      data=[ReadRegistration.model_validate(jeton) for jeton in reg_repo.data],
      status_code=reg_repo.status_code,
      service_name=msg.REGISTRATION_JETON
    )