from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, ForeignKey, func, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin

# Noms des contraintes
FK_VIEWED_POST_USER = "fk_viewed_post_user"
FK_VIEWED_POST_POSTS = "fk_viewed_post_posts"
IDX_VIEWED_AT = "viewed_at_index"
PK_VIEWED_POST = "pk_viewed_post"


class PostViews(Base, IntegrityMapperMixin):
    """Vu des posts"""

    __tablename__ = "post_views"

    # Attributs
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE", name=FK_VIEWED_POST_USER), nullable=False)
    post_id: Mapped[UUID] = mapped_column(ForeignKey("posts.id", ondelete="CASCADE", name=FK_VIEWED_POST_POSTS), nullable=False)

    # Timestamps
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False, init=False)

    # Index
    __table_args__ = (
        Index(IDX_VIEWED_AT, "viewed_at"),
        PrimaryKeyConstraint("post_id", "user_id", name=PK_VIEWED_POST)
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="viewed_posts", uselist=False, init=False)
    post: Mapped["Post"] = relationship("Post", foreign_keys=[post_id], back_populates="views", uselist=False, init=False)
