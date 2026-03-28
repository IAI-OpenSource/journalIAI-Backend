from fastapi_mail import ConnectionConfig, FastMail

from app.core.config import (
  MAIL_FROM, 
  MAIL_FROM_NAME, 
  MAIL_PASSWORD, 
  MAIL_PORT, 
  MAIL_USERNAME, 
  MAIL_SERVER
)


config = ConnectionConfig(
    MAIL_USERNAME = MAIL_USERNAME ,
    MAIL_PASSWORD = MAIL_PASSWORD, 
    MAIL_FROM = MAIL_FROM,
    MAIL_FROM_NAME = MAIL_FROM_NAME,
    MAIL_PORT = MAIL_PORT,
    MAIL_SERVER = MAIL_SERVER,
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)


fm = FastMail(config=config)