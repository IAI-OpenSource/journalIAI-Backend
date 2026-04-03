## Ce fichier contient les différents schémas concernant les opérations 
# sur la table classes


from datetime import datetime
from typing import Optional

from pydantic import BaseModel,Field

from uuid import UUID

from app.db.models.enums import ClasseType
from app.schemas import ApiBaseResponse


class ReadUserClasse(BaseModel):
  """modeles permettant de lires la classe d'une etudiant donné, 
    par exemple quand on récupère les infos de l'étudiant.

  Args:
      BaseModel (_type_): Hérite de base model
  """
  
  id: UUID 
  classe_prefix: ClasseType 
  classe_suffix: str 
  
  class Config:
    from_attributes=True


class ClasseCreateRequest(BaseModel):
  """ Schemas pydantic pour la création d'une classe

  attributes:
    classe_prefix: Le préfixe de la classe (ex: "TC1", "TC2", etc.)
    classe_suffix: Le suffixe de la classe (ex: "A", "B", etc.)
  """

  classe_prefix: ClasseType = Field(..., description="Le préfixe de la classe (ex: 'TC1', 'TC2', etc.)")
  classe_suffix: str = Field(...,max_length=1, description="Le suffixe de la classe (ex: 'A', 'B', etc.)")



class ClasseUpdateRequest(BaseModel):
  """ Schemas pydantic pour la mise à jour d'une classe

  attributes:
    classe_prefix: Le préfixe de la classe (ex: "TC1", "TC2", etc.)
    classe_suffix: Le suffixe de la classe (ex: "A", "B", etc.)
  """

  classe_prefix: Optional[ClasseType] = Field(None, description="Le préfixe de la classe (ex: 'TC1', 'TC2', etc.)")
  classe_suffix: Optional[str] = Field(None, max_length=1, description="Le suffixe de la classe (ex: 'A', 'B', etc.)")


class ClasseResponse(BaseModel):
  """ Schemas pydantic pour la réponse d'une classe

  attributes:
    id: L'identifiant de la classe
    classe_prefix: Le préfixe de la classe (ex: "TC1", "TC2", etc.)
    classe_suffix: Le suffixe de la classe (ex: "A", "B", etc.)
    effectif: L'effectif de la classe
    academic_year_id: L'identifiant de l'année académique à laquelle appartient la classe
    created_at: La date de création de la classe
    updated_at: La date de mise à jour de la classe
  """

  model_config = {"from_attributes": True}
  id: UUID 
  classe_prefix: ClasseType 
  classe_suffix: str 
  effectif: int 
  academic_year_id: UUID 
  created_at: datetime 
  updated_at: datetime

class ClasseListResponse(BaseModel):
  """ Schemas pydantic pour la réponse d'une liste de classes

    attributes:
      classes: La liste des classes
  """

  classes: list[ClasseResponse]
  total: int
  page : int
  page_size : int

class ClasseApiResponse(ApiBaseResponse[ClasseResponse]):
  """ Schemas pydantic pour la réponse d'une classe dans une API, hérite de ApiBaseResponse avec un result de type ClasseResponse"""

  pass

class ClassesListApiResponse(ApiBaseResponse[ClasseListResponse]):
  """ Schemas pydantic pour la réponse d'une liste de classes dans une API, hérite de ApiBaseResponse avec un result de type ClasseListResponse"""

  pass