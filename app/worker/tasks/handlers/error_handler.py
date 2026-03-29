"""Handler pour la gestion centralisée des erreurs."""

from logging import getLogger
from typing import Optional

from app.worker.tasks.base.processing_result import ProcessingResult

logger = getLogger(__name__)


class ErrorHandler:
    """
    Handler centralisé pour gérer les erreurs et le logging pendant le traitement.
    
    Normalise la gestion des exceptions et la création de résultats d'erreur.
    """

    def __init__(self, logger_instance=None):
        """
        Initialise le handler d'erreurs.
        
        Args:
            logger_instance: Logger à utiliser (par défaut: logger du module).
        """
        self.logger = logger_instance or logger

    def log_error(
        self,
        message: str,
        exception: Optional[Exception] = None,
        is_critical: bool = False,
    ) -> None:
        """
        Enregistre une erreur avec contexte.
        
        Args:
            message: Message d'erreur descriptif.
            exception: Exception associée si applicable.
            is_critical: Si True, utilise logger.exception avec traceback complet.
        """
        if exception and is_critical:
            self.logger.exception(
                f"{message} | Exception: {exception.__class__.__name__}: {exception}",
                exc_info=exception,
            )
        else:
            self.logger.error(message)

    def create_error_result(
        self,
        message: str,
        exception: Optional[Exception] = None,
        operation_name: str = "Operation",
    ) -> ProcessingResult:
        """
        Crée un résultat d'erreur et enregistre l'erreur.
        
        Args:
            message: Message d'erreur.
            exception: Exception associée si applicable.
            operation_name: Nom de l'opération pour le log.
            
        Returns:
            ProcessingResult avec succès=False et le message d'erreur.
        """
        if exception:
            full_message = f"Erreur ({exception.__class__.__name__}) lors de {operation_name}: {message}"
            self.log_error(full_message, exception)
        else:
            self.log_error(f"Erreur lors de {operation_name}: {message}")

        return ProcessingResult.error_response(message)

    def handle_exception(
        self,
        exception: Exception,
        context: str = "processing",
        default_message: Optional[str] = None,
    ) -> ProcessingResult:
        """
        Traite une exception inattendue.
        
        Args:
            exception: Exception à traiter.
            context: Contexte d'exécution (par défaut: "processing").
            default_message: Message par défaut si non fourni.
            
        Returns:
            ProcessingResult avec l'erreur.
        """
        message = default_message or f"Unexpected error during {context}"
        self.log_error(f"{message}: {exception}", exception, is_critical=True)
        return ProcessingResult.error_response(message)

