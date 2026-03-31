

from typing import Annotated
from app.cache.helpers.base import CacheWrapper, get_redis
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas.global_schemas import GlobalStringMessage, VerifyOTPData
from app.schemas.user_schemas import CreateUser, LoginData, UserInfos
from app.services.auth_service import AuthService
from app.services.user_service import UserService


router = APIRouter(prefix="/auth", tags=[ApiTags.AUTHENTIFICATION])


## dependence pour appeler le cache qu'on va injecter dans 
# les routes pour créer le service du user
def get_redis_cache(redis: CacheWrapper = Depends(get_redis))-> CacheWrapper:
  return redis

def get_user_service(
  db: Annotated[AsyncSession, Depends(get_db)],
  cache: CacheWrapper = Depends(get_redis_cache)
) -> UserService:
  return UserService(db, cache)

def get_auth_service(
  response: Response,
  request: Request,
  db: Annotated[AsyncSession, Depends(get_db)],
  cache: CacheWrapper = Depends(get_redis_cache),
) -> AuthService:
  return AuthService(db, cache, response, request)


@router.post(
  "/register",
  response_model=GlobalStringMessage,
  tags=[ApiTags.ALL_USERS]
)
async def register(
  user_data:CreateUser,
  response: Response,
  user_service: Annotated[UserService, Depends(get_user_service)]
):
  """Route pour Inscription utilisateur: Création de compte"""

  service_result = await user_service.service_create_user(user_data=user_data)

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
  
  
@router.post(
  "/request-otp",
  tags=[ApiTags.AUTHENTIFICATION],
  response_model=GlobalStringMessage
)
async def login_request_otp(
  login_data: LoginData,
  response: Response,
  auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
  """Route d'authentification pour demander le OTP"""

  auth_service_result = await auth_service.service_find_user_by_email(login_data=login_data)

  return auth_service_result.to_HTTP_api_base_response(reponse=response)


@router.post(
  "/verify-otp",
  tags=[ApiTags.AUTHENTIFICATION],
  response_model=GlobalStringMessage
)
async def login_verify_otp(
  otp_verify_data: VerifyOTPData,
  response: Response,
  auth_service: Annotated[AuthService, Depends(get_auth_service)]
):
  """Route d'authentification pour verifier le OTP"""

  auth_service_result = await auth_service.verify_user_otp_code(otp_verify_data=otp_verify_data)

  return auth_service_result.to_HTTP_api_base_response(reponse=response)