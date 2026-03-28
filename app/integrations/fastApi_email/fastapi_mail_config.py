from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail

from app.core.config import (
  MAIL_FROM, 
  MAIL_FROM_NAME, 
  MAIL_PASSWORD, 
  MAIL_PORT, 
  MAIL_USERNAME, 
  MAIL_SERVER
)

CURRENT_DIR = Path(__file__).resolve().parent
TEMPLATE_FOLDER_NAME = CURRENT_DIR / "templates"

config = ConnectionConfig(
    MAIL_USERNAME = MAIL_USERNAME ,
    MAIL_PASSWORD = MAIL_PASSWORD, 
    MAIL_FROM = MAIL_FROM,
    MAIL_FROM_NAME = MAIL_FROM_NAME,
    MAIL_PORT = MAIL_PORT,
    MAIL_SERVER = MAIL_SERVER,
    MAIL_STARTTLS = False,
    MAIL_SSL_TLS = True,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True,
    TEMPLATE_FOLDER = TEMPLATE_FOLDER_NAME
)


fm = FastMail(config=config)