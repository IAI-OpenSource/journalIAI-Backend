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
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"
    SPECTATOR = "SPECTATOR"
    EXECUTIVE_MEMBER = "EXECUTIVE_MEMBER"

class ClasseType(str, Enum):
    """Classes de l'établissement."""
    TC1 = "TC1"
    TC2 = "TC2"
    GLSI_3 = "GLSI_3"
    ASR_3 = "ASR_3"
    MTWI_3 = "MTWI_3"

class TypeActions(str, Enum):
    CREATION = "CREATION"
    ACCESSION = "ACCESSION"
    MODIFICATION = "MODIFICATION"
    SUPPRESSION = "SUPPRESSION"

class ClubMembersType(str, Enum):
    """Rôles des membres dans les clubs."""
    LEAD = "LEAD"
    CO_LEAD = "CO_LEAD"
    EXECUTIVE_MEMBER = "EXECUTIVE_MEMBER"
    SIMPLE_MEMBER = "SIMPLE_MEMBER"

class SexeType(str, Enum):
    """Sexes possibles pour les utilisateurs."""
    F = "F"
    M = "M"

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

class ModerationTargetType(str, Enum):
    """Types de cibles pour les actions de modération."""
    POST = "POST"
    COMMENT = "COMMENT"
    USER = "USER"


class EventStatus(str, Enum):
    """Statuts des événements."""
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class ExecutiveRoleType(str, Enum):
    """Rôles des membres exécutifs dans l'école."""
    DELEGUE_GENERAL = "DELEGUE_GENERAL"
    DELEGUE_GENERAL_ADJOINT = "DELEGUE_GENERAL_ADJOINT"
    SECRETAIRE_GENERAL = "SECRETAIRE_GENERAL"
    SECRETAIRE_GENERAL_ADJOINT = "SECRETAIRE_GENERAL_ADJOINT"
    CACA = "CACA"
    VICE_CACA = "VICE_CACA"
    TRESORIER_GENERAL = "TRESORIER_GENERAL"
    VICE_TRESORIER_GENERAL = "VICE_TRESORIER_GENERAL"
    CONSEILLER = "CONSEILLER"


class CeleryStatus(str, Enum):
    """les différents status de celery"""
    PENDING = "PENDING" 
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE" 
    
class DownloadFormat(str, Enum):
    """Les différents formats de téléchargement"""
    JSON = "JSON"
    PDF = "PDF"