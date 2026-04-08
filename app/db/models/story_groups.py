import uuid
from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, DateTime, Index, func
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin

IDX_STORY_GROUPS_FEED = "idx_story_groups_feed"
IDX_STORY_GROUPS_AUTHOR = "idx_story_groups_author"
IDX_STORY_GROUPS_EXPIRATION = "idx_story_groups_expiration"
UQ_AUTHOR_ACTIVE_GROUP = "uq_author_active_group"
FK_STORY_GROUPS_AUTHOR = "fk_story_groups_author"
class StoryGroups(Base, IntegrityMapperMixin):
    """
    Table dénormalisée sciemment pour faciliter la gestion des groupes de stories et leur expiration.
    Un groupe de stories correspond à l'ensemble des stories publiées par un auteur dans une même session
    (ex: un étudiant qui publie 3 stories à la suite, elles appartiennent au même groupe). Cela permet de
    gérer plus facilement l'expiration des stories (toutes les stories d'un groupe expirent en même temps)
    et d'optimiser les requêtes pour le feed (on peut filtrer directement sur les groupes expirés).
    """

    __tablename__ = "story_groups"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)

    author_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name=FK_STORY_GROUPS_AUTHOR),
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        init=False
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False
    )

    is_expired: Mapped[bool] = mapped_column(default=False, nullable=False)

    __table_args__ = (
        Index(
            IDX_STORY_GROUPS_FEED,
            updated_at.desc(), id.desc(),
            postgresql_where=(is_expired == False)
        ),
        Index(
            IDX_STORY_GROUPS_AUTHOR,
            "author_id",
            postgresql_where=(is_expired == False)
        ),
        Index(
            IDX_STORY_GROUPS_EXPIRATION,
            "expires_at",
            postgresql_where=(is_expired == False)
        ),
        Index(
            UQ_AUTHOR_ACTIVE_GROUP,
            "author_id",
            unique=True,
            postgresql_where=(is_expired == False)
        )
    )

    # Relationships
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], back_populates="story_group", uselist=False, init=False)
    stories: Mapped[list["Story"]] = relationship("Story", back_populates="group", uselist=True, init=False)


    ERROR_MESSAGES = {
        UQ_AUTHOR_ACTIVE_GROUP: "L'auteur spécifié a déja un groupe actif",
        FK_STORY_GROUPS_AUTHOR: "L'auteur spécifié n'existe pas."
    }
