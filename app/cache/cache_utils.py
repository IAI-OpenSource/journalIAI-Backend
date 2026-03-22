from logging import Logger

from redis.exceptions import ConnectionError as RedisConnectionError


class CacheUtils:
    """Classe avec des fonctions utilitaires pour cache"""

    @classmethod
    def traiter_exceptions(cls, e : Exception, logger: Logger) -> None:
        """
        Gerer de maniere centralisé les exceptions liées au cache, comme les problèmes de connexion ou d'autres erreurs inattendues.
        Args:
            e: L'exception de l'utilitaire
            logger: Le logger

        Returns:
            Que Dalle
        """

        if isinstance(e, RedisConnectionError):
            logger.exception(f"Erreur de connexion à Redis : {e}")
        else:
            logger.exception(f"Erreur inattendue liée à une opération cache : {e.__class__.__name__} - {e}")

