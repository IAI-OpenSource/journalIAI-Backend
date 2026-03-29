"""Type pour les résultats de traitement normalisés."""

from typing import Optional, TypeVar, Union

from app.globals.app_result import GlobalAppResult

T = TypeVar("T")


class ProcessingResult(GlobalAppResult[T]):
    """
    Classe générique pour encapsuler les résultats de traitement.
    """

    # Ajout d'un booleen sucess ici car beaucoup de func retournerons None meme en cas de réussite
    success: bool


    def __init__(self, success: bool, data: Optional[T] = None, error: Optional[str] = None):
        """
        Initialise un résultat de traitement.
        
        Args:
            success: Indique si l'opération a réussi.
            data: Les données du résultat (si succès).
            error: Le message d'erreur (si échec).
        """
        self.success = success
        super().__init__(data=data, error=error)

    @classmethod
    def ok_response(cls, data: T) -> "ProcessingResult[T]":
        """Crée un résultat de succès avec les données."""
        if data is None:
            data = ""   # Petit hack pour éviter probleme avec la classe parente
        return cls(success=True, data=data)

    @classmethod
    def error_response(cls, error: str) -> "ProcessingResult[T]":
        """Crée un résultat d'erreur avec le message."""
        return cls(success=False, error=error)

    def is_success(self) -> bool:
        """Vérifie si l'opération a réussi."""
        return self.success

    def is_error(self) -> bool:
        """Vérifie si l'opération a échoué."""
        return not self.success

    def get_or_raise(self) -> T:
        """
        Récupère les données ou lève une exception.
        
        Raises:
            RuntimeError: Si l'opération a échoué.
            
        Returns:
            Les données du résultat.
        """
        if self.is_error():
            raise RuntimeError(f"Processing failed: {self.error_response}")
        return self.data

    def get_or_default(self, default: T) -> T:
        """Récupère les données ou une valeur par défaut."""
        return self.data if self.is_success() else default

    def __bool__(self) -> bool:
        """Permet d'utiliser le résultat dans un contexte booléen."""
        return self.success

    def __str__(self) -> str:
        """Représentation textuelle du résultat."""
        if self.is_success():
            return f"ProcessingResult(success=True, data={self.data})"
        return f"ProcessingResult(success=False, error={self.error_response})"

    def __repr__(self) -> str:
        """Représentation pour le debugging."""
        return self.__str__()


# Type aliases pour plus de clarté
ProcessingResultType = Union[ProcessingResult[T], None]

