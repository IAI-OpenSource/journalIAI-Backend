import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.db.models.club import Club
from app.repositories.club_repository import ClubRepository
from app.schemas.club_schemas import ClubCreateRequest, ClubUpdateRequest, ClubResponse,ClubsListResponse
from app.schemas.global_schemas import GlobalStringMessage, StringMessage
from app.services import ServiceResult
from app.globals.messages import Messages as msg
from app.globals.status_codes import StatusCode as status
from app.cache.helpers.base import CacheWrapper

logger = logging.getLogger(__name__)
CLUB_CACHE_TTL = 3600  # 1 heure

class ClubService:
    """Service pour les opérations sur les clubs
    """
    def __init__(self, db : AsyncSession, redis: CacheWrapper):
        self.db = db
        self.redis = redis
        self.club_repository = ClubRepository(db)
        
    def _build_club_cache_key(self, club_id: UUID):
        """Construit la clé de cache pour un club par son ID."""
        return (
            CacheKeysFactory.get_cache_key(AvailableCacheKeys.CLUB_OBJECT).set_arguments(id=str(club_id))
        )
    
    async def get_club(self, club_id: UUID) -> ServiceResult[ClubResponse]:
        """Récupère un club par son ID.
        
        Args:
            club_id (UUID): L'identifiant du club.
            
        Returns:
            Optional[ClubResponse]: Les données du club ou None.
        """
        cache_key = self._build_club_cache_key(club_id)
        try:
            club_from_cache = await self.redis.get_pydantic_model_from_cache(cache_key, ClubResponse)
            if club_from_cache is not None:
                logger.info(f"Club trouvé dans le cache pour l'ID {club_id}")
                return ServiceResult.service_success(club_from_cache, status._200_STATUS_SUCCESS, msg.CLUB_SERVICE)
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération du club depuis le cache: {e}")

        logger.info(f"Club non trouvé dans le cache pour l'ID {club_id}, récupération depuis la base de données")
        club_result = await self.club_repository.get_club_by_id(club_id)
        if club_result.is_error():
            return ServiceResult.service_error(club_result.error, club_result.status_code)
        club_response = ClubResponse.model_validate(club_result.data)
        try:
            await self.redis.save_pydantic_model_in_cache(cache_key, club_response, CLUB_CACHE_TTL)
            logger.info(f"Club sauvegardé dans le cache pour l'ID {club_id}")
        except Exception:
            logger.warning(f"Impossible de sauvegarder le club {club_id} dans le cache")
 
        return ServiceResult.service_success(club_response, status._200_STATUS_SUCCESS, msg.CLUB_SERVICE)
    
    async def get_club_by_slug(self, slug: str) :
        """Récupère un club par son slug.
        
        Args:
            slug (str): Le slug du club.
            
        Returns:
            Optional[ClubResponse]: Les données du club ou None.
        """
        club_result = await self.club_repository.get_club_by_slug(slug)

        if club_result.is_error():
            return ServiceResult.service_error(club_result.error, club_result.status_code, msg.CLUB_SERVICE)
        
        club_response = ClubResponse.model_validate(club_result.data)

        try:
            cache_key = self._build_club_cache_key(club_result.data.id)
            await self.redis.save_pydantic_model_in_cache(cache_key, club_response, CLUB_CACHE_TTL)
            logger.info(f"Cache SAVED via slug — club {club_result.data.id}")
        except Exception:
            logger.warning(f"Cache WRITE ERROR via slug — {slug}")
 
        return ServiceResult.service_success(club_response, status._200_STATUS_SUCCESS, msg.CLUB_SERVICE)
        

    async def get_all_clubs(self, page :int =1, page_size: int = 20, is_active : bool = False) -> ServiceResult[ClubsListResponse]:
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
        return ServiceResult.service_success(ClubsListResponse(clubs=clubs_list, total=total, page=page, page_size=page_size), status._200_STATUS_SUCCESS, msg.CLUB_SERVICE) 


    async def create_club(self, payload: ClubCreateRequest) -> ServiceResult[ClubResponse]:
        """Crée un nouveau club.
        
        Args:
            payload (ClubCreateRequest): Les données du club à créer.
            
        Returns:
            Optional[ClubResponse]: Les données du club créé ou None.
        """
        existing_club = await self.club_repository.get_club_by_slug(payload.slug)
        if existing_club.is_success():
            return ServiceResult.service_error(msg.CLUB_ALREADY_EXISTS, status._400_STATUS_BAD_REQUEST, msg.CLUB_SERVICE)

        club = Club(name=payload.name,
                    slug=payload.slug,
                    description=payload.description
                    )
        
        create_result = await self.club_repository.create_club(club)
        if create_result.is_error():
            return ServiceResult.service_error(create_result.error, create_result.status_code)
        
        club_response = ClubResponse.model_validate(create_result.data)
 
        # Alimentation du cache après création
        try:
            cache_key = self._build_club_cache_key(create_result.data.id)
            await self.redis.save_pydantic_model_in_cache(cache_key, club_response, CLUB_CACHE_TTL)
            logger.info(f"Cache SAVED after create — club {create_result.data.id}")
        except Exception:
            logger.warning(f"Cache WRITE ERROR after create — {payload.slug}")
 
        return ServiceResult.service_success(club_response, status._201_STATUS_CREATED, msg.CLUB_SERVICE)


    async def update_club(self, club_id: UUID, payload: ClubUpdateRequest) -> ServiceResult[ClubResponse]:
        """Met à jour un club existant.
        
        Args:
            club_id (UUID): L'identifiant du club à mettre à jour.
            payload (ClubUpdateRequest): Les données du club à mettre à jour.
            
        Returns:
            Optional[ClubResponse]: Les données du club mis à jour ou None.
        """
        club_result = await self.club_repository.get_club_by_id(club_id)
 
        if club_result.is_error():
            return ServiceResult.service_error(
                club_result.error, club_result.status_code, msg.CLUB_SERVICE
            )
 
        fields = payload.model_dump(exclude_none=True)
        update_result = await self.club_repository.update_club(club_result.data, **fields)
 
        if update_result.is_error():
            return ServiceResult.service_error(
                update_result.error, update_result.status_code, msg.CLUB_SERVICE
            )
 
        club_response = ClubResponse.model_validate(update_result.data)
 
        # Mise à jour du cache avec la version fraîche
        try:
            cache_key = self._build_club_cache_key(club_id)
            await self.redis.save_pydantic_model_in_cache(cache_key, club_response, CLUB_CACHE_TTL)
            logger.info(f"Cache UPDATED — club {club_id}")
        except Exception:
            logger.warning(f"Cache WRITE ERROR after update — club {club_id}")
 
        return ServiceResult.service_success(club_response, status._200_STATUS_SUCCESS, msg.CLUB_SERVICE)
    

    async def delete_club(self, club_id: UUID) :
        """Supprime un club existant (soft delete).
        
        Args:
            club_id (UUID): L'identifiant du club à supprimer.
            
        Returns:
            ServiceResult: Un objet ServiceResult indiquant le succès ou l'échec de l'opération.
        """
        club_result = await self.club_repository.get_club_by_id(club_id)
 
        if club_result.is_error():
            return ServiceResult.service_error(
                club_result.error, club_result.status_code, msg.CLUB_SERVICE
            )
 
        delete_result = await self.club_repository.soft_delete_club(club_result.data)
 
        if delete_result.is_error():
            return ServiceResult.service_error(
                delete_result.error, delete_result.status_code, msg.CLUB_SERVICE
            )
 
        # Invalidation du cache — le club ne doit plus être servi depuis Redis
        try:
            cache_key = self._build_club_cache_key(club_id)
            await self.redis.delete_in_cache(cache_key)
            logger.info(f"Cache INVALIDATED — club {club_id}")
        except Exception:
            logger.warning(f"Cache DELETE ERROR after soft delete — club {club_id}")
 
        return ServiceResult.service_success(
            StringMessage(message="Club supprimé avec succès"), status._200_STATUS_SUCCESS, msg.CLUB_SERVICE
        )
 