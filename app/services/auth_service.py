
## fichier contenant le service/logique métier de la table 
## vous y trouverez les appels fonctions de repository
import logging
import random
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.integrations.fastApi_email.email_manager import EmailServiceManager
from app.schemas.global_schemas import SendOTPEmail, StringMessage
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
  
  def __init__(self, db: AsyncSession, cache: CacheWrapper):
    self.db = db
    self.user_cache = UserCache(cache)
    self.user_repo = UserRepository(self.db)
    self.email_manager = EmailServiceManager(fast_mail=fm)
      
      
  async def service_find_user_by_email(self, login_data: LoginData) -> ServiceResult[StringMessage]:
    """Logique métier pour récupérer un utilisateur à partir de 
      son email: Beaucoup plus spécial pour la connexion"""

    db_user = await self.user_repo.get_user_by_email(login_data=login_data)
    
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
      
    