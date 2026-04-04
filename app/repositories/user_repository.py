## fichier contenant le repository de la table user
## vous y trouverez les requetes base de donnée

from dataclasses import dataclass
import logging
from uuid import UUID

from pydantic import EmailStr

from app.repositories.registration_repository import RegistrationRepository
from app.schemas.registration_schemas import FindRegistration
from app.utils.security_utils import hasher_password
from sqlalchemy import func, insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.registration_jeton import RegistrationJeton
from app.db.models.user import User
from app.schemas.user_schemas import CreateUser, LoginData, UpdateUserData
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
      
      user_registration = await RegistrationRepository(db=self.db).get_registration_by_jeton(
        find_reg_data=user_data.jeton
      )
      
      if user_registration.is_error():
        return CRUDResult.crud_error(
          message=f"{user_registration.error} : Usurpateur de Jeton",
          status_code=user_registration.status_code
        )
      
      # etape 2: on récupère certaines données du jeton pour complèter avant d'inserer
      data_to_insert = user_data.model_dump(exclude={"password", "jeton"})
      data_to_insert["role"] = user_registration.data.role
      data_to_insert["executive_role"] = user_registration.data.executive_role
      data_to_insert["classe_id"] = user_registration.data.classe_id
      data_to_insert["access_jeton_id"] = user_registration.data.id
      data_to_insert["sexe"] = user_registration.data.sexe
      data_to_insert["last_name"] = user_registration.data.last_name.upper()
      data_to_insert["first_name"] = user_registration.data.first_name.title()
      
      stmt2 = (
        insert(User)
        .values(**data_to_insert, password_hash=hasher_password(user_data.password))
        .returning(User)
      )
      
      result_2 = await self.db.execute(stmt2)
      user = result_2.scalars().one()
      
      ## marquer user_registration comme desormais déjà utilisé
      user_registration.data.soft_delete()
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

      if user.deleted_at:
        logger.info(msg.DELETED_USER)
        return CRUDResult.crud_error(msg.USER_NOT_FOUND, status_code=status._403_STATUS_FORBIDEN.value)
      
      
      logger.info(msg.USER_FOUNDED)
      return CRUDResult.crud_success(data=user)
      
    except IntegrityError as ie:
      return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, User)

    except Exception as e:
      return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
    
    
    
  async def get_user_by_jeton_id(self, jeton_id: UUID) -> CRUDResult[User]:
    """function dao pour trouver un utilisateur a partir du id de son jeton

    Args:
        jeton_id (UUID): ID du jeton de l'utilisateur

    Returns:
        CRUDResult[Session]: _description_
    """
    
    try:
      
      stmt = (
        select(User)
        .options(joinedload(User.classe))
        .where(User.access_jeton_id == jeton_id)
      )
      result = await self.db.execute(stmt)
      user = result.scalar_one_or_none()
      
      if user is None:
        logger.info("Utilisateur non Trouvé")
        return CRUDResult.crud_error(msg.USER_NOT_FOUND, status_code=status._404_STATUS_NOT_FOUND.value)

      if user.deleted_at:
        logger.info(msg.DELETED_USER)
        return CRUDResult.crud_error(msg.USER_NOT_FOUND, status_code=status._403_STATUS_FORBIDEN.value)
      
      
      logger.info(msg.USER_FOUNDED)
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
    
    
  async def get_all_users(self) -> CRUDResult[list[User]]:
    """fonction repository pour récupérer tout les utisateur/étudiants

    Returns:
        CRUDResult[list[User]]: retourne une liste de tous les étudiants
    """
    
    stmt= (
      select(User)
      .options(joinedload(User.classe))
    )
    
    result = await self.db.execute(stmt)
    users = list(result.scalars().all())
    
    return CRUDResult.crud_success(data=users)
  
  
  async def update_user(self, user_id: UUID, user_update_data: UpdateUserData) -> CRUDResult[User]:
    """fonction repository pour mettre à jour quelques infos d'un user

    Args:
        user_id (UUID): le ID du user pour le chercher dans la bd
        user_update_data (UpdateUserData): les nouvelles informations

    Returns:
        CRUDResult[User]: retourne le nouveau user mis a jour
    """

    try:
      
      old_user = await self.get_user_by_id(user_id=user_id)

      if old_user.is_error():
        return CRUDResult.crud_error(
          message=old_user.error,
          status_code=old_user.status_code
        )
        
      if user_update_data.username:
        old_user.data.username = user_update_data.username 
      
      if user_update_data.bio:
        old_user.data.bio = user_update_data.bio 
      
      if user_update_data.avatar_url:
        old_user.data.avatar_url = user_update_data.avatar_url 
      
      if user_update_data.sexe:
        old_user.data.sexe = user_update_data.sexe 
        
      await self.db.commit()

      logger.info("Utilisateur mis à jour avec succès")
      return CRUDResult.crud_success(
        data=old_user.data,
        status_code=status._200_STATUS_SUCCESS.value
      )

    except IntegrityError as ie:
      return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, User)

    except Exception as e:
      return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)
