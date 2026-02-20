from sqlalchemy.exc import IntegrityError
from typing import Optional


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

        # asyncpg expose l'objet PostgreSQL dans __cause__
        cause = exception.__cause__

        # asyncpg wrappe lui-même l'erreur PG dans __cause__
        if hasattr(cause, "__cause__"):
            cause = cause.__cause__

        # L'objet asyncpg.exceptions.PostgresError expose constraint_name
        constraint_name: str | None = getattr(cause, "constraint_name", None)

        return cls.ERROR_MESSAGES.get(
                constraint_name,
                f"Violation de contrainte : {constraint_name}"
            ) if constraint_name else "Violation d'intégrité non identifiée"