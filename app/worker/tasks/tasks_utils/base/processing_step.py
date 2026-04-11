"""Enum pour les étapes de traitement des médias avec métadonnées associées."""

from enum import Enum

from app.schemas.post_upload_schemas import WsMediasProcessingInfoSchemaSteps


class ProcessingStep(Enum):
    """
    Énumération des étapes de traitement des médias.
    
    Chaque étape contient :
    - value[0]: Nom lisible de l'étape
    - value[1]: Incrément de progression associé (en %)
    """

    # Étapes communes
    UNKNOWN = (WsMediasProcessingInfoSchemaSteps.UNKNOWN.value, 0)
    VERIFICATION = (WsMediasProcessingInfoSchemaSteps.VERIFICATION.value, 25)
    COMPRESSING = (WsMediasProcessingInfoSchemaSteps.COMPRESSING.value, 45)
    CREATING = (WsMediasProcessingInfoSchemaSteps.CREATING.value, 25)
    FINALIZING = (WsMediasProcessingInfoSchemaSteps.FINALIZING.value, 5)
    COMPLETED = (WsMediasProcessingInfoSchemaSteps.COMPLETED.value, 0)

    def get_name(self) -> str:
        """Récupère le nom lisible de l'étape."""
        return self.value[0]

    def get_progress_increment(self) -> int:
        """Récupère l'incrément de progression (en %) associé à l'étape."""
        return self.value[1]


