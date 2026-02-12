"""
Modèle pour la table moderation_logs.
Logs des actions de modération.
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, Text, ForeignKey, JSON, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums import ModerationActionType, ModerationTargetType

# Noms des contraintes
FK_MODERATION_LOGS_MODERATOR = "fk_moderation_logs_moderator"
IDX_MODERATION_LOGS_MODERATOR = "idx_moderation_logs_moderator"
IDX_MODERATION_LOGS_TARGET = "idx_moderation_logs_target"
IDX_MODERATION_LOGS_CREATED_AT = "idx_moderation_logs_created_at"


class ModerationLog(Base, IntegrityMapperMixin):
    """Historique des actions de modération."""

    __tablename__ = "moderation_logs"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    moderator_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE", name=FK_MODERATION_LOGS_MODERATOR), nullable=False)

    # Action et cible
    action: Mapped[ModerationActionType] = mapped_column(SQLEnum(ModerationActionType), nullable=False)
    target_type: Mapped[ModerationTargetType] = mapped_column(SQLEnum(ModerationTargetType), nullable=False)
    target_id: Mapped[UUID] = mapped_column(nullable=False)

    # Détails
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    moderation_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)

    # Index
    __table_args__ = (
        Index(IDX_MODERATION_LOGS_MODERATOR, "moderator_id", "created_at"),
        Index(IDX_MODERATION_LOGS_TARGET, "target_type", "target_id", "created_at"),
        Index(IDX_MODERATION_LOGS_CREATED_AT, "created_at"),
    )

    # Relationships
    moderator: Mapped["User"] = relationship("User", foreign_keys=[moderator_id], back_populates="moderation_logs", uselist=False)

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_MODERATION_LOGS_MODERATOR: "Le modérateur spécifié n'existe pas.",
    }
