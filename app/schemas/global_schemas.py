
from pydantic import BaseModel

from app.schemas import ApiBaseResponse


class StringMessage(BaseModel):
  """Schémas pydantic pour valider le retour d'un message String
  Args:
      BaseModel (_type_): Hérite de bas model
  """
  
  message: str


class GlobalStringMessage(ApiBaseResponse):
  
  """Schémas pydantic pour valider le retour d'un message String
  NB: Utiliser pour tout les message simple"""

  result: StringMessage

  