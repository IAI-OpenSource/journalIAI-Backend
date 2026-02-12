from typing import TypeVar, Optional

from fastapi.responses import Response

from app.globals.app_result import GlobalAppResult
from app.schemas import ApiBaseResponse

T = TypeVar("T")

class ServiceResult(GlobalAppResult[T]):
    """
    Classe générique pour typer les réponses d'opérations des Services.

    Elle encapsule soit une donnée de succès (data), soit un message d'erreur (error).
    """

    data: Optional[ApiBaseResponse[T]]
    error: Optional[str]
    service_name: str
    status_code: int

    def __init__(self,status_code : int, data: Optional[ApiBaseResponse[T]] = None, error: Optional[str] = None, service_name: str = "Service Inconnu"):
        """N'utilisez pas directement le constructeur, utilisez les méthodes de classe service_success et service_error pour créer des instances de ServiceResult."""
        super().__init__(data, error)
        self.service_name = service_name
        self.status_code = status_code

    # --- Méthodes utilitaires (Optional) ---

    def __repr__(self) -> str:
        if self.is_success():
            return f"<Service {self.service_name} Response Success: {self._data!r}>"
        return f"<Service {self.service_name} Response Error: {self._error!r}>"

    # --- Fonctions d'aide (Helpers) ---

    @classmethod
    def service_success(cls, data: ApiBaseResponse[T], status_code: int = 200, service_name: str = "Service Inconnu") -> "ServiceResult[ApiBaseResponse[T]]":
        """
        Crée une réponse de succès avec les données fournies, le code de status HTTP à retourner et le nom du service.
        Args:
            data: Les données de succès à encapsuler dans la réponse.
            status_code: Le code de status HTTP à retourner (200 par défaut, mais doit être personnalisé ouiiiii).
            service_name: Le nom du service qui génère cette réponse (optionnel, par défaut "Service Inconnu").

        Returns:
            L'instance de ServiceResult contenant les données de succès.
        """
        if not isinstance(data, ApiBaseResponse):
            raise ValueError("Ohhhhh pour une ServiceResult de succès, data (de l'instance ServiceResult) doit être une instance ou une sous classe de ApiBaseResponse")

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


    def to_HTTP_response(self, response : Response) -> ApiBaseResponse[T]:
        """
        Convertit ce ServiceResult en une réponse HTTP FastAPI appropriée.
        Args:
            response: L'objet Response de FastAPI pour pouvoir modifier des trucs.

        Returns:
            Une sous-classe de ApiBaseResponse contenant les données de succès ou le message d'erreur, avec le status code HTTP approprié.
        """

        if self.is_success():
            if not isinstance(self.data, ApiBaseResponse):
                raise ValueError("Ohhhhh pour une ServiceResult de succès, data (de l'instance ServiceResult) doit être une instance ou une sous classe de ApiBaseResponse")
            # On peut personnaliser le status code pour les succès si besoin, mais par défaut on met 200
            return self.data.success_response(data=self.data.result, response=response, status_code=self.status_code)
        else:
            # Pour les erreurs, on peut aussi personnaliser le status code selon le message d'erreur ou le service
            return ApiBaseResponse.error_response(error_message=self.error, response=response, status_code=self.status_code)
