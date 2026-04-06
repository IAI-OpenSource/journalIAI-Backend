from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, model_validator

from uuid import UUID

from app.db.models.enums import MediaType
from app.schemas import ApiBaseResponse
from app.schemas.post_schemas import CreatePost


class FileToUploadSchema(BaseModel):
    """Schéma de validation pour les informations d'un fichier à uploader, contenant le nom du fichier, sa taille et son type de média"""
    file_name: str = Field(description="Le nom du fichier à uploader, incluant son extension. TOUT LES "
                                       "NOMS DOIVENT ETRE DISTINCT LES UNS DES AUTRES")
    file_size: int = Field(
        description="La taille du fichier à uploader en octets, le fichier ne doit pas depasser 100Mo sinon Errrooor",
        gt=0,
    )
    media_type: MediaType = Field(description="Le type de média du fichier à uploader")
    @property
    def is_video(self) -> bool:
        return self.media_type == MediaType.VIDEO

#TODO: REndre la doc beaucoup plus claire et enlever quelques petites incohérences
class CreateMediaUploadIntent(CreatePost):
    """Schéma de validation pour un intent d'upload de fichier, contenant les informations nécessaires pour initier des uploads de fichiers, comme le nom du fichier, son type et sa taille"""
    files: List[FileToUploadSchema] = Field(
        description="La liste des fichiers à uploader, actuellement limité à un 10 fichiers",
        min_length=1,
        max_length=10
    )

    content: Optional[str] = Field(
        default=None,
        description="Contenu textuel du post",
    )

    @model_validator(mode='after')
    def check_files_names(self):
        names = []
        for file in self.files:
            if file.file_name in names:
                raise ValueError(f"Noms de fichier doublons detecté: {file.file_name}")
            names.append(file.file_name)
        return self


class CreateMediaUploadIntentFullData(CreateMediaUploadIntent):
    academic_year_id: Optional[UUID] = Field(None)
    classe_id: Optional[UUID] = Field(None)

class AvailableUploadMethod(str, Enum):
    PUT = "PUT"
    POST = "POST"

class FileInUploadURLSchema(BaseModel):
    # file_id: UUID = Field(description="L'id du fichier")
    upload_url: str = Field(description="L'url sur lequel l'Upload doit s'effectuer")
    method: AvailableUploadMethod = Field(description="La méthode HTTP à utiliser pour l'upload")
    file_name: str = Field(description="Le nom du fichier à uploader, envoyé précedemment")
    media_type: MediaType = Field(description="Le type de média du fichier à uploader")


class UploadURLSchema(BaseModel):
    intent_id: str = Field(
        description="Id de l'intent, cet id sera réutiliser pour les prochaines opérations, donc gardez çà jalousement,"
                    "vous allez faire beaucoup de choses avec🤣"
    )
    files: List[FileInUploadURLSchema] = Field(
        description="La liste des fichiers à uploader, avec leur id et leur url d'upload respective",
        min_length=1,
        max_length=10,
    )


class MediaUploadCompleteSchema(BaseModel):
    job_id: str = Field(
        description="L'id du job de post-traitement qui a été lancé pour traiter le média uploadée, vous "
                    "pouvez utiliser cet id pour suivre l'état de traitement du post via le websocket"
                    " de suivi. PS: C'est intent_id juste renommé"
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

class PostMediaUploadIntentResponse(ApiBaseResponse):

    result: Optional[UploadURLSchema] = Field(
        default=None,
        description="Présent seulement si la création de l'intent d'upload a réussi, contient l'id "
                    "de l'intent d'upload à réutiliser pour les prochaines étapes, et la liste des fichiers"
                    " à uploader avec leur url d'upload respective"
    )

class PostMediaUploadCompleteResponse(ApiBaseResponse):

    result: Optional[MediaUploadCompleteSchema] = Field(
        default=None,
        description="Présent seulement si la vérification de complétion de l'upload a réussi, contient l'id"
                    " du job de post-traitement lancé pour traiter le média uploadée,"
                    " vous pouvez utiliser cet id pour suivre l'état de traitement du post"
                    " via le websocket de suivi"
    )