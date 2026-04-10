
## fichier contenant le service/logique métier de la table 
## vous y trouverez les appels fonctions de repository
from datetime import UTC, datetime, timedelta
import logging
import random
import secrets
from uuid import UUID
from fastapi import HTTPException, Request, Response, status
from pydantic import EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.cookie_handler import CookieManager
from app.auth.jwt_handler import JWTManager
from app.core.config import ACCESS_SECRET_KEY, JWT_COOKIE_ACCESS_ID, JWT_EXPIRES_SECONDES, SID_REF_COOKIE, REFRESH_TOKEN_EXPIRES_SECONDES
from app.db.models.user import User
from app.integrations.fastApi_email.email_manager import EmailServiceManager
from app.schemas.global_schemas import SendOTPEmail, StringMessage, VerifyOTPData
from app.schemas.session_schemas import CreateSession
from app.services.session_service import SessionService
from app.utils.security_utils import get_real_ip, verify_password
from app.cache.helpers.base import CacheWrapper
from app.cache.user_cache import UserCache
from app.globals.status_codes import StatusCode
from app.repositories.user_repository import UserRepository
from app.schemas.user_schemas import LoginData
from app.globals.messages import Messages as msg
from app.globals.cache_duration import CacheDurartion 
from app.integrations.fastApi_email.fastapi_mail_config import fm

from . import ServiceResult


logger = logging.getLogger(__name__)


class AuthService: 
  
  def __init__(self, db: AsyncSession, cache: CacheWrapper, response: Response, request: Request):
    self.__db = db
    self.__user_cache = UserCache(cache)
    self.__user_repo = UserRepository(self.__db)
    self.__email_manager = EmailServiceManager(fast_mail=fm)
    self.__session_service = SessionService(self.__db, cache)
    self.__cookie_manager = CookieManager(response=response, request=request)
      
  ## ------- Service find user by email / connexion etape 1 --------- ##
  async def service_find_user_by_email(self, login_data: LoginData) -> ServiceResult[StringMessage]:
    """Logique métier pour récupérer un utilisateur à partir de 
      son email: Beaucoup plus spécial pour la connexion"""

    db_user = await self.__user_repo.get_user_by_email(email=login_data.email)
    
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
      
    mail_result = await self.__email_manager.send_otp_email(data_email_to=email_data)
    
    if mail_result.is_error():
      return ServiceResult.service_error(
        message=mail_result.error,
        status_code=mail_result.status_code,
        service_name=mail_result.service_name
      )
      
    await self.__user_cache.set_user_otp_code_in_cache(
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

    db_user = await self.__user_repo.get_user_by_email(email=email)
    
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


  ## ------------ Service verify OTP ----------------- ##
  async def verify_user_otp_code(self, otp_verify_data: VerifyOTPData) -> ServiceResult[StringMessage]:
    """Logique métier pour vérifier le OTP et créer la session de l'utilisateur"""

    cache_otp = await self.__user_cache.get_user_otp_in_cache(email=otp_verify_data.sender_email)

    if cache_otp is None:
      return ServiceResult.service_error(
        message=f"Impossible de récupérer le OTP pour {otp_verify_data.sender_email}",
        status_code=StatusCode._404_STATUS_NOT_FOUND.value,
        service_name=msg.OTP_SERVICE
      )
      
    if cache_otp["otp"] == str(otp_verify_data.otp):
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
        ip_address=None, ## géré cette partie après
        user_agent=self.__cookie_manager.request.headers.get("user-agent"),
        expires_at=datetime.now(UTC) + timedelta(days=1) # 1 jours pour les test
      )
      created_session = await self.__session_service.service_create_session(db_user_session)
      
      if created_session.is_error():
        return ServiceResult.service_error(
          message=created_session.error,
          status_code=created_session.status_code,
          service_name=created_session.service_name
        )
        
      ## on cré ensuite le access plus court 15 min
      access_token = JWTManager.create_access_token(data_to_encode={"sid": str(created_session.data.id)}, cle=ACCESS_SECRET_KEY)
      ref_token = JWTManager.create_access_token(data_to_encode={"sid": str(created_session.data.id), "ref_token_hash": created_session.data.refresh_token_hash}, cle=ACCESS_SECRET_KEY)

      ## maintenant on les stock dans les cookie pour gérer les requettes avec ça
      self.__cookie_manager.add_cookie(id=JWT_COOKIE_ACCESS_ID, value=access_token, age=JWT_EXPIRES_SECONDES)
      self.__cookie_manager.add_cookie(id=SID_REF_COOKIE, value=ref_token, age=REFRESH_TOKEN_EXPIRES_SECONDES) 
      
      ##TODO : avant d'aller en prod, implementer suppression du cache ici
      return ServiceResult.service_success(
        data=StringMessage(message=msg.LOGIN_SUCCESSFUL),
        status_code=StatusCode._200_STATUS_SUCCESS.value,
        service_name=msg.OTP_SERVICE
      )
      
      
    return ServiceResult.service_error(
      message="le OTP fourni est incorrect",
      status_code=StatusCode._400_STATUS_BAD_REQUEST.value,
      service_name=msg.OTP_SERVICE
    )
    
  
  ## ----------------- Service refresh token ------------------------ ##  
  async def service_manage_refresh(self) -> ServiceResult[StringMessage]:
    """Logique métier pour gérer le refresh token"""
    
    access_token = self.__cookie_manager.get_cookie(id=SID_REF_COOKIE)
    
    if access_token is None:
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Aucune clé d'access fourni tchaley"
      )

    payload = JWTManager.decode_access_token(token=access_token, cle=ACCESS_SECRET_KEY)

    if payload is None:
      raise HTTPException(
          status_code=status.HTTP_401_UNAUTHORIZED,
          detail="Clé d'accès invalide"
      )
    
    user_session = await self.__session_service.service_find_session_by_sid(sid=UUID(payload["sid"]))
        
    if user_session.is_error():
        raise HTTPException(
            status_code=user_session.status_code,
            detail=user_session.error
        )
        
    if user_session.data.refresh_token_hash != payload["ref_token_hash"]:
      return ServiceResult.service_error(
        message="Session non valide tchaley",
        status_code=StatusCode._401_STATUS_UNAUTHORIZED.value,
        service_name=msg.USER_SERVICE
      )
      
    ## si la session est valide et est la bonne on cré un nouveau access token puis le cookie
    access_token = JWTManager.create_access_token(data_to_encode={"sid": str(user_session.data.id)}, cle=ACCESS_SECRET_KEY)
    self.__cookie_manager.add_cookie(id=JWT_COOKIE_ACCESS_ID, value=access_token, age=JWT_EXPIRES_SECONDES)
      
    
    return ServiceResult.service_success(
      data=StringMessage(message="Nouveau access créé avec success"),
      status_code=StatusCode._200_STATUS_SUCCESS.value,
      service_name=msg.USER_SERVICE
    )
    
    
  ## ---------------- Service pour gérer les déconnexion / logout ------------------ ##
  def service_logout_account(self) ->ServiceResult[StringMessage]:
    """Logique métier pour gérer les déconnexion / logout"""

    ## qd le user veux se déconnecter, on supprime tou ses cookies simplement
    self.__cookie_manager.delete_cookie(id=JWT_COOKIE_ACCESS_ID)
    self.__cookie_manager.delete_cookie(id=SID_REF_COOKIE)

    return ServiceResult.service_success(
      data=StringMessage(message="Déconnecter avec succès"),
      status_code=StatusCode._200_STATUS_SUCCESS.value,
      service_name=msg.USER_SERVICE
    )
    
      
    