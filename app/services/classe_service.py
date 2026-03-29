import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.db.models.classe import Classe
from app.globals.messages import Messages as msg
from app.globals.status_codes import StatusCode as status
from app.repositories.academic_year_repository import AcademicYearRepository
from app.repositories.classe_repository import ClasseRepository
from app.schemas.classe_schemas import ClasseCreateRequest,ClasseListResponse,ClasseResponse,ClasseUpdateRequest
from app.schemas.global_schemas import StringMessage
from app.services import ServiceResult

logger = logging.getLogger(__name__)
CLASSE_CACHE_TTL = 3600  # 1 heure


class ClasseService:
    """Service pour les opérations sur les classes."""

    def __init__(self, db: AsyncSession, redis: CacheWrapper):
        self.db = db
        self.redis = redis
        self.classe_repository = ClasseRepository(db)
        self.academic_year_repository = AcademicYearRepository(db)

    def _build_classe_cache_key(self, classe_id: UUID):
        """Construit la clé de cache pour une classe par son ID."""
        return CacheKeysFactory.get_cache_key(AvailableCacheKeys.CLASSE_OBJECT).set_arguments(id=str(classe_id))

 

    async def get_classe_by_id(self, classe_id: UUID) -> ServiceResult[ClasseResponse]:
        """Récupère une classe par son ID — cache en priorité."""

        cache_key = self._build_classe_cache_key(classe_id)

        try:
            classe_from_cache = await self.redis.get_pydantic_model_from_cache(cache_key, ClasseResponse)
            if classe_from_cache is not None:
                logger.info(f"Classe {classe_id} trouvée dans le cache")
                return ServiceResult.service_success(classe_from_cache, status._200_STATUS_SUCCESS, msg.CLASSE_SERVICE)
        except Exception as e:
            logger.warning(f"Erreur cache lors de la récupération de la classe {classe_id}: {e}")

        classe_result = await self.classe_repository.get_classe_by_id(classe_id)
        if classe_result.is_error():
            return ServiceResult.service_error(classe_result.error, classe_result.status_code, msg.CLASSE_SERVICE)

        classe_response = ClasseResponse.model_validate(classe_result.data)

        try:
            await self.redis.save_pydantic_model_in_cache(cache_key, classe_response, CLASSE_CACHE_TTL)
            logger.info(f"Classe {classe_id} sauvegardée dans le cache")
        except Exception:
            logger.warning(f"Impossible de sauvegarder la classe {classe_id} dans le cache")

        return ServiceResult.service_success(classe_response, status._200_STATUS_SUCCESS, msg.CLASSE_SERVICE)

    async def get_all_classes(self, page: int = 1, page_size: int = 20) -> ServiceResult[ClasseListResponse]:
        """Récupère toutes les classes avec pagination."""

        classes_result = await self.classe_repository.get_all_classes(page, page_size)
        if classes_result.is_error():
            return ServiceResult.service_error(
                classes_result.error, classes_result.status_code, msg.CLASSE_SERVICE)

        classes, total = classes_result.data
        classes_response = [ClasseResponse.model_validate(c) for c in classes]

        return ServiceResult.service_success(
            ClasseListResponse(classes=classes_response,total=total,page=page,page_size=page_size),status._200_STATUS_SUCCESS,msg.CLASSE_SERVICE)

    async def create_classe(self, payload: ClasseCreateRequest) -> ServiceResult[ClasseResponse]:
        """Crée une nouvelle classe.
        """

        academic_year_result = await self.academic_year_repository.get_academic_year_by_id(payload.academic_year_id)
        if academic_year_result.is_error():
            return ServiceResult.service_error(msg.ACADEMIC_YEAR_NOT_FOUND,status._404_STATUS_NOT_FOUND,msg.CLASSE_SERVICE)


        existing = await self.classe_repository.get_classe_by_prefix_sufix_year(classe_prefix=payload.classe_prefix,classe_suffix=payload.classe_suffix,academic_year_id=payload.academic_year_id)
        if existing.is_success():
            return ServiceResult.service_error(msg.CLASSE_ALREADY_EXISTS,status._400_STATUS_BAD_REQUEST,msg.CLASSE_SERVICE)


        nouvelle_classe = Classe(classe_prefix=payload.classe_prefix,classe_suffix=payload.classe_suffix,academic_year_id=payload.academic_year_id)

        create_result = await self.classe_repository.create_classe(nouvelle_classe)
        if create_result.is_error():
            return ServiceResult.service_error(create_result.error, create_result.status_code, msg.CLASSE_SERVICE)

        classe_response = ClasseResponse.model_validate(create_result.data)

        try:
            cache_key = self._build_classe_cache_key(create_result.data.id)
            await self.redis.save_pydantic_model_in_cache(cache_key, classe_response, CLASSE_CACHE_TTL)
        except Exception:
            logger.warning("Impossible de sauvegarder la nouvelle classe dans le cache")

        return ServiceResult.service_success(classe_response, status._201_STATUS_CREATED, msg.CLASSE_SERVICE)

    async def update_classe(self, classe_id: UUID, payload: ClasseUpdateRequest) -> ServiceResult[ClasseResponse]:
        """Met à jour une classe existante."""

        classe_result = await self.classe_repository.get_classe_by_id(classe_id)
        if classe_result.is_error():
            return ServiceResult.service_error(classe_result.error, classe_result.status_code, msg.CLASSE_SERVICE)

        # 2. Mettre à jour uniquement les champs fournis
        fields = payload.model_dump(exclude_none=True)
        update_result = await self.classe_repository.update_classe(
            classe_result.data, **fields
        )
        if update_result.is_error():
            return ServiceResult.service_error(update_result.error, update_result.status_code, msg.CLASSE_SERVICE)

        classe_response = ClasseResponse.model_validate(update_result.data)

        try:
            cache_key = self._build_classe_cache_key(classe_id)
            await self.redis.save_pydantic_model_in_cache(cache_key, classe_response, CLASSE_CACHE_TTL)
            logger.info(f"Cache UPDATED — classe {classe_id}")
        except Exception:
            logger.warning(f"Cache WRITE ERROR après update — classe {classe_id}")

        return ServiceResult.service_success(classe_response, status._200_STATUS_SUCCESS, msg.CLASSE_SERVICE)

    async def delete_classe(self, classe_id: UUID) -> ServiceResult[StringMessage]:
        """Supprime une classe (soft delete) et invalide son cache."""

        classe_result = await self.classe_repository.get_classe_by_id(classe_id)
        if classe_result.is_error():
            return ServiceResult.service_error(classe_result.error, classe_result.status_code, msg.CLASSE_SERVICE)

        delete_result = await self.classe_repository.delete_classe(classe_result.data)
        if delete_result.is_error():
            return ServiceResult.service_error(delete_result.error, delete_result.status_code, msg.CLASSE_SERVICE)

        try:
            cache_key = self._build_classe_cache_key(classe_id)
            await self.redis.delete_in_cache(cache_key)
            logger.info(f"Cache INVALIDATED — classe {classe_id}")
        except Exception:
            logger.warning(f"Cache DELETE ERROR — classe {classe_id}")

        return ServiceResult.service_success(StringMessage(message="Classe supprimée avec succès."),status._200_STATUS_SUCCESS,msg.CLASSE_SERVICE)