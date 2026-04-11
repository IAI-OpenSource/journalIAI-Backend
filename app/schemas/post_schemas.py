## Ce fichier contient les différents schémas concernant les opérations
# sur les tables posts, post_media et post_views


from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.db.models.enums import MediaType, PostType, UserRole, ExecutiveRoleType, EventStatus, ClasseType
from app.schemas import ApiBaseResponse
from app.storage.media_read_storage import MediaReadStorage


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

class CreatePostFullData(CreatePost):
    academic_year_id: Optional[UUID] = Field(None)
    classe_id: Optional[UUID] = Field(None)


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

class PostAuthorSchema(BaseModel):
    """Schéma pour les infos de l'auteur d'un post."""

    id: UUID
    username: str
    first_name: str
    last_name: str
    avatar_url: Optional[str] = Field(
        default=None,
        description="URL de la photo de profil de l'auteur, si disponible.",
    )
    role: UserRole = Field(
        description="Le role de l'auteur du post, qui peut influencer la façon dont vous allez affiche le post (ex: badge de modérateur, etc.)"
    )
    executive_role: Optional[ExecutiveRoleType] = Field(
        default=None,
        description="Le role éxecutif pour les membres du bureau executif, ce truc sera seulement là si `role`"
                    " est à EXECUTIVE_MEMBER, sinon c'est null, vous pouvez aussi l'ignorer si vous voulez, c'est"
                    " pas super important pour l'affichage du post, c'est juste un bonus d'infos sur l'auteur du post,"
                    " mais n'ignorez pas🤣"
    )

    class Config:
        from_attributes = True

    @field_validator("avatar_url")
    @classmethod
    def format_avatar_url(cls, v: Optional[str]) -> Optional[str]:
        return MediaReadStorage.generate_read_public_asset(v)

class PostClubSchema(BaseModel):
    """Infos du club porteur du post (si applicable)."""


    id: UUID
    name: str
    slug: str
    logo_url: Optional[str] = Field(
        default=None,
        description="URL du logo du club, si disponible, à afficher à coté du nom du club quand vous affichez le post"
    )

    class Config:
        from_attributes = True

    @field_validator("logo_url")
    @classmethod
    def format_public_url(cls, v: Optional[str]) -> Optional[str]:
        return MediaReadStorage.generate_read_public_asset(v)

class PostClasseSchema(BaseModel):
    """Info de la classe qui est concernée par le post (si applicable)"""
    id: UUID
    classe_prefix: ClasseType
    classe_suffix: str

    class Config:
        from_attributes = True

class PostEventSchema(BaseModel):
    """Infos de l'événement lié au post (si applicable)."""

    id: UUID
    title: str
    slug: str
    start_date: datetime
    end_date: Optional[datetime] = Field(None, description="Date de fin l'event")
    status: EventStatus = Field(
        description="Le status de l'event, qui peut influencer la façon dont vous allez afficher le post (ex: badge d'event à venir, etc.)"
    )

    class Config:
        from_attributes = True

class PostMediaSchema(BaseModel):
    """Schéma de lecture d'un média associé à un post."""

    id: UUID
    media_type: MediaType

    thumbnail_url: Optional[str] = Field(
        default=None,
        description="Lien direct public pour récup la miniature du média",
    )

    hls_master_url: Optional[str] = Field(
        default=None,
        description="Lien pour récupérer le master playlist HLS du média, uniquement présent si"
                    " `media_type` est `VIDEO`, ce lien est à utiliser pour les players vidéo supportant le HLS"
                    ", à utiliser pour les players vidéo supportant le HLS"
    )

    image_medium_url: Optional[str] = Field(
        default=None,
        description="Lien pour récuperer l'image de qualité medium du média, uniquement présent si `media_type` est IMAGE, "
                    "ce lien est à utiliser pour les affichages d'image classiques dans le feed, en cas d'aggrandissement "
                    "vaut mieux passer sur `image_high_url` si disponible pour une meilleure qualité"
    )

    image_high_url: Optional[str] = Field(
        default=None,
        description="Lien pour récuperer l'image de qualité haute du média, uniquement présent si `media_type` est IMAGE, "
                    "ce lien est à utiliser pour les affichages d'image en grand format (ex: dans la page de détail du"
                    " post) pour une meilleure qualité, si ce lien n'est pas disponible vous pouvez utiliser"
                    " `image_medium_url` qui est toujours disponible pour les images"
    )

    blur_hash: Optional[str] = Field(
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

    @field_validator("thumbnail_url")
    @classmethod
    def format_public_url(cls, v: Optional[str]) -> Optional[str]:
        return MediaReadStorage.generate_read_public_asset(v)


class ReadPost(BaseModel):
    """Schéma de lecture complète d'un post (avec ses médias)."""

    id: UUID = Field(description="Id du post")
    post_type: PostType
    author_id: UUID
    content: Optional[str] = Field(None, description="Le contenu textuel du post, peut être null si le post est uniquement composé de médias.")
    medias: list[PostMediaSchema] = Field(
        default_factory=list,
        description="Liste des médias attachés au post.",
    )
    club_id: Optional[UUID] = Field(None, description="Id du club du post")
    event_id: Optional[UUID] = Field(None, description="Id du event du post")
    target_classe_id: Optional[UUID] = Field(None, description="Id de la classe auquelle le post est restreint")
    academic_year_id: Optional[UUID] = Field(None, description="Id de l'année académique à laquelle le post est restreint")


    like_count: int = Field(description="Le nombre de lik sur le post")
    comment_count: int = Field(description="Le nombre de comments sur le post")

    is_pinned: bool = Field(description="Indique si le post est épinglé, pour l'instant on prends pas çà en compte")

    created_at: datetime = Field(description="La date de création du post")
    updated_at: datetime = Field(description="La date de dernierer modif du post")

    author_info: PostAuthorSchema = Field(description="Informations sur l'auteur du post : nom, prénom..")

    club_info: Optional[PostClubSchema] = Field(
        default=None,
        description="Informations sur le club lié au post, si applicable, sinon null"
    )

    event_info: Optional[PostEventSchema] = Field(
        default=None,
        description="Informations sur l'événement lié au post, si applicable, sinon null"
    )

    target_classe_info: Optional[PostClasseSchema] = Field(
        default=None,
        description="Infos sur la classe à laquelle le post est restreint, si applicable, sinon null",
    )


    class Config:
        from_attributes = True

ReadPost.model_rebuild()


class ReadPostList(BaseModel):
    """Schéma de réponse paginée pour un feed de posts (cursor-based pagination).
    """

    items: list[ReadPost] = Field(description="Posts de la page courante.")
    next_cursor: Optional[str] = Field(
        default=None,
        description="Curseur opaque à renvoyer pour obtenir la page suivante. NULL si dernière page.",
    )
    has_more: bool = Field(description="Indique s'il existe encore d'autres post, si c'est false c'est terminéééé")


# Réponses API enveloppées dans ApiBaseResponsez

class PostInfos(ApiBaseResponse):
    """Réponse API pour un post unique."""

    result: Optional[ReadPost] = Field(default=None, description="Données du post.")


class PostListInfos(ApiBaseResponse):
    """Réponse API pour un feed paginé de posts."""

    result: Optional[ReadPostList] = Field(default=None,description="Page de posts avec curseur de pagination.")