from sqlalchemy.exc import IntegrityError
from typing import Optional

from logging import getLogger

logger = getLogger(__name__)

class IntegrityMapperMixin:
    """Mixin pour traduire les erreurs d'intégrité PostgreSQL en messages clairs."""

    # On va faire des surcharge dans les modèle enfant pour associer les noms de contraintes à des messages d
    # 'erreur clairs
    ERROR_MESSAGES: dict[str, str] = {}

    @classmethod
    def translate_integrity_error(cls, exception: IntegrityError) -> Optional[str]:
        """
        Extrait le nom de la contrainte via diagnostic directe de l'erreur BD et retourne un message
        d'erreur clair si une correspondance est trouvée dans ERROR_MESSAGES, sinon retourne None
        Args:
            exception: L'exception d'intégrité levée par SQLAlchemy lors d'une violation de contrainte

        Returns:
            Optional[str] : Un message d'erreur clair si la contrainte est reconnue, sinon None
        """

        try:
            # asyncpg expose l'objet PostgreSQL dans __cause__
            # asyncpg wrappe lui-même l'erreur PG dans __cause__ (encore)
            cause = exception.__cause__.__cause__

            if not cause:
                logger.warning("Cause de l'integrityError non trouvé : %s", exception)
                return None

            logger.debug("Cause de l'integrityError trouvé avec succès : %s", cause)

            # L'objet asyncpg.exceptions.PostgresError expose constraint_name
            constraint_name: str | None = getattr(cause, "constraint_name", None)

            if constraint_name is None:
                logger.warning("Nom de la contrainte BD non trouvé dans la cause : %s", cause)
                return None

            logger.debug("Nom de la contrainte BD extrait avec succès : %s", constraint_name)

            friendly_message = cls.ERROR_MESSAGES.get(constraint_name, None)

            if not friendly_message:
                logger.warning(
                    "Aucun message d'erreur clair trouvé dans le mappers de la classe pour la contrainte : %s",
                    constraint_name
                )
                return None

            return friendly_message

        except AttributeError as exception:
            logger.error("Erreur lors de l'extraction du nom de la contrainte, __cause__ n'est pas dispo : %s", exception, exc_info=exception)
            return None
        except Exception as exception:
            logger.error("Erreur inattendue lors de la traduction de l'integrity error : %s", exception, exc_info=exception)
            return None
