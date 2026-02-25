from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models.club import Club
from app.repositories.club_repository import ClubRepository
from app.schemas.clubs_schemas import ClubCreateRequest, ClubUpdateRequest, ClubResponse,ClubsListResponse
from app.services import ServiceResult
from app.globals.messages import Messages as msg
from app.globals.status_codes import StatusCode as status


class ClubService:
    """Service pour les opérations sur les clubs
    """
    def __init__(self, db : AsyncSession):
        self.db = db
        self.club_repository = ClubRepository(db)
        
    async def get_club(self, club_id: UUID) :
        """Récupère un club par son ID.
        
        Args:
            club_id (UUID): L'identifiant du club.
            
        Returns:
            Optional[ClubResponse]: Les données du club ou None.
        """
        club_result = await self.club_repository.get_club_by_id(club_id)

        if club_result.is_error():
            return ServiceResult.service_error(msg.INTERNAL_SERVER_ERROR, status.INTERNAL_SERVER_ERROR)
        
        club = club_result.data

        if club is None:
            return ServiceResult.service_error(msg.NOT_FOUND, status.NOT_FOUND)
        
        return ServiceResult.service_success(ClubResponse.model_validate(club), status.OK)
    
    async def get_club_by_slug(self, slug: str) :
        """Récupère un club par son slug.
        
        Args:
            slug (str): Le slug du club.
            
        Returns:
            Optional[ClubResponse]: Les données du club ou None.
        """
        club_result = await self.club_repository.get_club_by_slug(slug)

        if club_result.is_error():
            return ServiceResult.service_error(msg.INTERNAL_SERVER_ERROR, status.INTERNAL_SERVER_ERROR)
        
        club = club_result.data

        if club is None:
            return ServiceResult.service_error(msg.NOT_FOUND, status.NOT_FOUND)
        
        return ServiceResult.service_success(ClubResponse.model_validate(club), status.OK)
    

    async def get_all_clubs(self, page :int =1, page_size: int = 20, is_active : bool = False) :
        """Récupère tous les clubs avec pagination et filtrage par statut actif/inactif.
        
        Args:
            page (int): Le numéro de page à récupérer (par défaut 1).
            page_size (int): Le nombre de clubs par page (par défaut 20).
            is_active (bool): Filtrer les clubs actifs ou inactifs (par défaut False, tous les clubs).
        returns:
            ClubResponse: La liste des clubs avec pagination et filtrage par statut actif/inactif.
        """
        clubs_result = await self.club_repository.get_all_clubs(page,page_size,is_active)
        if clubs_result.is_error():
            return ServiceResult.service_error(msg.INTERNAL_SERVER_ERROR, status.INTERNAL_SERVER_ERROR)
        
        clubs, total = clubs_result.data
        clubs_list = [ClubResponse.model_validate(club) for club in clubs]
        return ServiceResult.service_success(ClubsListResponse(clubs=clubs_list, total=total, page=page, page_size=page_size), status.OK) 


    async def create_club(self, payload: ClubCreateRequest) :
        """Crée un nouveau club.
        
        Args:
            payload (ClubCreateRequest): Les données du club à créer.
            
        Returns:
            Optional[ClubResponse]: Les données du club créé ou None.
        """
        club = Club(name=payload.name,
                    slug=payload.slug,
                    description=payload.description)
        existing_club = await self.club_repository.get_club_by_slug(club.slug)
        if existing_club.data is not None:
            return ServiceResult.service_error(msg.CLUB_ALREADY_EXISTS, status.CONFLICT)
        
        create_result = await self.club_repository.create_club(club)
        if create_result.is_error():
            return ServiceResult.service_error(msg.INTERNAL_SERVER_ERROR, status.INTERNAL_SERVER_ERROR)
        
        created_club = create_result.data
        return ServiceResult.service_success(ClubResponse.model_validate(created_club), status.CREATED)
    

    async def update_club(self, club_id: UUID, payload: ClubUpdateRequest) :
        """Met à jour un club existant.
        
        Args:
            club_id (UUID): L'identifiant du club à mettre à jour.
            payload (ClubUpdateRequest): Les données du club à mettre à jour.
            
        Returns:
            Optional[ClubResponse]: Les données du club mis à jour ou None.
        """
        club_result = await self.club_repository.get_club_by_id(club_id)
        if club_result.is_error():
            return ServiceResult.service_error(msg.INTERNAL_SERVER_ERROR, status.INTERNAL_SERVER_ERROR)
        
        club = club_result.data
        if club is None:
            return ServiceResult.service_error(msg.NOT_FOUND, status.NOT_FOUND)
        
        fields = payload.model_dump(exclude_none=True)
        
        update_result = await self.club_repository.update_club(club, **fields)
        if update_result.is_error():
            return ServiceResult.service_error(msg.INTERNAL_SERVER_ERROR, status.INTERNAL_SERVER_ERROR)
        
        updated_club = update_result.data
        return ServiceResult.service_success(ClubResponse.model_validate(updated_club), status.OK)
    
    async def delete_club(self, club_id: UUID) :
        """Supprime un club existant (soft delete).
        
        Args:
            club_id (UUID): L'identifiant du club à supprimer.
            
        Returns:
            ServiceResult: Un objet ServiceResult indiquant le succès ou l'échec de l'opération.
        """
        club_result = await self.club_repository.get_club_by_id(club_id)
        if club_result.is_error():
            return ServiceResult.service_error(msg.INTERNAL_SERVER_ERROR, status.INTERNAL_SERVER_ERROR)
        
        club = club_result.data
        if club is None:
            return ServiceResult.service_error(msg.NOT_FOUND, status.NOT_FOUND)
        
        delete_result = await self.club_repository.soft_delete_club(club)
        if delete_result.is_error():
            return ServiceResult.service_error(msg.INTERNAL_SERVER_ERROR, status.INTERNAL_SERVER_ERROR)
        
        return ServiceResult.service_success(msg.CLUB_DELETED_SUCCESSFULLY, status.OK)