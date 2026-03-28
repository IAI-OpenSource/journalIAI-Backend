
## fichier contenant le service/logique métier de la table session
## vous y trouverez les appels fonctions de repository


from dataclasses import dataclass
import logging
import traceback
from typing import Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

<<<<<<< HEAD
=======
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import CreateUser, ReadUser
from app.globals.messages import Messages as msg
from app.cache.helpers.base import CacheWrapper
from app.cache.user_cache import UserCache
from app.globals.status_codes import StatusCode
>>>>>>> origin/feature/clubs-events
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import CreateUser, ReadUser
from app.globals.messages import Messages as msg

from . import ServiceResult


logger = logging.getLogger(__name__)


class UserService: 
  
  def __init__(self, db: AsyncSession):
    self.db = db
    self.user_repo = UserRepository(self.db)
  
    
  async def service_find_user_by_id(self, user_id: UUID) -> ServiceResult[ReadUser]:
    """Logique métier de récupération d'un utilisateur par ID"""

    user = await self.user_repo.get_user_by_sid(user_id=user_id)
    
    if user.is_error():
      logger.error(f"Erreur: {user.error}")
      return ServiceResult.service_error(
        message=user.error, 
        status_code=user.status_code, 
        service_name=msg.USER_SERVICE
      )
    
    if ReadUser.model_validate(user.data).is_deleted(): 
      
      logger.error(f"Erreur: {msg.DELETED_USER}")                        
      return ServiceResult.service_error(
        message=f"Erreur: {msg.DELETED_USER}", 
        status_code=400, 
        service_name=msg.USER_SERVICE
      )
        
    return ServiceResult.service_success(user.data, status_code=user.status_code)