"""
Modèle pour la table posts.
Publications sur la plateforme - optimisé pour cursor-based pagination.
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, ForeignKey, Integer, Boolean, Text, func, CheckConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums import PostType

# Noms des contraintes
FK_POSTS_AUTHOR = "fk_posts_author"
FK_POSTS_EVENT = "fk_posts_event"
FK_POSTS_CLUB = "fk_posts_club"
CHK_POSTS_METRICS = "chk_posts_metrics"
CHK_POSTS_CONTENT_REQUIRED = "chk_posts_content_required"
CHK_POSTS_CONTENT_LENGTH = "chk_posts_content_length"
IDX_POSTS_FEED_PAGINATION = "idx_posts_feed_pagination"
IDX_POSTS_PINNED_FEED = "idx_posts_pinned_feed"
IDX_POSTS_BY_AUTHOR = "idx_posts_by_author"
IDX_POSTS_BY_CLUB = "idx_posts_by_club"
IDX_POSTS_BY_EVENT = "idx_posts_by_event"
IDX_POSTS_POPULAR = "idx_posts_popular"
IDX_POSTS_DELETED_AT = "idx_posts_deleted_at"


class Post(Base, IntegrityMapperMixin):
    """Publications sur la plateforme - optimisé pour cursor-based pagination."""

    __tablename__ = "posts"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE", name=FK_POSTS_AUTHOR), nullable=False)
    event_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("events.id", ondelete="SET NULL", name=FK_POSTS_EVENT), nullable=True)
    club_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("clubs.id", ondelete="SET NULL", name=FK_POSTS_CLUB), nullable=True)

    # Contenu
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    post_type: Mapped[PostType] = mapped_column(SQLEnum(PostType), default=PostType.TEXT, nullable=False, init=False)

    # Métriques (dénormalisées pour performance)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, init=False)
    comment_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, init=False)

    # Visibilité
    academic_year_id: Mapped[UUID] = mapped_column(
        ForeignKey("academic_year.id", ondelete="CASCADE"),
        nullable=True,
        comment="Année académique à laquelle ce post est associé. Permet de filtrer les posts par année scolaire, même pour les posts généraux qui ne sont pas liés à un club ou un événement spécifique."
    )

    target_classe_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("classe.id", ondelete="SET NULL"),
        nullable=True,
        comment="Si le post est ciblé vers une classe spécifique (ex: annonce pour la promo 2023), sinon NULL pour un post général."
    )

    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, init=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, init=False)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, init=False)

    # Timestamps (CRUCIAL pour cursor pagination)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False, init=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False, init=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=func.now(), init=False)

    __table_args__ = (
        Index(IDX_POSTS_FEED_PAGINATION, "created_at", "id", postgresql_where=(deleted_at == None) & (is_published == True)),
        Index(IDX_POSTS_PINNED_FEED, "is_pinned", "created_at", "id", postgresql_where=(deleted_at == None) & (is_published == True)),
        Index(IDX_POSTS_BY_AUTHOR, "author_id", "created_at", "id", postgresql_where=(deleted_at == None)),
        Index(IDX_POSTS_BY_CLUB, "club_id", "created_at", "id", postgresql_where=(deleted_at == None) & (club_id != None)),
        Index(IDX_POSTS_BY_EVENT, "event_id", "created_at", "id", postgresql_where=(deleted_at == None) & (event_id != None)),
        Index(IDX_POSTS_POPULAR, "like_count", "created_at", "id", postgresql_where=(deleted_at == None) & (is_published == True)),
        Index(IDX_POSTS_DELETED_AT, "deleted_at", postgresql_where=(deleted_at != None)),
        CheckConstraint("like_count >= 0 AND comment_count >= 0", name=CHK_POSTS_METRICS),
        CheckConstraint("content IS NOT NULL OR post_type != 'TEXT'", name=CHK_POSTS_CONTENT_REQUIRED),
        CheckConstraint("content IS NULL OR LENGTH(content) <= 10000", name=CHK_POSTS_CONTENT_LENGTH),
    )

    # Relationships
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], back_populates="posts", uselist=False, init=False)
    club: Mapped[Optional["Club"]] = relationship("Club", foreign_keys=[club_id], back_populates="posts", uselist=False, init=False)
    event: Mapped[Optional["Event"]] = relationship("Event", foreign_keys=[event_id], back_populates="posts", uselist=False, init=False)
    comments: Mapped[list["Comment"]] = relationship("Comment", back_populates="post", cascade="all, delete-orphan", uselist=True, init=False)
    media: Mapped[list["PostMedia"]] = relationship("PostMedia", back_populates="post", cascade="all, delete-orphan", uselist=True, init=False)
    likes: Mapped[list["Like"]] = relationship("Like", foreign_keys="Like.post_id", back_populates="post", cascade="all, delete-orphan", uselist=True, init=False)
    academic_year: Mapped["AcademicYear"] = relationship("AcademicYear", back_populates="posts", uselist=False, init=False)
    classe: Mapped[Optional["Classe"]] = relationship("Classe", foreign_keys=[target_classe_id], back_populates="posts", uselist=False, init=False)
    views: Mapped[list["PostViews"]] = relationship("PostViews", back_populates="post", cascade="all, delete-orphan", uselist=True, init=False)

    # Messages d'erreur d'intégrité spécifiques au modèle Post
    ERROR_MESSAGES = {
        FK_POSTS_AUTHOR: "L'auteur spécifié n'existe pas.",
        FK_POSTS_EVENT: "L'événement spécifié n'existe pas.",
        FK_POSTS_CLUB: "Le club spécifié n'existe pas.",
    }

