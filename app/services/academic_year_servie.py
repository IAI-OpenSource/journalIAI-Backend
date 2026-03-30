import logging
from uuid import UUID
from app.globals.messages import Messages as msg
from app.globals.status_codes import StatusCode as status
from sqlalchemy.ext.asyncio import AsyncSession
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.db.models.academic_year import AcademicYear
from app.repositories.academic_year_repository import AcademicYearRepository
from app.schemas.academicYear_schemas import AcademicYearCreateRequest, AcademicYearListResponse, AcademicYearResponse, AcademicYearUpdateRequest
from app.schemas.global_schemas import StringMessage
from app.services import ServiceResult


logger = logging.getLogger(__name__)
ACADEMIC_YEAR_CACHE_TTL = 3600  # 1 heure

class AcademicYearService:
    """Service pour les opérations sur les années académiques
    """
    def __init__(self, db : AsyncSession, redis:CacheWrapper):
        self.db = db
        self.redis = redis
        self.academic_year_repository = AcademicYearRepository(db)

    def _build_academic_year_cache_key(self, academic_year_id: UUID):
        """Construit la clé de cache pour une année académique par son ID."""
        return (
            CacheKeysFactory.get_cache_key(AvailableCacheKeys.ACADEMIC_YEAR_OBJECT).set_arguments(id=str(academic_year_id))
        )

    async def get_academic_year_by_id(self, academic_year_id: UUID) -> ServiceResult[AcademicYearResponse]:
        """Récupère une année académique par son ID.
        
        Args:
            academic_year_id (UUID): L'identifiant de l'année académique.
            
        Returns:
            Optional[AcademicYearResponse]: Les données de l'année académique ou None.
        """
        cache_key = self._build_academic_year_cache_key(academic_year_id)
        try:
            academic_year_from_cache = await self.redis.get_pydantic_model_from_cache(cache_key, AcademicYearResponse)
            if academic_year_from_cache is not None:
                logger.info(f"Année académique trouvée dans le cache pour l'ID {academic_year_id}")
                return ServiceResult.service_success(academic_year_from_cache, 200, "Service Année Académique")
        except Exception as e:
            logger.warning(f"Erreur lors de la récupération de l'année académique depuis le cache: {e}")

        logger.info(f"Année académique non trouvée dans le cache pour l'ID {academic_year_id}, récupération depuis la base de données")
        academic_year_result = await self.academic_year_repository.get_academic_year_by_id(academic_year_id)
        if academic_year_result.is_error():
            return ServiceResult.service_error(academic_year_result.error, academic_year_result.status_code)
        academic_year_response = AcademicYearResponse.model_validate(academic_year_result.data)
        try:
            await self.redis.save_pydantic_model_in_cache(cache_key, academic_year_response, ACADEMIC_YEAR_CACHE_TTL)
            logger.info(f"Année académique sauvegardée dans le cache pour l'ID {academic_year_id}")
        except Exception:
            logger.warning(f"Impossible de sauvegarder l'année académique {academic_year_id} dans le cache")
        
        return ServiceResult.service_success(academic_year_response, status._200_STATUS_SUCCESS, msg.ACADEMIC_YEAR_SERVICE)

    async def get_active_academic_year(self) -> ServiceResult[AcademicYearResponse]:
        """Récupère l'année académique active.
        
        Returns:
            Optional[AcademicYearResponse]: Les données de l'année académique active ou None.
        """
        try:
            academic_year_result = await self.academic_year_repository.get_active_academic_year()
            if academic_year_result.is_error():
                return ServiceResult.service_error(academic_year_result.error, academic_year_result.status_code)
            academic_year_response = AcademicYearResponse.model_validate(academic_year_result.data)
            try:
                cache_key = self._build_academic_year_cache_key(academic_year_response.id)
                await self.redis.save_pydantic_model_in_cache(cache_key, academic_year_response, ACADEMIC_YEAR_CACHE_TTL)
                logger.info(f"Année académique active sauvegardée dans le cache pour l'ID {academic_year_response.id}")
            except Exception:
                logger.warning(f"Impossible de sauvegarder l'année académique active {academic_year_response.id} dans le cache")
            return ServiceResult.service_success(academic_year_response, status._200_STATUS_SUCCESS, msg.ACADEMIC_YEAR_SERVICE)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'année académique active: {e}")
            return ServiceResult.service_error("Une erreur est survenue lors de la récupération de l'année académique active.", 500, msg.ACADEMIC_YEAR_SERVICE)
        
    async def get_all_academic_years(self, page: int, page_size: int) -> ServiceResult[list[AcademicYearResponse]]:
        """Récupère toutes les années académiques avec pagination.
        
        Args:
            page (int): Le numéro de la page à récupérer.
            page_size (int): Le nombre d'éléments par page.
            
        Returns:
            list[AcademicYearResponse]: La liste des années académiques.
        """
        try:
            academic_years_result = await self.academic_year_repository.get_all_academic_years(page, page_size)
            if academic_years_result.is_error():
                return ServiceResult.service_error(academic_years_result.error, academic_years_result.status_code)
            academic_years, total = academic_years_result.data
            academic_years_response = [AcademicYearResponse.model_validate(academic_year) for academic_year in academic_years]
            academic_years_list_response = AcademicYearListResponse(years=academic_years_response, total=total, page=page, page_size=page_size)
            return ServiceResult.service_success(academic_years_list_response, status._200_STATUS_SUCCESS, msg.ACADEMIC_YEAR_SERVICE)
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de toutes les années académiques: {e}")
            return ServiceResult.service_error("Une erreur est survenue lors de la récupération de toutes les années académiques.", 500, msg.ACADEMIC_YEAR_SERVICE)
        
    
    async def update_academic_year(self, academic_year_id: UUID, payload: AcademicYearUpdateRequest) -> ServiceResult[AcademicYearResponse]:        
        """Met à jour une année académique existante.
        
        Args:
            academic_year_id: L'identifiant de l'année académique à mettre à jour.
            payload: Les données de l'année académique à mettre à jour.
            
        Returns:
            AcademicYearResponse: Les données de l'année académique mise à jour.
        """
        existing_academic_year_result = await self.academic_year_repository.get_academic_year_by_id(academic_year_id)
        if existing_academic_year_result.is_error():
            return ServiceResult.service_error(existing_academic_year_result.error, existing_academic_year_result.status_code, msg.ACADEMIC_YEAR_SERVICE)
        
        fields = payload.model_dump(exclude_none=True)   # exclut les champs None
        
        try:
            update_result = await self.academic_year_repository.update_academic_year(existing_academic_year_result.data, **fields)
            if update_result.is_error():
                return ServiceResult.service_error(update_result.error, update_result.status_code, msg.ACADEMIC_YEAR_SERVICE)
            academic_year_response = AcademicYearResponse.model_validate(update_result.data)
            cache_key = self._build_academic_year_cache_key(academic_year_response.id)
            try:
                await self.redis.save_pydantic_model_in_cache(cache_key, academic_year_response, ACADEMIC_YEAR_CACHE_TTL)
                logger.info(f"Année académique mise à jour sauvegardée dans le cache pour l'ID {academic_year_response.id}")
            except Exception:
                logger.warning(f"Impossible de sauvegarder l'année académique mise à jour {academic_year_response.id} dans le cache")
            return ServiceResult.service_success(academic_year_response, status._200_STATUS_SUCCESS, msg.ACADEMIC_YEAR_SERVICE)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'année académique: {e}")
            return ServiceResult.service_error("Une erreur est survenue lors de la mise à jour de l'année académique.", 500, msg.ACADEMIC_YEAR_SERVICE)


    async def soft_delete_academic_year(self, academic_year_id: UUID) -> ServiceResult[StringMessage]:
        """Supprime une année académique (soft delete).
        
        Args:
            academic_year_id: L'identifiant de l'année académique à supprimer.
            
        Returns:
            StringMessage: Un message indiquant le résultat de l'opération de suppression.
        """
        existing_academic_year_result = await self.academic_year_repository.get_academic_year_by_id(academic_year_id)
        if existing_academic_year_result.is_error():
            return ServiceResult.service_error(existing_academic_year_result.error, existing_academic_year_result.status_code, msg.ACADEMIC_YEAR_SERVICE)
        
        academic_year_to_delete = existing_academic_year_result.data
        
        try:
            delete_result = await self.academic_year_repository.soft_delete_academic_year(academic_year_to_delete)
            if delete_result.is_error():
                return ServiceResult.service_error(delete_result.error, delete_result.status_code, msg.ACADEMIC_YEAR_SERVICE)
            cache_key = self._build_academic_year_cache_key(academic_year_id)
            try:
                await self.redis.delete_in_cache(cache_key)
                logger.info(f"Année académique supprimée du cache pour l'ID {academic_year_id}")
            except Exception:
                logger.warning(f"Impossible de supprimer l'année académique {academic_year_id} du cache")
            return ServiceResult.service_success(StringMessage("Année académique supprimée avec succès."), status._200_STATUS_SUCCESS, msg.ACADEMIC_YEAR_SERVICE)
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'année académique: {e}")
            return ServiceResult.service_error("Une erreur est survenue lors de la suppression de l'année académique.", 500, msg.ACADEMIC_YEAR_SERVICE)

    async def create_academic_year(self, payload: AcademicYearCreateRequest) -> ServiceResult[AcademicYearResponse]:
        """Crée une nouvelle année académique.
        
        Args:
            payload: Les données de l'année académique à créer.
            
        Returns:
            AcademicYearResponse: Les données de l'année académique créée.
        """
        # 1. Vérifier que le libelle n'existe pas déjà
        existing = await self.academic_year_repository.get_academic_year_by_libelle(payload.libelle)
        if existing.is_success():
            return ServiceResult.service_error(msg.ACADEMIC_YEAR_ALREADY_EXISTS, status._400_STATUS_BAD_REQUEST, msg.ACADEMIC_YEAR_SERVICE)

        # 2. Désactiver l'ancienne année active si elle existe
        active_year = await self.academic_year_repository.get_active_academic_year()
        if active_year.is_success():
            deactivate_result = await self.academic_year_repository.deactivate_academic_year()
            if deactivate_result.is_error():
                return ServiceResult.service_error(deactivate_result.error, deactivate_result.status_code, msg.ACADEMIC_YEAR_SERVICE)

        # 3. Créer la nouvelle année
        academic_year_to_create = AcademicYear(
            libelle=payload.libelle,
            start_date=payload.start_date,
            end_date=payload.end_date
        )
        try:
            create_result = await self.academic_year_repository.create_academic_year(academic_year_to_create)
            if create_result.is_error():
                return ServiceResult.service_error(create_result.error, create_result.status_code, msg.ACADEMIC_YEAR_SERVICE)
            
            academic_year_response = AcademicYearResponse.model_validate(create_result.data)
            try:
                cache_key = self._build_academic_year_cache_key(academic_year_response.id)
                await self.redis.save_pydantic_model_in_cache(cache_key, academic_year_response, ACADEMIC_YEAR_CACHE_TTL)
            except Exception:
                logger.warning(f"Impossible de sauvegarder dans le cache")
            
            return ServiceResult.service_success(academic_year_response, status._201_STATUS_CREATED, msg.ACADEMIC_YEAR_SERVICE)
        except Exception as e:
            logger.error(f"Erreur lors de la création : {e}")
            return ServiceResult.service_error("Une erreur est survenue lors de la création.", 500, msg.ACADEMIC_YEAR_SERVICE)