import os

from dotenv import load_dotenv
from pydantic import SecretStr

load_dotenv()  ## Permet de charger les configs depuis le fichier .env

# Environnement courant, on doit définir à LOCAL si on est en local et à PRODUCTION si on est sur le serveur
ENVIRONMENT: str = os.getenv("ENVIRONMENT") or ""

# Username de la db
DATABASE_USER: str = os.getenv("DATABASE_USER") or ""

# Driver avec lequel on communique en low-level avec la bd
DATABASE_PILOT: str = os.getenv("DATABASE_PILOT") or ""

# Le type de bd
DATABASE_TYPE: str = os.getenv("DATABASE_TYPE") or ""

# MDP de la db
DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD") or ""

# Lien vers la db, à définir directement avec le port de connexion
DATABASE_HOST: str = os.getenv("DATABASE_HOST") or ""

# Nom de la db
DATABASE_NAME: str = os.getenv("DATABASE_NAME") or ""

# Clé secrete pour hashage et autres
ACCESS_SECRET_KEY: str = os.getenv("SECRET_KEY") or ""
REFRESH_TOKEN_SECRET_KEY: str = os.getenv("REFRESH_TOKEN_SECRET_KEY", "refresh-cles-secrete") or ""

# Algorithme de hashage qu'on va utiliser
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")

# Minutes par défauts après lequel les tokens JWT s'expirent
JWT_EXPIRES_SECONDES: int = int(os.getenv("JWT_EXPIRES_SECONDES", 300))
REFRESH_TOKEN_EXPIRES_SECONDES: int = int(os.getenv("REFRESH_TOKEN_EXPIRES_SECONDES", 7 * 24 * 3600))

## les IDs des cookies
JWT_COOKIE_ACCESS_ID: str = "_SECURE_TOKEN" ## encoder ID de le session
SID_REF_COOKIE: str = "_SID_REFRESH" ## encoder le refresh token

## url redis
REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

MINIO_SERVER_URL = os.getenv("MINIO_SERVER_URL") or ""
MINIO_PUBLIC_URL: str = os.getenv("MINIO_PUBLIC_URL") or ""
MINIO_USER: str = os.getenv("MINIO_ROOT_USER") or ""
MINIO_PASSWORD: str = os.getenv("MINIO_ROOT_PASSWORD") or ""
MINIO_BROWSER_REDIRECT_URL: str = os.getenv("MINIO_BROWSER_REDIRECT_URL") or ""

## Start period pour docker
START_PERIOD: int = int(os.getenv("START_PERIOD", "60"))

## Gestion du mail
MAIL_USERNAME: str = os.getenv("MAIL_USERNAME") or ""
MAIL_PASSWORD: SecretStr = SecretStr(os.getenv("MAIL_PASSWORD", "")) 
MAIL_FROM: str = os.getenv("MAIL_FROM") or  ""
MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME") or ""
MAIL_PORT: int = int(os.getenv("MAIL_PORT", "465"))
MAIL_SERVER: str = os.getenv("MAIL_SERVER") or ""
