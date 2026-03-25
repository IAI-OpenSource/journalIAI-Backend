

from typing import Annotated
from app.cache.helpers.base import CacheWrapper, get_redis
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas.user_schemas import CreateUser, UserInfos
from app.services.user_service import UserService


router = APIRouter(prefix="/auth", tags=[ApiTags.AUTHENTIFICATION])


## dependence pour appeler le cache qu'on va injecter dans 
# les routes pour créer le service du user
def get_redis_cache()-> CacheWrapper:
  return Depends(get_redis)

def get_user_service(db: Annotated[AsyncSession, Depends(get_db)]) -> UserService:
  return UserService(db, get_redis_cache())


@router.post(
  "/register",
  response_model=UserInfos,
  tags=[ApiTags.ALL_USERS]
)
async def register(
  user_data:CreateUser,
  response: Response,
  user_service: Annotated[UserService, Depends(get_user_service)]
):
  """Route pour Inscription utilisateur: Création de compte"""

  db_user = await user_service.service_create_user(user_data=user_data)

  db_user.to_HTTP_api_base_response(response)