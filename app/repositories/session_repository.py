## fichier contenant le repository de la table session
## vous y trouverez les requetes base de donnée

from dataclasses import dataclass
import logging
from typing import Optional, Union
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.session import Session
from app.schemas.session_schemas import CreateSession
from . import CRUDResult
from app.globals.messages import Messages as msg
from .repositories_utils import RepositoriesUtils


logger = logging.getLogger(__name__)


@dataclass
class SessionRepository:
  
  db: AsyncSession
  
  async def insert_session(self, session_data: CreateSession) -> CRUDResult[Session]:
    """fonction dao pour créer un e session

    Args:
        session_data (CreateSession): on prend les infos de la session

    Returns:
        CRUDResult[Session]: _description_
    """
    
    try:
      
      stmt = (
        insert(Session)
        .values(**session_data.model_dump())
        .returning(Session)
      )
      
      result = await self.db.execute(stmt)
      db_session = result.scalar_one()
      await self.db.commit()

      logger.info("Session ajoutée avec succès !")
      return CRUDResult.crud_success(db_session, 201)
      
    except IntegrityError as ie:
      traceback.print_exc()
      return RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Session)

    except Exception as e:
      traceback.print_exc()
      return RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
    
    
  async def get_session_by_sid(self, sid: UUID) -> CRUDResult[Session]:
    """function dao pour trouver une session a partir de son ID

    Args:
        sid (UUID): ID de la session

    Returns:
        CRUDResult[Session]: _description_
    """
    
    try:
      
      stmt = select(Session).where(Session.id == sid)
      result = await self.db.execute(stmt)
      session = result.scalar_one_or_none()
      
      if session is None:
        logger.info("Session non Trouvé")
        return CRUDResult.crud_error(msg.NOT_FOUND, status_code=status._404_STATUS_NOT_FOUND.value)
      
      logger.info("Session récupérer avec succès !")
      return CRUDResult.crud_success(session)
      
    except IntegrityError as ie:
      return RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Session)

    except Exception as e:
      traceback.print_exc()
      return RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
    
    
  async def delete_session(self, sid: UUID) -> CRUDResult[str]:
    """function dao pour supprimer une session si elle est 
      invalide ou révoquée

    Args:
        sid (UUID): ID de la session

    Returns:
        CRUDResult[str]: _description_
    """
    
    session = await self.get_session_by_sid(sid)
    
    if session.is_error():
      return CRUDResult.crud_error(session.error, status_code=session.status_code)
    
    await self.db.delete(session.data)
    await self.db.commit()
    
    
    return CRUDResult.crud_success("Session supprimée avec succès", 204)
      
    

    
    