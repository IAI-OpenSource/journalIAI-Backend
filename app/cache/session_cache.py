
from typing import Optional
from uuid import UUID

from logging import getLogger

import redis

from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.keys_factory import CacheKeysFactory

from app.cache.helpers.cache_keys import CacheKey
from app.schemas.session_schemas import ReadSession
from app.globals. messages import Messages as msg


logger = getLogger(__name__)


class SessionCache:
  
  def __init__(self, cache: CacheWrapper):
    self.session_cache = cache
    self.message: Optional[str] = None
    
  
  def create_session_cache_key(self, id: UUID) -> CacheKey:
    """fonction de dépendance pour créer/formater la clé de cache d'une session donnée.
      Cette clé permettra de mettre en cache la donnée d'une session spécifique

    Args:
        id (UUID): ID de la session concernée

    Returns:
        CacheKey: Retourne une instance de CacheKey
    """
    
    cache_key = CacheKeysFactory.get_cache_key(
      AvailableCacheKeys.SESSION_OBJECT
    ).set_arguments(id=str(id))
    
    return cache_key
    
  
  async def set_session_in_cache(self, session_id: UUID, session: ReadSession, ttl: int):
    """fonction permettant de mettre les infos d'une session en cache. 
      Ici on met toute la session conformement a la validation de ReadSession

    Args:
        session_id (UUID): On prend le ID de la session pour constituer la clé du cache
        session (ReadSession): la donné (pydantic) à sauvegarder
        ttl (int): la durée en secondes de la donnée dans le cache

    Returns:
       Cette fonction ne retourne rien mais va levé une exception en cas d'absence de connexion
       avec le serveur redis
    """
    
    try:
      
      cache_key = self.create_session_cache_key(session_id)
      
      await self.session_cache.save_pydantic_model_in_cache(
        key=cache_key,
        model_instance=session,
        expire_seconds=ttl
      )
            
    except redis.ConnectionError as e:
      logger.exception(f"Erreur de connexion à redis {e.__class__.__name__}: {e}")     
    
    
  async def get_session_from_cache(self, session_id: UUID, session_model: ReadSession) -> Optional[ReadSession]:
    """fonction permettant de récupérer les infos d'une session du cache. 
      Ici on récupère toute la session conformement a la validation de ReadSession

    Args:
        session_id (UUID): On prend le ID de la session pour constituer la clé du cache
        session_model (ReadSession): Ici c'est le modèle de validation. Ce qu'on espère récupérer du cache

    Returns:
        Optional[ReadSession]: Retourne un ReadSession ou None si le cache est vide
    """

    try:
      
      cache_key = self.create_session_cache_key(session_id)
      
      session_in_cache = await self.session_cache.get_pydantic_model_from_cache(
        key=cache_key,
        model_class=session_model
      )

      if session_in_cache is None:
        self.message = msg.CACHE_SESSION_NOT_FOUND
      
      return session_in_cache
    
    except redis.ConnectionError as e:
      logger.exception(f"Erreur de connexion à redis {e.__class__.__name__}: {e}")     
    
    
  