from typing import Optional
from app.cache.helpers.base import CacheWrapper
from app.schemas.clubs_schemas import ClubResponse
from app.cache.helpers import keys_factory
from app.cache.helpers.availables import AvailableCacheKeys

CLUB_BY_ID_KEY = keys_factory.CacheKeysFactory.get_cache_key(AvailableCacheKeys.CLUB_OBJECT)

class ClubCache:
    def __init__(self, redis:CacheWrapper)-> None:
        self._redis = redis

    async def get_club_by_id(self, club_id: str)-> Optional[ClubResponse]:
        """Récupère un club depuis le cache en utilisant son ID.
        
        Args:
            club_id (str): L'identifiant du club à récupérer.
            
        Returns:
            Optional[dict]: Les données du club si trouvées dans le cache, sinon None.
        """
        cache_key = CLUB_BY_ID_KEY.set_arguments(id=club_id)
        return await self._redis.get_pydantic_model_from_cache(cache_key, ClubResponse)
    
    
    async def set_club_in_cache(self, club_data: ClubResponse, expire_seconds: int = 3600) -> None:
        """Stocke les données d'un club dans le cache avec une clé basée sur son ID.
        
        Args:
            club_id (str): L'identifiant du club à stocker dans le cache.
            club_data (ClubResponse): Les données du club à stocker dans le cache.
            expire_seconds (int): Le temps d'expiration du cache en secondes (par défaut 3600 secondes, soit 1 heure).
        """
        cache_key = CLUB_BY_ID_KEY.set_arguments(id=str(club_data.id))
        await self._redis.save_pydantic_model_in_cache(cache_key, club_data, expire_seconds)

    async def delete_club_from_cache(self, club_id: str) -> None:
        """Supprime les données d'un club du cache en utilisant son ID.
        
        Args:
            club_id (str): L'identifiant du club à supprimer du cache.
        """
        cache_key = CLUB_BY_ID_KEY.set_arguments(id=club_id)
        await self._redis.delete_in_cache(cache_key)