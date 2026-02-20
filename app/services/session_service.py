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
          status_code=500, 
          service_name="Service: Insertion Session"
        )
      
      return ServiceResult.service_success(session_repo.data)

    except Exception as e:
      logger.exception(f"Exception {e.__class__.__name__}: {e}")
      traceback.print_exc()
      return ServiceResult.service_error(msg.INTERNAL_SERVER_ERROR)
    
    
  async def service_find_session_by_sid(self, sid: UUID) -> ServiceResult[ReadSession, str]:
    """Logique métier de récupération d'un session by SID"""

    try:
      
      session = await self.session_repo.get_session_by_sid(sid)
      
      if session.is_error():
        logger.error(f"Erreur: {session.error}")
        return ServiceResult.service_error(session.error, 500, "Service: Insertion Session")
      
      if not ReadSession.model_validate(session.data).is_valide_session(): ## je convertit Session en SesionRead 
        
        logger.error(f"Erreur: {msg.INVALID_SESSION}")                            # pour accéder a la fonction utilitaire
        sess_deleted = await self.session_repo.delete_session(session.data.id)
        
        if sess_deleted.is_error():
          logger.error(sess_deleted.error)
          return ServiceResult.service_error(
            message=sess_deleted.error, 
            service_name="Service: Suppression Session"
          )
          
        return ServiceResult.service_error(
          message=f"Erreur: {msg.INVALID_SESSION}", 
          status_code=403, 
          service_name="Service: Lecture d'une Session"
        )
        
      
      return ServiceResult.service_success(session.data)

    except Exception as e:
      logger.exception(f"Exception {e.__class__.__name__}: {e}")
      traceback.print_exc()
      return ServiceResult.service_error(msg.INTERNAL_SERVER_ERROR)
    
