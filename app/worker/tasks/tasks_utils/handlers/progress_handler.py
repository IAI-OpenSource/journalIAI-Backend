"""Handler pour la gestion centralisée de la progression."""

from logging import getLogger
from time import time
from typing import Optional

from app.globals.messages import Messages
from app.schemas.post_upload_schemas import WsMediasProcessingInfoSchema, WsMediasProcessingInfoSchemaSteps
from app.worker.tasks.tasks_utils.base.processing_context import ProcessingContext
from app.worker.tasks.tasks_utils.base.processing_step import ProcessingStep

logger = getLogger(__name__)


class ProgressHandler:
    """
    Handler centralisé pour gérer la progression du traitement.
    
    Encapsule la logique de mise à jour de progression et d'envoi aux clients via Redis.
    """

    def __init__(self, context: ProcessingContext):
        """
        Initialise le handler de progression.
        
        Args:
            context: Contexte du traitement contenant les informations de cache et d'identifiants.
        """
        self.context = context
        self.logger = logger

    async def update_step(
        self,
        step: ProcessingStep,
        weight: float,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Met à jour l'étape du traitement et envoie la progression aux clients.
        
        Args:
            step: Nouvelle étape du traitement.
            weight: nsm
            error_message: Message d'erreur si applicable.
        """
        # Mise à jour du contexte
        self.context.update_progress(step, int(step.get_progress_increment() * weight), error_message)

        # Convertir ProcessingStep vers WsMediasProcessingInfoSchemaSteps
        ws_step = WsMediasProcessingInfoSchemaSteps(step.get_name())

        # Construction du schéma de progression
        progression = WsMediasProcessingInfoSchema(
            step=ws_step,
            progress=self.context.global_progress_percentage,
            timestamp=time(),
            error_message=error_message,
        )

        # Envoi vers Redis
        await self.context.upload_cache.add_upload_event_in_a_stream(
            self.context.user_id,
            self.context.intent_id,
            progression,
        )

    async def error(self, error_message: Optional[str] = None) -> None:
        """
        Met à jour l'état à une erreur.
        
        Args:
            error_message: Message d'erreur à afficher (par défaut: message d'erreur générique).
        """
        message = error_message or Messages.INTERNAL_SERVER_ERROR
        await self.update_step(
            self.context.current_step,
            error_message=message,
            weight=0
        )

    async def increment_progress(self, increment: int) -> None:
        """
        Incrémente simplement la progression de la même étape.
        
        Args:
            increment: Valeur à ajouter au pourcentage de progression.
        """
        self.context.global_progress_percentage = min(
            self.context.global_progress_percentage + increment,
            100
        )

        # Convertir ProcessingStep vers WsMediasProcessingInfoSchemaSteps
        ws_step = WsMediasProcessingInfoSchemaSteps(self.context.current_step.get_name())

        progression = WsMediasProcessingInfoSchema(
            step=ws_step,
            progress=self.context.global_progress_percentage,
            timestamp=time(),
            error_message=None,
        )

        await self.context.upload_cache.add_upload_event_in_a_stream(
            self.context.user_id,
            self.context.intent_id,
            progression,
        )

    async def complete(self) -> None:
        """Marque le traitement comme complété."""
        await self.update_step(ProcessingStep.COMPLETED, 0)





