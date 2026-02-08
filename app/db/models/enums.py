"""
Énumérations pour les types de base de données.
Basé sur le schéma PostgreSQL schema_final.sql
"""
from enum import Enum


class UserRole(str, Enum):
    """Rôles des utilisateurs sur la plateforme."""
    STUDENT = "STUDENT"
    CLUB_LEADER = "CLUB_LEADER"
    DELEGATE = "DELEGATE"
    GENERAL_DELEGATE = "GENERAL_DELEGATE"
    SECRETAIRE_GENERAL = "SECRETAIRE_GENERAL"
    EXECUTIVE_MEMBER = "EXECUTIVE_MEMBER"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"
    SPECTATOR = "SPECTATOR"


class ClasseType(str, Enum):
    """Classes de l'établissement."""
    TC1 = "TC1"
    TC2 = "TC2"
    GLSI_3 = "GLSI_3"
    ASR_3 = "ASR_3"
    MTWI_3 = "MTWI_3"


class ClubMembersType(str, Enum):
    """Rôles des membres dans les clubs."""
    LEAD = "LEAD"
    CO_LEAD = "CO_LEAD"
    EXECUTIVE_MEMBER = "EXECUTIVE_MEMBER"
    SIMPLE_MEMBER = "SIMPLE_MEMBER"


class PostType(str, Enum):
    """Types de publications."""
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    CAROUSSEL = "CAROUSSEL"


class MediaType(str, Enum):
    """Types de médias."""
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"


class ModerationActionType(str, Enum):
    """Types d'actions de modération."""
    DELETE_POST = "DELETE_POST"
    DELETE_COMMENT = "DELETE_COMMENT"
    WARN_USER = "WARN_USER"
    SUSPEND_USER = "SUSPEND_USER"
    RESTORE_POST = "RESTORE_POST"
    RESTORE_COMMENT = "RESTORE_COMMENT"


class EventStatus(str, Enum):
    """Statuts des événements."""
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

