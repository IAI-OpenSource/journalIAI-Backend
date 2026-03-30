## fichier contenant le repository de la table user
## vous y trouverez les requetes base de donnée

from dataclasses import dataclass
import logging
from uuid import UUID

from pydantic import EmailStr

from app.utils.security_utils import hasher_password
from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.registration_jeton import RegistrationJeton
from app.db.models.user import User
from app.schemas.user_schemas import CreateUser, LoginData
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
      
      ## etape 1: on cherche si le jeton est le bon
      stmt1 = (
        select(RegistrationJeton)
        .where(
          RegistrationJeton.jeton == user_data.jeton.jeton,
        )
      )
      
      result = await self.db.execute(stmt1)
      user_registration = result.scalar_one_or_none()
      
      if user_registration is None:
        logger.info("Cet utilisateurs n'existe pas dans la DB de IAI")
        return CRUDResult.crud_error(
          message=f"Usurpateur de Jeton. {msg.USER_NOT_FOUND}",
          status_code=status._404_STATUS_NOT_FOUND.value
        )
      
      # etape 2: on récupère certaines données du jeton pour complèter avant d'inserer
      data_to_insert = user_data.model_dump(exclude={"password", "jeton"})
      data_to_insert["role"] = user_registration.role
      data_to_insert["classe_id"] = user_registration.classe_id
      data_to_insert["access_jeton_id"] = user_registration.id
      data_to_insert["sexe"] = user_registration.sexe
      data_to_insert["last_name"] = user_registration.last_name
      data_to_insert["first_name"] = user_registration.first_name
      
      stmt2 = (
        insert(User)
        .values(**data_to_insert, password_hash=hasher_password(user_data.password))
        .returning(User)
      )
      
      result_2 = await self.db.execute(stmt2)
      user = result_2.scalars().one()
      await self.db.commit()
      await self.db.refresh(user, attribute_names=["classe"])

      logger.info("Utilisateur ajoutée avec succès !")
      return CRUDResult.crud_success(data=user, status_code=status._201_STATUS_CREATED.value)
      
    except IntegrityError as ie:
      return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, User)

    except Exception as e:
      return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
    
    
  async def get_user_by_id(self, user_id: UUID) -> CRUDResult[User]:
    """function dao pour trouver un utilisateur a partir de son ID

    Args:
        user_id (UUID): ID de l'utilisateur

    Returns:
        CRUDResult[Session]: _description_
    """
    
    try:
      
      stmt = (
        select(User)
        .options(joinedload(User.classe))
        .where(User.id == user_id)
      )
      result = await self.db.execute(stmt)
      user = result.scalar_one_or_none()
      
      if user is None:
        logger.info("Utilisateur non Trouvé")
        return CRUDResult.crud_error(msg.USER_NOT_FOUND, status_code=status._404_STATUS_NOT_FOUND.value)
      
      logger.info("Utilisateur récupérer avec succès !")
      return CRUDResult.crud_success(user)
      
    except IntegrityError as ie:
      return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, User)

    except Exception as e:
      return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)


  async def get_user_by_email(self, email: EmailStr) -> CRUDResult[User]:
    """function dao pour trouver un utilisateur a partir de son email

    Args:
        login_data (LoginData): les infos de l'utilisateur

    Returns:
        CRUDResult[Session]: _description_
    """
    
    try:
      
      stmt = (
        select(User)
        .options(joinedload(User.classe))
        .where(User.email == email)
      )
      result = await self.db.execute(stmt)
      user = result.scalar_one_or_none()
      
      if user is None:
        logger.info(msg.LOGIN_NOT_FOUND)
        return CRUDResult.crud_error(msg.LOGIN_NOT_FOUND, status_code=status._404_STATUS_NOT_FOUND.value)
      
      logger.info("Utilisateur récupérer avec succès !")
      return CRUDResult.crud_success(user)
      
    except IntegrityError as ie:
      return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, User)

    except Exception as e:
      return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)