## Ce fichier contient les différents schémas concernant les opérations 
# la table session. Inspirez-vous en

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field

from uuid import UUID

class CreateSession(BaseModel):
  """schémas pydantic pour les validation des 
    données de création d'une session

  Args:
      BaseModel (_type_): heride de BaseModel
  """
  
  user_id: UUID = Field(description="Id de l'utilisateur qui se connecte pour une session")
  ref_token: str  = Field(description="token généré pour valider la session d'un user")
  ip_address: Optional[str] = Field(description="Addresse IP du user")
  user_agent: Optional[str] = Field(description="Le navigateur de connexion")
  expires_at: datetime
  
  
class ReadSession(BaseModel):
  """schémas pour la validation des données de lecture d'une session

  Args:
      BaseModel (_type_): Héride de base model
  """
  
  id: UUID  = Field(description="ID de la session")
  user_id: UUID = Field(description="Id de l'utilisateur qui se connecte pour une session")
  refresh_token_hash: str  = Field(description="token généré pour valider la session d'un user")
  ip_address: Optional[str] = Field(description="Addresse IP du user")
  user_agent: Optional[str] = Field(description="Le navigateur de connexion")
  expires_at: datetime
  created_at: datetime
  
  def is_valide_session(self) -> bool:
    """fonction pour vérifier si une session est valid

        Return True si valide sinon False
    """
    
    # On force maintenant en UTC pour avoir un meme fuseau horaire 
    now_utc = datetime.now(timezone.utc)
    
    expires = self.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
        
    created = self.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)

    return expires > created and now_utc < expires 
  
  class Config:
    from_attributes = True
    
ReadSession.model_rebuild()