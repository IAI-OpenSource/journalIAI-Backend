from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas import ApiBaseResponse
from app.schemas.post_upload_schemas import FileToUploadSchema, FileInUploadURLSchema, MediaUploadCompleteSchema


class StoryUploadURLSchema(BaseModel):
    """Schéma de réponse avec les URLs d'upload pour une story."""
    intent_id: str = Field(
        description="Id de l'intent, cet id sera réutiliser pour les prochaines opérations"
    )
    file: FileInUploadURLSchema = Field(
        description="Le fichier à uploader avec son URL d'upload et sa méthode"
    )


class CreateStoryUploadIntent(BaseModel):
    """Schéma de validation pour un intent d'upload de story avec fichier unique."""

    legend: Optional[str] = Field(
        default=None,
        description="Légende de la story, max 200 caractères",
        max_length=200
    )

    club_id: Optional[UUID] = Field(None, description="L'ID du club auquel la story est associée")

    only_for_a_class: Optional[bool] = Field(
        default=None,
        description="Si true, la story est visible uniquement par la classe de l'utilisateur (pour les délégués)"
    )

    file: FileToUploadSchema = Field(
        ...,
        description="Le fichier à uploader pour la story"
    )


class CreateStoryUploadIntentFullData(CreateStoryUploadIntent):
    """Schéma complet avec les données resolues (académique, classe, etc.)."""
    academic_year_id: Optional[UUID] = Field(None)
    target_classe_id: Optional[UUID] = Field(None)


class StoryMediaUploadIntentResponse(ApiBaseResponse):
    """Réponse pour la création d'un intent d'upload de story."""
    result: Optional[StoryUploadURLSchema] = Field(
        default=None,
        description="Présent seulement si la création de l'intent d'upload a réussi"
    )


class StoryMediaUploadCompleteResponse(ApiBaseResponse):
    """Réponse pour la complétion d'un upload de story."""
    result: Optional[MediaUploadCompleteSchema] = Field(
        default=None,
        description="Présent seulement si la vérification de complétion de l'upload a réussi"
    )


