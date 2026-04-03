"""
Modèle pour la table club_members.
Relation entre utilisateurs et clubs.
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Index, ForeignKey, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums import ClubMembersType

# Noms des contraintes
FK_CLUB_MEMBERS_CLUB = "fk_club_members_club"
FK_CLUB_MEMBERS_USER = "fk_club_members_user"
UQ_CLUB_MEMBERS_CLUB_USER = "uq_club_members_club_user"
IDX_CLUB_MEMBERS_CLUB_ID = "idx_club_members_club_id"
IDX_CLUB_MEMBERS_USER_ID = "idx_club_members_user_id"
IDX_CLUB_MEMBERS_ROLE_IN_CLUB = "idx_club_members_role_in_club"
IDX_CLUB_MEMBERS_DELETED_AT = "idx_club_members_deleted_at"


class ClubMember(Base, IntegrityMapperMixin):
    """Relation entre utilisateurs et clubs."""

    __tablename__ = "club_members"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)
    club_id: Mapped[UUID] = mapped_column(ForeignKey("clubs.id", ondelete="CASCADE", name=FK_CLUB_MEMBERS_CLUB), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE", name=FK_CLUB_MEMBERS_USER), nullable=False)

    # Rôle dans le club
    role_in_club: Mapped[ClubMembersType] = mapped_column(SQLEnum(ClubMembersType), default=ClubMembersType.SIMPLE_MEMBER, nullable=False, init=False)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False, init=False)

    # Index
    __table_args__ = (
        Index(IDX_CLUB_MEMBERS_CLUB_ID, "club_id", postgresql_where=(deleted_at == None)),
        Index(IDX_CLUB_MEMBERS_USER_ID, "user_id", postgresql_where=(deleted_at == None)),
        Index(IDX_CLUB_MEMBERS_ROLE_IN_CLUB, "club_id", "role_in_club", postgresql_where=(deleted_at == None) & (role_in_club.in_(["LEAD", "CO_LEAD"]))),
        Index(IDX_CLUB_MEMBERS_DELETED_AT, "deleted_at", postgresql_where=(deleted_at != None)),
        # Contrainte d'unicité
        Index(UQ_CLUB_MEMBERS_CLUB_USER, "club_id", "user_id", unique=True, postgresql_where=(deleted_at != None)),
    )

    # Relationships
    club: Mapped["Club"] = relationship("Club", foreign_keys=[club_id], back_populates="members", uselist=False, init=False)
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="club_members", uselist=False, init=False)

    # Messages d'erreur
    ERROR_MESSAGES = {
        FK_CLUB_MEMBERS_CLUB: "Le club spécifié n'existe pas.",
        FK_CLUB_MEMBERS_USER: "L'utilisateur spécifié n'existe pas.",
        UQ_CLUB_MEMBERS_CLUB_USER: "Cet utilisateur est déjà membre de ce club.",
    }
