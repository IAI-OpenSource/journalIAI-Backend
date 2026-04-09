from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.enums import StoryGroupsType
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
    """
    Schéma de validation pour un intent d'upload de story avec fichier unique.
    Petite subtilité : Si `only_for_a_class` est `true` alors la story est marqué comme une
    story de classe (pour que cet argument puisse etre `true` il faudraitt que l'utilisateur ourant soit un délégué
    de classe. Si `club_id` est fourni alors la story est marqué comme une story de club.
    Si ces deux options ne sont pas vérifiés alors la story est consiférée comme une simple story utilisateur
    """

    legend: Optional[str] = Field(
        default=None,
        description="Légende de la story, max 200 caractères",
        max_length=200
    )

    story_duration_hours: int = Field(
        default=24,
        description="Durée de vie de la story en heures (par défaut 24h",
        gt=0, lt=24
    )

    club_id: Optional[UUID] = Field(None, description="L'ID du club (Si la story est pour un club)")

    only_for_a_class: Optional[bool] = Field(
        default=None,
        description="Si true, la story est visible uniquement par la classe de l'utilisateur (pour les délégués)"
    )

    file: FileToUploadSchema = Field(
        ...,
        description="Les infos du fichier à uploader pour la story"
    )


class CreateStoryUploadIntentFullData(CreateStoryUploadIntent):
    """Schéma complet avec les données resolues (académique, classe, etc.)."""
    target_group_type: StoryGroupsType = Field(
        None
    )
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


