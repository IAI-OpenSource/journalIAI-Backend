"""
Modèle pour la table audit_logs.
Logs d'audit pour traçabilité.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin

# Noms des contraintes
FK_AUDIT_LOGS_USER = "fk_audit_logs_user"
IDX_AUDIT_LOGS_USER_ID = "idx_audit_logs_user_id"
IDX_AUDIT_LOGS_ENTITY = "idx_audit_logs_entity"
IDX_AUDIT_LOGS_CREATED_AT = "idx_audit_logs_created_at"


class AuditLog(Base, IntegrityMapperMixin):
    """Logs d'audit pour traçabilité."""

    __tablename__ = "audit_logs"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", name=FK_AUDIT_LOGS_USER),
        nullable=True
    )

    # Action
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)

    # Données
    old_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Métadonnées
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)

    # Index
    __table_args__ = (
        Index(IDX_AUDIT_LOGS_USER_ID, "user_id", "created_at", postgresql_where=(user_id != None)),
        Index(IDX_AUDIT_LOGS_ENTITY, "entity_type", "entity_id", "created_at"),
        Index(IDX_AUDIT_LOGS_CREATED_AT, "created_at"),
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[user_id], back_populates="audit_logs", uselist=False)

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_AUDIT_LOGS_USER: "L'utilisateur spécifié n'existe pas.",
    }
