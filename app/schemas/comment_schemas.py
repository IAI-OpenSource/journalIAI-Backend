from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.schemas import ApiBaseResponse


# ── Base ──────────────────────────────────────────────────────────────────────

class CommentBase(BaseModel):
    """
    Modèle de base représentant un commentaire.

    Contient les champs communs utilisés par la création,
    la mise à jour et la lecture des commentaires.
    """
    post_id: UUID = Field(..., description="Identifiant du post associé")
    content: str = Field(..., min_length=1, max_length=2000, description="Contenu du commentaire")
    parent_comment_id: Optional[UUID] = Field(None, description="Identifiant du commentaire parent (pour les réponses)")


# ── Création ──────────────────────────────────────────────────────────────────

class CommentCreate(CommentBase):
    """
    Schéma utilisé pour la création d'un commentaire.

    Hérite de CommentBase.
    """
    pass


# ── Mise à jour ───────────────────────────────────────────────────────────────

class CommentUpdate(BaseModel):
    """
    Schéma utilisé pour la mise à jour partielle ou complète d'un commentaire.

    Seul le contenu est modifiable.
    """
    content: Optional[str] = Field(None, min_length=1, max_length=2000, description="Nouveau contenu du commentaire")


# ── Lecture complète ──────────────────────────────────────────────────────────

class CommentRead(CommentBase):
    """Schéma complet de lecture d'un commentaire."""

    id: UUID = Field(..., description="Identifiant unique du commentaire")
    like_count: int = Field(..., description="Nombre de likes du commentaire")
    reply_count: int = Field(..., description="Nombre de réponses au commentaire")
    deleted_at: Optional[datetime] = Field(None, description="Date de suppression (si supprimé)")
    created_at: datetime = Field(..., description="Date de création du commentaire")
    updated_at: datetime = Field(..., description="Date de dernière mise à jour")

    model_config = {"from_attributes": True}

    def is_deleted(self) -> bool:
        return self.deleted_at is not None


# ── Résumé léger ──────────────────────────────────────────────────────────────

class CommentSummary(BaseModel):
    """
    Schéma léger pour représenter un commentaire dans des listes.

    Contient uniquement les informations essentielles
    afin d'optimiser les performances des requêtes.
    """
    id: UUID = Field(..., description="Identifiant unique du commentaire")
    author_id: UUID = Field(..., description="Identifiant de l'auteur")
    content: str = Field(..., description="Contenu du commentaire")
    like_count: int = Field(..., description="Nombre de likes")
    reply_count: int = Field(..., description="Nombre de réponses")
    created_at: datetime = Field(..., description="Date de création")
    parent_comment_id: Optional[UUID] = Field(None, description="Identifiant du commentaire parent")

    model_config = {"from_attributes": True}


# ── Réponses API ──────────────────────────────────────────────────────────────

class CommentInfo(ApiBaseResponse):
    result: Optional[CommentRead] = Field(None, description="Informations du commentaire")

class SimpleCommentListResponse(BaseModel):
    comments: List[CommentRead] = Field(..., description="Liste des commentaires")

class PaginatedCommentListResponse(SimpleCommentListResponse):
    next_cursor: Optional[UUID] = None

class ApiPaginatedCommentListResponse(ApiBaseResponse):
    result: Optional[PaginatedCommentListResponse] = None

class ApiCommentListResponse(ApiBaseResponse):
    result: Optional[SimpleCommentListResponse] = None


class CommentCountResponse(ApiBaseResponse):
    result: Optional[int] = Field(None, description="Nombre de commentaires du post")
    

class ReplyCountResponse(ApiBaseResponse):
    result: Optional[int] = Field(None, description="Nombre de réponses du commentaire")