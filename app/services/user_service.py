
## fichier contenant le service/logique métier de la table user
## vous y trouverez les appels fonctions de repository
import logging
from typing import Optional, Union
from uuid import UUID

from alembic.environment import Union
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.enums import MediaType
from app.schemas.global_schemas import StringMessage
from app.schemas.post_upload_schemas import AvailableUploadMethod, FileInUploadURLSchema, UploadURLSchema
from app.services.media_upload_service import generate_random_intent_id
from app.storage.minio_client import MinioClientFactory
from app.storage.minio_config import BucketName
from app.storage.post_upload_storage import PostUploadStorage
from fastapi import status
from app.cache.helpers.base import CacheWrapper
from app.cache.user_cache import UserCache
from app.globals.status_codes import StatusCode
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import CreateUser, ReadUser, UpdateAvatarUrl, UpdateUserData
from app.globals.messages import Messages as msg
from app.globals.cache_duration import CacheDurartion 

from . import ServiceResult


logger = logging.getLogger(__name__)


class UserService: 
  
  def __init__(self, db: AsyncSession, cache: CacheWrapper):
    self.__db = db
    self.__user_cache = UserCache(cache)
    self.__user_repo = UserRepository(self.__db)
  
  ## -------------- Logique find user by id ------------------ ##
  async def service_find_user_by_id(self, user_id: UUID) -> ServiceResult[ReadUser]:
    """Logique métier de récupération d'un utilisateur par ID"""
    
    ## on cherche dans le cache d'abord  
    user_data_from_cache = await self.__user_cache.get_user_from_cache(user_id=user_id, user_model=ReadUser)
    
    if user_data_from_cache is not None:
      return ServiceResult.service_success(data=user_data_from_cache, status_code=StatusCode._200_STATUS_SUCCESS.value)

    ## si le cache est vide, on fait la requete BD
    user = await self.__user_repo.get_user_by_id(user_id=user_id)
    
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
      
    await self.__user_cache.set_user_in_cache(
      user_id=user_read.id, 
      user=user_read, 
      ttl=CacheDurartion.USER_DURATION.value
    )
        
    return ServiceResult.service_success(
      data=ReadUser.model_validate(user.data), 
      status_code=user.status_code,
      service_name=msg.USER_SERVICE
    )


  ## -------------- Logique métier de création d'utilisateur ------------------ ##
  async def service_create_user(self, user_data: CreateUser) -> ServiceResult[StringMessage]:
    """logique métier pour inserer un utilisateur dans la bd (genre à la création de compte quoi)

    Args:
        user_data (CreateUser): On prend les données validé et envoyer par le front

    Returns:
        ServiceResult[ReadUser]: on va retourner une instance de ServiceResult
    """
    
    db_user = await self.__user_repo.insert_user(user_data=user_data)
    
    if db_user.is_error():
      return ServiceResult.service_error(
        message=db_user.error,
        status_code=db_user.status_code,
        service_name=msg.USER_SERVICE
      )
    
    try:
      
      read_user = ReadUser.model_validate(db_user.data)

      await self.__user_cache.set_user_in_cache(
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
      
  
  ## -------------- Logique métier pour récupérer tous les utilisateurs ------------------ ##
  async def service_get_all_users(self, for_back: Optional[str] = None) -> ServiceResult[list[ReadUser]]:
    """Logique métier pour gérer la récupération de tous les utilisateurs"""

    users_repo = await self.__user_repo.get_all_users(for_back=for_back)

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
    
 
  ## -------------- Logique métier pour mettre à jour les infos d'un utilisateur ------------------ ##  
  async def service_update_user(self, user_id: UUID, user_update_data: Union[UpdateUserData, UpdateAvatarUrl]) -> ServiceResult[StringMessage]:
    """Logique métier pour mettre à jour les informations d'un utilisateur"""

    new_user = await self.__user_repo.update_user(user_id=user_id, user_update_data=user_update_data)

    if new_user.is_error():
      return ServiceResult.service_error(
        message=new_user.error,
        status_code=new_user.status_code,
        service_name=msg.USER_SERVICE
      )
      
    ## comme opération à réusssi il faut supprimer l'ancien dans le cache
    ## et ajouter le nouveau
    await self.__user_cache.delete_user_from_cache(user_id=user_id)
    await self.__user_cache.set_user_in_cache(
      user_id=new_user.data.id,
      user=ReadUser.model_validate(new_user.data),
      ttl=CacheDurartion.USER_DURATION.value
    )
    
    return ServiceResult.service_success(
      data=StringMessage(message=msg.USER_UPDATED),
      status_code=new_user.status_code,
      service_name=msg.USER_SERVICE
    )
    

  ## -------------- Logique métier pour demander une URL présignée ------------------ ##
  def get_avatar_upload_intent(self, file_name: str) -> ServiceResult[UploadURLSchema]:
      """
      Logique métier pour demander une URL présignée pour uploader un nouvel avatar.
      """

      intent_id = generate_random_intent_id(16)
      upload_url = PostUploadStorage.get_image_upload_intent_presigned_upload_url(
        intent_id=intent_id, 
        filename=file_name
      )
      
      if not upload_url:
        return ServiceResult.service_error(
          message="Erreur lors de la génération de l'URL",
          status_code=StatusCode._500_INTERNAL_SERVER_ERROR.value,
        )
  
      return ServiceResult.service_success(
        data=UploadURLSchema(
          intent_id=intent_id,
          files=[FileInUploadURLSchema(
              upload_url=upload_url,
              method=AvailableUploadMethod.PUT,
              file_name=file_name,
              media_type=MediaType.IMAGE
          )]
        )
      )