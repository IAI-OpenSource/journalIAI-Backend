"""
Modèle pour la table events.
Événements universitaires.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, String, ForeignKey, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLEnum

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums import EventStatus

# Noms des contraintes
FK_EVENTS_ORGANIZER_CLUB = "fk_events_organizer_club"
FK_EVENTS_PARENT_EVENT = "fk_events_parent_event"
UQ_EVENTS_SLUG = "uq_events_slug"
CHK_EVENTS_DATES = "chk_events_dates"
IDX_EVENTS_CREATED_AT_ID = "idx_events_created_at_id"
IDX_EVENTS_START_DATE = "idx_events_start_date"
IDX_EVENTS_STATUS = "idx_events_status"
IDX_EVENTS_ORGANIZER_CLUB_ID = "idx_events_organizer_club_id"
IDX_EVENTS_SLUG = "idx_events_slug"
IDX_EVENTS_DELETED_AT = "idx_events_deleted_at"


class Event(Base, IntegrityMapperMixin):
    """Événements universitaires."""

    __tablename__ = "events"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Détails de l'événement
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Hiérarchie (récursif pour sous-événements)
    parent_event_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE", name=FK_EVENTS_PARENT_EVENT),
        nullable=True
    )

    # Médias
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Organisation
    organizer_club_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("clubs.id", ondelete="SET NULL", name=FK_EVENTS_ORGANIZER_CLUB),
        nullable=True
    )
    status: Mapped[EventStatus] = mapped_column(SQLEnum(EventStatus), default=EventStatus.DRAFT, nullable=False)

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
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Index
    __table_args__ = (
        Index(IDX_EVENTS_CREATED_AT_ID, "created_at", "id", postgresql_where=(deleted_at == None)),
        Index(IDX_EVENTS_START_DATE, "start_date", postgresql_where=(deleted_at == None)),
        Index(IDX_EVENTS_STATUS, "status", postgresql_where=(deleted_at == None)),
        Index(IDX_EVENTS_ORGANIZER_CLUB_ID, "organizer_club_id", postgresql_where=(deleted_at == None) & (organizer_club_id != None)),
        Index(IDX_EVENTS_SLUG, "slug", postgresql_where=(deleted_at == None)),
        Index(IDX_EVENTS_DELETED_AT, "deleted_at", postgresql_where=(deleted_at != None)),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name=CHK_EVENTS_DATES),
    )

    # Relationships
    organizer_club: Mapped[Optional["Club"]] = relationship("Club", foreign_keys=[organizer_club_id], back_populates="events", uselist=False)
    parent_event: Mapped[Optional["Event"]] = relationship("Event", remote_side=[id], foreign_keys=[parent_event_id], back_populates="child_events", uselist=False)
    child_events: Mapped[list["Event"]] = relationship("Event", remote_side=[parent_event_id], back_populates="parent_event", cascade="all, delete-orphan", uselist=True)
    posts: Mapped[list["Post"]] = relationship("Post", foreign_keys="Post.event_id", back_populates="event", cascade="all, delete-orphan", uselist=True)

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_EVENTS_ORGANIZER_CLUB: "Le club organisateur spécifié n'existe pas.",
        FK_EVENTS_PARENT_EVENT: "L'événement parent spécifié n'existe pas.",
        UQ_EVENTS_SLUG: "Ce slug d'événement est déjà utilisé.",
        CHK_EVENTS_DATES: "La date de fin doit être après la date de début.",
    }
