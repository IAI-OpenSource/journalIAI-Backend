
## fichier contenant le service/logique métier de la table user
## vous y trouverez les appels fonctions de repository
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.global_schemas import StringMessage
from app.utils.security_utils import verify_password
from fastapi import status
from app.cache.helpers.base import CacheWrapper
from app.cache.user_cache import UserCache
from app.globals.status_codes import StatusCode
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import CreateUser, LoginData, ReadUser, UpdateUserData
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
        status_code=StatusCode._403_STATUS_FORBIDEN.value, 
        service_name=msg.USER_SERVICE
      )
      
    await self.user_cache.set_user_in_cache(
      user_id=user_read.id, 
      user=user_read, 
      ttl=CacheDurartion.USER_DURATION.value
    )
        
    return ServiceResult.service_success(
      data=ReadUser.model_validate(user.data), 
      status_code=user.status_code,
      service_name=msg.USER_SERVICE
    )



  async def service_create_user(self, user_data: CreateUser) -> ServiceResult[StringMessage]:
    """logique métier pour inserer un utilisateur dans la bd (genre à la création de compte quoi)

    Args:
        user_data (CreateUser): On prend les données validé et envoyer par le front

    Returns:
        ServiceResult[ReadUser]: on va retourner une instance de ServiceResult
    """
    
    db_user = await self.user_repo.insert_user(user_data=user_data)
    
    if db_user.is_error():
      return ServiceResult.service_error(
        message=db_user.error,
        status_code=db_user.status_code,
        service_name=msg.USER_SERVICE
      )
    
    try:
      
      read_user = ReadUser.model_validate(db_user.data)

      await self.user_cache.set_user_in_cache(
        user_id=read_user.id, 
        user=read_user,
        ttl=CacheDurartion.USER_DURATION.value
      )


      return ServiceResult.service_success(
        data=StringMessage(message=msg.ACCOUNT_CREATED_SUCCESSFULLY),
        status_code=db_user.status_code,
        service_name=msg.USER_SERVICE
      )

    except Exception as e:
      logger.info(f"CRASH SERVICE {e.__class__.__name__} : {str(e)}")
      return ServiceResult.service_error(
        message=msg.INTERNAL_SERVER_ERROR,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
      )
      
  
  async def service_get_all_users(self, for_back: Optional[str] = None) -> ServiceResult[list[ReadUser]]:
    """Logique métier pour gérer la récupération de tous les utilisateurs"""

    users_repo = await self.user_repo.get_all_users(for_back=for_back)

    if users_repo.is_error():
      return ServiceResult.service_error(
        message=users_repo.error,
        status_code=users_repo.status_code,
        service_name=msg.USER_SERVICE
      )
      
    ##TODO: implémeter le cache et filtrer la liste via le soft delete. Je veux tester les dependance de role d'abord

    return ServiceResult.service_success(
      data=[ReadUser.model_validate(user) for user in users_repo.data],
      status_code=users_repo.status_code,
      service_name=msg.USER_SERVICE
    )
    
    
  async def service_update_user(self, user_id: UUID, update_user_data: UpdateUserData) -> ServiceResult[StringMessage]:
    """Logique métier pour mettre à jour les informations d'un utilisateur"""

    new_user = await self.user_repo.update_user(user_id=user_id, user_update_data=update_user_data)

    if new_user.is_error():
      return ServiceResult.service_error(
        message=new_user.error,
        status_code=new_user.status_code,
        service_name=msg.USER_SERVICE
      )
      
    ## comme opération à réusssi il faut supprimer l'ancien dans le cache
    ## et ajouter le nouveau
    await self.user_cache.delete_user_from_cache(user_id=user_id)
    await self.user_cache.set_user_in_cache(
      user_id=new_user.data.id,
      user=ReadUser.model_validate(new_user.data),
      ttl=CacheDurartion.USER_DURATION.value
    )
    
    return ServiceResult.service_success(
      data=StringMessage(message=msg.USER_UPDATED),
      status_code=new_user.status_code,
      service_name=msg.USER_SERVICE
    )