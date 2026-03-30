from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.db.models.enums import ClubMembersType
from app.schemas import ApiBaseResponse




class ClubMemberCreate(BaseModel):
    """Schéma pour ajouter un membre à un club."""
    club_id: UUID = Field(..., description="Identifiant du club")
    user_id: UUID = Field(..., description="Identifiant de l'utilisateur")
    role_in_club: ClubMembersType = Field(ClubMembersType.SIMPLE_MEMBER, description="Rôle dans le club")



class ClubMemberUpdate(BaseModel):
    """Schéma pour mettre à jour le rôle d'un membre."""
    role_in_club: Optional[ClubMembersType] = Field(None, description="Nouveau rôle dans le club")



class ClubMemberRead(BaseModel):
    """Schéma complet de lecture d'un membre de club."""
    id: UUID = Field(..., description="Identifiant unique")
    club_id: UUID = Field(..., description="Identifiant du club")
    user_id: UUID = Field(..., description="Identifiant de l'utilisateur")
    role_in_club: ClubMembersType = Field(..., description="Rôle dans le club")
    joined_at: datetime = Field(..., description="Date d'adhésion")
    deleted_at: Optional[datetime] = Field(None, description="Date de suppression (si supprimé)")

    model_config = {"from_attributes": True}

    def is_deleted(self) -> bool:
        return self.deleted_at is not None



class ClubMemberSummary(BaseModel):
    """Schéma léger pour afficher un membre dans une liste."""
    id: UUID = Field(..., description="Identifiant unique")
    user_id: UUID = Field(..., description="Identifiant de l'utilisateur")
    role_in_club: ClubMembersType = Field(..., description="Rôle dans le club")
    joined_at: datetime = Field(..., description="Date d'adhésion")

    model_config = {"from_attributes": True}



class ClubMemberInfo(ApiBaseResponse):
    result: Optional[ClubMemberRead] = Field(None, description="Informations du membre")

class ClubMemberListResponse(BaseModel):
    members: list[ClubMemberRead] = Field(..., description="Liste des membres du club")

class PaginatedClubMemberListResponse(ClubMemberListResponse):
    next_cursor: Optional[UUID] = None

class ApiClubMemberListResponse(ApiBaseResponse):
    result: Optional[ClubMemberListResponse] = None

class ApiPaginatedClubMemberListResponse(ApiBaseResponse):
    result: Optional[PaginatedClubMemberListResponse] = None

