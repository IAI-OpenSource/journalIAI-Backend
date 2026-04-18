import logging
from uuid import UUID

from app.cache.cache_utils import CacheUtils
from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.base import CacheWrapper
from app.cache.helpers.cache_keys import CacheKey
from app.cache.helpers.keys_factory import CacheKeysFactory

logger = logging.getLogger(__name__)


def _liked_posts_key(user_id: UUID) -> CacheKey:
    """Génère la clé Redis pour les posts likés par un utilisateur."""
    return CacheKeysFactory.get_cache_key(AvailableCacheKeys.USER_DAILY_POST_LIKED).set_arguments(id=str(user_id))


def _daily_liked_posts_key() -> CacheKey:
    """Génère la clé Redis pour le SET journalier des utilisateurs ayant liké un post."""
    return CacheKeysFactory.get_cache_key(AvailableCacheKeys.USERS_HAS_LIKED_POST_ON_A_DAY).set_arguments()


class LikeCache:
    """Cache Redis pour la gestion des posts likés par utilisateur.
    """

    def __init__(self, cache: CacheWrapper):
        self._cache = cache

    async def get_daily_liked_post_ids(self, user_id: UUID) -> list[UUID] | None:
        """Récupère la liste des UUIDs de posts likés par l'utilisateur.

        Commande Redis : SMEMBERS user:{user_id}:liked_posts

        Args:
            user_id: ID de l'utilisateur.

        Returns:
            Liste de UUIDs si Redis répond, None si Redis crash.
            None déclenche le fallback PostgreSQL dans le service.
        """
        try:
            key = _liked_posts_key(user_id)
            members = await self._cache.get_from_a_set(key)
            result = [UUID(m) for m in members]
            logger.debug(
                "Cache hit liked_posts user=%s count=%d", user_id, len(result)
            )
            return result
        except Exception as e:
            logger.warning(
                "Redis unavailable (get_liked_posts) user=%s : %s — fallback PostgreSQL",
                user_id,
                e,
            )
            return None

    async def mark_posts_as_liked(self, user_id: UUID, post_ids: list[UUID]) -> int | None:
        """Marque une liste de posts comme likés dans Redis.

        Opérations :
        1. SADD batch (un seul appel pour N posts)
        2. EXPIRE pour renouveler le TTL

        Args:
            user_id: ID de l'utilisateur.
            post_ids: Liste des posts à marquer comme likés.

        Returns:
            Nombre de posts ajoutés au SET, None si erreur Redis.
        """
        if not post_ids:
            return None

        try:
            key = _liked_posts_key(user_id)
            str_ids = [str(pid) for pid in post_ids]

            res = await self._cache.add_to_a_set(key, *str_ids)

            logger.debug(
                "Posts marqués comme likés user=%s total_set=%d",
                user_id,
                res,
            )
            return res

        except Exception as e:
            logger.error(
                "Erreur lors du marquage d'un post comme liké user_id=%s, post_ids=%s",
                user_id,
                post_ids,
            )
            CacheUtils.traiter_exceptions(e, logger)
            return None

    async def clear_daily_liked_posts_for_user(self, user_id: UUID) -> None:
        """Supprime complètement le SET des posts likés (ex: reset des likes).

        Rarement utilisé — préférer mark_posts_as_liked qui est idempotent.

        Args:
            user_id: ID de l'utilisateur.
        """
        try:
            key = _liked_posts_key(user_id)
            await self._cache.delete_in_cache(key)
            logger.info("SET liked_posts supprimé avec succès user=%s", user_id)
        except Exception as e:
            logger.warning(
                "Redis unavailable (clear_liked_posts) user=%s : %s", user_id, e
            )

    async def add_user_to_daily_liked_posts(self, user_id: UUID) -> None:
        """Ajoute un utilisateur au SET journalier des utilisateurs ayant liké un post.

        Args:
            user_id: ID de l'utilisateur.

        Returns:
            None
        """
        try:
            key = _daily_liked_posts_key()
            user_to_add = [str(user_id)]
            await self._cache.add_to_a_set(key, *user_to_add)

        except Exception as e:
            logger.error(
                "Erreur lors d'un insert d'user (%s) dans le set journalier des users ayant liké",
                user_id,
            )
            CacheUtils.traiter_exceptions(e, logger)

    async def get_daily_users_liked_posts_set(self) -> set[str] | None:
        """Récupère le SET journalier des utilisateurs ayant liké un post.

        Returns:
            SET des UUIDs d'utilisateurs si Redis répond, None si erreur.
        """
        try:
            key = _daily_liked_posts_key()
            res = await self._cache.get_from_a_set(key)
            logger.info("Set journalier des users ayant liké récupéré avec succès")
            return res
        except Exception as e:
            logger.error(
                "Erreur lors la recup du SET journalier des users ayant liké"
            )
            CacheUtils.traiter_exceptions(e, logger)

    async def restart_daily_users_liked_posts_set(self) -> None:
        """Réinitialise le SET journalier des utilisateurs ayant liké un post.

        Returns:
            None
        """
        try:
            key = _daily_liked_posts_key()
            await self._cache.delete_in_cache(key)
            logger.info("Set journalier des users ayant liké réinitialisé avec succès")
        except Exception as e:
            logger.error(
                "Erreur lors du restart du SET journalier des users ayant liké"
            )
            CacheUtils.traiter_exceptions(e, logger)
