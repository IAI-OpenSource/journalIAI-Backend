## Ce fichier contient les différents schémas concernant les opérations 
# la table session. Inspirez-vous en

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from uuid import UUID

from app.db.models.enums import ClasseType, ExecutiveRoleType, SexeType, UserRole
from app.schemas import ApiBaseResponse
from app.schemas.classe_schemas import ReadUserClasse


class CreateRegistration(BaseModel):
  """Schémas pydantic pour valider la création d'un obje Registration_jeton

  Args:
      BaseModel (_type_): Hérite de bas model
  """

  first_name: str = Field(description="Prenom de l'utilisateur")
  last_name: str = Field(description="Nom de l'etudiant")
  role: UserRole = Field(description="role de l'utilisateur")
  executive_role: Optional[ExecutiveRoleType] = Field(
      default=None,
        description="role exécutif de l'utilisateur. Peut etre None si le user est un STUDENT ou ADMIN"
    )
  sexe: SexeType 
  classe_id: UUID = Field(description="ID de la Classe de l'utilisateur")


class CreateMultileRegistration(BaseModel):
  """Schémas pydantic pour valider la création de plusieurs obje Registration_jeton
    depuis le chargement d'un fichier excel
  Args:
      BaseModel (_type_): Hérite de bas model
  """

  first_name: str 
  last_name: str 
  sexe: SexeType 
  
  
class FindRegistration(BaseModel):
    """Schémas pydantic pour valider les données devant permettre de récupérer
        une registration_jeton    

    Args:
        BaseModel (_type_): Hérite de BaseModel
    """
    
    jeton: str = Field(description="le jeton appartenant a lutilisateur. EX: E45FTR0P")


class JetonUpdateData(BaseModel):
    """schemas de validation pour update le role dans registration jeton

    Args:
        BaseModel (_type_): _description_

    Returns:
        _type_: _description_
    """
    role: Optional[UserRole] = None
    executive_role: Optional[ExecutiveRoleType] = None

  
class ReadRegistration(BaseModel):
  """Schémas pydantic pour valider la création d'un obje Registration_jeton

  Args:
      BaseModel (_type_): Hérite de bas model
  """
  
  id: UUID = Field(description="ID de la registration")
  jeton: str = Field(description="Jeton a remettre aux utilisteurs")
  first_name: str = Field(description="Prenom de l'utilisateur")
  last_name: str = Field(description="Nom de l'etudiant")
  role: UserRole = Field(description="role de l'utilisateur")
  executive_role: Optional[ExecutiveRoleType] = Field(description="role executif de l'utilisateur")
  classe: Optional[ReadUserClasse] = Field(description="Classe de l'utilisateur")
  used_at: Optional[datetime] = None
  added_at: datetime
  
  def is_valide(self) -> bool:
    if self.used_at is None:
        return True 
    return False
  
  class Config:
      from_attributes=True
      
ReadRegistration.model_rebuild()


class RegistrationInfos(ApiBaseResponse):
    """Modele de validations des registrations coté routers"""

    result: Optional[ReadRegistration] = Field(description="Infos d'une registration de jeton")


class ListRegistrationInfos(ApiBaseResponse):
    """Modele de validations des registrations coté routers"""

    result: Optional[list[ReadRegistration]] = Field(description="Infos d'une registration de jeton")