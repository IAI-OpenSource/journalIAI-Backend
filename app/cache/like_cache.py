import logging
from app.cache.helpers.base import CacheWrapper


logger = logging.getLogger(__name__)



class LikeCache:
    """Cache Redis pour la gestion des posts likés par utilisateur.
    """

    def __init__(self, cache: CacheWrapper):
        self._cache = cache


