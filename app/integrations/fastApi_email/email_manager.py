

from logging import getLogger
import traceback

from fastapi_mail import FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import NameEmail

from app.schemas.global_schemas import SendOTPEmail, StringMessage
from app.schemas.registration_schemas import ReadRegistration
from app.services import ServiceResult
from app.globals.messages import Messages as msg
from app.globals.status_codes import StatusCode


logging = getLogger(__name__)


class EmailServiceManager:
  """classe pour gérer l'envoi des emails. Pour le moment juste pour le OTP
  """
  
  _fastapi_mail: FastMail

  def __init__(self, fast_mail: FastMail):
    self._fastapi_mail = fast_mail
    
    
  async def send_otp_email(self, data_email_to: SendOTPEmail) -> ServiceResult[StringMessage] :
    """fonction pour envoyer le OTP à l'étudiant

    Args:
        data_email_to (SendOTPEmail): on prend les données nécéssaire à l'envoi du mail

    Returns:
        ServiceResult[StringMessage]: retourne un StringMessage
    """
    
    try:
      
      fast_mail_message_type = MessageSchema(
        subject="Code de vérification venant de Journal IAI suport", 
        recipients=[NameEmail(
          name=f"{data_email_to.last_name} {data_email_to.first_name}", 
          email=data_email_to.email_to)
        ],
        template_body={
          "otp_code": data_email_to.otp,
          "last_name": data_email_to.last_name,
          "first_name": data_email_to.first_name,
        },
        subtype=MessageType.html
      )
      
      await self._fastapi_mail.send_message(message=fast_mail_message_type, template_name="otp_email.html")

      return ServiceResult.service_success(
        data=StringMessage(message=f"Email envoyé avec succès à {data_email_to.email_to}"),
        status_code=StatusCode._200_STATUS_SUCCESS,
        service_name=msg.MAIL_SERVICE
      )
     
    except ConnectionErrors as ce:
      logging.error(f"Erreur {ce.__class__.__name__}: {ce}")
      traceback.print_exc()
      return ServiceResult.service_error(
        message=msg.MAIL_ERROR,
        status_code=StatusCode._421_STATUS_UNAVAILABLE,
        service_name=msg.MAIL_SERVICE
      )



async def send_jetons_email(self, url_inscription: str, all_receivers: list[ReadRegistration]) -> ServiceResult[StringMessage] :
    """fonction pour envoyer le Jton à l'étudiant

    Args:
        all_receivers (list[ReadRegistration]): on prend les données nécéssaire à l'envoi du mail
        url_inscription: (str): URL pour rédiriger l'étudiant vers la page de création de compte

    Returns:
        ServiceResult[StringMessage]: retourne un StringMessage
    """
    
    try:
      
      fast_mail_message_type = MessageSchema(
        subject="Jeton de créatin de compte venant de Journal IAI suport", 
        recipients=[NameEmail(
          name=f"{receiver.last_name} {receiver.first_name}", 
          ) for receiver in all_receivers
        ],
        template_body=[{
          "classe_prefix": receiver.classe.classe_prefix if receiver.classe.classe_prefix else None,
          "classe_prefix": receiver.classe.classe_suffix if receiver.classe.classe_suffix else None,
          "jeton": receiver.jeton,
          "url_inscription": url_inscription,
          "last_name": receiver.last_name,
          "first_name": receiver.first_name,
        } for receiver in all_receivers],
        subtype=MessageType.html
      )
      
      await self._fastapi_mail.send_message(message=fast_mail_message_type, template_name="jetons_email.html")

      return ServiceResult.service_success(
        data=StringMessage(message="Plusieurs Email pour jetons envoyé avec succès !"),
        status_code=StatusCode._200_STATUS_SUCCESS,
        service_name=msg.MAIL_SERVICE
      )
     
    except ConnectionErrors as ce:
      logging.error(f"Erreur {ce.__class__.__name__}: {ce}")
      traceback.print_exc()
      return ServiceResult.service_error(
        message=msg.MAIL_ERROR,
        status_code=StatusCode._421_STATUS_UNAVAILABLE,
        service_name=msg.MAIL_SERVICE
      )