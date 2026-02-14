from typing import TypeVar, Optional

from app.globals.app_result import GlobalAppResult

T = TypeVar("T")


class CRUDResult(GlobalAppResult[T]):
    """
    Classe générique pour typer les réponses d'opérations CRUD dans les Repository.

    Elle encapsule soit une donnée de succès (data), soit un message d'erreur (error).
    """

    def __init__(self, data: Optional[T] = None, error: Optional[str] = None):
        super().__init__(data, error)

    # --- Méthodes utilitaires (Optional) ---

    def __repr__(self) -> str:
        if self.is_success():
            return f"<CRUDResponse Success: {self._data!r}>"
        return f"<CRUDResponse Error: {self._error!r}>"

    # --- Fonctions d'aide (Helpers) ---

    @classmethod
    def crud_success(cls, data: T):
        """Crée une réponse de succès avec les données fournies."""
        return cls(data=data)

    @classmethod
    def crud_error(cls, message: str):
        """Crée une réponse d'erreur avec le message fourni."""
        return cls(error=message)
