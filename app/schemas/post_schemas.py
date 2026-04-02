## Ce fichier contient les différents schémas concernant les opérations
# sur les tables posts, post_media et post_views


from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.db.models.enums import MediaType, PostType
from app.schemas import ApiBaseResponse
from app.storage.minio_config import BucketName


# Schémas d'entrée (écriture)

class CreatePost(BaseModel):
    """Schéma de validation pour la création d'un post."""

    content: str = Field(
        description="Contenu textuel du post",
    )

    event_id: Optional[UUID] = Field(None, description="L'ID de l'événement auquel le post est associé, si applicable")
    club_id: Optional[UUID] = Field(None, description="L'ID du club auquel le post est associé, si applicable")
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

class CreatePostView(BaseModel):
    """Schéma pour enregistrer des vues de post"""

    posts_ids: List[UUID] = Field(
        description="Les ids des posts vu, faites çà intelligemment, n'envoyez pas une requete à chaque fois qu'un post"
                    " est vu 💀, vous pouvez regrouper en batch de n post et envoyer au bon moment, bref un algo intelligent"
    )

# Schémas de lecture (réponse)

class ReadPostMedia(BaseModel):
    """Schéma de lecture d'un média associé à un post."""

    id: UUID
    media_type: MediaType
    media_url: str = Field(
        description="Lien pour récuperer le média en question, au cas où c'est du HLS vous devriez"
                    " faire des magouilles supplémmentaires coté player"
    )
    thumbnail_url: Optional[str] = Field(
        default=None,
        description="Lien direct public pour récup la miniature du média",
    )
    media_blur_hash: Optional[str] = Field(
        default=None,
        description="BlurHash du média pour affichage d'un placeholder flou pendant le chargement."
    )

    width: Optional[int] = Field(
        default=None,
        description="Largeur en pixels, vous pouvez utiliser pour savoir comment générer votre player vidéo ou votre composant d'affichage d'image en fonction du ratio"
    )

    height: Optional[int] = Field(
        default=None,
        description="Hauteur en pixels, vous pouvez utiliser pour savoir comment générer votre player vidéo ou votre composant d'affichage d'image en fonction du ratio"
    )

    duration: Optional[int] = Field(
        default=None,
        description="Durée en secondes, uniquement pour les vidéos.",
    )

    display_order: int = Field(
        description="Ordre d'affichage du média parmi les médias du post (0 = premier média, 1 = deuxième, etc.)"
    )

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

    result: Optional[ReadPostList] = Field(description="Page de posts avec curseur de pagination.")


class PostMediaInfos(ApiBaseResponse):
    """Réponse API pour un média de post."""

    result: ReadPostMedia = Field(description="Données du média.")


class PresignedUrlInfos(ApiBaseResponse):
    """Réponse API contenant l'URL présignée MinIO."""

    result: PresignedUploadUrlResponse = Field(description="URL d'upload présignée.")
