from typing import Optional

from pydantic import BaseModel

from app.schemas import ApiBaseResponse


class StringMessage(BaseModel):
  """Schémas pydantic pour valider le retour d'un message String"""
  
  message: str


class GlobalStringMessage(ApiBaseResponse):
  
  """Réponse contennant uniquement un message de type string, utiliser pour les endpoints qui ne retournent pas de données spécifiques mais juste un message de succès"""

  result: Optional[StringMessage]

  