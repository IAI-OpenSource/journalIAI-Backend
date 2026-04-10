import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import ForeignKey, DateTime, Index, func
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.db.base import Base
from app.db.models.enums import StoryGroupsType
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin
from sqlalchemy import Enum as SQLEnum

IDX_STORY_GROUPS_FEED = "idx_story_groups_feed"
IDX_STORY_GROUPS_AUTHOR = "idx_story_groups_author"
IDX_STORY_GROUPS_EXPIRATION = "idx_story_groups_expiration"
UQ_AUTHOR_ACTIVE_GROUP = "uq_author_active_group"
UQ_CLUB_ACTIVE_GROUP = "uq_club_active_group"
UQ_CLASSE_ACTIVE_GROUP = "uq_clause_active_group"
FK_STORY_GROUPS_AUTHOR = "fk_story_groups_author"
FK_STORIES_CLUB = "fk_stories_club"
FK_STORIES_CLASSE = "fk_stories_classe"
class StoryGroups(Base, IntegrityMapperMixin):
    """
    Table dénormalisée sciemment pour faciliter la gestion des groupes de stories et leur expiration.
    Un groupe de stories correspond à l'ensemble des stories publiées par un auteur dans une même session
    (ex: un étudiant qui publie 3 stories à la suite, elles appartiennent au même groupe). Cela permet de
    gérer plus facilement l'expiration des stories et d'optimiser les requêtes pourle feed
    """

    __tablename__ = "story_groups"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)

    author_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE", name=FK_STORY_GROUPS_AUTHOR),
        nullable=True
    )

    group_type: Mapped[StoryGroupsType] = mapped_column(
        SQLEnum(StoryGroupsType),
        nullable=False
    )

    # Au cas où le groupe de story concerne un club
    club_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("clubs.id", ondelete="CASCADE", name=FK_STORIES_CLUB),
        nullable=True
    )

    # Au cas où le groupe de story concerne une classe
    target_classe_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("classe.id", ondelete="SET NULL", name=FK_STORIES_CLASSE),
        nullable=True,
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

    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    __table_args__ = (
        Index(
            IDX_STORY_GROUPS_FEED,
            updated_at.desc(), id.desc(),
            postgresql_where=(is_active == True)
        ),
        Index(
            IDX_STORY_GROUPS_AUTHOR,
            "author_id",
            postgresql_where=(is_active == True)
        ),
        Index(
            IDX_STORY_GROUPS_EXPIRATION,
            "expires_at",
            postgresql_where=(is_active == True)
        ),
        Index(
            UQ_AUTHOR_ACTIVE_GROUP,
            "author_id",
            unique=True,
            postgresql_where=((is_active == True) & (author_id != None)),
        ),
        Index(
            UQ_CLUB_ACTIVE_GROUP,
            "club_id",
            unique=True,
            postgresql_where=(is_active == True) & (club_id != None)
        ),
        Index(
            UQ_CLASSE_ACTIVE_GROUP,
            "target_classe_id",
            unique=True,
            postgresql_where=(is_active == True) & (target_classe_id != None)
        ),
    )

    # Relationships
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id], back_populates="story_groups", uselist=False, init=False, lazy="noload")
    stories: Mapped[list["Story"]] = relationship("Story", back_populates="group", uselist=True, init=False, lazy="noload")
    club: Mapped[Optional["Club"]] = relationship("Club", foreign_keys=[club_id], back_populates="story_groups", uselist=False, init=False, lazy="noload")
    classe: Mapped[Optional["Classe"]] = relationship("Classe", foreign_keys=[target_classe_id], back_populates="story_groups", uselist=False, init=False, lazy="noload")


    ERROR_MESSAGES = {
        UQ_AUTHOR_ACTIVE_GROUP: "L'auteur spécifié a déja un groupe actif",
        FK_STORY_GROUPS_AUTHOR: "L'auteur spécifié n'existe pas.",
        FK_STORIES_CLUB: "Le club spécifié n'existe pas.",
        FK_STORIES_CLASSE: "La classe spécifiée n'existe pas.",
    }
