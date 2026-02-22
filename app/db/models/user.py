"""
Modèle pour la table users.
Tous les utilisateurs de la plateforme.
"""
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Boolean, func, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLEnum

from app.db.base import Base
from app.db.models.mixins.integrity_error_mixin import IntegrityMapperMixin
from app.db.models.enums import UserRole, ExecutiveRoleType, SexeType

# Noms des contraintes
UQ_USERS_EMAIL = "uq_users_email"
UQ_USERS_USERNAME = "uq_users_username"
FK_USERS_ACCESS_JETON = "fk_users_access_jeton"
FK_USERS_CLASSE = "fk_users_classe"
CHK_USERS_BIO_LENGTH = "chk_users_bio_length"
CHK_USERS_EXEC_ROLE_VALID = "chk_users_exec_role_valid"
IDX_USERS_CREATED_AT_ID = "idx_users_created_at_id"
IDX_USERS_EMAIL = "idx_users_email"
IDX_USERS_USERNAME = "idx_users_username"
IDX_USERS_ROLE = "idx_users_role"
IDX_USERS_CAN_POST = "idx_users_can_post"
IDX_USERS_CLASSE = "idx_users_classe"
IDX_USERS_ACCESS_JETON = "idx_users_access_jeton"
IDX_USERS_DELETED_AT = "idx_users_deleted_at"


class User(Base, IntegrityMapperMixin):
    """Utilisateurs de la plateforme (étudiants, modérateurs, etc.)."""

    __tablename__ = "users"

    # Attributs
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4, init=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Informations personnelles
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    bio: Mapped[Optional[str]] = mapped_column(nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sexe: Mapped[SexeType] = mapped_column(SQLEnum(SexeType), nullable=False)

    classe_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("classe.id", ondelete="SET NULL", name=FK_USERS_CLASSE),
        nullable=True,
        comment="Référence à la classe de l'utilisateur (peut être NULL pour les membres du bureau ou les anciens élèves qui ne sont plus rattachés à une classe active)"
    )

    # Rôle et permissions
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.STUDENT, nullable=False, init=False)
    executive_role: Mapped[Optional[ExecutiveRoleType]] = mapped_column(SQLEnum(ExecutiveRoleType), default=None, nullable=True, init=False)
    can_post: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, init=False)

    # Métadonnées
    access_jeton_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("registration_jeton.id", ondelete="SET NULL", name=FK_USERS_ACCESS_JETON),
        nullable=True,
        comment="Référence au jeton d'inscription utilisé"
    )

    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, init=False)

    # Soft delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None, init=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), nullable=False, init=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
        nullable=True,
        init=False
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Index
    __table_args__ = (
        Index(IDX_USERS_CREATED_AT_ID, "created_at", "id", postgresql_where=(deleted_at == None)),
        Index(IDX_USERS_EMAIL, "email", postgresql_where=(deleted_at == None)),
        Index(IDX_USERS_USERNAME, "username", postgresql_where=(deleted_at == None)),
        Index(IDX_USERS_ROLE, "role", postgresql_where=(deleted_at == None)),
        Index(IDX_USERS_CAN_POST, "can_post", postgresql_where=(deleted_at == None) & (can_post == True)),
        Index(IDX_USERS_CLASSE, "classe", postgresql_where=(deleted_at == None)),
        Index(IDX_USERS_ACCESS_JETON, "access_jeton_id", postgresql_where=(access_jeton_id != None)),
        Index(IDX_USERS_DELETED_AT, "deleted_at", postgresql_where=(deleted_at != None)),
        CheckConstraint("bio IS NULL OR LENGTH(bio) <= 500", name=CHK_USERS_BIO_LENGTH),
        CheckConstraint(
            "(role = 'EXECUTIVE_MEMBER' AND executive_role IS NOT NULL) OR "
            "(role != 'EXECUTIVE_MEMBER' AND executive_role IS NULL)",
            name=CHK_USERS_EXEC_ROLE_VALID
        )
    )

    # Relationships
    posts: Mapped[list["Post"]] = relationship("Post", foreign_keys="Post.author_id", back_populates="author", cascade="all, delete-orphan", uselist=True, init=False)
    comments: Mapped[list["Comment"]] = relationship("Comment", foreign_keys="Comment.author_id", back_populates="author", cascade="all, delete-orphan", uselist=True, init=False)
    likes: Mapped[list["Like"]] = relationship("Like", back_populates="user", cascade="all, delete-orphan", uselist=True, init=False)
    club_members: Mapped[list["ClubMember"]] = relationship("ClubMember", back_populates="user", cascade="all, delete-orphan", uselist=True, init=False)
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan", uselist=True, init=False)
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user", cascade="all, delete-orphan", uselist=True, init=False)
    moderation_logs: Mapped[list["ModerationLog"]] = relationship("ModerationLog", foreign_keys="ModerationLog.moderator_id", back_populates="moderator", cascade="all, delete-orphan", uselist=True, init=False)
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan", uselist=True, init=False)
    access_jeton_ref: Mapped[Optional["RegistrationJeton"]] = relationship("RegistrationJeton", back_populates="users", foreign_keys=[access_jeton_id], uselist=False, init=False)

    # Messages d'erreur
    ERROR_MESSAGES = {
        UQ_USERS_EMAIL: "Cet email est déjà utilisé.",
        UQ_USERS_USERNAME: "Ce nom d'utilisateur est déjà pris.",
        FK_USERS_CLASSE: "La classe spécifiée n'existe pas.",
        FK_USERS_ACCESS_JETON: "Le jeton d'inscription spécifié n'existe pas.",
        CHK_USERS_BIO_LENGTH: "La biographie ne peut pas dépasser 500 caractères.",
        CHK_USERS_EXEC_ROLE_VALID: "Erreur au niveau des roles",
    }
