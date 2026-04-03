from typing import Optional
from uuid import UUID
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.schemas.academic_year_schemas import AcademicYearResponse

ACADEMIC_YEAR_BY_ID_KEY = CacheKeysFactory.get_cache_key(AvailableCacheKeys.ACADEMIC_YEAR_OBJECT)
ACADEMIC_YEAR_ACTIVE_KEY = ACADEMIC_YEAR_BY_ID_KEY.set_arguments(id="active")


class AcademicYearCache:
    def __init__(self, redis: CacheWrapper) -> None:
        self._redis = redis

    async def get_academic_year_by_id(self, academic_year_id: str) -> Optional[AcademicYearResponse]:
        cache_key = ACADEMIC_YEAR_BY_ID_KEY.set_arguments(id=academic_year_id)
        return await self._redis.get_pydantic_model_from_cache(cache_key, AcademicYearResponse)

    async def set_academic_year_in_cache(self, academic_year_data: AcademicYearResponse, expire_seconds: int = 3600) -> None:
        cache_key = ACADEMIC_YEAR_BY_ID_KEY.set_arguments(id=str(academic_year_data.id))
        await self._redis.save_pydantic_model_in_cache(cache_key, academic_year_data, expire_seconds)

    async def delete_academic_year_from_cache(self, academic_year_id: str) -> None:
        cache_key = ACADEMIC_YEAR_BY_ID_KEY.set_arguments(id=academic_year_id)
        await self._redis.delete_in_cache(cache_key)

    async def get_active_academic_year(self) -> Optional[AcademicYearResponse]:
        """Récupère l'année académique active depuis le cache."""
        return await self._redis.get_pydantic_model_from_cache(ACADEMIC_YEAR_ACTIVE_KEY, AcademicYearResponse)
 
    async def set_active_academic_year_in_cache(self, academic_year_data: AcademicYearResponse, expire_seconds: int = 3600) -> None:
        """Sauvegarde l'année académique active dans le cache."""
        await self._redis.save_pydantic_model_in_cache(ACADEMIC_YEAR_ACTIVE_KEY, academic_year_data, expire_seconds)
 
    async def delete_active_academic_year_from_cache(self) -> None:
        """Invalide le cache de l'année académique active."""
        await self._redis.delete_in_cache(ACADEMIC_YEAR_ACTIVE_KEY)
 