## fichier contenant le service/logique métier de la table session
## vous y trouverez les appels fonctions de repository


from dataclasses import dataclass
import logging
import traceback
from typing import Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.base import CacheWrapper
from app.cache.session_cache import SessionCache
from app.globals.cache_duration import CacheDurartion
from app.globals.status_codes import StatusCode
from app.repositories.session_repository import SessionRepository
from app.schemas.session_schemas import CreateSession, ReadSession
from app.globals.messages import Messages as msg

from . import ServiceResult


logger = logging.getLogger(__name__)


class SessionService: 
  
  def __init__(self, db: AsyncSession, cache: CacheWrapper):
    self.db = db
    self.session_cache = SessionCache(cache)
    self.session_repo = SessionRepository(self.db)
  
  
  async def service_create_session(
    self, 
    session_data: CreateSession
  ) -> ServiceResult[ReadSession]:
    """Logique Métier concernant l'insertion d'une session en BD"""  
      
    session_repo = await self.session_repo.insert_session(session_data=session_data)
      
    if session_repo.is_error():
      logger.error(f"Erreur: {session_repo.error}")
      return ServiceResult.service_error(
        message=session_repo.error, 
        status_code=session_repo.status_code, 
        service_name=msg.INSERT_SESSSION
      )
      
    return ServiceResult.service_success(session_repo.data, status_code=session_repo.status_code)

    
  async def service_find_session_by_sid(self, sid: UUID) -> ServiceResult[ReadSession]:
    """Logique métier de récupération d'une session by SID"""
    
    ## On cherhe d'abord la donnée dans le cache
    session_cache_data = self.session_cache.get_session_from_cache(session_id=sid, session_model=ReadSession)

    if session_cache_data is not None:
      return ServiceResult.service_success(data=session_cache_data, status_code=StatusCode._200_STATUS_SUCCESS.value)

    ## si le cache est vide on passe a la requete BD
    session = await self.session_repo.get_session_by_sid(sid)
    
    if session.is_error():
      logger.error(f"Erreur: {session.error}")
      return ServiceResult.service_error(message=session.error, status_code=session.status_code, service_name=msg.INSERT_SESSSION)

    session_read = ReadSession.model_validate(session.data) ## je convertit Session en SesionRead 
                                                            # pour accéder a la fonction utilitaire
                                                            
    if not session_read.is_valide_session(): 
      
      logger.error(f"Erreur: {msg.INVALID_SESSION}")                            
      sess_deleted = await self.session_repo.delete_session(session.data.id)
      
      if sess_deleted.is_error():
        logger.error(sess_deleted.error)
        return ServiceResult.service_error(
          message=sess_deleted.error, 
          status_code=sess_deleted.status_code,
          service_name=msg.DELETE_SESSION
        )
        
      return ServiceResult.service_error(
        message=f"Erreur: {msg.INVALID_SESSION}", 
        status_code=403, 
        service_name=msg.READ_SESSION
      )
    
    await self.session_cache.set_session_in_cache(
      session_id=session_read.id, 
      session=session_read,
      ttl=CacheDurartion.SESSION_DURATION.value
    )  
    
    return ServiceResult.service_success(session.data)


    
