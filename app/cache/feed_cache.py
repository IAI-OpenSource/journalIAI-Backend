## Cache Redis pour la gestion des posts vus par utilisateur.
## Implémente la spec technique Feed IAI-Togo v2.0 :
## - Clé : user:{user_id}:seen_posts (SET Redis)
## - TTL : 7 jours (604800 secondes)
## - Taille max : 2000 posts par utilisateur (SPOP si dépassement)
## - Fallback PostgreSQL si Redis crash

import logging
from uuid import UUID

from app.cache.helpers.base import CacheWrapper

logger = logging.getLogger(__name__)

# TTL du SET Redis en secondes (7 jours)
SEEN_POSTS_TTL = 60 * 60 * 24 * 7

# Nombre maximum de posts vus stockés par utilisateur dans Redis
# Au-delà, SPOP supprime l'excès aléatoirement
MAX_SEEN_POSTS = 2000

# Clé Redis : user:{user_id}:seen_posts
def _seen_posts_key(user_id: UUID) -> str:
    return f"user:{user_id}:seen_posts"


class FeedCache:
    """Cache Redis pour les posts vus dans le feed.

    Toutes les méthodes wrappent les opérations Redis dans des try/except
    pour ne jamais laisser une erreur Redis bloquer le feed de l'utilisateur.
    Le fallback PostgreSQL est géré au niveau du service.
    """

    def __init__(self, cache: CacheWrapper):
        self.cache = cache

    async def get_seen_post_ids(self, user_id: UUID) -> list[str] | None:
        """Récupère la liste des UUIDs de posts déjà vus par l'utilisateur.

        Commande Redis : SMEMBERS user:{user_id}:seen_posts

        Returns:
            Liste de strings (UUIDs) si Redis répond, None si Redis crash.
            None déclenche le fallback PostgreSQL dans le service.
        """
        try:
            key = _seen_posts_key(user_id)
            members = await self.cache.smembers(key)
            # smembers retourne un set Python vide {} si la clé n'existe pas
            result = [m.decode() if isinstance(m, bytes) else m for m in members]
            logger.debug(
                "Cache hit seen_posts user=%s count=%d", user_id, len(result)
            )
            return result
        except Exception as e:
            logger.warning(
                "Redis unavailable (get_seen_posts) user=%s : %s — fallback PostgreSQL",
                user_id, e,
            )
            return None  # Signal fallback

    async def mark_posts_as_seen(self, user_id: UUID, post_ids: list[UUID]) -> None:
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
            return

        try:
            key = _seen_posts_key(user_id)

            # 1. SADD batch — un seul appel réseau pour tous les posts
            str_ids = [str(pid) for pid in post_ids]
            await self.cache.sadd(key, *str_ids)

            # 2. Renouveler le TTL à chaque activité (sliding window 7j)
            await self.cache.expire(key, SEEN_POSTS_TTL)

            # 3. Vérifier la taille du SET
            count = await self.cache.scard(key)

            # 4. SPOP si dépassement (suppression aléatoire de l'excès)
            if count > MAX_SEEN_POSTS:
                excess = count - MAX_SEEN_POSTS
                await self.cache.spop(key, excess)
                logger.info(
                    "SET seen_posts tronqué user=%s excess=%d", user_id, excess
                )

            logger.debug(
                "Posts marqués comme vus user=%s count=%d total_set=%d",
                user_id, len(post_ids), min(count, MAX_SEEN_POSTS),
            )

        except Exception as e:
            logger.warning(
                "Redis unavailable (mark_as_seen) user=%s : %s",
                user_id, e,
            )
            # Pas de raise — une erreur ici ne doit pas bloquer la réponse client

    async def clear_seen_posts(self, user_id: UUID) -> None:
        """Supprime complètement le SET des posts vus (ex: pull-to-refresh total).

        Rarement utilisé — préférer mark_posts_as_seen qui est idempotent.
        """
        try:
            key = _seen_posts_key(user_id)
            await self.cache.delete(key)
            logger.info("SET seen_posts supprimé user=%s", user_id)
        except Exception as e:
            logger.warning(
                "Redis unavailable (clear_seen_posts) user=%s : %s", user_id, e
            )

    async def get_seen_count(self, user_id: UUID) -> int:
        """Retourne le nombre de posts vus dans Redis (SCARD). Utile pour monitoring."""
        try:
            key = _seen_posts_key(user_id)
            return await self.cache.scard(key)
        except Exception:
            return 0