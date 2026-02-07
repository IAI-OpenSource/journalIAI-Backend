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

# Clé API Google AI
GOOGLE_AI_API_KEY: str = os.getenv("GOOGLE_AI_API_KEY")

# Minutes par défauts après lequel les tokens JWT s'expirent
ACCESS_TOKEN_EXPIRES_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRES_MINUTES", 240))
REFRESH_TOKEN_EXPIRES_MINUTES: int = int(os.getenv("REFRESH_TOKEN_EXPIRES_MINUTES", 7 * 24 * 60))

## les IDs des cookies
ACCESS_IDENTIFIER: str = os.getenv("ACCESS_IDENTIFIER", "access_token")
REFRESH_IDENTIFIER: str = os.getenv("REFRESH_IDENTIFIER", "refresh_token")
PROFESSEUR_ACTIVE_ETABLISSEMENT_ID: str = os.getenv("PROFESSEUR_ACTIVE_ETABLISSEMENT_ID", "active_etab_id")

## url redis
REDIS_URL: str = os.getenv("REDIS_URL")