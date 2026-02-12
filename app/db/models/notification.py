"""
Modèle pour la table notifications.
Système de notifications.
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, String, Text, ForeignKey, Boolean, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin

# Noms des contraintes
FK_NOTIFICATIONS_USER = "fk_notifications_user"
CHK_NOTIFICATIONS_TITLE_NOT_EMPTY = "chk_notifications_title_not_empty"
CHK_NOTIFICATIONS_MESSAGE_NOT_EMPTY = "chk_notifications_message_not_empty"
CHK_NOTIFICATIONS_READ_AT = "chk_notifications_read_at"
IDX_NOTIFICATIONS_USER_UNREAD = "idx_notifications_user_unread"
IDX_NOTIFICATIONS_USER_PAGINATION = "idx_notifications_user_pagination"
IDX_NOTIFICATIONS_DELETED_AT = "idx_notifications_deleted_at"


class Notification(Base, IntegrityMapperMixin):
    """Système de notifications."""

    __tablename__ = "notifications"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE", name=FK_NOTIFICATIONS_USER), nullable=False)

    # Type et contenu
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Lien vers la ressource
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[UUID]] = mapped_column(nullable=True)

    # État
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Index
    __table_args__ = (
        Index(IDX_NOTIFICATIONS_USER_UNREAD, "user_id", "is_read", "created_at", postgresql_where=(deleted_at == None) & (is_read == False)),
        Index(IDX_NOTIFICATIONS_USER_PAGINATION, "user_id", "created_at", "id", postgresql_where=(deleted_at == None)),
        Index(IDX_NOTIFICATIONS_DELETED_AT, "deleted_at", postgresql_where=(deleted_at != None)),
        CheckConstraint("LENGTH(TRIM(title)) > 0", name=CHK_NOTIFICATIONS_TITLE_NOT_EMPTY),
        CheckConstraint("LENGTH(TRIM(message)) > 0", name=CHK_NOTIFICATIONS_MESSAGE_NOT_EMPTY),
        CheckConstraint("(is_read = FALSE AND read_at IS NULL) OR (is_read = TRUE AND read_at IS NOT NULL)", name=CHK_NOTIFICATIONS_READ_AT),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="notifications", uselist=False)

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_NOTIFICATIONS_USER: "L'utilisateur spécifié n'existe pas.",
        CHK_NOTIFICATIONS_TITLE_NOT_EMPTY: "Le titre ne peut pas être vide.",
        CHK_NOTIFICATIONS_MESSAGE_NOT_EMPTY: "Le message ne peut pas être vide.",
        CHK_NOTIFICATIONS_READ_AT: "La date de lecture doit être définie si le message est marqué comme lu.",
    }
