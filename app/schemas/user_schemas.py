## Ce fichier contient les différents schémas concernant les opérations 
# sur la table utilisateur/user


from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from uuid import UUID

from app.db.models.enums import ExecutiveRoleType, SexeType, UserRole
from app.schemas import ApiBaseResponse
from app.schemas.classe_schemas import ReadUserClasse
from app.schemas.registration_schemas import FindRegistration


class CreateUser(BaseModel):
  """schémas de validation de a création d'un utilisateur (Création de compte)

  Args:
      BaseModel (_type_): Hérite de base model
  """
  
  last_name: str = Field(description="Nom de l'utilisateur")
  first_name: str = Field(description="Prénom de l'utiisateur")
  email: EmailStr
  username: str = Field(description="Nom d'utilisateur")
  password: str
  jeton: FindRegistration
  
  
class LoginData(BaseModel):
    """schéma de validation des données de connexion (login)

    Args:
        BaseModel (_type_): Hérite de BaseModel

    Returns:
        _type_: Retourne rien, sert juste a la validation
    """
    
    email: EmailStr = Field(description="Email de connexion")
    password: str = Field(description="Mot de passe de l'utilisateur")
    
    
    
  
class ReadUser(BaseModel):
    """Schémas de validation des infos 'un utilisateur

    Args:
        BaseModel (_type_): Hérite de base model
    """
    
    id: UUID = Field(description="Identifiant de l'utilisateur")
    email: EmailStr
    username: str
    last_name: str
    first_name: str
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    sexe: SexeType
    classe: Optional[ReadUserClasse] = None
    role: UserRole
    executive_role: Optional[ExecutiveRoleType] = None
    can_post: bool
    access_jeton_id: Optional[UUID] = None
    is_verified: bool
    deleted_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime] = None
    
    def is_deleted(self) -> bool:
        if self.deleted_at is None:
            return False
        return True

    model_config = ConfigDict(from_attributes=True)
        
ReadUser.model_rebuild()


class UserInfos(ApiBaseResponse):
    
    result: Optional[ReadUser] = Field(description="Informations d'un utilisateur")