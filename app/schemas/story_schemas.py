from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.enums import MediaType, StoryGroupsType, UserRole, ExecutiveRoleType
from app.schemas import ApiBaseResponse
from app.schemas.post_upload_schemas import FileToUploadSchema


class CreateStory(BaseModel):
    """Schéma de validation pour la création d'une story"""

    legend: Optional[str] = Field(
        default=None,
        description="Légende de la story, un texte court qui accompagne le média et qui sera affiché sous celui-ci,"
                    " max 200 caractères",
        max_length=200
    )

    club_id: Optional[UUID] = Field(None, description="L'ID du club auquel la story est associée, si applicable")

    only_for_a_class: Optional[bool] = Field(
        default=None,
        description="Indique si la story doit etre limité seulement aux étudiants d'une classe précise, si `true` "
                    "la story sera visible uniquement par eux sinon la story sera visible pour tous les étudiants de "
                    "l'école. CET ATTRIBUT NE PEUT ETRE MIS A `true` QUE POUR LES DELEGUES DES SALLES, SI LE USER"
                    " N'EST PAS DELEGUE D'UNE SALLE LA REQUETE RENVERRA UNE BELLE `ERREUR 404`"
    )

    file_info: FileToUploadSchema = Field(
        ...,
        description="Les informations du fichier à uploader pour la story, incluant son nom, sa taille et son type de"
                    " média"
    )


# Schémas de lecture pour le feed de stories

class StoryAuthorSchema(BaseModel):
    """Schéma pour les infos de l'auteur d'une story."""

    id: UUID
    username: str
    first_name: str
    last_name: str
    avatar_url: Optional[str] = Field(
        default=None,
        description="URL de la photo de profil de l'auteur, si disponible.",
    )
    role: UserRole = Field(
        description="Le rôle de l'auteur de la story."
    )
    executive_role: Optional[ExecutiveRoleType] = Field(
        default=None,
        description="Le rôle exécutif pour les membres du bureau exécutif, présent seulement si role est EXECUTIVE_MEMBER.",
    )

    class Config:
        from_attributes = True


class StoryClubSchema(BaseModel):
    """Infos du club lié au groupe de stories (si applicable)."""

    id: UUID
    name: str
    slug: str
    logo_url: Optional[str] = Field(
        default=None,
        description="URL du logo du club, si disponible, à afficher à côté du nom du club.",
    )

    class Config:
        from_attributes = True


class StoryClasseSchema(BaseModel):
    """Infos de la classe liée au groupe de stories (si applicable)."""

    id: UUID
    classe_prefix: str = Field(
        description="Préfixe de la classe style TC1, TC2, GLSI_3, etc.."
    )
    classe_suffix: Optional[str] = Field(
        default=None,
        description="Suffixe optionnel de la classe style A, B, C... "
                    "Donc avec le prefix et suffix tu peut avoir un truc comme TC2-A",
    )

    class Config:
        from_attributes = True


class StoryRead(BaseModel):
    """Schéma de lecture d'une story individuelle."""

    id: UUID
    author_id: UUID
    author: StoryAuthorSchema = Field(
        description="Informations sur l'auteur réel de la story."
    )
    media_type: MediaType = Field(
        description="Type du média (IMAGE ou VIDEO)."
    )
    thumbnail_url: Optional[str] = Field(
        default=None,
        description="URL MinIO de la miniature (pour les vidéos ou images lourdes).",
    )
    hls_master_url: Optional[str] = Field(
        default=None,
        description="URL du master playlist HLS, présent seulement si media_type est VIDEO.",
    )
    image_medium_url: Optional[str] = Field(
        default=None,
        description="URL de l'image en qualité moyenne, présent seulement si media_type est IMAGE.",
    )
    image_high_url: Optional[str] = Field(
        default=None,
        description="URL de l'image en haute qualité, présent seulement si media_type est IMAGE.",
    )
    legend: Optional[str] = Field(
        default=None,
        description="Légende optionnelle de la story.",
    )
    width: Optional[int] = Field(default=None, description="Largeur du média en pixels.")
    height: Optional[int] = Field(default=None, description="Hauteur du média en pixels.")
    duration_seconds: Optional[int] = Field(
        default=None,
        description="Durée en secondes, présent seulement si media_type est VIDEO.",
    )
    already_viewed: bool = Field(
        default=False,
        description="Indique si la story a déjà été vue par l'utilisateur courant.",
    )
    created_at: datetime = Field(description="Date de création de la story.")
    expires_at: datetime = Field(description="Date d'expiration de la story.")

    class Config:
        from_attributes = True


class StoryGroupRead(BaseModel):
    """Schéma pour un groupe de stories (bulle style Instagram)."""

    id: UUID
    group_type: StoryGroupsType = Field(description="Type du groupe (USER_GROUP, CLUB_GROUP, CLASSE_GROUP).")
    author_id: Optional[UUID] = Field(
        default=None,
        description="ID de l'auteur si group_type est USER_GROUP.",
    )
    author: Optional[StoryAuthorSchema] = Field(
        default=None,
        description="Infos de l'auteur, présent si group_type est USER_GROUP.",
    )
    club_id: Optional[UUID] = Field(
        default=None,
        description="ID du club si group_type est CLUB_GROUP.",
    )
    club_info: Optional[StoryClubSchema] = Field(
        default=None,
        description="Infos du club, présent seulement si group_type est CLUB_GROUP.",
    )
    target_classe_id: Optional[UUID] = Field(
        default=None,
        description="ID de la classe si group_type est CLASSE_GROUP.",
    )
    target_classe_info: Optional[StoryClasseSchema] = Field(
        default=None,
        description="Infos de la classe, présent seulement si group_type est CLASSE_GROUP.",
    )
    stories: List[StoryRead] = Field(
        description="Liste des stories du groupe, triées par created_at DESC.",
    )
    stories_count: int = Field(
        description="Nombre total de stories dans ce groupe.",
    )
    viewed_index_in_group: List[int] = Field(
        default_factory=list,
        description="Liste des index des stories déjà vues par l'utilisateur courant dans ce groupe"
                    " Genre si il y'a 0, 1, 3 çà veut dire que la 1er la 2eme et la 4eme story est déja vue par l'utilisateur courant"
                    ", la liste peut etre vide, dans ce cas aucune story n'est vue dans le groupe",
    )
    updated_at: datetime = Field(description="Date de dernière mise à jour du groupe.")
    expires_at: datetime = Field(description="Date d'expiration du groupe.")

    class Config:
        from_attributes = True


class StoryGroupListResult(BaseModel):
    """Résultat paginé du feed de stories."""

    items: List[StoryGroupRead] = Field(description="Groupes de stories pour cette page.")
    next_cursor: Optional[str] = Field(
        default=None,
        description="Curseur opaque pour la page suivante, None si pas de page suivante.",
    )
    has_more: bool = Field(description="Indique s'il y a d'autres pages après celle-ci.")

    class Config:
        from_attributes = True


class StoryGroupListRead(ApiBaseResponse):
    """Schéma pour la réponse paginée du feed de stories."""

    result: Optional[StoryGroupListResult] = Field(
        default=None,
        description="Présent seulement si la récupération du feed a réussi.",
    )


class CreateStoryView(BaseModel):
    """Schéma pour enregistrer les vues de stories."""

    story_ids: List[UUID] = Field(
        description="IDs des stories vues, regroupées en batch pour optimiser les requêtes."
    )


