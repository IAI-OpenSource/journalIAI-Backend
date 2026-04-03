from typing import Optional
from uuid import UUID

from logging import getLogger

from pydantic import EmailStr
import redis

from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper

from app.cache.helpers.cache_keys import CacheKey
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.schemas.user_schemas import ReadUser
from app.globals. messages import Messages as msg


logger = getLogger(__name__)


class UserCache:
  
  def __init__(self, cache: CacheWrapper):
    self.user_cache = cache
    self.message: Optional[str] = None
    
  
  def create_user_cache_key(self, id: UUID) -> CacheKey:
    """fonction de dépendance pour créer/formater la clé de cache d'un utilisateur donné.
      Cette clé permettra de mettre en cache la donnée d'un utilisateur spécifique

    Args:
        id (UUID): ID de l'utilisateur concerné

    Returns:
        CacheKey: Retourne une instance de CacheKey
    """
    
    cache_key = CacheKeysFactory.get_cache_key(
      AvailableCacheKeys.SESSION_OBJECT
    ).set_arguments(id=str(id))
    
    return cache_key

  
  def create_user_otp_cache_key(self, email: EmailStr) -> CacheKey:
    """fonction de dépendance pour créer/formater la clé de cache pour le OTP d'un utilisateur donné.
      Cette clé permettra de mettre en cache la donnée(code OTP) d'un utilisateur spécifique

    Args:
        email (EmailStr): email de l'utilisateur concerné

    Returns:
        CacheKey: Retourne une instance de CacheKey
    """
    
    cache_key = CacheKeysFactory.get_cache_key(
      AvailableCacheKeys.USER_OTP
    ).set_arguments(email=str(email))
    
    return cache_key
    
  
  async def set_user_in_cache(self, user_id: UUID, user: ReadUser, ttl: int):
    """fonction permettant de mettre les infos d'un utilisateur en cache. 
      Ici on met tout l'utilisateur conformement a la validation de ReadUser

    Args:
        user_id (UUID): On prend le ID de l'utilisateur pour constituer la clé du cache
        user (ReadUser): la donné (pydantic) à sauvegarder
        ttl (int): la durée en secondes de la donnée dans le cache

    Returns:
       Cette fonction ne retourne rien mais va levé une exceptio en cas d'absence de connexion
       avec le serveur redis
    """
    
    try:
      
      cache_key = self.create_user_cache_key(user_id)
      
      await self.user_cache.save_pydantic_model_in_cache(
        key=cache_key,
        model_instance=user,
        expire_seconds=ttl
      )
            
    except redis.ConnectionError as e:
      logger.exception(f"Erreur de connexion à redis {e.__class__.__name__}: {e}")     
    
    
  async def get_user_from_cache(self, user_id: UUID, user_model: type[ReadUser]) -> Optional[ReadUser]:
    """fonction permettant de récupérer les infos d'un utilisateur du cache. 
      Ici on récupère tout l'utilisateur conformement a la validation de ReadUser

    Args:
        user_id (UUID): On prend le ID de l'utilisateur pour constituer la clé du cache
        user_model (ReadUser): Ici c'est le modèlede validation. Ce qu'on espère récupérer du cache

    Returns:
        Optional[ReadUser]: Retourne un ReadUser ou None si le cache est vide
    """

    try:
      
      cache_key = self.create_user_cache_key(user_id)
      
      user_in_cache = await self.user_cache.get_pydantic_model_from_cache(
        key=cache_key,
        model_class=user_model
      )

      if user_in_cache is None:
        self.message = msg.CACHE_USER_NOT_FOUND
        return None
      
      return ReadUser.model_validate(user_in_cache)
    
    except redis.ConnectionError as e:
      logger.exception(f"Erreur de connexion à redis {e.__class__.__name__}: {e}")
      return None
      
      
  async def set_user_otp_code_in_cache(self, user_mail: EmailStr, otp: str, ttl: int):
    """fonction pour mettre le code OTP généré d'un utilisateur en cache.
    ce cache sera un peu comme notre db

    Args:
        user_mail (EmailStr): le email de l'utilisateur qui va servir à créer le clé du cache
        otp (str): On prend le OTP(la donnée) à mettre en cache
        ttl (int): On prend la durée
    """
    
    try:
      
      cache_key = self.create_user_otp_cache_key(email=user_mail)
      
      await self.user_cache.save_dict_in_cache(
        key=cache_key,
        value={"otp": otp},
        expire_seconds=ttl
      )
            
    except redis.ConnectionError as e:
      logger.exception(f"Erreur de connexion à redis {e.__class__.__name__}: {e}")   
      
      
  async def get_user_otp_in_cache(self, email: EmailStr) -> Optional[dict] :
    """fonction pour récupérer le code otp stocké dans le cache

    Args:
        email (EmailStr): on prend le email pour constituer la clé 

    Returns:
        Optional[str]: retourne None ou le code
    """
    
    try:
      
      cache_key = self.create_user_otp_cache_key(email=email)
      
      cache_data = await self.user_cache.get_dict_from_cache(
        key=cache_key,
      )
      
      return cache_data
            
    except redis.ConnectionError as e:
      logger.exception(f"Erreur de connexion à redis {e.__class__.__name__}: {e}")   
      return None
     
    


