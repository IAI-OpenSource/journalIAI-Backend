## fichier contenant le service/logique métier de la table session
## vous y trouverez les appels fonctions de repository


from dataclasses import dataclass
import logging
import traceback
from typing import Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.session_repository import SessionRepository
from app.schemas.session_schemas import CreateSession, ReadSession
from app.globals.messages import Messages as msg

from . import ServiceResult


logger = logging.getLogger(__name__)


class SessionService: 
  
  def __init__(self, db: AsyncSession):
    self.db = db
    self.session_repo = SessionRepository(self.db)
  
  
  async def service_create_session(
    self, 
    session_data: CreateSession
  ) -> ServiceResult[Union[ReadSession, str]]:
    """Logique Métier concernant l'insertion d'une session en BD"""
    
    try:
      
      session_repo = await self.session_repo.insert_session(session_data=session_data)
      
      if session_repo.is_error():
        logger.error(f"Erreur: {session_repo.error}")
        return ServiceResult.service_error(
          message=session_repo.error, 
          status_code=session_repo.status_code, 
          service_name=msg.INSERT_SESSSION
        )
      
      return ServiceResult.service_success(session_repo.data, status_code=session_repo.status_code)

    except Exception as e:
      logger.exception(f"Exception {e.__class__.__name__}: {e}")
      traceback.print_exc()
      return ServiceResult.service_error(msg.INTERNAL_SERVER_ERROR, status_code=500)
    
    
  async def service_find_session_by_sid(self, sid: UUID) -> ServiceResult[ReadSession, str]:
    """Logique métier de récupération d'un session by SID"""

    try:
      
      session = await self.session_repo.get_session_by_sid(sid)
      
      if session.is_error():
        logger.error(f"Erreur: {session.error}")
        return ServiceResult.service_error(message=session.error, status_code=session.status_code, service_name=msg.INSERT_SESSSION)
      
      if not ReadSession.model_validate(session.data).is_valide_session(): ## je convertit Session en SesionRead 
        
        logger.error(f"Erreur: {msg.INVALID_SESSION}")                            # pour accéder a la fonction utilitaire
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
        
      
      return ServiceResult.service_success(session.data)

    except Exception as e:
      logger.exception(f"Exception {e.__class__.__name__}: {e}")
      traceback.print_exc()
      return ServiceResult.service_error(msg.INTERNAL_SERVER_ERROR)
    
