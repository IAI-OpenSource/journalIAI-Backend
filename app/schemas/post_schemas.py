## Ce fichier contient les différents schémas concernant les opérations
# sur les tables posts, post_media et post_views


from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.db.models.enums import MediaType, PostType
from app.schemas import ApiBaseResponse
from app.storage.minio_config import BucketName


# Schémas d'entrée (écriture)

class CreatePost(BaseModel):
    """Schéma de validation pour la création d'un post.

    NB : author_id et academic_year_id sont injectés côté serveur
    (token JWT + contexte académique actif), jamais envoyés par le client.
    """

    content: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Contenu textuel du post. Obligatoire si post_type=TEXT.",
    )
    post_type: PostType = Field(
        default=PostType.TEXT,
        description="Type du post (TEXT, IMAGE, VIDEO…)",
    )
    club_id: Optional[UUID] = Field(
        default=None,
        description="Club auquel ce post est rattaché (optionnel).",
    )
    event_id: Optional[UUID] = Field(
        default=None,
        description="Événement auquel ce post est rattaché (optionnel).",
    )
    target_classe_id: Optional[UUID] = Field(
        default=None,
        description="Classe ciblée par ce post (optionnel, NULL = post général).",
    )

    @model_validator(mode="after")
    def content_required_for_text(self) -> "CreatePost":
        if self.post_type == PostType.TEXT and not self.content:
            raise ValueError("Le contenu est obligatoire pour un post de type TEXT.")
        return self


class UpdatePost(BaseModel):
    """Schéma de validation pour la mise à jour partielle d'un post.

    Tous les champs sont optionnels (PATCH sémantique).
    """

    content: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Nouveau contenu textuel.",
    )
    is_pinned: Optional[bool] = Field(
        default=None,
        description="Épingler ou désépingler le post.",
    )
    is_published: Optional[bool] = Field(
        default=None,
        description="Publier ou dépublier le post.",
    )
    target_classe_id: Optional[UUID] = Field(
        default=None,
        description="Modifier la classe ciblée.",
    )


# Schémas de lecture (réponse)

class ReadPostMedia(BaseModel):
    """Schéma de lecture d'un média associé à un post."""

    id: UUID
    media_type: MediaType
    media_url: str = Field(description="Clé objet MinIO (pas une URL directe).")
    thumbnail_url: Optional[str] = Field(
        default=None,
        description="Clé objet MinIO du thumbnail (généré de manière asynchrone).",
    )
    file_size: Optional[int]
    width: Optional[int]
    height: Optional[int]
    duration: Optional[int] = Field(
        default=None,
        description="Durée en secondes, uniquement pour les vidéos.",
    )
    display_order: int
    is_processed: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ReadPost(BaseModel):
    """Schéma de lecture complète d'un post (avec ses médias)."""

    id: UUID
    author_id: UUID
    club_id: Optional[UUID]
    event_id: Optional[UUID]
    target_classe_id: Optional[UUID]
    academic_year_id: Optional[UUID]

    content: Optional[str]
    post_type: PostType

    like_count: int
    comment_count: int

    is_pinned: bool
    is_published: bool

    created_at: datetime
    updated_at: datetime
    published_at: Optional[datetime]

    # Relations chargées avec selectinload dans le repository
    media: list[ReadPostMedia] = Field(
        default_factory=list,
        description="Liste des médias attachés au post.",
    )

    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    class Config:
        from_attributes = True

ReadPost.model_rebuild()


class ReadPostList(BaseModel):
    """Schéma de réponse paginée pour un feed de posts (cursor-based pagination).

    Le curseur est construit côté serveur sous la forme :
    base64(created_at.isoformat() + '|' + str(id))
    """

    items: list[ReadPost] = Field(description="Posts de la page courante.")
    next_cursor: Optional[str] = Field(
        default=None,
        description="Curseur opaque à renvoyer pour obtenir la page suivante. NULL si dernière page.",
    )
    has_more: bool = Field(description="Indique s'il existe une page suivante.")


# Schémas pour l'upload de médias via MinIO (presigned URL)

class RequestMediaUploadUrl(BaseModel):
    """Schéma de demande d'URL d'upload présignée MinIO.

    Étape 1 du flow : le client demande une URL, upload directement sur MinIO,
    puis confirme via PostMediaConfirm.
    """

    filename: str = Field(description="Nom original du fichier (ex: photo.jpg).")
    media_type: MediaType = Field(description="Type du média : IMAGE ou VIDEO.")
    file_size: Optional[int] = Field(
        default=None,
        gt=0,
        description="Taille du fichier en octets (optionnel, pour validation préalable).",
    )


class PresignedUploadUrlResponse(BaseModel):
    """Réponse contenant l'URL présignée MinIO et la clé objet."""

    upload_url: str = Field(description="URL PUT présignée MinIO. Valide 15 minutes.")
    object_key: str = Field(
        description="Clé objet à conserver et renvoyer lors de la confirmation."
    )


class ConfirmMediaUpload(BaseModel):
    """Schéma de confirmation d'upload.
 
    Étape 3 du flow : le client confirme que l'upload a réussi.
    Le service appellera object_exists() sur source_bucket / object_key
    avant de créer l'entrée PostMedia — évite les entrées DB orphelines
    si le client ment sur un upload qui aurait échoué.
    """
 
    object_key: str = Field(
        description="Clé objet renvoyée par PresignedUploadUrlResponse."
    )
    # Le client renvoie toujours POSTS_RAW_UPLOADS pour un post média.
    # On le garde explicite pour ne pas le coder en dur côté service.
    source_bucket: BucketName = Field(
        default=BucketName.POSTS_RAW_UPLOADS,
        description="Bucket dans lequel l'objet a été uploadé.",
    )
    media_type: MediaType
    file_size: Optional[int] = Field(default=None, gt=0)
    width: Optional[int] = Field(default=None, gt=0)
    height: Optional[int] = Field(default=None, gt=0)
    duration: Optional[int] = Field(
        default=None,
        gt=0,
        description="Durée en secondes (uniquement pour les vidéos).",
    )
    display_order: int = Field(default=0, ge=0)
 
    @model_validator(mode="after")
    def duration_only_for_video(self) -> "ConfirmMediaUpload":
        if self.media_type == MediaType.IMAGE and self.duration is not None:
            raise ValueError("La durée ne s'applique qu'aux vidéos.")
        return self


# Réponses API enveloppées dans ApiBaseResponsez

class PostInfos(ApiBaseResponse):
    """Réponse API pour un post unique."""

    result: ReadPost = Field(description="Données du post.")


class PostListInfos(ApiBaseResponse):
    """Réponse API pour un feed paginé de posts."""

    result: ReadPostList = Field(description="Page de posts avec curseur de pagination.")


class PostMediaInfos(ApiBaseResponse):
    """Réponse API pour un média de post."""

    result: ReadPostMedia = Field(description="Données du média.")


class PresignedUrlInfos(ApiBaseResponse):
    """Réponse API contenant l'URL présignée MinIO."""

    result: PresignedUploadUrlResponse = Field(description="URL d'upload présignée.")
