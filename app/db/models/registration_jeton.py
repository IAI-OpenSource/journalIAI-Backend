"""
Modèle pour la table registration_jeton.
Jetons d'inscription pré-générés pour les étudiants.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum as SQLEnum, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums import UserRole, ClasseType

# Noms des contraintes
UQ_REGISTRATION_JETON_JETON = "uq_registration_jeton_jeton"
IDX_REGISTRATION_JETON_JETON = "idx_registration_jeton_jeton"
IDX_REGISTRATION_JETON_UNUSED = "idx_registration_jeton_unused"
IDX_REGISTRATION_JETON_CLASSE = "idx_registration_jeton_classe"


class RegistrationJeton(Base, IntegrityMapperMixin):
    """Jetons pré-générés pour l'inscription des étudiants."""

    __tablename__ = "registration_jeton"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True)
    jeton: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Informations de l'étudiant
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.STUDENT, nullable=False)
    classe: Mapped[ClasseType] = mapped_column(SQLEnum(ClasseType), nullable=False)

    # Suivi d'utilisation
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)

    # Index
    __table_args__ = (
        Index(IDX_REGISTRATION_JETON_JETON, "jeton", postgresql_where=(used_at == None)),
        Index(IDX_REGISTRATION_JETON_UNUSED, "used_at", postgresql_where=(used_at == None)),
        Index(IDX_REGISTRATION_JETON_CLASSE, "classe", "added_at"),
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", foreign_keys="User.access_jeton", back_populates="access_jeton_ref", uselist=True)

    # Messages d'erreur
    ERROR_MESSAGES = {
        UQ_REGISTRATION_JETON_JETON: "Ce jeton d'inscription a déjà été utilisé.",
    }
