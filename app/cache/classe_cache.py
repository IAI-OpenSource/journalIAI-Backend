from typing import Optional
from uuid import UUID
 
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.schemas.classe_schemas import ClasseResponse
 
CLASSE_BY_ID_KEY = CacheKeysFactory.get_cache_key(AvailableCacheKeys.CLASSE_OBJECT)
 
 
class ClasseCache:
    def __init__(self, redis: CacheWrapper) -> None:
        self._redis = redis
 
    async def get_classe_by_id(self, classe_id: str) -> Optional[ClasseResponse]:
        cache_key = CLASSE_BY_ID_KEY.set_arguments(id=classe_id)
        return await self._redis.get_pydantic_model_from_cache(cache_key, ClasseResponse)
 
    async def set_classe_in_cache(self, classe_data: ClasseResponse, expire_seconds: int = 3600) -> None:
        cache_key = CLASSE_BY_ID_KEY.set_arguments(id=str(classe_data.id))
        await self._redis.save_pydantic_model_in_cache(cache_key, classe_data, expire_seconds)
 
    async def delete_classe_from_cache(self, classe_id: str) -> None:
        cache_key = CLASSE_BY_ID_KEY.set_arguments(id=classe_id)
        await self._redis.delete_in_cache(cache_key)