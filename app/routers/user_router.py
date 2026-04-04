from typing import Annotated
from app.auth.dependencies import get_current_user
from app.cache.helpers.base import CacheWrapper, get_redis
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas.global_schemas import GlobalStringMessage, StringMessage
from app.schemas.user_schemas import ListUserInfos, ReadUser, UpdateUserData, UserInfos
from app.services.user_service import UserService
from app.auth.role_depends import RoleDepends
from app.globals.status_codes import StatusCode
from app.globals.messages import Messages as msg


router = APIRouter(prefix="/user", tags=[ApiTags.USER])


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
  dependencies=[Depends(RoleDepends.all_authorize)],
  tags=[ApiTags.ADMINISTRATEUR]
)
async def all_users(
  response: Response,
  user_service: Annotated[UserService, Depends(get_user_service)]
):
  """Route pour avoir tout les utilisateurs de la db"""

  service_result = await user_service.service_get_all_users()

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
  "/user-profil-data",
  response_model=UserInfos,
  tags=[ApiTags.ADMINISTRATEUR]
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
@router.post(
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
  l'utilisateur connecté veux changer des informations du profil  
  """
  
  service_result = await user_service.service_update_user(
    user_id=current_user.id,
    update_user_data=new_user_infos
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