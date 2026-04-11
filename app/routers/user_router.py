from typing import Annotated, Optional, Union
from urllib import response

from fastapi.params import Body
from app.auth.dependencies import get_current_user
from app.auth.role_depends import RoleDepends
from app.cache.helpers.base import CacheWrapper, get_redis
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas.global_schemas import GlobalStringMessage, StringMessage
from app.schemas.user_schemas import ConfirmUploadAvatarFile, ListUserInfos, ReadUser, UpdateAvatarUrl, UpdateUserData, UploadAvatarFile, UserAvatarInfos, UserInfos
from app.services.user_service import UserService
from app.globals.status_codes import StatusCode
from app.globals.messages import Messages as msg
from app.storage.media_upload_storage import MediaUploadStorage
from app.worker.tasks.user_avatar_process_task import process_user_avatar_task


router = APIRouter(prefix="/user", tags=[ApiTags.USER], dependencies=[Depends(RoleDepends.all_authorize)],)


## dependence pour appeler le cache qu'on va injecter dans 
# les routes pour créer le service du user
def get_redis_cache(redis: CacheWrapper = Depends(get_redis))-> CacheWrapper:
  return redis

def get_user_service(
  db: Annotated[AsyncSession, Depends(get_db)],
  cache: CacheWrapper = Depends(get_redis_cache)
) -> UserService:
  return UserService(db, cache)



## -------------- Route pour avoir tous les utilisateurs --------------- ## 
@router.get(
  "/all",
  response_model=ListUserInfos,
  tags=[ApiTags.ADMINISTRATEUR]
)
async def all_users(
  response: Response,
  user_service: Annotated[UserService, Depends(get_user_service)],
  for_back: Annotated[Optional[str], Query(description="ce paramètre concerne le backend. vous pouvez forget")] = None
):
  """Route pour avoir tout les utilisateurs de la db"""

  service_result = await user_service.service_get_all_users(for_back=for_back)

  if service_result.is_error():
    return ListUserInfos.error_response(
      error_message=service_result.error,
      status_code=service_result.status_code,
      response=response
    )
    
  return ListUserInfos.success_response(
    data=service_result.data,
    status_code=service_result.status_code,
    response=response,
  )
  


## -------------- Route pour avoir le profil de l'utilisateur actuellement connecter ---------------- ##
@router.get(
  "/me/user-profil-data",
  response_model=UserInfos,
)
async def get_current_user_data(
  response: Response,
  current_user: Annotated[ReadUser, Depends(get_current_user)]
):
  """Route pour avoir tous les les infos du users actuellement 
  connecter. Utiliser ça pour le profil de létudiant"""


  if current_user is None:
    return UserInfos.error_response(
      error_message=msg.USER_NOT_FOUND,
      status_code=StatusCode._404_STATUS_NOT_FOUND.value,
      response=response
    )
    
  return UserInfos.success_response(
    data=current_user,
    status_code=StatusCode._200_STATUS_SUCCESS.value,
    response=response,
  )
  
  
## ---------------- Route pour mettre à jour les infos d'un utilisateur ------------------- ## 
@router.patch(
  "/update",
  response_model=GlobalStringMessage
)
async def update_user_infos(
  response: Response,
  new_user_infos: UpdateUserData,
  current_user: Annotated[ReadUser, Depends(get_current_user)],
  user_service: Annotated[UserService, Depends(get_user_service)]
):
  """Route pour mettre à jour les données d'un utilisateur. Utiliser cette route quand 
  l'utilisateur connecté veux changer des informations du profil(username, bio, sexe).  
  """
  
  service_result = await user_service.service_update_user(
    user_id=current_user.id,
    user_update_data=new_user_infos
  )

  if service_result.is_error():
    return GlobalStringMessage.error_response(
      error_message=service_result.error,
      status_code=service_result.status_code,
      response=response
    )
    
  return GlobalStringMessage.success_response(
    data=service_result.data,
    status_code=service_result.status_code,
    response=response,
  )
  
  

## -------------- Route pour demander une URL présignée pour uploader un nouvel avatar ------------------ ##
@router.post(
  "/me/avatar/upload-intent", 
  response_model=UserAvatarInfos
)
async def get_avatar_upload_intent(
  response: Response,
  user_service: Annotated[UserService, Depends(get_user_service)],
  file_name: UploadAvatarFile,
):
  """Route pour demander une URL présignée pour uploader un nouvel avatar. 
    L'utilisateur doit d'abord uploader l'image sur l'URL présignée, 
    ensuite vous récupérez le nom du fichier pour nous envoyer.
    On va vous renvoyer l'URL de l'image traitée pour que vous puissiez faire une requete sur Minio et
    l'afficher dans le profil de l'utilisateur
  """
  
  service_result = user_service.get_avatar_upload_intent(file_name=file_name)

  return service_result.to_HTTP_api_base_response(reponse=response)


## -------------- Route pour confirmer que l'upload de l'avatar est fini ------------------ ##
@router.post(
  "/me/avatar/confirm",
  response_model=GlobalStringMessage
)
async def confirm_avatar_upload(
  response: Response,
 confirm_data: ConfirmUploadAvatarFile,
  current_user: Annotated[ReadUser, Depends(get_current_user)]
):
  """Route pur confirme que l'upload est fini, 
    appeler cette route pour confirmer que l'upload est fini et on va update dans la DB
  """
  
  # On vérifie d'abord si le fichier existe bien dans le bucket RAW minio
  file_info =  MediaUploadStorage.get_image_upload_intent_file_info(
    intent_id=confirm_data.indent_id,
    filename=confirm_data.file_name
  )
  
  if not file_info:
      return GlobalStringMessage.error_response(
          error_message="Fichier non trouvé sur le serveur de stockage",
          status_code=StatusCode._404_STATUS_NOT_FOUND.value,
          response=response
      )

  process_user_avatar_task.delay(
      user_id=str(current_user.id),
      intent_id=confirm_data.indent_id,
      filename=confirm_data.file_name
  )

  return GlobalStringMessage.success_response( 
    data=StringMessage(message="Upload confirmé. Le traitement de l'image est en cours."),
    status_code=StatusCode._200_STATUS_SUCCESS.value,
    response=response
  ) 

