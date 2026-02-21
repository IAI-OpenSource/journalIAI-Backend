from logging import Logger
import traceback

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.globals.messages import Messages
from app.repositories import CRUDResult


class RepositoriesUtils:
    """Classe pour les fonctions utilitaires des repositories, tout ce qui est redondant sera mit ici"""
    @classmethod
    async def traiter_exception_inconnue(cls, exception: Exception, session: AsyncSession, logger: Logger) -> CRUDResult:
        """
        Fait le log de l'exception et rollback la session pour éviter les transactions incomplètes
        Args:
            exception: L'exception à traiter
            session: La session de base de données à rollback en cas d'exception
            logger: Le logger à utiliser pour enregistrer l'exception
        Returns:
            Un objet CrudResult d'erreur
        """
        logger.exception(f"Exception {exception.__class__.__name__} : {exception}", exc_info=exception)
        await session.rollback()
        return CRUDResult.crud_error(message=Messages.INTERNAL_SERVER_ERROR, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @classmethod
    async def traiter_integrity_error(cls, exception: IntegrityError, session: AsyncSession, logger: Logger, model_class) -> CRUDResult:
        """
        Traite une exception d'intégrité en cherchant une conrespondance dans le dictionnaire des contrainte de la classe
        du model `model_class` (ERROR_MESSAGES)
        Args:
            exception: L'exception d'intégrité à traiter
            session: La session de base de données à rollback en cas d'exception
            logger: Le logger à utiliser pour enregistrer l'exception
            model_class: La classe du modèle SQLAlchemy qui a levé l'exception, utilisée pour traduire l'erreur
        Returns:
            Un objet CrudResult avec le message clair si une correspondance est trouvée avec la contrainte, une 500 sinon
        """

        # Recheche de correspondance dans le ERROR_MESSAGE de la classe du model
        user_friendly_message = model_class.translate_integrity_error(exception)

        if user_friendly_message:
            traceback.print_exc()
            return CRUDResult.crud_error(user_friendly_message, status.HTTP_400_BAD_REQUEST)

        # Falllback
        return await RepositoriesUtils.traiter_exception_inconnue(exception, session, logger)

    @classmethod
    async def traiter_errors_en_global(cls, exception: Exception, session: AsyncSession, logger: Logger, model_bd) -> CRUDResult:
        """
        Traite une exception en gérant IntegrityError et Exception en meme temps
        Args:
            exception: L'exception à traiter
            session: La session bd
            logger: Le logger
            model_bd: La classe du modèle SQLAlchemy qui a levé l'exception, utilisée pour traduire l'erreur

        Returns:
            Un objet CrudResult d'erreur
        """

        if isinstance(exception, IntegrityError):
            return await RepositoriesUtils.traiter_integrity_error(exception, session, logger, model_bd)

        return await RepositoriesUtils.traiter_exception_inconnue(exception, session, logger)
