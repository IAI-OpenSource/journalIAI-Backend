"""
Modèle pour la table comments.
Commentaires et réponses (structure récursive).
Optimisé pour cursor-based pagination.
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, Text, ForeignKey, Integer, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin

# Noms des contraintes
FK_COMMENTS_POST = "fk_comments_post"
FK_COMMENTS_AUTHOR = "fk_comments_author"
FK_COMMENTS_PARENT = "fk_comments_parent"
CHK_COMMENTS_CONTENT_LENGTH = "chk_comments_content_length"
CHK_COMMENTS_METRICS = "chk_comments_metrics"
CHK_COMMENTS_NO_SELF_PARENT = "chk_comments_no_self_parent"
IDX_COMMENTS_POST_ROOT = "idx_comments_post_root"
IDX_COMMENTS_REPLIES = "idx_comments_replies"
IDX_COMMENTS_BY_AUTHOR = "idx_comments_by_author"
IDX_COMMENTS_POST_COUNT = "idx_comments_post_count"
IDX_COMMENTS_DELETED_AT = "idx_comments_deleted_at"


class Comment(Base, IntegrityMapperMixin):
    """Commentaires et réponses (structure récursive)."""

    __tablename__ = "comments"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    post_id: Mapped[UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE", name=FK_COMMENTS_POST), nullable=False)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE", name=FK_COMMENTS_AUTHOR), nullable=False)

    # Hiérarchie (récursif pour réponses)
    parent_comment_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE", name=FK_COMMENTS_PARENT),
        nullable=True
    )

    # Contenu
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Métriques
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps (CRUCIAL pour cursor pagination)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Index
    __table_args__ = (
        Index(IDX_COMMENTS_POST_ROOT, "post_id", "created_at", "id", postgresql_where=(deleted_at == None) & (parent_comment_id == None)),
        Index(IDX_COMMENTS_REPLIES, "parent_comment_id", "created_at", "id", postgresql_where=(deleted_at == None) & (parent_comment_id != None)),
        Index(IDX_COMMENTS_BY_AUTHOR, "author_id", "created_at", "id", postgresql_where=(deleted_at == None)),
        Index(IDX_COMMENTS_POST_COUNT, "post_id", postgresql_where=(deleted_at == None)),
        Index(IDX_COMMENTS_DELETED_AT, "deleted_at", postgresql_where=(deleted_at != None)),
        CheckConstraint("LENGTH(content) <= 2000", name=CHK_COMMENTS_CONTENT_LENGTH),
        CheckConstraint("like_count >= 0 AND reply_count >= 0", name=CHK_COMMENTS_METRICS),
        CheckConstraint("parent_comment_id IS NULL OR parent_comment_id != id", name=CHK_COMMENTS_NO_SELF_PARENT),
    )

    # Relationships
    post: Mapped["Post"] = relationship("Post", foreign_keys=[post_id], back_populates="comments", uselist=False)
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], back_populates="comments", uselist=False)
    parent_comment: Mapped[Optional["Comment"]] = relationship("Comment", remote_side=[id], foreign_keys=[parent_comment_id], back_populates="replies", uselist=False)
    replies: Mapped[list["Comment"]] = relationship("Comment", remote_side=[parent_comment_id], back_populates="parent_comment", cascade="all, delete-orphan", uselist=True)
    likes: Mapped[list["Like"]] = relationship("Like", foreign_keys="Like.comment_id", back_populates="comment", cascade="all, delete-orphan", uselist=True)

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_COMMENTS_POST: "Le post spécifié n'existe pas.",
        FK_COMMENTS_AUTHOR: "L'auteur spécifié n'existe pas.",
        FK_COMMENTS_PARENT: "Le commentaire parent spécifié n'existe pas.",
        CHK_COMMENTS_CONTENT_LENGTH: "Le contenu du commentaire ne peut pas dépasser 2000 caractères.",
        CHK_COMMENTS_METRICS: "Les métriques (likes, réponses) ne peuvent pas être négatives.",
        CHK_COMMENTS_NO_SELF_PARENT: "Un commentaire ne peut pas être son propre parent.",
    }
