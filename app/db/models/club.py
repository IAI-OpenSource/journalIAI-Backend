"""
Modèle pour la table clubs.
Clubs et associations de l'université.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Boolean, Integer, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin

# Noms des contraintes
UQ_CLUBS_SLUG = "uq_clubs_slug"
CHK_CLUBS_MEMBER_COUNT = "chk_clubs_member_count"
IDX_CLUBS_CREATED_AT_ID = "idx_clubs_created_at_id"
IDX_CLUBS_SLUG = "idx_clubs_slug"
IDX_CLUBS_IS_ACTIVE = "idx_clubs_is_active"
IDX_CLUBS_DELETED_AT = "idx_clubs_deleted_at"


class Club(Base, IntegrityMapperMixin):
    """Clubs et associations universitaires."""

    __tablename__ = "clubs"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cover_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Métadonnées
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    member_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Index
    __table_args__ = (
        Index(IDX_CLUBS_CREATED_AT_ID, "created_at", "id", postgresql_where=(deleted_at == None)),
        Index(IDX_CLUBS_SLUG, "slug", postgresql_where=(deleted_at == None)),
        Index(IDX_CLUBS_IS_ACTIVE, "is_active", postgresql_where=(deleted_at == None) & (is_active == True)),
        Index(IDX_CLUBS_DELETED_AT, "deleted_at", postgresql_where=(deleted_at != None)),
        CheckConstraint("member_count >= 0", name=CHK_CLUBS_MEMBER_COUNT),
    )

    # Relationships
    members: Mapped[list["ClubMember"]] = relationship("ClubMember", back_populates="club", cascade="all, delete-orphan", uselist=True)
    posts: Mapped[list["Post"]] = relationship("Post", foreign_keys="Post.club_id", back_populates="club", cascade="all, delete-orphan", uselist=True)
    events: Mapped[list["Event"]] = relationship("Event", foreign_keys="Event.organizer_club_id", back_populates="organizer_club", cascade="all, delete-orphan", uselist=True)

    # Messages d'erreur
    ERROR_MESSAGES = {
        UQ_CLUBS_SLUG: "Ce slug de club est déjà utilisé.",
        CHK_CLUBS_MEMBER_COUNT: "Le nombre de membres ne peut pas être négatif.",
    }
