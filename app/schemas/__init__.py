from typing import Generic, TypeVar, Optional
from fastapi import Response
from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")


# Modele de base pour toutes les reponses de l'API
class ApiBaseResponse(BaseModel, Generic[T]):
    """Scema de base pour uniformiser les réponses de l'API"""

    ok: bool = Field(
        ...,
        title="Champ pour véreifier si la reequete à réussi, True si la requete a reussi, False sinon",
    )

    result: Optional[T] = Field(
        default=None,
        title="Champ de résultat",
        description="Présent seulement si la requet à réussi",
    )

    error: Optional[str] = Field(
        default=None,
        title="Champ des erreurs à afficher directement à l'utilisateur",
        description="Présent seulement si la requete à échouée ou si quelque chose s'est mal passé durant le traitement",
    )

    @model_validator(mode="after")
    def check_response(self):
        if self.ok and self.error is not None:
            raise ValueError("Le champ error doit être null lorsque ok est True")
        if not self.ok and self.result is not None:
            raise ValueError("Le champ result doit être null lorsque ok est False")
        return self

    # Cette methode permettra de renvoyer les reponse de succèss directement depuis les classes filles
    @classmethod
    def success_response(cls, data: T, response : Response, status_code: int = 200):
        """
        Methode pour instancier une reponse de succes
        Args:
            data: Données à retourner
            response: L'objet Response de FastAPI pour pouvoir modifier le status code de la réponse
            status_code: Le code de status HTTP à retourner (200 par défaut, mais doit être personnalisé ouiiiii)
        Returns:
            Une instance de ApiBaseResponse
        """

        response.status_code = status_code

        return cls(ok=True, result=data, error=None)

    # Cette methode permettra de renvoyer les reponse d'erreur directement depuis les classes filles
    @classmethod
    def error_response(cls, error_message: str,  response : Response, status_code: int = 400):
        """
        Methode pour instancier une réponse d'échec
        Args:
            error_message: Le message d'erreur à retourner
            response: L'objet Response de FastAPI pour pouvoir modifier le status code de la réponse
            status_code: Le code de status HTTP à retourner (400 par défaut, on mettra des codes plus spécifiques selon les cas d'erreur)
        Returns:
            Une instance de ApiBaseResponse
        """
        response.status_code = status_code

        return cls(ok=False, result=None, error=error_message)
