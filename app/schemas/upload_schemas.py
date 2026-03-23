from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from uuid import UUID

from app.schemas import ApiBaseResponse

class CreateVideoUploadIntent(BaseModel):
    """Schéma de validation pour un intent d'upload de fichier, contenant les informations nécessaires pour initier un upload de fichier, comme le nom du fichier, son type et sa taille"""

    file_name: str = Field(description="Le nom du fichier à uploader, incluant son extension")
    file_size: int = Field(description="La taille du fichier à uploader en octets")
    event_id: Optional[UUID] = Field(None, description="L'ID de l'événement auquel le fichier est associé, si applicable")
    club_id: Optional[UUID] = Field(None, description="L'ID du club auquel le fichier est associé, si applicable")
    content: Optional[str] = Field(None, description="Le contenu textuel associé au post")

    class Config:
        from_attributes = True

class UploadURLSchema(BaseModel):
    upload_url: str = Field(description="L'url sur lequel l'Upload doit s'effectuer")
    intent_id: str = Field(
        description="Id de l'intent, cet id sera réutiliser pour les prochaines opérations, donc gardez çà jalousement,"
                    "vous allez faire beaucoup de choses avec🤣"
    )
class WsPostProcessingInfoSchemaSteps(str, Enum):
    VERIFICATION = "verification"
    PROCESSING = "processing"

class WsPostProcessingInfoSchema(BaseModel):
    step: WsPostProcessingInfoSchemaSteps = Field(..., description="L'étape à laquelle on est")
    progress: int = Field(..., description="Le pourcentage de progression")
    timestamp: float = Field(..., description="Le timestamp de l'information de suivi, en millisecondes depuis epoch")
    error_message: Optional[str] = Field(
        None,
        description="Message d'erreur en cas d'échec, apres çà c'est terminé, l'opération est instantanément"
                    " interrompue, le message sera abstrait donc affichable aux utilisateurs, gardez juste en tete que"
                    " après çà ékpa, mission échouée"
    )

class StringResponse(BaseModel):
    message: str = Field(description="Le message de réponse relatif au résultat de l'opération, ce message là sera"
                                     " forcément pour un succès, si c'est echec ca sera dans le champ 'error'")

class VideoUploadIntentResponse(ApiBaseResponse):

    result: UploadURLSchema