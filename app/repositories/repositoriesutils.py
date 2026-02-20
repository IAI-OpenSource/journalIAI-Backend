from logging import Logger

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


class RepositoriesUtils:
    @staticmethod
    async def traiter_exception(exception: Exception, session: AsyncSession, logger: Logger) -> None:
        """
        Fait le log de l'exception et rollback la session pour éviter les transactions incomplètes
        Args:
            exception: L'exception à traiter
            session: La session de base de données à rollback en cas d'exception
            logger: Le logger à utiliser pour enregistrer l'exception
        Returns:
            Que dalle, c'est une méthode utilitaire pour le logging et le rollback
        """
        logger.exception(f"Exception {exception.__class__.__name__} : {exception}", exc_info=exception)
        await session.rollback()
    @staticmethod
    async def traiter_integrity_error(exception: IntegrityError, session: AsyncSession, logger: Logger, model_class) -> str:
        """
        Traite une exception d'intégrité en effectuant un rollback de la session et en traduisant l'erreur
        Args:
            exception: L'exception d'intégrité à traiter
            session: La session de base de données à rollback en cas d'exception
            logger: Le logger à utiliser pour enregistrer l'exception
            model_class: La classe du modèle SQLAlchemy qui a levé l'exception, utilisée pour traduire l'erreur
        Returns:
            Un message d'erreur clair traduit à partir de l'exception d'intégrité
        """
        await RepositoriesUtils.traiter_exception(exception, session, logger)
        return model_class.translate_integrity_error(exception)



