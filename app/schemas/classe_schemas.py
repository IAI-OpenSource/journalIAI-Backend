## Ce fichier contient les différents schémas concernant les opérations 
# sur la table classes


from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from uuid import UUID

from app.db.models.enums import ClasseType, ExecutiveRoleType, SexeType, UserRole
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

