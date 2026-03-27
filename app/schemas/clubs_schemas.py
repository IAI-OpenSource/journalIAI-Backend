from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID
from app.schemas import ApiBaseResponse

class ClubCreateRequest(BaseModel):
    """Schemas pydantic pour la creation d'un club
    
    Attributes:
        name: Le nom du club
        slug: Le slug du club
        description: La description du club
    """
    name : str = Field(..., min_length=2, max_length=200, description = "le nom du club")
    slug : str = Field(..., min_length=2, max_length=200, description = "le slug du club", pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    description : Optional[str] = Field(None, max_length=500, description = "la description du club")


class ClubUpdateRequest(BaseModel):
    """Schemas pydantic pour la mise à jour d'un club
    
    Attributes (optionnels):
        name: Le nom du club
        is_active: (bool) le club est actif ou pas
        description: La description du club
    """
    name : Optional[str] = Field(None, min_length=2, max_length=200, description = "le nom du club")
    is_active : Optional[bool] = Field(None, description = "le club est actif ou pas")
    description : Optional[str] = Field(None, max_length=500, description = "la description du club")



class ClubResponse(BaseModel):
    """Schemas pydantic pour la réponse d'un club
    
    Attributes:
        id: L'identifiant du club
        name: Le nom du club
        slug: Le slug du club
        description: La description du club
        logo_url: L'url du logo du club
        cover_url: L'url de la cover du club
        is_active: (bool) le club est actif ou pas
        created_at: La date de création du club
        updated_at: La date de mise à jour du club
        member_count: Le nombre de membres du club
    """
    model_config = {"from_attributes": True}
    id : UUID 
    name : str 
    slug : str 
    description : Optional[str] = None
    logo_url : Optional[str] = None
    cover_url : Optional[str] = None
    is_active : bool 
    created_at : datetime
    updated_at : datetime 
    member_count : int 


class ClubsListResponse(BaseModel):
    """Schemas pydantic pour la requete de la liste des clubs
    
    Attributes:
        clubs: La liste des clubs
    """
    clubs : list[ClubResponse] 
    total :int 
    page : int
    page_size : int


class ClubApiResponse(ApiBaseResponse[ClubResponse]):
    """Schemas pydantic pour la réponse d'un club dans l'API, hérite de ApiBaseResponse avec un result de type ClubResponse"""
    pass

class ClubsListApiResponse(ApiBaseResponse[ClubsListResponse]):
    """Schemas pydantic pour la réponse de la liste des clubs dans l'API, hérite de ApiBaseResponse avec un result de type ClubsListResponse"""
    pass