from typing import Optional

from pydantic import BaseModel, Field

from app.schemas import ApiBaseResponse


class StringMessage(BaseModel):
  """Schémas pydantic pour le retour d'un message de type String"""

  message: str = Field(description="Le message de réponse relatif au résultat de l'opération, ce message là sera"
                                   " forcément pour un succès, si c'est echec ca sera dans le champ 'error'")


class GlobalStringMessage(ApiBaseResponse):
  
  """
  Réponse contennant uniquement un message de type string, utiliser pour les endpoints qui ne retournent
  pas de données spécifiques mais juste un message de succès
  """

  result: Optional[StringMessage]

  