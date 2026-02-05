import logging
from logging.handlers import RotatingFileHandler
import os
from fast_api_app.core.config import ENVIRONMENT

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "app.log")
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return
    
    formatter = logging.Formatter(LOG_FORMAT)
    
    # 1. Gestion de la CONSOLE (Toujours active pour Uvicorn)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Gestion du FICHIER (Uniquement en développement)
    if ENVIRONMENT == "LOCAL":
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=5_000_000,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler) # On l'ajoute SEULEMENT ici

def silencer_loggers_externes():
    # Liste des loggers à mettre en mode "silence" (seulement les erreurs)
    loggers_a_taire = [
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "asyncpg",
        "apscheduler.scheduler",  # Pour les messages "Scheduler started"
        "apscheduler.executors.default", # Pour éviter les logs à chaque job fini
    ]
    
    for name in loggers_a_taire:
        l = logging.getLogger(name)
        l.setLevel(logging.WARNING) # N'affichera que si ça plante
        l.propagate = False 

    # On garde Uvicorn en INFO pour voir passer les requêtes dans la console
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)