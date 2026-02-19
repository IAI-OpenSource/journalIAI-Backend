## Ce fichier contient les différents schémas concernant les oérations 
# la table session. Inspirez-vous en

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from uuid import UUID

class CreateSession(BaseModel):
  """schémas pydantic pour les validation des 
    données de création d'une session

  Args:
      BaseModel (_type_): heride de BaseModel
  """
  
  user_id: UUID = Field("Id de l'utilisateur qui se connecte pour une session")
  ref_token: str  = Field("token généré pour valider la session d'un user")
  ip_address: Optional[str] = Field("Addresse IP du user")
  user_agent: Optional[str] = Field("Le navigateur de connexion")
  expires_at: datetime
  created_at: datetime