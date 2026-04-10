## Cache Redis pour la gestion des posts vus par utilisateur.
## Implémente la spec technique Feed IAI-Togo v2.0 :
## - Clé : user:{user_id}:seen_posts (SET Redis)
## - TTL : 7 jours (604800 secondes)
## - Taille max : 2000 posts par utilisateur (SPOP si dépassement)
## - Fallback PostgreSQL si Redis crash

import logging
from uuid import UUID

from app.cache.cache_utils import CacheUtils
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.cache_keys import CacheKey
from app.cache.helpers.keys_factory import CacheKeysFactory

logger = logging.getLogger(__name__)


# Clé Redis : user:{user_id}:seen_posts
def _seen_posts_key(user_id: UUID) -> CacheKey:
    return CacheKeysFactory.get_cache_key(AvailableCacheKeys.USER_DAILY_POST_SEEN).set_arguments(id=str(user_id))

def _daily_seen_posts_key() -> CacheKey:
    return CacheKeysFactory.get_cache_key(AvailableCacheKeys.USERS_HAS_SEEN_POST_ON_A_DAY).set_arguments()


class FeedCache:
    """Cache Redis pour les posts vus dans le feed.

    Toutes les méthodes wrappent les opérations Redis dans des try/except
    pour ne jamais laisser une erreur Redis bloquer le feed de l'utilisateur.
    Le fallback PostgreSQL est géré au niveau du service.
    """

    def __init__(self, cache: CacheWrapper):
        self.cache = cache

    async def get_daily_seen_post_ids(self, user_id: UUID) -> list[UUID] | None:
        """Récupère la liste des UUIDs de posts déjà vus par l'utilisateur.

        Commande Redis : SMEMBERS user:{user_id}:seen_posts

        Returns:
            Liste de strings (UUIDs) si Redis répond, None si Redis crash.
            None déclenche le fallback PostgreSQL dans le service.
        """
        try:
            key = _seen_posts_key(user_id)
            members = await self.cache.get_from_a_set(key)
            result = [UUID(m) for m in members]
            logger.debug(
                "Cache hit seen_posts user=%s count=%d", user_id, len(result)
            )
            return result
        except Exception as e:
            logger.warning(
                "Redis unavailable (get_seen_posts) user=%s : %s — fallback PostgreSQL",
                user_id, e,
            )
            return None

    async def mark_posts_as_seen(self, user_id: UUID, post_ids: list[UUID]) -> int | None:
        """Marque une liste de posts comme vus dans Redis.

        Opérations :
        1. SADD batch (un seul appel pour N posts)
        2. EXPIRE pour renouveler le TTL à 7 jours
        3. SCARD pour compter
        4. SPOP si dépassement de MAX_SEEN_POSTS

        Args:
            user_id: ID de l'utilisateur.
            post_ids: Liste des posts à marquer comme vus.
        """
        if not post_ids:
            return None

        try:
            key = _seen_posts_key(user_id)

            str_ids = [str(pid) for pid in post_ids]

            res = await self.cache.add_to_a_set(key, *str_ids)

            logger.debug(
                "Posts marqués comme vus user=%s total_set=%d",
                user_id, res
            )
            return res

        except Exception as e:
            logger.error(f"Erreur lors du marquage d'un post comme vu user_id = {user_id}, post_id = {post_ids}")
            CacheUtils.traiter_exceptions(e, logger)
            return None

            # Pas de raise — une erreur ici ne doit pas bloquer la réponse client

    async def clear_daily_seen_posts_for_user(self, user_id: UUID) -> None:
        """Supprime complètement le SET des posts vus (ex: pull-to-refresh total).

        Rarement utilisé — préférer mark_posts_as_seen qui est idempotent.
        """
        try:
            key = _seen_posts_key(user_id)
            await self.cache.delete_in_cache(key)
            logger.info("SET seen_posts supprimé avec succès user=%s", user_id)
        except Exception as e:
            logger.warning(
                "Redis unavailable (clear_seen_posts) user=%s : %s", user_id, e
            )

    async def add_user_to_daily_seen_posts(self, user_id: UUID) -> None:

        try:
            key = _daily_seen_posts_key()
            user_to_add = [str(user_id)]
            await self.cache.add_to_a_set(key, *user_to_add)

        except Exception as e:
            logger.error(f"Erreur lors d'un insert d'user ({user_id}) dans le set journalier des users")
            CacheUtils.traiter_exceptions(e, logger)

    async def get_daily_users_seen_posts_set(self) -> set[str] | None:
        try:
            key = _daily_seen_posts_key()
            res = await self.cache.get_from_a_set(key)
            logger.info("Set journalier des users récupéré avec succès")
            return res
        except Exception as e:
            logger.error("Erreur lors la recup du Set journalier des users")
            CacheUtils.traiter_exceptions(e, logger)

    async def restart_daily_users_seen_posts_set(self) -> None:
        try:
            key = _daily_seen_posts_key()
            await self.cache.delete_in_cache(key)
            logger.info("Set journalier des users restatrt avec succès")
        except Exception as e:
            logger.error("Erreur lors du restart du Set journalier des users")
            CacheUtils.traiter_exceptions(e, logger)