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

        # Récupération de l'objet diag d'asyncpg
        diag = getattr(exception.orig, 'diag', None)

        if diag and diag.constraint_name:
            # Recherche direct dans le dictionnaire du modèle
            return cls.ERROR_MESSAGES.get(
                diag.constraint_name,
                f"Violation de contrainte : {diag.constraint_name}"
            )


        return None