from app.cache.availables import AvailableCacheKeys
from .cache_keys import CacheKey

cache_keys_mapping: dict[AvailableCacheKeys, CacheKey] = {
    AvailableCacheKeys.USER_OBJECT: CacheKey(AvailableCacheKeys.USER_OBJECT, 1),
    AvailableCacheKeys.USER_POSTS: CacheKey(AvailableCacheKeys.USER_POSTS, 1),
    AvailableCacheKeys.POST_OBJECT: CacheKey(AvailableCacheKeys.POST_OBJECT, 1),
    AvailableCacheKeys.POST_COMMENTS: CacheKey(AvailableCacheKeys.POST_COMMENTS, 1),
    AvailableCacheKeys.CLUB_OBJECT: CacheKey(AvailableCacheKeys.CLUB_OBJECT, 1),
    AvailableCacheKeys.CLUB_MEMBERS: CacheKey(AvailableCacheKeys.CLUB_MEMBERS, 1),
    AvailableCacheKeys.EVENT_OBJECT: CacheKey(AvailableCacheKeys.EVENT_OBJECT, 1),
    AvailableCacheKeys.SESSION_OBJECT: CacheKey(AvailableCacheKeys.SESSION_OBJECT, 1),
    AvailableCacheKeys.NOTIFICATION_OBJECT: CacheKey(AvailableCacheKeys.NOTIFICATION_OBJECT, 1),
    AvailableCacheKeys.FEED_OBJECT: CacheKey(AvailableCacheKeys.FEED_OBJECT, 1),
    AvailableCacheKeys.LIKE_OBJECT: CacheKey(AvailableCacheKeys.LIKE_OBJECT, 1),
    AvailableCacheKeys.POST_LIKE_COUNT: CacheKey(AvailableCacheKeys.POST_LIKE_COUNT, 1),
    AvailableCacheKeys.COMMENT_LIKE_COUNT: CacheKey(AvailableCacheKeys.COMMENT_LIKE_COUNT, 1),
}