from typing import TypeVar, Optional

from app.globals.app_result import GlobalAppResult

T = TypeVar("T")

class ServiceResult(GlobalAppResult[T]):
    """
    Classe générique pour typer les réponses d'opérations des Services.

    Elle encapsule soit une donnée de succès (data), soit un message d'erreur (error).
    """
    def __init__(self, data: Optional[T] = None, error: Optional[str] = None, service_name: str = "Service Inconnu"):
        super().__init__(data, error)
        self.service_name = service_name

    # --- Méthodes utilitaires (Optional) ---

    def __repr__(self) -> str:
        if self.is_success():
            return f"<Service {self.service_name} Response Success: {self._data!r}>"
        return f"<Service {self.service_name} Response Error: {self._error!r}>"

    # --- Fonctions d'aide (Helpers) ---

    @classmethod
    def service_success(cls, data: T, service_name: str = "Service Inconnu") -> "ServiceResult[T]":
        """
        Crée une réponse de succès avec les données fournies.
        Args:
            data: Les données de succès à encapsuler dans la réponse.
            service_name: Le nom du service qui génère cette réponse (optionnel, par défaut "Service Inconnu").

        Returns:
            L'instance de ServiceResult contenant les données de succès.
        """
        return cls(data=data, service_name=service_name)

    @classmethod
    def service_error(cls, message: str, service_name: str = "Service Inconnu") -> "ServiceResult[None]":
        """
        Crée une réponse d'erreur avec le message fourni.
        Args:
            message: Le message d'erreur à encapsuler dans la réponse.
            service_name: Le nom du service qui génère cette réponse (optionnel, par défaut "Service Inconnu").

        Returns:
            L'instance de ServiceResult contenant le message d'erreur.
        """
        return cls(error=message, service_name=service_name)
