from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.cache.club_cache import ClubCache
from app.db.models.club import Club
from app.repositories.club_repository import ClubRepository
from app.schemas.clubs_schemas import ClubCreateRequest, ClubUpdateRequest, ClubResponse,ClubsListResponse
from app.services import ServiceResult
from app.globals.messages import Messages as msg
from app.globals.status_codes import StatusCode as status
from app.cache.helpers.base import CacheWrapper


class ClubService:
    """Service pour les opérations sur les clubs
    """
    def __init__(self, db : AsyncSession, redis: CacheWrapper):
        self.db = db
        self.redis = redis
        self.club_repository = ClubRepository(db)
        self.clubCache = ClubCache(self.redis)
        
    async def get_club(self, club_id: UUID) :
        """Récupère un club par son ID.
        
        Args:
            club_id (UUID): L'identifiant du club.
            
        Returns:
            Optional[ClubResponse]: Les données du club ou None.
        """
        club_from_cache = await self.clubCache.get_club_by_id(str(club_id))
        if club_from_cache:
            return ServiceResult.service_success(club_from_cache, status.OK)
        
        club_result = await self.club_repository.get_club_by_id(club_id)
        if club_result.is_error():
            return ServiceResult.service_error(club_result.error, club_result.status_code)
        club = club_result.data
        await self.clubCache.set_club_in_cache(ClubResponse.model_validate(club_result.data))

        
        return ServiceResult.service_success(ClubResponse.model_validate(club), status.OK)
    
    async def get_club_by_slug(self, slug: str) :
        """Récupère un club par son slug.
        
        Args:
            slug (str): Le slug du club.
            
        Returns:
            Optional[ClubResponse]: Les données du club ou None.
        """
        club_from_cache = await self.clubCache.get_club_by_slug(slug)
        if club_from_cache:
            return ServiceResult.service_success(club_from_cache, status.OK)

        club_result = await self.club_repository.get_club_by_slug(slug)

        if club_result.is_error():
            return ServiceResult.service_error(club_result.error, club_result.status_code)
        
        await self.clubCache.set_club_in_cache(ClubResponse.model_validate(club_result.data))
        club = club_result.data
        
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
            return ServiceResult.service_error(clubs_result.error, clubs_result.status_code)
        
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
        
        create_result = await self.club_repository.create_club(club)
        if create_result.is_error():
            return ServiceResult.service_error(create_result.error, create_result.status_code)
        
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
            return ServiceResult.service_error(club_result.error, club_result.status_code)
        club = club_result.data
        
        fields = payload.model_dump(exclude_none=True)
        
        update_result = await self.club_repository.update_club(club, **fields)
        if update_result.is_error():
            return ServiceResult.service_error(update_result.error, update_result.status_code)
        
        await self.clubCache.delete_club_from_cache(str(club_id))
        await self.clubCache.set_club_in_cache(ClubResponse.model_validate(update_result.data))
        
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
            return ServiceResult.service_error(club_result.error, club_result.status_code)
        
        club = club_result.data
        
        delete_result = await self.club_repository.soft_delete_club(club)
        if delete_result.is_error():
            return ServiceResult.service_error(delete_result.error, delete_result.status_code)
        
        await self.clubCache.delete_club_from_cache(str(club_id))
        
        return ServiceResult.service_success(msg.CLUB_DELETED_SUCCESSFULLY, status.OK)