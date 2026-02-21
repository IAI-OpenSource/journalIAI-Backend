## Ce fichier contient les différents schémas concernant les opérations 
# la table session. Inspirez-vous en

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from uuid import UUID

from app.db.models.enums import ClasseType, UserRole


class CreateRegistration(BaseModel):
  """Schémas pydantic pour valider la création d'un obje Registration_jeton

  Args:
      BaseModel (_type_): Hérite de bas model
  """

  jeton: str = Field("Jeton a remettre aux utilisteurs")
  first_name: str = Field("Prenom de l'utilisateur")
  last_name: str = Field("Nom de l'etudiant")
  role: UserRole = Field("rolede l'utilisateur")
  classe: ClasseType = Field("Classe de l'utilisateur")
  
  
class FindRegistration(BaseModel):
    """Schémas pydantic pour valider les données devant permettre de récupérer
        une registration_jeton    

    Args:
        BaseModel (_type_): Hérite de BaseModel
    """
    
    jeton: str
    first_name: str
    last_name: str  
    classe: ClasseType
  
  
class ReadRegistration(BaseModel):
  """Schémas pydantic pour valider la création d'un obje Registration_jeton

  Args:
      BaseModel (_type_): Hérite de bas model
  """
  
  id: UUID = Field("ID de la registration")
  jeton: str = Field("Jeton a remettre aux utilisteurs")
  first_name: str = Field("Prenom de l'utilisateur")
  last_name: str = Field("Nom de l'etudiant")
  role: UserRole = Field("rolede l'utilisateur")
  classe: ClasseType = Field("Classe de l'utilisateur")
  used_at: Optional[datetime]
  added_at: datetime
  
  def is_valide(self) -> bool:
    if self.used_at is None:
        return True 
    return False
  
  class Config:
      from_attributes=True
      
      
ReadRegistration.model_rebuild()