from typing import TypeVar, Optional

from fastapi import Response

from app.globals.messages import Messages


from app.globals.app_result import GlobalAppResult
from app.schemas import ApiBaseResponse

T = TypeVar("T")

class ServiceResult(GlobalAppResult[T]):
    """
    Classe générique pour typer les réponses d'opérations des Services.

    Elle encapsule soit une donnée de succès (data), soit un message d'erreur (error).
    """
    service_name: str
    status_code: int

    def __init__(self, status_code : int, data: Optional[T] = None, error: Optional[str] = None, service_name: str = Messages.UNKNOWN_SERVICE):
        """N'utilisez pas directement le constructeur, utilisez les méthodes de classe service_success et service_error pour créer des instances de ServiceResult."""
        super().__init__(data, error)
        self.service_name = service_name
        self.status_code = status_code

    def to_HTTP_api_base_response(self, reponse: Response) -> ApiBaseResponse[T]:
        """
        Methode pour convertir une instance de ServiceResult en une réponse HTTP API standardisée (ApiBaseResponse)
        à retourner aux clients de l'API.

        Cette méthode n'est utilisable que si la reponse à retourner est exactement ce que le service renvoie, c'est pas
        magie

        Args:
            reponse: L'objet Response de FastAPI pour pouvoir modifier le status code de la réponse HTTP à retourner.

        Returns:
            ApiBaseResponse[T]: Une instance de ApiBaseResponse contenant les données de succès ou le message d'erreur,
             avec le code de status HTTP approprié.

        """
        if self.is_error():
            return ApiBaseResponse.error_response(error_message=self._error, response=reponse, status_code=self.status_code)

        return ApiBaseResponse.success_response(data=self._data, response=reponse, status_code=self.status_code)
    # --- Méthodes utilitaires (Optional) ---

    def __repr__(self) -> str:
        if self.is_success():
            return f"<Service {self.service_name} Response Success: {self._data!r}>"
        return f"<Service {self.service_name} Response Error: {self._error!r}>"

    # --- Fonctions d'aide (Helpers) ---

    @classmethod
    def service_success(cls, data: T, status_code: int = 200, service_name: str = "Service Inconnu") -> "ServiceResult[T]":
        """
        Crée une réponse de succès avec les données fournies, le code de status HTTP à retourner et le nom du service.
        Args:
            data: Les données de succès à encapsuler dans la réponse.
            status_code: Le code de status HTTP à retourner (200 par défaut, mais doit être personnalisé ouiiiii).
            service_name: Le nom du service qui génère cette réponse (optionnel, par défaut "Service Inconnu").

        Returns:
            L'instance de ServiceResult contenant les données de succès.
        """

        return cls(data=data, service_name=service_name, status_code=status_code)

    @classmethod
    def service_error(cls, message: str, status_code: int = 400,  service_name: str = "Service Inconnu") -> "ServiceResult[None]":
        """
        Crée une réponse d'erreur avec le message fourni, le code de status HTTP à retourner et le nom du service.
        Args:
            message: Le message d'erreur à encapsuler dans la réponse.
            status_code: Le code de status HTTP à retourner (400 par défaut, on mettra des codes plus spécifiques selon les cas d'erreur)
            service_name: Le nom du service qui génère cette réponse (optionnel, par défaut "Service Inconnu").

        Returns:
            L'instance de ServiceResult contenant le message d'erreur.
        """
        return cls(error=message, service_name=service_name, status_code=status_code)