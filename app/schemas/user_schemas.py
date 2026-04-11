## Ce fichier contient les différents schémas concernant les opérations 
# sur la table utilisateur/user


from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from uuid import UUID

from app.db.models.enums import ExecutiveRoleType, SexeType, UserRole
from app.schemas import ApiBaseResponse
from app.schemas.classe_schemas import ReadUserClasse
from app.schemas.post_upload_schemas import UploadURLSchema
from app.schemas.registration_schemas import FindRegistration
from app.storage.media_read_storage import MediaReadStorage


class CreateUser(BaseModel):
  """schémas de validation de a création d'un utilisateur (Création de compte)

  Args:
      BaseModel (_type_): Hérite de base model
  """
  
  username: str = Field(description="Nom d'utilisateur")
  password: str = Field(description="Mot de passe de l'utilisateur", min_length=8)
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
    
    
    
class UpdateUserData(BaseModel):
    """schéma de validation des données pour permettre à un utilisateur de mettre à jour 
        ses propres informations. NB: Seul les champs modifiable sont présents

    Args:
        BaseModel (_type_): Hérite de BaseModel

    Returns: 
        _type_: Retourne rien, sert juste a la validation
    """    
    
    username: Optional[str] = None
    bio: Optional[str] = None
    sexe: Optional[SexeType] = None
    

class UpdateAvatarUrl(BaseModel):
    """validation de l'avatar url d'un utilisateur"""

    avatar_url: Optional[str] = None

 
class UploadAvatarFile(BaseModel):
    """validation du nom de fichier pour l'avatar url d'un utilisateur"""

    file_name: str = Field(description="Nom du fichier de l'avatar que l'utilisateur veux uploader.")

 
class ConfirmUploadAvatarFile(BaseModel):
    """validation du nom de fichier pour l'avatar url d'un utilisateur"""

    file_name: str = Field(description="Nom du fichier de l'avatar que l'utilisateur veux uploader.")
    indent_id: str = Field(description="le indent id que vous avez récupérez dans la route de création de l'url paginée")
 
  
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
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    
    
    @model_validator(mode="after")
    def format_avatar_url(self) -> 'ReadUser':
        """
        Décorateur pour transformer le chemin relatif de la BD en URL complète pour le Front.
        """
        if self.avatar_url:
            self.avatar_url = MediaReadStorage.generate_avatar_url(self.avatar_url)
        return self
    
    def is_deleted(self) -> bool:
        if self.deleted_at is None:
            return False
        return True

    model_config = ConfigDict(from_attributes=True)
        
ReadUser.model_rebuild()



class UserInfos(ApiBaseResponse):
    
    result: Optional[ReadUser] = Field(description="Informations d'un utilisateur")

class ListUserInfos(ApiBaseResponse):
    
    result: Optional[list[ReadUser]] = Field(description="Informations d'un utilisateur")


class UserAvatarInfos(ApiBaseResponse):
    
    result: Optional[UploadURLSchema] = Field(description="Informations de l'avatar d'un utilisateur")