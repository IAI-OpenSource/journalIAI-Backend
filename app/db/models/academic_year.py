"""
Modèle pour la table academic_year.
Les années académiques (ex: 2023-2024) - utilisées pour organiser les événements, clubs, etc. par année scolaire.
"""
import uuid
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Boolean, func, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin


# Noms des contraintes
UQ_ACADEMIC_YEAR_ACTIVE = "uq_academic_year_active"
IDX_ACADEMIC_YEAR_ACTIVE_ID = "idx_academic_year_active_id"
CHK_ACADEMIC_YEAR_DATES = "chk_academic_year_dates"


class AcademicYear(Base, IntegrityMapperMixin):
    """Années académiques (ex: 2023-2024) - utilisées pour organiser les événements, clubs, etc. par année scolaire."""
    __tablename__ = "academic_year"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)
    libelle: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, init=False)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None, init=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False, init=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=True,
        init=False
    )

    # Index
    __table_args__ = (
        Index(IDX_ACADEMIC_YEAR_ACTIVE_ID, "active", "id", postgresql_where=(deleted_at == None)),
        Index(
            UQ_ACADEMIC_YEAR_ACTIVE,
            "active",
            unique=True,
            postgresql_where=(active == True) & (deleted_at == None)
        ),
        CheckConstraint("end_date > start_date", name=CHK_ACADEMIC_YEAR_DATES)
    )

    # Relationships
    classes: Mapped[List["Classe"]] = relationship("Classe", back_populates="academic_year", cascade="all, delete-orphan")
    posts: Mapped[List["Post"]] = relationship("Post", back_populates="academic_year", cascade="all, delete-orphan")

    # Messages d'erreur
    ERROR_MESSAGES = {
        UQ_ACADEMIC_YEAR_ACTIVE: "Il ne peut y avoir qu'une seule année académique active à la fois.",
        CHK_ACADEMIC_YEAR_DATES: "La date de fin doit être postérieure à la date de début.",
    }
