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
from sqlalchemy.orm import joinedload

from app.db.models.registration_jeton import RegistrationJeton
from app.globals.status_codes import StatusCode
from app.repositories.repositories_utils import RepositoriesUtils
from app.schemas.registration_schemas import CreateRegistration, FindRegistration
from . import CRUDResult
from app.globals.messages import Messages as msg
from app.utils.jetons_utils import JetonUtils


logger = logging.getLogger(__name__)


@dataclass
class RegistrationRepository:
  
  db: AsyncSession
  
  
  async def multiple_registration(self, users: list[dict]) -> CRUDResult[str]:
    """function repository pour inserer plusieurs etudiants dans 
      la table de registration token

    Args:
        users (list[dict]): on prends la liste des etudiants lu depuis 
        le fichier excel

    Returns:
        CRUDResult[str]: on return un simple message de succés
    """

    try:
      
      stmt = (
        insert(RegistrationJeton).values(users)
      )
      
      await self.db.execute(stmt)
      await self.db.commit()

      logger.info("Plusieurs jetons ajoutée avec succès !")
      return CRUDResult.crud_success("Plusieurs jetons ajoutée avec succès !", StatusCode._201_STATUS_CREATED.value)
      
    except IntegrityError as ie:
      return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, RegistrationJeton)

    except Exception as e:
      return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)



  async def insert_registration(self, reg_data: CreateRegistration) -> CRUDResult[RegistrationJeton]:
    """fonction base de donnée pour ajouter un enregistrement de jeton avec
      l'utilisateur concerné

    Args:
        reg_data (CreateRegistration): on prend en paramètre la donnée de la registration

    Returns:
        CRUDResult[RegistrationJeton]: return une instance de CRUDResult
    """
    
    try:
      
      ## génération du jeton
      jeton = JetonUtils.generate_code_jeton(8)
      
      stmt = (
        insert(RegistrationJeton)
        .values(
          jeton=jeton,
          first_name=reg_data.first_name,
          last_name=reg_data.last_name,
          role=reg_data.role,
          sexe=reg_data.sexe,
          classe_id=reg_data.classe_id
        )
        .returning(RegistrationJeton)
      )
      
      result = await self.db.execute(stmt)
      db_reg = result.scalar_one()
      await self.db.commit()

      logger.info("Jeton ajoutée avec succès !")
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
        .options(joinedload(RegistrationJeton.classe))
        .where(
          RegistrationJeton.jeton == find_reg_data.jeton,
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


    
    
  