"""
Modèle pour la table registration_jeton.
Jetons d'inscription pré-générés pour les étudiants.
"""
import uuid
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum as SQLEnum, Index, String, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums import ExecutiveRoleType, UserRole, SexeType

# Noms des contraintes
UQ_REGISTRATION_JETON_JETON = "uq_registration_jeton_jeton"
IDX_REGISTRATION_JETON_JETON = "idx_registration_jeton_jeton"
IDX_REGISTRATION_JETON_UNUSED = "idx_registration_jeton_unused"
IDX_REGISTRATION_JETON_CLASSE = "idx_registration_jeton_classe"
FK_JETON_CLASSE = "fk_registration_jeton_classe"
UQ_USERS_EMAIL = "uq_registration_jeton_email"

class RegistrationJeton(Base, IntegrityMapperMixin):
    """Jetons pré-générés pour l'inscription des étudiants."""

    # TODO: Avant de passer en Prod Ajouter une logique robuste pour controoler tout (regenération, expiration, etc.) et éviter les problèmes d'intégrité (ex: jetons utilisés plusieurs fois, jetons associés à des classes supprimées, etc.)
    __tablename__ = "registration_jeton"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)
    jeton: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Informations de l'étudiant
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.STUDENT, nullable=False, init=False)
    executive_role: Mapped[Optional[ExecutiveRoleType]] = mapped_column(SQLEnum(ExecutiveRoleType), nullable=True, init=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    sexe: Mapped[SexeType] = mapped_column(SQLEnum(SexeType), nullable=False)

    classe_id: Mapped[UUID] = mapped_column(
        ForeignKey("classe.id", ondelete="SET NULL", name=FK_JETON_CLASSE),
        nullable=True,
        comment="Référence à la classe de l'utilisateur (peut être NULL pour les membres du bureau ou les anciens élèves qui ne sont plus rattachés à une classe active)"
    )

    # Suivi d'utilisation
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False, init=False)

    # Index
    __table_args__ = (
        Index(IDX_REGISTRATION_JETON_JETON, "jeton", postgresql_where=(used_at == None)),
        Index(IDX_REGISTRATION_JETON_UNUSED, "used_at", postgresql_where=(used_at == None)),
        Index(IDX_REGISTRATION_JETON_CLASSE, "classe_id", "added_at"),
        Index(UQ_USERS_EMAIL, "email", unique=True, postgresql_where=(used_at == None)),
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="access_jeton_ref", uselist=True, init=False)
    classe: Mapped[Optional["Classe"]] = relationship("Classe", foreign_keys=[classe_id], back_populates="jetons", uselist=False, init=False)
    # Messages d'erreur
    ERROR_MESSAGES = {
        UQ_REGISTRATION_JETON_JETON: "Ce jeton d'inscription a déjà été utilisé.",
        FK_JETON_CLASSE: "La classe associée au jeton d'inscription n'existe pas.",
    }
    
    
    ## fonctions utilitaire sur la table
    
    ## 1: soft delete
    def soft_delete(self):
        self.used_at = datetime.now(UTC)
