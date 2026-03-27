from typing import Optional
from uuid import UUID

from logging import getLogger

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
    
    
  async def get_user_from_cache(self, user_id: UUID, user_model: ReadUser) -> Optional[ReadUser]:
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
      
      return user_in_cache
    
    except redis.ConnectionError as e:
      logger.exception(f"Erreur de connexion à redis {e.__class__.__name__}: {e}")     
    
    
  