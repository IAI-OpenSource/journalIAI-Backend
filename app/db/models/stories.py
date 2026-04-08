"""
Modèle pour la table stories.
Stories sur la plateforme - optimisé pour cursor-based pagination.
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, ForeignKey, Integer, func, String, BigInteger, BOOLEAN
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums import MediaType

# Noms des contraintes
FK_STORIES_AUTHOR = "fk_stories_author"
FK_STORIES_CLUB = "fk_stories_club"
FK_STORIES_CLASSE = "fk_stories_classe"
FK_STORIES_GROUP = "fk_stories_group"
IDX_STORIES_FEED_PAGINATION = "idx_stories_feed_pagination"
IDX_STORIES_BY_AUTHOR = "idx_stories_by_author"
IDX_STORIES_BY_CLUB = "idx_stories_by_club"



class Story(Base, IntegrityMapperMixin):
    """Stories sur la plateforme - optimisé pour cursor-based pagination."""

    __tablename__ = "stories"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE", name=FK_STORIES_AUTHOR), nullable=False)

    club_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("clubs.id", ondelete="SET NULL", name=FK_STORIES_CLUB), nullable=True)

    target_classe_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("classe.id", ondelete="SET NULL", name=FK_STORIES_CLASSE),
        nullable=True,
        comment="Si la story est ciblée vers une classe spécifique (ex: annonce pour la promo 2023), sinon NULL pour une story générale."
    )

    media_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="URL MinIO du média associé à la story (image, vidéo, etc.)"
    )

    media_type: Mapped[MediaType] = mapped_column(
        SQLEnum(MediaType),
        nullable=False,
        comment="Type du média (image, vidéo, etc.) - utilisé pour le rendu côté client"
    )

    thumbnail_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="URL MinIO de la miniature du média (pour les vidéos ou les images très lourdes) - peut être NULL pour les images légères"
    )

    legend: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Légende optionnelle pour la story, affichée sous le média"
    )

    group_id: Mapped[UUID] = mapped_column(
        ForeignKey("story_groups.id", ondelete="CASCADE", name=FK_STORIES_GROUP),
        nullable=False
    )



    # Métadonnées
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Soft delete
    # Pas pour le moment
    # deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps (CRUCIAL pour cursor pagination)
    is_expired: Mapped[bool] = mapped_column(BOOLEAN, default=False, nullable=False, init=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False, init=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="Date et heure d'expiration de la story (généralement 24h après la création)")

    __table_args__ = (
        Index(IDX_STORIES_FEED_PAGINATION, "created_at", "id", postgresql_where=(is_expired == False)),
        Index(IDX_STORIES_BY_AUTHOR, "author_id", "created_at", "id", postgresql_where=(is_expired == False)),
        Index(IDX_STORIES_BY_CLUB, "club_id", "created_at", "id", postgresql_where=(is_expired == False) & (club_id != None)),
    )

    # Relationships*
    views: Mapped[list["StoryViews"]] = relationship("StoryViews", back_populates="story", uselist=True, init=False)
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], back_populates="stories", uselist=False, init=False)
    club: Mapped[Optional["Club"]] = relationship("Club", foreign_keys=[club_id], back_populates="stories", uselist=False, init=False)
    classe: Mapped[Optional["Classe"]] = relationship("Classe", foreign_keys=[target_classe_id], back_populates="stories", uselist=False, init=False)
    group: Mapped["StoryGroups"] = relationship("StoryGroups", back_populates="stories", uselist=False, init=False)
    # Messages d'erreur d'intégrité spécifiques au modèle Post
    ERROR_MESSAGES = {
        FK_STORIES_AUTHOR: "L'auteur spécifié n'existe pas.",
        FK_STORIES_CLUB: "Le club spécifié n'existe pas.",
        FK_STORIES_CLASSE: "La classe spécifiée n'existe pas.",
        FK_STORIES_GROUP: "Le groupe de stories spécifié n'existe pas."
    }

