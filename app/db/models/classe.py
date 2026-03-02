"""
Modèle pour la table classe.
Les classes des étudiants (ex: TC1 A, TC2 C....) - utilisées pour organiser les étudiants par classe et faciliter la gestion des permissions et des accès aux contenus spécifiques à chaque classe.
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, func, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLEnum

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums import ClasseType

# Noms des contraintes
IDX_CLASSE_CREATED_AT_ID = "idx_classe_created_at_id"
UQ_PREFIX_SUFFIX_ACADEMIC_YEAR = "uq_prefix_suffix_academic_year"
FK_CLASSE_ACADEMIC_YEAR = "fk_classe_academic_year"

CHK_EFFECTIF_VALID = "chk_effectif_valid"

IDX_USERS_DELETED_AT = "idx_users_deleted_at"


class Classe(Base, IntegrityMapperMixin):
    """Utilisateurs de la plateforme (étudiants, modérateurs, etc.)."""

    __tablename__ = "classe"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)
    classe_prefix: Mapped[ClasseType] = mapped_column(SQLEnum(ClasseType), nullable=False)
    classe_suffix: Mapped[str] = mapped_column(String(1), nullable=True)

    # Dénormalisation de l'effectif pour éviter les calculs coûteux à chaque requête. L'effectif est mis à
    # jour via des triggers ou des méthodes spécifiques lors de l'ajout/suppression d'étudiants dans la classe.
    effectif: Mapped[int] = mapped_column(default=0, nullable=False, init=False)


    # Métadonnées
    academic_year_id: Mapped[UUID] = mapped_column(
        ForeignKey("academic_year.id", ondelete="CASCADE", name=FK_CLASSE_ACADEMIC_YEAR),
        nullable=False,
        comment="Référence de l'année académique à laquelle cette classe appartient"
    )

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
        Index(IDX_CLASSE_CREATED_AT_ID, "created_at", "id", postgresql_where=(deleted_at == None)),
        UniqueConstraint("classe_prefix", "classe_suffix", "academic_year_id", name=UQ_PREFIX_SUFFIX_ACADEMIC_YEAR, postgresql_where=(deleted_at == None)),
        CheckConstraint("effectif >= 0", name=CHK_EFFECTIF_VALID)
    )

    # Relationships
    posts: Mapped[list["Post"]] = relationship("Post", foreign_keys="Post.target_classe_id", back_populates="classe", cascade="all, delete-orphan", uselist=True, init=False)
    academic_year: Mapped["AcademicYear"] = relationship("AcademicYear", back_populates="classes", uselist=False, init=False)
    students: Mapped[list["User"]] = relationship("User", back_populates="classe", cascade="all, delete-orphan", uselist=True, init=False)
    jetons: Mapped[list["RegistrationJeton"]] = relationship("RegistrationJeton", back_populates="classe", cascade="all, delete-orphan", uselist=True, init=False)
    stories: Mapped[list["Story"]] = relationship("Story", back_populates="classe", cascade="all, delete-orphan", uselist=True, init=False)

    # Messages d'erreur
    ERROR_MESSAGES = {
        UQ_PREFIX_SUFFIX_ACADEMIC_YEAR: "La combinaison de préfixe, suffixe et année académique doit être unique.",
        CHK_EFFECTIF_VALID: "L'effectif doit être un nombre entier positif ou nul.",
        FK_CLASSE_ACADEMIC_YEAR: "L'année académique associée à la classe doit exister."
    }
