from typing import TypeVar, Optional

from app.globals.app_result import GlobalAppResult

T = TypeVar("T")


class CRUDResult(GlobalAppResult[T]):
    """
    Classe générique pour typer les réponses d'opérations CRUD dans les Repository.

    Elle encapsule soit une donnée de succès (data), soit un message d'erreur (error).
    """

    def __init__(self, status_code: int, data: Optional[T] = None, error: Optional[str] = None):
        super().__init__(data, error)
        self.status_code = status_code

    # --- Méthodes utilitaires (Optional) ---

    def __repr__(self) -> str:
        if self.is_success():
            return f"<CRUDResponse Status {self.status_code} Success: {self._data!r}>"
        return f"<CRUDResponse Status {self.status_code} Error: {self._error!r}>"

    # --- Fonctions d'aide (Helpers) ---

    @classmethod
    def crud_success(cls, data: T, status_code: int = 200) -> "CRUDResult[T]":
        """Crée une réponse de succès avec les données fournies."""
        return cls(data=data, status_code=status_code)

    @classmethod
    def crud_error(cls, message: str, status_code: int = 500) -> "CRUDResult[T]":
        """Crée une réponse d'erreur avec le message fourni."""
        return cls(error=message, status_code=status_code)
