

from logging import getLogger
import traceback

from fastapi_mail import FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import NameEmail

from app.schemas.global_schemas import SendOTPEmail, StringMessage
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
