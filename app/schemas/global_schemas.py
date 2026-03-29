from typing import Optional

from pydantic import BaseModel, EmailStr, Field

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


class SendOTPEmail(BaseModel):
  """schéma de validation de l'envoi du OTP a un utilisateur

  Args:
      BaseModel (_type_): _description_
  """
  
  email_to: EmailStr = Field(description="Le email du destinataire/l'étudiant")
  otp: str = Field(description="Le code OTP généré pour l'utilisateur")
  last_name: str
  first_name: str
  
class VerifyOTPData(BaseModel):
  """schémas de validation des données pour le OTP, vaidatio du OTP que 
      l'utilisateur va soumettre
  Args:
      BaseModel (_type_): _description_
  """

  sender_email: EmailStr = Field(description="Email de l'utilisateur qui envoi le OTP donc technique c'est celui qui essaye de se connecter")
  otp: int = Field(description="le OTP saisie")