from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, ForeignKey, func, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin

# Noms des contraintes
FK_VIEWED_STORIES_USER = "fk_viewed_story_user"
FK_VIEWED_STORIES_STORY = "fk_viewed_story_story"
IDX_VIEWED_AT = "viewed_at_story_index"
PK_STORY_VIEWS = "pk_story_views"
IDX_STORY_VIEWS_FEED_PAGINATION = "idx_story_view_feed_pagination"

class StoryViews(Base, IntegrityMapperMixin):
    """Vu des stories"""

    __tablename__ = "story_views"

    # Attributs
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE", name=FK_VIEWED_STORIES_USER), nullable=False)
    story_id: Mapped[UUID] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE", name=FK_VIEWED_STORIES_STORY), nullable=False)

    # Timestamps
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False, init=False)

    # Index
    __table_args__ = (
        Index(IDX_VIEWED_AT, "viewed_at"),
        PrimaryKeyConstraint("story_id", "user_id", name=PK_STORY_VIEWS),
        Index(IDX_STORY_VIEWS_FEED_PAGINATION, "story_id", "viewed_at")
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="viewed_stories", uselist=False, init=False)
    story: Mapped["Story"] = relationship("Story", foreign_keys=[story_id], back_populates="views", uselist=False, init=False)

    ERROR_MESSAGES = {
        PK_STORY_VIEWS: "Un utilisateur ne peut voir une même story qu'une seule fois.",
        FK_VIEWED_STORIES_STORY: "La story associée à une vue doit exister.",
        FK_VIEWED_STORIES_USER: "L'utilisateur associé à une vue doit exister.",
    }
