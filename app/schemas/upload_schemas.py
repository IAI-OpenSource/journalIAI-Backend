from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from uuid import UUID

from app.schemas import ApiBaseResponse

class CreateVideoUploadIntent(BaseModel):
    """Schéma de validation pour un intent d'upload de fichier, contenant les informations nécessaires pour initier un upload de fichier, comme le nom du fichier, son type et sa taille"""

    file_name: str = Field(description="Le nom du fichier à uploader, incluant son extension")
    file_size: int = Field(description="La taille du fichier à uploader en octets, le fichier ne doit pas depasser 500Mo sinon Errrooor")
    event_id: Optional[UUID] = Field(None, description="L'ID de l'événement auquel le fichier est associé, si applicable")
    club_id: Optional[UUID] = Field(None, description="L'ID du club auquel le fichier est associé, si applicable")
    content: Optional[str] = Field(None, description="Le contenu textuel associé au post")
    for_current_academic_year: Optional[bool] = Field(
        description="Indique si le post doit etre limité à l'année académique en cours, si true alors"
                    " le post ne sera visible que pendant l'année académique en cours, sinon le post sera"
                    " visible sans limite de temps"
    )
    only_for_a_class: Optional[bool] = Field(
        description="Indique si le post doit etre limité seulement aux étudiants d'une classe précise, si true "
                    "le post sera visible uniquement par eux sinon le post sera visible pour tous les étudiants"
                    " de l'école, QUAND CE ATTRIBUT EST A True `for_current_academic_year` LE DEVIENT AUSSI AUTOMATIQUEMENT "
                    "DONC PLUS LA PEINE DE LE PASSER (`for_current_academic_year` SERA TOUJOURS TRUE QUAND `only_for_a_class` EST TRUE)"
    )

class CreateVideoUploadIntentFullData(CreateVideoUploadIntent):
    academic_year_id: Optional[UUID] = Field(None)
    classe_id: Optional[UUID] = Field(None)



class UploadURLSchema(BaseModel):
    upload_url: str = Field(description="L'url sur lequel l'Upload doit s'effectuer")
    intent_id: str = Field(
        description="Id de l'intent, cet id sera réutiliser pour les prochaines opérations, donc gardez çà jalousement,"
                    "vous allez faire beaucoup de choses avec🤣"
    )

class VideoUploadCompleteSchema(BaseModel):
    job_id: str = Field(
        description="L'id du job de post-traitement qui a été lancé pour traiter la vidéo uploadée, vous "
                    "pouvez utiliser cet id pour suivre l'état de traitement de la vidéo via le websocket"
                    " de suivi PS: C'est intent_id juste renommé"
    )

class WsPostProcessingInfoSchemaSteps(str, Enum):
    UNKNOWN = "unknown"
    FINALIZING = "finalizing"
    IN_QUEUE = "in_queue"
    VERIFICATION = "verification"
    PROCESSING = "processing"
    COMPRESSING = "compressing"
    CREATING = "creating"
    COMPLETED = "completed"

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

class VideoUploadIntentResponse(ApiBaseResponse):

    result: Optional[UploadURLSchema]

class VideoUploadCompleteResponse(ApiBaseResponse):

    result: Optional[VideoUploadCompleteSchema]