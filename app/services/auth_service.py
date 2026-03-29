
## fichier contenant le service/logique métier de la table 
## vous y trouverez les appels fonctions de repository
from datetime import UTC, datetime, timedelta
import logging
import random
import secrets
from uuid import UUID

from fastapi import Request, Response
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.cookie_handler import CookieManager
from app.auth.jwt_handler import JWTManager
from app.core.config import ACCESS_SECRET_KEY, JWT_COOKIE_ACCESS_ID, JWT_EXPIRES_MINUTES, SID_REF_COOKIE
from app.db.models.user import User
from app.integrations.fastApi_email.email_manager import EmailServiceManager
from app.schemas.global_schemas import SendOTPEmail, StringMessage, VerifyOTPData
from app.schemas.session_schemas import CreateSession
from app.services.session_service import SessionService
from app.utils.security_utils import verify_password
from app.cache.helpers.base import CacheWrapper
from app.cache.user_cache import UserCache
from app.globals.status_codes import StatusCode
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import CreateUser, LoginData, ReadUser
from app.globals.messages import Messages as msg
from app.globals.cache_duration import CacheDurartion 
from app.integrations.fastApi_email.fastapi_mail_config import fm

from . import ServiceResult


logger = logging.getLogger(__name__)


class AuthService: 
  
  def __init__(self, db: AsyncSession, cache: CacheWrapper, response: Response, request: Request):
    self.db = db
    self.user_cache = UserCache(cache)
    self.user_repo = UserRepository(self.db)
    self.email_manager = EmailServiceManager(fast_mail=fm)
    self.session_service = SessionService(self.db, cache)
    self.cookie_manager = CookieManager(response=response, request=request)
      
      
  async def service_find_user_by_email(self, login_data: LoginData) -> ServiceResult[StringMessage]:
    """Logique métier pour récupérer un utilisateur à partir de 
      son email: Beaucoup plus spécial pour la connexion"""

    db_user = await self.user_repo.get_user_by_email(email=login_data.email)
    
    if db_user.is_error():
      return ServiceResult.service_error(
        message=db_user.error,
        status_code=db_user.status_code,
        service_name=msg.USER_SERVICE
      )
      
    if not verify_password(
      plain_password=login_data.password,
      hashed_password=db_user.data.password_hash ):
      return ServiceResult.service_error(
        message=msg.LOGIN_NOT_FOUND,
        status_code=db_user.status_code,
        service_name=msg.USER_SERVICE
      )
    
    ## si on a pas d'erreur bd, on génère un code aléatoire (OTP)
    # qu'on va envoyer a l'utiisateur et metre en cache
    code_otp = random.randint(100000, 999999)
      
    email_data = SendOTPEmail(
      email_to=db_user.data.email,
      otp=str(code_otp),
      last_name=db_user.data.last_name,
      first_name=db_user.data.first_name
    )
      
    mail_result = await self.email_manager.send_otp_email(data_email_to=email_data)
    
    if mail_result.is_error():
      return ServiceResult.service_error(
        message=mail_result.error,
        status_code=mail_result.status_code,
        service_name=mail_result.service_name
      )
      
    await self.user_cache.set_user_otp_code_in_cache(
      user_mail=db_user.data.email,
      otp=str(code_otp),
      ttl=CacheDurartion.OTP_DURATION.value
    )
    
    return ServiceResult.service_success(
      data=mail_result.data,
      status_code=mail_result.status_code,
      service_name=mail_result.service_name
    )
    
    
  async def find_user_by_email(self, email: EmailStr) -> ServiceResult[User]:
    """Logique métier pour récupérer un utilisateur à partir de 
      son email: Mais celle ci ne concerne par la connexion"""

    db_user = await self.user_repo.get_user_by_email(email=email)
    
    if db_user.is_error():
      return ServiceResult.service_error(
        message=db_user.error,
        status_code=db_user.status_code,
        service_name=msg.USER_SERVICE
      )
      
    return ServiceResult.service_success(
      data=db_user.data,
      status_code=db_user.status_code,
      service_name=msg.USER_SERVICE
    )


  async def verify_user_otp_code(self, otp_verify_data: VerifyOTPData) -> ServiceResult[StringMessage]:
    """Logique métier pour vérifier le OTP et créer la session de l'utilisateur"""

    cache_otp = await self.user_cache.get_user_otp_in_cache(email=otp_verify_data.sender_email)

    if cache_otp is None:
      return ServiceResult.service_error(
        message=f"Impossible de récupérer le OTP pour {otp_verify_data.sender_email}",
        status_code=StatusCode._404_STATUS_NOT_FOUND,
        service_name=msg.OTP_SERVICE
      )
      
    if cache_otp["otp"] == otp_verify_data.otp:
      ## comme le OTP est valide on va :
      ## générer le refresh_token sous form de jeton secret et on cré une session dans la db
      refresh_token = secrets.token_urlsafe(16)
      user = await self.find_user_by_email(email=otp_verify_data.sender_email)
      
      if user.is_error():
        return ServiceResult.service_error(
          message=user.error,
          status_code=user.status_code,
          service_name=user.service_name
        )
        
      db_user_session = CreateSession(
        user_id=user.data.id,
        ref_token=refresh_token,
        ip_address=None,
        user_agent=None,
        expires_at=datetime.now(UTC) + timedelta(days=1) # 1 jours pour les test
      )
      created_session = await self.session_service.service_create_session(db_user_session)
      
      if created_session.is_error():
        return ServiceResult.service_error(
          message=created_session.error,
          status_code=created_session.status_code,
          service_name=created_session.service_name
        )
        
      ## on cré ensuite le access plus court 15 min
      access_token = JWTManager.create_access_token(data_to_encode={"sid": str(created_session.data.id)}, cle=ACCESS_SECRET_KEY)

      ## maintenant on les stock dans les cookie pour gérer les requettes avec ça
      self.cookie_manager.add_cookie(id=JWT_COOKIE_ACCESS_ID, value=access_token, age=JWT_EXPIRES_MINUTES)
      self.cookie_manager.add_cookie(id=SID_REF_COOKIE, value=created_session.data.refresh_token_hash, age=60*24*2) ## age c'est pr test

      return ServiceResult.service_success(
        data=StringMessage(message=msg.LOGIN_SUCCESSFUL),
        status_code=StatusCode._200_STATUS_SUCCESS,
        service_name=msg.OTP_SERVICE
      )
      
    return ServiceResult.service_error(
      message="le OTP fourni est incorrect",
      status_code=StatusCode._400_STATUS_BAD_REQUEST,
      service_name=msg.OTP_SERVICE
    )
      
    