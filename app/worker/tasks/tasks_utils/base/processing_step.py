"""Enum pour les étapes de traitement des médias avec métadonnées associées."""

from enum import Enum

from app.schemas.post_upload_schemas import WsPostProcessingInfoSchemaSteps


class ProcessingStep(Enum):
    """
    Énumération des étapes de traitement des médias.
    
    Chaque étape contient :
    - value[0]: Nom lisible de l'étape
    - value[1]: Incrément de progression associé (en %)
    """

    # Étapes communes
    UNKNOWN = (WsPostProcessingInfoSchemaSteps.UNKNOWN.value, 0)
    VERIFICATION = (WsPostProcessingInfoSchemaSteps.VERIFICATION.value, 25)
    COMPRESSING = (WsPostProcessingInfoSchemaSteps.COMPRESSING.value, 45)
    CREATING = (WsPostProcessingInfoSchemaSteps.CREATING.value, 25)
    FINALIZING = (WsPostProcessingInfoSchemaSteps.FINALIZING.value, 5)
    COMPLETED = ("completed", 15)

    def get_name(self) -> str:
        """Récupère le nom lisible de l'étape."""
        return self.value[0]

    def get_progress_increment(self) -> int:
        """Récupère l'incrément de progression (en %) associé à l'étape."""
        return self.value[1]

    @staticmethod
    def from_schema_step(schema_step: str) -> "ProcessingStep":
        """
        Convertit une chaîne depuis WsPostProcessingInfoSchemaSteps vers ProcessingStep.
        
        Args:
            schema_step: Le nom de l'étape depuis le schema (ex: "verification")
            
        Returns:
            L'énumération ProcessingStep correspondante
        """
        for step in ProcessingStep:
            if step.get_name() == schema_step:
                return step
        return ProcessingStep.UNKNOWN


