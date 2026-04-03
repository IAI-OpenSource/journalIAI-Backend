# Ce fichier contient les différents schémas concernant les opérations
# sur la table academic_year

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID
from app.schemas import ApiBaseResponse

class AcademicYearCreateRequest(BaseModel):
    """ Schemas pydantic pour la création d'une année académique
    
    attributes:
        libelle: Le libellé de l'année académique (ex: "2025-2026")
        start_date: La date de début de l'année académique
        end_date: La date de fin de l'année académique
    """
    
    libelle: str = Field(..., min_length=5, max_length=20, description="Le libellé de l'année académique (ex: '2025-2026')")
    start_date: datetime = Field(..., description="La date de début de l'année académique")
    end_date: datetime = Field(..., description="La date de fin de l'année académique")

class AcademicYearUpdateRequest(BaseModel):
    """ Schemas pydantic pour la mise à jour d'une année académique
    
    attributes (optionnels):
        libelle: Le libellé de l'année académique (ex: "2025-2026")
        start_date: La date de début de l'année académique
        end_date: La date de fin de l'année académique
    """
    
    libelle: Optional[str] = Field(None, min_length=5, max_length=20, description="Le libellé de l'année académique (ex: '2025-2026')")
    start_date: Optional[datetime] = Field(None, description="La date de début de l'année académique")
    end_date: Optional[datetime] = Field(None, description="La date de fin de l'année académique")

class AcademicYearResponse(BaseModel):
    """ Schemas pydantic pour la réponse d'une année académique
    
    attributes:
        id: L'identifiant de l'année académique
        libelle: Le libellé de l'année académique (ex: "2025-2026")
        start_date: La date de début de l'année académique
        end_date: La date de fin de l'année académique
        active: (bool) l'année académique est active ou pas
        created_at: La date de création de l'année académique
        updated_at: La date de mise à jour de l'année académique
    """
    
    model_config = {"from_attributes": True}
    id: UUID
    libelle: str
    start_date: datetime
    end_date: datetime
    active: bool
    created_at: datetime
    updated_at: datetime


class AcademicYearListResponse(BaseModel):
    """ Schemas pydantic pour la réponse d'une liste d'années académiques
    
    attributes:
        classes: La liste des années académiques
    """
    
    years: list[AcademicYearResponse]
    total: int
    page : int
    page_size : int


class AcademicYearApiResponse(ApiBaseResponse[AcademicYearResponse]):
    """ Schemas pydantic pour la réponse d'une année académique dans une API, hérite de ApiBaseResponse avec un result de type AcademicYearResponse"""
    
    pass

class AcademicYearsListApiResponse(ApiBaseResponse[AcademicYearListResponse]):
    """ Schemas pydantic pour la réponse d'une liste d'années académiques dans une API, hérite de ApiBaseResponse avec un result de type AcademicYearListResponse"""
    
    pass