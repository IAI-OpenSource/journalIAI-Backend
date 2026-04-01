from typing import Annotated
from app.cache.helpers.base import CacheWrapper, get_redis
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas.global_schemas import GlobalStringMessage
from app.schemas.user_schemas import CreateUser, ListUserInfos, UserInfos
from app.services.user_service import UserService
from app.auth.role_depends import RoleDepends

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


@router.get(
  "/all",
  response_model=ListUserInfos,
  dependencies=[Depends(RoleDepends.all_authorize)],
  tags=[ApiTags.ADMINISTRATEUR]
)
async def register(
  response: Response,
  user_service: Annotated[UserService, Depends(get_user_service)]
):
  """Route pour avoir tout les utilisateurs de la db"""

  service_result = await user_service.service_get_all_users()

  if service_result.is_error():
    return ListUserInfos.success_response(
      data=service_result.data,
      status_code=service_result.status_code,
      response=response
    )
    
  return ListUserInfos.success_response(
    data=service_result.data,
    status_code=service_result.status_code,
    response=response,
  )
  