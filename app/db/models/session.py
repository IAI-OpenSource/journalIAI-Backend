"""
Modèle pour la table sessions.
Sessions utilisateurs (pour gestion de l'authentification).
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text, ForeignKey, func, CheckConstraint
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin

# Noms des contraintes
FK_SESSIONS_USER = "fk_sessions_user"
UQ_SESSIONS_REF_TOKEN_HASH = "uq_sessions_ref_token_hash"
CHK_SESSIONS_EXPIRES_AFTER_CREATION = "chk_sessions_expires_after_creation"
IDX_SESSIONS_USER_ID = "idx_sessions_user_id"
IDX_SESSIONS_REF_TOKEN_HASH = "idx_sessions_ref_token_hash"
IDX_SESSIONS_EXPIRES_AT = "idx_sessions_expires_at"



class Session(Base, IntegrityMapperMixin):
    """Sessions utilisateurs (authentification)."""

    __tablename__ = "sessions"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE", name=FK_SESSIONS_USER), nullable=False)

    # Détails de session
    refresh_token_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    # Métadonnées
    ip_address: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Index
    __table_args__ = (
        Index(IDX_SESSIONS_USER_ID, "user_id", "last_activity_at"),
        Index(IDX_SESSIONS_REF_TOKEN_HASH, "refresh_token_hash"),
        Index(IDX_SESSIONS_EXPIRES_AT, "expires_at"),
        CheckConstraint("expires_at > created_at", name=CHK_SESSIONS_EXPIRES_AFTER_CREATION),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="sessions", uselist=False)

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_SESSIONS_USER: "L'utilisateur spécifié n'existe pas.",
        UQ_SESSIONS_REF_TOKEN_HASH: "Ce jeton est déjà utilisé par une autre session.",
        CHK_SESSIONS_EXPIRES_AFTER_CREATION: "La date d'expiration doit être après la création.",
    }
