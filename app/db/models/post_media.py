"""
Modèle pour la table post_media.
Médias associés aux posts (images, vidéos).
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, String, ForeignKey, BigInteger, Integer, Boolean, func, CheckConstraint, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums import MediaType

# Noms des contraintes
FK_POST_MEDIA_POST = "fk_post_media_post"
CHK_POST_MEDIA_FILE_SIZE = "chk_post_media_file_size"
CHK_POST_MEDIA_DIMENSIONS = "chk_post_media_dimensions"
CHK_POST_MEDIA_DURATION = "chk_post_media_duration"
CHK_POST_MEDIA_DISPLAY_ORDER = "chk_post_media_display_order"
IDX_POST_MEDIA_POST_ID = "idx_post_media_post_id"
IDX_POST_MEDIA_IS_PROCESSED = "idx_post_media_is_processed"
IDX_POST_MEDIA_DELETED_AT = "idx_post_media_deleted_at"


class PostMedia(Base, IntegrityMapperMixin):
    """Médias associés aux posts (images, vidéos)."""

    __tablename__ = "post_media"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)
    post_id: Mapped[UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE", name=FK_POST_MEDIA_POST), nullable=False)

    # Détails du média
    media_type: Mapped[MediaType] = mapped_column(SQLEnum(MediaType), nullable=False)
    media_url: Mapped[str] = mapped_column(String(500), nullable=False)
    blur_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stored_bucket_name: Mapped[str] = mapped_column(String(255), nullable=False)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Métadonnées
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Ordre d'affichage
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, init=False)

    # Processing status
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, init=False)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None, init=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False, init=False)

    # Index
    __table_args__ = (
        Index(IDX_POST_MEDIA_POST_ID, "post_id", "display_order", postgresql_where=(deleted_at == None)),
        Index(IDX_POST_MEDIA_IS_PROCESSED, "is_processed", postgresql_where=(deleted_at == None) & (is_processed == False)),
        Index(IDX_POST_MEDIA_DELETED_AT, "deleted_at"),
        CheckConstraint("file_size IS NULL OR file_size > 0", name=CHK_POST_MEDIA_FILE_SIZE),
        CheckConstraint("(width IS NULL AND height IS NULL) OR (width > 0 AND height > 0)", name=CHK_POST_MEDIA_DIMENSIONS),
        CheckConstraint("(media_type = 'VIDEO' AND (duration IS NULL OR duration > 0)) OR (media_type = 'IMAGE' AND duration IS NULL)", name=CHK_POST_MEDIA_DURATION),
        CheckConstraint("display_order >= 0", name=CHK_POST_MEDIA_DISPLAY_ORDER),
    )

    # Relationships
    post: Mapped["Post"] = relationship("Post", lazy="noload", foreign_keys=[post_id], back_populates="media", uselist=False, init=False)

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_POST_MEDIA_POST: "Le post spécifié n'existe pas.",
        CHK_POST_MEDIA_FILE_SIZE: "La taille du fichier doit être supérieure à 0.",
        CHK_POST_MEDIA_DIMENSIONS: "Les dimensions (largeur/hauteur) doivent être supérieures à 0.",
        CHK_POST_MEDIA_DURATION: "La durée (pour vidéos) doit être supérieure à 0.",
        CHK_POST_MEDIA_DISPLAY_ORDER: "L'ordre d'affichage ne peut pas être négatif.",
    }
