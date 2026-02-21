import os

from dotenv import load_dotenv

load_dotenv()  ## Permet de charger les configs depuis le fichier .env

# Environnement courant, on doit définir à LOCAL si on est en local et à PRODUCTION si on est sur le serveur
ENVIRONMENT: str= os.getenv("ENVIRONMENT")

# Username de la db
DATABASE_USER: str = os.getenv("DATABASE_USER")

# Driver avec lequel on communique en low-level avec la bd
DATABASE_PILOT: str = os.getenv("DATABASE_PILOT")

# Le type de bd
DATABASE_TYPE: str = os.getenv("DATABASE_TYPE")

# MDP de la db
DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD")

# Lien vers la db, à définir directement avec le port de connexion
DATABASE_HOST: str = os.getenv("DATABASE_HOST")

# Nom de la db
DATABASE_NAME: str = os.getenv("DATABASE_NAME")

# Clé secrete pour hashage et autres
SECRET_KEY: str = os.getenv("SECRET_KEY")
REFRESH_TOKEN_SECRET_KEY: str = os.getenv("REFRESH_TOKEN_SECRET_KEY", "refresh-cles-secrete")

# Algorithme de hashage qu'on va utiliser
ALGORITHM: str = os.getenv("ALGORITHM", "HS256")

# Minutes par défauts après lequel les tokens JWT s'expirent
JWT_EXPIRES_MINUTES: int = int(os.getenv("JWT_EXPIRES_MINUTES"))
REFRESH_TOKEN_EXPIRES_MINUTES: int = int(os.getenv("REFRESH_TOKEN_EXPIRES_MINUTES", 7 * 24 * 60))

## les IDs des cookies
ACCESS_IDENTIFIER: str = "Access-Token"
REFRESH_IDENTIFIER: str = "Refresh-Token"

## url redis
REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")

## Start period pour docker
START_PERIOD: int = os.getenv("START_PERIOD", 10)