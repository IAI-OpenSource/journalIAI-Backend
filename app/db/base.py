from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import (
    DATABASE_HOST,
    DATABASE_USER,
    DATABASE_NAME,
    DATABASE_PILOT,
    DATABASE_TYPE,
    DATABASE_PASSWORD,
    ENVIRONMENT
)

other_args = ""
if ENVIRONMENT == "PRODUCTION":
    # Ce bloc est à garder en tête pour la production, mais pour l'instant, on n'en a pas besoin
    # Utile quand on sera en production pour activer le ssl et d'autres options de connexion
    # Pour l'instant, on n'en a pas besoin, mais c'est à garder en tête
    other_args = ""


# URL de la BD
DATABASE_URL = f"{DATABASE_TYPE}+{DATABASE_PILOT}://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}/{DATABASE_NAME}{other_args}"

# Configuration de l'engine
# future=True, permet de refuser directment l'utilisation des methodes deprecatedd
engine = create_async_engine(DATABASE_URL, echo=True, future=True,
                             connect_args={"statement_cache_size": 0})

# Creation de  Base: classe qui va servir a creer les model sqlalchemy et les tables
Base = declarative_base()




