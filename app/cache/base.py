from datetime import timedelta
from typing import Optional, AsyncGenerator

from app.cache.cache_keys import CacheKey
from app.core.config import REDIS_URL
from redis.asyncio import Redis, ConnectionPool


class CacheWrapper:
    """Classe wrapper pour les opérations de cache, offrant une interface simple pour les opérations courantes."""

    _connection: Redis
    def __init__(self, connection: Redis):
        """Initialise le CacheWrapper avec une connection from pool de Redis."""
        self._connection = connection

    @staticmethod
    def _format_cache_key(cle: CacheKey) -> str:
        if len(cle.args) != cle.number_of_placeholders:
            raise ValueError(f"Nombre d'arguments fourni ({len(cle.args)}) ne correspond pas au nombre "
                             f"de placeholders attendu ({cle.number_of_placeholders}) pour la clé {cle.key}")

        return cle.key.value.format(cle.args)

    async def save_in_cache(self, key: CacheKey, value: str, expire_seconds: Optional[int | timedelta] = None) -> None:
        """
        Enregistre une valeur dans le cache avec une clé spécifique et une durée d'expiration optionnelle
        Args:
            key: La clé sous laquelle la valeur doit être enregistrée dans le cache, définie dans CacheKey
            value: La valeur à enregistrer dans le cache
            expire_seconds: La durée d'expiration en secondes ou en timedelta pour la clé de cache (optionnelle)

        Returns:
            Que dalle, cette méthode ne retourne rien, elle effectue simplement l'opération de cache
        """

        await self._connection.set(self._format_cache_key(key), value, ex=expire_seconds)


    async def delete_in_cache(self, key: CacheKey) -> None:
        """
        Supprime une valeur du cache en utilisant une clé spécifique
        Args:
            key: La clé de cache à supprimer, définie dans CacheKey

        Returns:
            Que dalle, cette méthode ne retourne rien, elle effectue simplement l'opération de suppression du cache
        """

        await self._connection.delete(self._format_cache_key(key))

    async def get_from_cache(self, key: CacheKey) -> Optional[str]:
        """
        Récupère une valeur du cache en utilisant une clé spécifique
        Args:
            key: La clé de cache à récupérer, définie dans CacheKey

        Returns:
            La valeur associée à la clé de cache si elle existe, sinon None
        """

        return await self._connection.get(self._format_cache_key(key))

    async def exists_in_cache(self, key: CacheKey) -> bool:
        """
        Vérifie si une clé de cache existe dans Redis
        Args:
            key: La clé de cache à vérifier, définie dans CacheKey

        Returns:
            True si la clé de cache existe, sinon False
        """

        return await self._connection.exists(self._format_cache_key(key)) == 1

    async def expire_in_cache(self, key: CacheKey, expire_seconds: Optional[int | timedelta] = None) -> None:
        """
        Met à jour la durée d'expiration d'une clé de cache existante
        Args:
            key: La clé de cache pour laquelle mettre à jour l'expiration, définie dans CacheKey
            expire_seconds: La nouvelle durée d'expiration en secondes ou en timedelta pour la clé de cache (optionnelle)

        Returns:
            Que dalle, cette méthode ne retourne rien, elle effectue simplement l'opération de mise à jour de l'expiration du cache
        """

        await self._connection.expire(self._format_cache_key(key), expire_seconds)

    async def ttl_in_cache(self, key: CacheKey) -> Optional[int]:
        """
        Récupère le temps restant avant l'expiration d'une clé de cache
        Args:
            key: La clé de cache pour laquelle récupérer le TTL, définie dans CacheKey

        Returns:
            Le temps restant en secondes avant l'expiration de la clé de cache, ou None si la clé n'existe pas ou n'a pas d'expiration
        """

        ttl = await self._connection.ttl(self._format_cache_key(key))
        return ttl if ttl >= 0 else None

    async def incr_in_cache(self, key: CacheKey, amount: int = 1) -> int:
        """
        Incrémente une valeur numérique dans le cache de manière atomique
        Args:
            key: La clé de cache à incrémenter, définie dans CacheKey
            amount: Le montant d'incrémentation (par défaut 1)

        Returns:
            La nouvelle valeur après incrémentation
        """

        return await self._connection.incr(self._format_cache_key(key), amount)

    async def decr_in_cache(self, key: CacheKey, amount: int = 1) -> int:
        """
        Décrémente une valeur numérique dans le cache de manière atomique
        Args:
            key: La clé de cache à décrémenter, définie dans CacheKey
            amount: Le montant de décrémentation (par défaut 1)

        Returns:
            La nouvelle valeur après décrémentation
        """

        return await self._connection.decr(self._format_cache_key(key), amount)

    def close(self) -> None:
        """
        Ferme la connexion Redis associée à ce CacheWrapper
        Returns:
            Que dalle, cette méthode ne retourne rien, elle effectue simplement l'opération de fermeture de la connexion Redis
        """
        self._connection.close()


class CacheManager:
    """Classe singleton pour gérer la connexion à Redis et les opérations de cache."""

    _instance = None

    _redis_client: Redis = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialise le CacheManager en créant une instance du client Redis."""
        self._pool = ConnectionPool.from_url(
            REDIS_URL,
            max_connections=20,  # Limite le nombre de connexions simultanées à Redis
            decode_responses=True  # Permet de décoder les réponses en string automatiquement
        )

    def get_redis_connection_from_pool(self) -> CacheWrapper:
        """Obtenir une instance du client Redis, en utilisant un pool de connexions pour une meilleure performance."""

        return CacheWrapper(Redis(connection_pool=self._pool))



cache_manager = CacheManager()  # singleton global

async def get_redis() -> AsyncGenerator[CacheWrapper]:
    """
    Fournit une instance CacheWrapper par requête FastAPI
    """
    redis_instance = cache_manager.get_redis_connection_from_pool()
    try:
        yield redis_instance
    finally:
        redis_instance.close()  # ferme juste le client, pas le pool