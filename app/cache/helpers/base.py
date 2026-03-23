from datetime import timedelta
from json import dumps, loads, JSONDecodeError
from typing import Optional, Any, AsyncIterator, AsyncGenerator

from pydantic import BaseModel, ValidationError
from redis.asyncio.client import PubSub

from app.cache.helpers.cache_keys import CacheKey
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

        return cle.key.value.format(**cle.args)

    @staticmethod
    def _serialize(value: Any) -> str:
        if isinstance(value, BaseModel):
            return value.model_dump_json()
        if isinstance(value, (str, int, float)):
            return str(value)
        try:
            return dumps(value)
        except TypeError:
            raise ValueError(f"Type de valeur non sérialisable pour le cache: {type(value)}")

    @staticmethod
    def _deserialize(value: str) -> Any:
        try:
            return loads(value)
        except JSONDecodeError:
            return value

    async def __save_in_cache(self, key: CacheKey, value: Any, expire_seconds: Optional[int | timedelta] = None) -> None:
        """
        Enregistre une valeur dans le cache avec une clé spécifique et une durée d'expiration optionnelle
        Args:
            key: La clé sous laquelle la valeur doit être enregistrée dans le cache, définie dans CacheKey
            value: La valeur à enregistrer dans le cache
            expire_seconds: La durée d'expiration en secondes ou en timedelta pour la clé de cache (optionnelle)

        Returns:
            Que dalle, cette méthode ne retourne rien, elle effectue simplement l'opération de cache
        Raises:
            ValueError: Si la valeur fournie n'est pas sérialisable pour le cache
        """

        await self._connection.set(self._format_cache_key(key), value, ex=expire_seconds)

    async def save_pydantic_model_in_cache(self, key: CacheKey, model_instance: BaseModel, expire_seconds: Optional[int | timedelta] = None) -> None:
        """
        Enregistre une instance de modèle Pydantic dans le cache avec une clé spécifique et une durée d'expiration optionnelle
        Args:
            key: La clé sous laquelle l'instance du modèle Pydantic doit être enregistrée dans le cache, définie dans CacheKey
            model_instance: L'instance du modèle Pydantic à enregistrer dans le cache
            expire_seconds: La durée d'expiration en secondes ou en timedelta pour la clé de cache (optionnelle)

        Returns:
            Que dalle, cette méthode ne retourne rien, elle effectue simplement l'opération de cache
        Raises:
            ValueError: Si l'instance du modèle Pydantic fournie n'est pas sérialisable pour le cache
        """

        if not isinstance(model_instance, BaseModel):
            raise ValueError(f"Type de valeur non pris en charge pour save_pydantic_model_in_cache: {type(model_instance)}. Seules les instances de BaseModel sont autorisées.")

        serialized_model = self._serialize(model_instance)
        await self.__save_in_cache(key, serialized_model, expire_seconds)

    async def save_dict_in_cache(self, key: CacheKey, value: dict, expire_seconds: Optional[int | timedelta] = None) -> None:
        """
        Enregistre un dictionnaire dans le cache avec une clé spécifique et une durée d'expiration optionnelle
        Args:
            key: La clé sous laquelle le dictionnaire doit être enregistré dans le cache, définie dans CacheKey
            value: Le dictionnaire à enregistrer dans le cache
            expire_seconds: La durée d'expiration en secondes ou en timedelta pour la clé de cache (optionnelle)

        Returns:
            Que dalle, cette méthode ne retourne rien, elle effectue simplement l'opération de cache
        Raises:
            ValueError: Si le dictionnaire fourni n'est pas sérialisable pour le cache
        """
        if not isinstance(value, dict):
            raise ValueError(f"Type de valeur non pris en charge pour save_dict_in_cache: {type(value)}. Seules les valeurs de type dict sont autorisées.")

        serialized_dict = self._serialize(value)
        await self.__save_in_cache(key, serialized_dict, expire_seconds)

    async def save_primitive_in_cache(self, key: CacheKey, value: str | int | float, expire_seconds: Optional[int | timedelta] = None) -> None:
        """
        Enregistre une valeur primitive (str, int, float) dans le cache avec une clé spécifique et une durée d'expiration optionnelle
        Args:
            key: La clé sous laquelle la valeur primitive doit être enregistrée dans le cache, définie dans CacheKey
            value: La valeur primitive à enregistrer dans le cache (str, int ou float)
            expire_seconds: La durée d'expiration en secondes ou en timedelta pour la clé de cache (optionnelle)

        Returns:
            Que dalle, cette méthode ne retourne rien, elle effectue simplement l'opération de cache
        Raises:
            ValueError: Si la valeur fournie n'est pas une valeur primitive sérialisable pour le cache
        """

        if not isinstance(value, (str, int, float)):
            raise ValueError(f"Type de valeur non pris en charge pour save_primitive_in_cache: {type(value)}. Seules les valeurs de type str, int ou float sont autorisées.")

        await self.__save_in_cache(key, value, expire_seconds)

    async def save_list_in_cache(self, key: CacheKey, value: list, expire_seconds: Optional[int | timedelta] = None) -> None:
        """
        Enregistre une liste dans le cache avec une clé spécifique et une durée d'expiration optionnelle
        Args:
            key: La clé sous laquelle la liste doit être enregistrée dans le cache, définie dans CacheKey
            value: La liste à enregistrer dans le cache
            expire_seconds: La durée d'expiration en secondes ou en timedelta pour la clé de cache (optionnelle)

        Returns:
            Que dalle, cette méthode ne retourne rien, elle effectue simplement l'opération de cache
        Raises:
            ValueError: Si la liste fournie n'est pas sérialisable pour le cache
        """
        if not isinstance(value, list):
            raise ValueError(f"Type de valeur non pris en charge pour save_list_in_cache: {type(value)}. Seules les valeurs de type list sont autorisées.")

        serialized_list = self._serialize(value)
        await self.__save_in_cache(key, serialized_list, expire_seconds)

    async def delete_in_cache(self, key: CacheKey) -> None:
        """
        Supprime une valeur du cache en utilisant une clé spécifique
        Args:
            key: La clé de cache à supprimer, définie dans CacheKey

        Returns:
            Que dalle, cette méthode ne retourne rien, elle effectue simplement l'opération de suppression du cache
        """

        await self._connection.delete(self._format_cache_key(key))

    async def __get_from_cache(self, key: CacheKey) -> Optional[str]:
        """
        Récupère une valeur du cache en utilisant une clé spécifique
        Args:
            key: La clé de cache à récupérer, définie dans CacheKey

        Returns:
            La valeur associée à la clé de cache si elle existe, sinon None
        """

        return await self._connection.get(self._format_cache_key(key))

    async def get_pydantic_model_from_cache(self, key: CacheKey, model_class: type[BaseModel]) -> Optional[BaseModel]:
        """
        Récupère une valeur du cache en utilisant une clé spécifique et la désérialise en un modèle Pydantic
        Args:
            key: La clé de cache à récupérer, définie dans CacheKey
            model_class: La classe du modèle Pydantic dans laquelle désérialiser la valeur récupérée

        Returns:
            Une instance du modèle Pydantic associée à la clé de cache si elle existe et peut être désérialisée, sinon None
        Raises:
            ValueError: Si la valeur récupérée du cache ne peut pas être désérialisée en une instance du modèle Pydantic spécifié, ou si la validation échoue
        """

        cached_value = await self.__get_from_cache(key)
        if cached_value is not None:
            try:
                return model_class.model_validate(cached_value)
            except ValidationError:
                raise ValueError(f"Erreur de validation lors de la désérialisation de la valeur du cache pour la clé {key}: "
                                 f"la valeur récupérée ne correspond pas au modèle {model_class.__name__}")
        return None

    async def get_dict_from_cache(self, key: CacheKey) -> Optional[dict]:
        """
        Récupère une valeur du cache en utilisant une clé spécifique et la désérialise en un dictionnaire
        Args:
            key: La clé de cache à récupérer, définie dans CacheKey

        Returns:
            Un dictionnaire associé à la clé de cache si elle existe et peut être désérialisée, sinon None
        Raises:
            ValueError: Si la valeur récupérée du cache ne peut pas être désérialisée en un dictionnaire
        """

        cached_value = await self.__get_from_cache(key)
        if cached_value is not None:
            deserialized_value = self._deserialize(cached_value)
            if isinstance(deserialized_value, dict):
                return deserialized_value
            else:
                raise ValueError(f"Erreur de désérialisation pour la clé {key}: la valeur récupérée n'est pas un dictionnaire")
        return None

    async def get_primitive_from_cache(self, key: CacheKey) -> Optional[str | int | float]:
        """
        Récupère une valeur du cache en utilisant une clé spécifique et la désérialise en une valeur primitive (str, int ou float)
        Args:
            key: La clé de cache à récupérer, définie dans CacheKey

        Returns:
            Une valeur primitive (str, int ou float) associée à la clé de cache si elle existe et peut être désérialisée, sinon None
        Raises:
            ValueError: Si la valeur récupérée du cache ne peut pas être désérialisée en une valeur primitive
        """

        cached_value = await self.__get_from_cache(key)
        if cached_value is not None:
            deserialized_value = self._deserialize(cached_value)
            if isinstance(deserialized_value, (str, int, float)):
                return deserialized_value
            else:
                raise ValueError(f"Erreur de désérialisation pour la clé {key}: la valeur récupérée n'est pas une valeur primitive (str, int ou float)")
        return None

    async def get_list_from_cache(self, key: CacheKey) -> Optional[list]:
        """
        Récupère une valeur du cache en utilisant une clé spécifique et la désérialise en une liste
        Args:
            key: La clé de cache à récupérer, définie dans CacheKey

        Returns:
            Une liste associée à la clé de cache si elle existe et peut être désérialisée, sinon None
        Raises:
            ValueError: Si la valeur récupérée du cache ne peut pas être désérialisée en une liste
        """

        cached_value = await self.__get_from_cache(key)
        if cached_value is not None:
            deserialized_value = self._deserialize(cached_value)
            if isinstance(deserialized_value, list):
                return deserialized_value
            else:
                raise ValueError(f"Erreur de désérialisation pour la clé {key}: la valeur récupérée n'est pas une liste")
        return None

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
        Assurez vous que la valeur associée à la clé de cache est un entier avant d'utiliser cette méthode,
        sinon une erreur sera levée par Redis
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
        Assurez vous que la valeur associée à la clé de cache est un entier avant d'utiliser cette méthode,
        sinon une erreur sera levée par Redis
        Args:
            key: La clé de cache à décrémenter, définie dans CacheKey
            amount: Le montant de décrémentation (par défaut 1)

        Returns:
            La nouvelle valeur après décrémentation
        """

        return await self._connection.decr(self._format_cache_key(key), amount)


    async def pub_sub_publish_message(self, channel: CacheKey, message: Any) -> int:
        """
        Publie un message sur un canal PubSub spécifique .
        Args:
            channel: La clé représentant le canal, définie dans CacheKey.
            message: Le message à publier (sera sérialisé automatiquement).
        Returns:
            Le nombre d'abonnés ayant reçu le message.
        """
        serialized_msg = self._serialize(message)
        return await self._connection.publish(self._format_cache_key(channel), serialized_msg)

    def get_pubsub_instance(self) -> PubSub:
        """
        Retourne une instance PubSub pour s'abonner (subscribe) aux canaux.
        Attention : Cette méthode n'est pas async, mais l'objet retourné s'utilise de manière asynchrone.
        Returns:
            Une instance PubSub configurée sur la connexion actuelle.
        """
        return self._connection.pubsub()

    async def pub_sub_channel_listener(self, channel: CacheKey) -> AsyncGenerator[Any, None]:
        """
        Souscrit à un channel et écoute les messages, cette methode est async generator donc elle yield les messages reçus sur le channel de manière asynchrone.
        Args:
            channel: La clé représentant le canal, définie dans CacheKey.
        Yields:
            Les messages reçus sur le canal
        """
        pubsub = self._connection.pubsub()
        await pubsub.subscribe(self._format_cache_key(channel))

        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue

                raw_data = message["data"]

                if isinstance(raw_data, bytes):
                    raw_data = raw_data.decode()

                yield raw_data
        finally:
            await pubsub.unsubscribe(self._format_cache_key(channel))
            await pubsub.close()


    async def stream_add(self, key: CacheKey, fields: dict, maxlen: Optional[int] = 10000) -> str:
        """
        Ajoute une entrée dans un flux (Stream) Redis.
        Args:
            key: La clé du stream, définie dans CacheKey.
            fields: Dictionnaire de données à insérer (les valeurs seront sérialisées).
            maxlen: Limite la taille du stream (optimisation mémoire). Utilise l'approximation (~).
        Returns:
            L'ID généré par Redis pour le message (ex: '1518951480106-0').
        """
        # Redis attend des strings/bytes pour les champs du stream. On sécurise ça.
        serialized_fields = {str(k): self._serialize(v) for k, v in fields.items()}

        return await self._connection.xadd(
            self._format_cache_key(key),
            serialized_fields,
            maxlen=maxlen,
            approximate=True if maxlen else False
        )

    async def stream_read(self, key: CacheKey, count: int = 10, last_id: str = "0-0",
                          block: Optional[int] = None) -> list:
        """
        Lit les messages d'un flux depuis un ID spécifique.
        Args:
            key: La clé du stream.
            count: Nombre maximum de messages à lire.
            last_id: L'ID à partir duquel lire (ex: '$' pour les nouveaux, '0-0' pour le début).
            block: Temps en millisecondes pour bloquer si le stream est vide (None = non-bloquant).
        Returns:
            Liste des messages sous la forme d'un tableau de tuples.
        """
        stream_name = self._format_cache_key(key)
        # xread prend un dictionnaire {stream_name: last_id}
        return await self._connection.xread({stream_name: last_id}, count=count, block=block)

    async def stream_create_group(self, key: CacheKey, group_name: str, start_id: str = "$",
                                  mkstream: bool = True) -> None:
        """
        Crée un groupe de consommateurs pour un stream (Idéal pour répartir la charge type Celery).
        Args:
            key: La clé du stream.
            group_name: Nom du groupe de consommateurs.
            start_id: '$' pour les messages futurs, '0' pour tout l'historique.
            mkstream: Si True, crée le stream s'il n'existe pas encore.
        Returns:
            Que dalle.
        """
        try:
            await self._connection.xgroup_create(
                self._format_cache_key(key),
                group_name,
                id=start_id,
                mkstream=mkstream
            )
        except Exception as e:
            # Gère silencieusement l'erreur classique "BUSYGROUP Consumer Group name already exists"
            if "BUSYGROUP" not in str(e):
                raise

    async def stream_read_group(self, key: CacheKey, group_name: str, consumer_name: str, count: int = 10,
                                block: Optional[int] = None) -> list:
        """
        Lit les messages en tant que consommateur d'un groupe spécifique.
        Args:
            key: La clé du stream.
            group_name: Le nom du groupe.
            consumer_name: Le nom unique de ce worker/consommateur.
            count: Nombre de messages à récupérer.
            block: Bloque X ms en attendant de nouveaux messages (ex: 5000 pour 5s).
        Returns:
            Liste des messages récupérés par ce consommateur.
        """
        stream_name = self._format_cache_key(key)
        # Le caractère '>' signifie : "donne moi les messages jamais assignés à un consommateur du groupe"
        return await self._connection.xreadgroup(
            group_name,
            consumer_name,
            {stream_name: ">"},
            count=count,
            block=block
        )

    async def stream_ack(self, key: CacheKey, group_name: str, *message_ids: str) -> int:
        """
        Acquitte (Acknowledge) un ou plusieurs messages lus dans un groupe.
        Crucial pour ne pas les re-traiter.
        Args:
            key: La clé du stream.
            group_name: Le nom du groupe.
            message_ids: Les IDs Redis des messages traités avec succès.
        Returns:
            Le nombre de messages acquittés.
        """
        if not message_ids:
            return 0
        return await self._connection.xack(self._format_cache_key(key), group_name, *message_ids)
    async def close(self) -> None:
        """
        Ferme la connexion Redis associée à ce CacheWrapper
        Returns:
            Que dalle, cette méthode ne retourne rien, elle effectue simplement l'opération de fermeture de la connexion Redis
        """
        await self._connection.close()


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

async def get_redis() -> AsyncIterator[CacheWrapper]:
    """
    Fournit une instance CacheWrapper par requête FastAPI
    """
    redis_instance = cache_manager.get_redis_connection_from_pool()
    try:
        yield redis_instance
    finally:
        await redis_instance.close()  # ferme juste le client, pas le pool