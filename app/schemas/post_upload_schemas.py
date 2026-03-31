from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field, model_validator

from uuid import UUID

from app.db.models.enums import MediaType
from app.schemas import ApiBaseResponse

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
class CreateMediaUploadIntent(BaseModel):
    """Schéma de validation pour un intent d'upload de fichier, contenant les informations nécessaires pour initier des uploads de fichiers, comme le nom du fichier, son type et sa taille"""
    files: List[FileToUploadSchema] = Field(
        description="La liste des fichiers à uploader, actuellement limité à un 10 fichiers",
        min_length=1,
        max_length=10
    )
    event_id: Optional[UUID] = Field(None, description="L'ID de l'événement auquel le post est associé, si applicable")
    club_id: Optional[UUID] = Field(None, description="L'ID du club auquel le post est associé, si applicable")
    content: Optional[str] = Field(None, description="Le contenu textuel associé au post")
    for_current_academic_year: Optional[bool] = Field(
        description="Indique si le post doit etre limité à l'année académique en cours, si true alors"
                    " le post ne sera visible que pendant l'année académique en cours, sinon le post sera"
                    " visible sans limite de temps"
    )
    only_for_a_class: Optional[bool] = Field(
        description="Indique si le post doit etre limité seulement aux étudiants d'une classe précise, si `true` "
                    "le post sera visible uniquement par eux sinon le post sera visible pour tous les étudiants"
                    " de l'école, QUAND CE ATTRIBUT EST A `true` `for_current_academic_year` LE DEVIENT AUSSI AUTOMATIQUEMENT "
                    "DONC PLUS LA PEINE DE LE PASSER (`for_current_academic_year` SERA TOUJOURS `true` QUAND `only_for_a_class` EST `true`)"
                    "CET ATTRIBUT NE PEUT ETRE MIS A `true` QUE POUR LES DELEGUES DES SALLES, SI LE USER N'EST PAS DELEGUE D'UNE SALLE "
                    "LA REQUETE RENVERRA UNE BELLE `ERREUR 404`"
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

    result: Optional[UploadURLSchema]

class PostMediaUploadCompleteResponse(ApiBaseResponse):

    result: Optional[MediaUploadCompleteSchema]