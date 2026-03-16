
## fichier contenant le service/logique métier de la table session
## vous y trouverez les appels fonctions de repository


from dataclasses import dataclass
import logging
import traceback
from typing import Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.helpers.base import CacheWrapper
from app.cache.user_cache import UserCache
from app.globals.status_codes import StatusCode
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import CreateUser, ReadUser
from app.globals.messages import Messages as msg
from app.globals.cache_duration import CacheDurartion 

from . import ServiceResult


logger = logging.getLogger(__name__)


class UserService: 
  
  def __init__(self, db: AsyncSession, cache: CacheWrapper):
    self.db = db
    self.user_cache = UserCache(cache)
    self.user_repo = UserRepository(self.db)
  
    
  async def service_find_user_by_id(self, user_id: UUID) -> ServiceResult[ReadUser]:
    """Logique métier de récupération d'un utilisateur par ID"""
    
    ## on cherche dans le cache d'abord  
    user_data_from_cache = await self.user_cache.get_user_from_cache(user_id=user_id, user_model=ReadUser)
    
    if user_data_from_cache is not None:
      return ServiceResult.service_success(data=user_data_from_cache, status_code=StatusCode._200_STATUS_SUCCESS.value)

    ## si le cache est vide, on fait la requete BD
    user = await self.user_repo.get_user_by_id(user_id=user_id)
    
    if user.is_error():
      logger.error(f"Erreur: {user.error}")
      return ServiceResult.service_error(
        message=user.error, 
        status_code=user.status_code, 
        service_name=msg.USER_SERVICE
      )
      
    user_read = ReadUser.model_validate(user.data)
    
    if user_read.is_deleted(): 
      
      logger.error(f"Erreur: {msg.DELETED_USER}")                        
      return ServiceResult.service_error(
        message=f"Erreur: {msg.DELETED_USER}", 
        status_code=StatusCode._400_STATUS_BAD_REQUEST.value, 
        service_name=msg.USER_SERVICE
      )
      
    await self.user_cache.set_user_in_cache(
      user_id=user_read.id, 
      user=user_read, 
      ttl=CacheDurartion.USER_DURATION.value
    )
        
    return ServiceResult.service_success(user.data, status_code=user.status_code)