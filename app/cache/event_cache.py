import redis

from app.cache.helpers.availables import AvailableCacheKeys
from app.cache.helpers.keys_factory import CacheKeysFactory


class EventCache:
    async def gctyc(self, leId):
        CacheKeysFactory.get_cache_key(AvailableCacheKeys.EVENT_OBJECT).set_arguments(id=leId)