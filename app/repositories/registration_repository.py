## fichier contenant le repository de la table registration_jeton
## vous y trouverez les requetes base de donnée

from dataclasses import dataclass
from datetime import datetime
import logging
import traceback
from typing import Optional, Union
from uuid import UUID

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.registration_jeton import RegistrationJeton
from app.globals.status_codes import StatusCode
from app.repositories.repositories_utils import RepositoriesUtils
from app.schemas.registration_schemas import CreateRegistration, FindRegistration
from . import CRUDResult
from app.globals.messages import Messages as msg


logger = logging.getLogger(__name__)


@dataclass
class RegistrationRepository:
  
  db: AsyncSession


  async def insert_registration(self, reg_data: CreateRegistration) -> CRUDResult[RegistrationJeton]:
    """fonction base de donnée pour ajouter un enregistrement de jeton avec
      l'utilisateur concerné

    Args:
        reg_data (CreateRegistration): on prend en paramètre la donnée de la registration

    Returns:
        CRUDResult[RegistrationJeton]: return une instance de CRUDResult
    """
    
    try:
      
      stmt = (
        insert(RegistrationJeton)
        .values(**reg_data.model_dump())
        .returning(RegistrationJeton)
      )
      
      result = await self.db.execute(stmt)
      db_reg = result.scalar_one()
      await self.db.commit()

      logger.info("Session ajoutée avec succès !")
      return CRUDResult.crud_success(db_reg, StatusCode._201_STATUS_CREATED.value)
      
    except IntegrityError as ie:
      return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, RegistrationJeton)

    except Exception as e:
      return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
    
    
  async def get_registration_by_jeton(self, find_reg_data: FindRegistration) -> CRUDResult[RegistrationJeton]:
    """function dao pour trouver une session a partir de son ID

    Args:
        sid (UUID): ID de la session

    Returns:
        CRUDResult[Session, str]: _description_
    """
    
    try:
      
      stmt = (
        select(RegistrationJeton)
        .where(
          RegistrationJeton.jeton == find_reg_data.jeton,
          RegistrationJeton.first_name == find_reg_data.first_name,
          RegistrationJeton.last_name == find_reg_data.last_name,
          RegistrationJeton.classe == find_reg_data.classe
        )
      )
      result = await self.db.execute(stmt)
      registration = result.scalar_one_or_none()
      
      if registration is None:
        logger.info("Registration non Trouvé")
        return CRUDResult.crud_error(msg.NOT_FOUND, status_code=StatusCode._404_STATUS_NOT_FOUND)
      
      logger.info("Registration récupérer avec succès !")
      return CRUDResult.crud_success(registration)
      
    except IntegrityError as ie:
      return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, RegistrationJeton)

    except Exception as e:
      return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
    
    
  async def delete_registration(self, to_delete_data: FindRegistration) -> CRUDResult[str]:
    """function pour delete une registration: Cependant , on ne vas pas supprimer 
    de la bd mais on va marquer son attribut used_at

    Args:
        to_delete_data (FindRegistration): prend le schéma de la donnée a supprimer

    Returns:
        CRUDResult[str]: retourne instance de CRUDResult
    """
    
    registration = await self.get_registration_by_jeton(find_reg_data=to_delete_data)
    
    if registration.is_error():
      return CRUDResult.crud_error(registration.error, registration.status_code)
    
    registration.data.used_at = datetime.now()
    await self.db.commit()

    return CRUDResult.crud_success("Registration révoquée avec succès", StatusCode._204_STATUS_NO_CONTENT)


    
    
  