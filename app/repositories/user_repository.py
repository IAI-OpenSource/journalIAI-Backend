## fichier contenant le repository de la table user
## vous y trouverez les requetes base de donnée

from dataclasses import dataclass
import logging
from typing import Optional, Union
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.schemas.user_schemas import CreateUser, ReadUser
from . import CRUDResult
from app.globals.messages import Messages as msg
from app.globals.status_codes import StatusCode as status
from .repositories_utils import RepositoriesUtils


logger = logging.getLogger(__name__)


@dataclass
class UserRepository:
  
  db: AsyncSession
  
  async def insert_user(self, user_data: CreateUser) -> CRUDResult[User]:
    """fonction dao pour créer un utilisateur

    Args:
        user_data (CreateSession): on prend les infos de l'utilisateur

    Returns:
        CRUDResult[Session]: Herite de crud result
    """
    
    try:
      
      ## NB TODO: Cette logique n'est pas complète. Je viendrais corrigé ça après un truc"
      stmt = (
        insert(User)
        .values(**user_data.model_dump())
        .returning(User)
      )
      
      result = await self.db.execute(stmt)
      user = result.scalar_one()
      await self.db.commit()

      logger.info("Utilisateur ajoutée avec succès !")
      return CRUDResult.crud_success(user, status._201_STATUS_CREATED.value)
      
    except IntegrityError as ie:
      return RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, User)

    except Exception as e:
      return RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
    
    
  async def get_user_by_sid(self, user_id: UUID) -> CRUDResult[User]:
    """function dao pour trouver un utilisateur a partir de son ID

    Args:
        user_id (UUID): ID de l'utilisateur

    Returns:
        CRUDResult[Session]: _description_
    """
    
    try:
      
      stmt = select(User).where(User.id == user_id)
      result = await self.db.execute(stmt)
      user = result.scalar_one_or_none()
      
      if user is None:
        logger.info("Utilisateur non Trouvé")
        return CRUDResult.crud_error(msg.USER_NOT_FOUND, status_code=status._404_STATUS_NOT_FOUND.value)
      
      logger.info("Session récupérer avec succès !")
      return CRUDResult.crud_success(user, 201)
      
    except IntegrityError as ie:
      return RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, User)

    except Exception as e:
      return RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)