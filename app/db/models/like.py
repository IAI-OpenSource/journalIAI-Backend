"""
Modèle pour la table likes.
Système de likes polymorphique (posts et comments).
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin

# Noms des contraintes
FK_LIKES_USER = "fk_likes_user"
FK_LIKES_POST = "fk_likes_post"
FK_LIKES_COMMENT = "fk_likes_comment"
CHK_LIKES_TARGET = "chk_likes_target"
UQ_LIKES_USER_POST = "uq_likes_user_post"
UQ_LIKES_USER_COMMENT = "uq_likes_user_comment"
IDX_LIKES_USER_POST = "idx_likes_user_post"
IDX_LIKES_USER_COMMENT = "idx_likes_user_comment"
IDX_LIKES_POST_ID = "idx_likes_post_id"
IDX_LIKES_COMMENT_ID = "idx_likes_comment_id"
IDX_LIKES_POST_PAGINATION = "idx_likes_post_pagination"
IDX_LIKES_COMMENT_PAGINATION = "idx_likes_comment_pagination"


class Like(Base, IntegrityMapperMixin):
    """Système de likes polymorphique (posts et comments)."""

    __tablename__ = "likes"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE", name=FK_LIKES_USER), nullable=False)
    post_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE", name=FK_LIKES_POST),
        nullable=True
    )
    comment_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE", name=FK_LIKES_COMMENT),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)

    # Index
    __table_args__ = (
        Index(IDX_LIKES_USER_POST, "user_id", "post_id", postgresql_where=(post_id != None)),
        Index(IDX_LIKES_USER_COMMENT, "user_id", "comment_id", postgresql_where=(comment_id != None)),
        Index(IDX_LIKES_POST_ID, "post_id", postgresql_where=(post_id != None)),
        Index(IDX_LIKES_COMMENT_ID, "comment_id", postgresql_where=(comment_id != None)),
        Index(IDX_LIKES_POST_PAGINATION, "post_id", "created_at", "id", postgresql_where=(post_id != None)),
        Index(IDX_LIKES_COMMENT_PAGINATION, "comment_id", "created_at", "id", postgresql_where=(comment_id != None)),
        Index(UQ_LIKES_USER_POST, "user_id", "post_id", unique=True),
        Index(UQ_LIKES_USER_COMMENT, "user_id", "comment_id", unique=True),
        CheckConstraint("(post_id IS NOT NULL AND comment_id IS NULL) OR (post_id IS NULL AND comment_id IS NOT NULL)", name=CHK_LIKES_TARGET),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="likes", uselist=False)
    post: Mapped[Optional["Post"]] = relationship("Post", foreign_keys=[post_id], back_populates="likes", uselist=False)
    comment: Mapped[Optional["Comment"]] = relationship("Comment", foreign_keys=[comment_id], back_populates="likes", uselist=False)

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_LIKES_USER: "L'utilisateur spécifié n'existe pas.",
        FK_LIKES_POST: "Le post spécifié n'existe pas.",
        FK_LIKES_COMMENT: "Le commentaire spécifié n'existe pas.",
        CHK_LIKES_TARGET: "Un like doit cibler soit un post, soit un commentaire.",
        UQ_LIKES_USER_POST: "Cet utilisateur a déjà liké ce post.",
        UQ_LIKES_USER_COMMENT: "Cet utilisateur a déjà liké ce commentaire.",
    }
