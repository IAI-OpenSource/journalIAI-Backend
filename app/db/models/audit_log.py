"""
Modèle pour la table audit_logs.
Logs d'audit pour traçabilité.
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, String, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLEnum
from app.db.base import Base
from app.db.models.enums import TypeActions
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
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", name=FK_AUDIT_LOGS_USER),
        nullable=True
    )

    # Action
    readable_message: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[TypeActions] = mapped_column(SQLEnum(TypeActions), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)

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
