from typing import Optional, List
from uuid import UUID
from logging import getLogger
import redis
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.cache_keys import CacheKey
from app.cache.helpers.keys_factory import CacheKeysFactory
from app.schemas.club_member_schema import ClubMemberRead

logger = getLogger(__name__)


class ClubMemberCache:
    def __init__(self, cache: CacheWrapper):
        self.cache = cache

    # -------------------------------------------------------------------------
    # Clés de cache
    # -------------------------------------------------------------------------

    def create_member_cache_key(self, member_id: UUID) -> CacheKey:
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.CLUB_MEMBER_OBJECT
        ).set_arguments(id=str(member_id))

    def create_member_list_cache_key(self, club_id: UUID) -> CacheKey:
        return CacheKeysFactory.get_cache_key(
            AvailableCacheKeys.CLUB_MEMBER_LIST
        ).set_arguments(id=str(club_id))

    # -------------------------------------------------------------------------
    # Cache : membre unique
    # -------------------------------------------------------------------------

    async def set_member_in_cache(self, member_id: UUID, member: ClubMemberRead, ttl: int) -> None:
        try:
            cache_key = self.create_member_cache_key(member_id)
            await self.cache.save_pydantic_model_in_cache(
                key=cache_key,
                model_instance=member,
                expire_seconds=ttl
            )
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la mise en cache du membre {member_id}")
        except Exception:
            logger.exception(f"Erreur lors de la mise en cache du membre {member_id}")

    async def get_member_from_cache(self, member_id: UUID) -> Optional[ClubMemberRead]:
        try:
            cache_key = self.create_member_cache_key(member_id)
            return await self.cache.get_pydantic_model_from_cache(
                key=cache_key,
                model_class=ClubMemberRead
            )
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la récupération du membre {member_id}")
            return None
        except Exception:
            logger.exception(f"Erreur lors de la récupération du membre {member_id}")
            return None

    async def delete_member_from_cache(self, member_id: UUID) -> None:
        try:
            cache_key = self.create_member_cache_key(member_id)
            await self.cache.delete_in_cache(key=cache_key)
            logger.info(f"Membre {member_id} supprimé du cache avec succès")
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la suppression du membre {member_id}")
        except Exception:
            logger.exception(f"Erreur lors de la suppression du membre {member_id} du cache")

    # -------------------------------------------------------------------------
    # Cache : liste des membres d'un club
    # -------------------------------------------------------------------------

    async def set_members_list_in_cache(
        self, club_id: UUID, members: List[ClubMemberRead], ttl: int
    ) -> None:
        try:
            cache_key = self.create_member_list_cache_key(club_id)
            await self.cache.save_list_in_cache(
                key=cache_key,
                value=[m.model_dump(mode="json") for m in members],
                expire_seconds=ttl
            )
            logger.info(f"Liste des membres du club {club_id} mise en cache avec succès")
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la mise en cache des membres du club {club_id}")
        except Exception:
            logger.exception(f"Erreur lors de la mise en cache des membres du club {club_id}")

    async def get_members_list_from_cache(self, club_id: UUID) -> Optional[List[ClubMemberRead]]:
        try:
            cache_key = self.create_member_list_cache_key(club_id)
            raw = await self.cache.get_list_from_cache(key=cache_key)
            if raw is None:
                return None
            return [ClubMemberRead(**item) for item in raw]
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la récupération des membres du club {club_id}")
            return None
        except Exception:
            logger.exception(f"Erreur lors de la récupération des membres du club {club_id}")
            return None

    async def delete_members_list_from_cache(self, club_id: UUID) -> None:
        try:
            cache_key = self.create_member_list_cache_key(club_id)
            await self.cache.delete_in_cache(key=cache_key)
            logger.info(f"Cache liste membres du club {club_id} supprimé avec succès")
        except redis.ConnectionError:
            logger.exception(f"Erreur de connexion Redis lors de la suppression du cache membres du club {club_id}")
        except Exception:
            logger.exception(f"Erreur lors de la suppression du cache membres du club {club_id}")