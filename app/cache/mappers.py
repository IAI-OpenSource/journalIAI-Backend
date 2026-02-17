from app.cache.availables import AvailableCacheKeys
from .cache_keys import CacheKey

cache_keys_mapping: dict[AvailableCacheKeys, CacheKey] = {
    AvailableCacheKeys.USER_OBJECT: CacheKey.new_key(AvailableCacheKeys.USER_OBJECT, 1),
    AvailableCacheKeys.USER_POSTS: CacheKey.new_key(AvailableCacheKeys.USER_POSTS, 1),
    AvailableCacheKeys.POST_OBJECT: CacheKey.new_key(AvailableCacheKeys.POST_OBJECT, 1),
    AvailableCacheKeys.POST_COMMENTS: CacheKey.new_key(AvailableCacheKeys.POST_COMMENTS, 1),
    AvailableCacheKeys.CLUB_OBJECT: CacheKey.new_key(AvailableCacheKeys.CLUB_OBJECT, 1),
    AvailableCacheKeys.CLUB_MEMBERS: CacheKey.new_key(AvailableCacheKeys.CLUB_MEMBERS, 1),
    AvailableCacheKeys.EVENT_OBJECT: CacheKey.new_key(AvailableCacheKeys.EVENT_OBJECT, 1),
    AvailableCacheKeys.SESSION_OBJECT: CacheKey.new_key(AvailableCacheKeys.SESSION_OBJECT, 1),
    AvailableCacheKeys.NOTIFICATION_OBJECT: CacheKey.new_key(AvailableCacheKeys.NOTIFICATION_OBJECT, 1),
    AvailableCacheKeys.FEED_OBJECT: CacheKey.new_key(AvailableCacheKeys.FEED_OBJECT, 1),
    AvailableCacheKeys.LIKE_OBJECT: CacheKey.new_key(AvailableCacheKeys.LIKE_OBJECT, 1),
    AvailableCacheKeys.POST_LIKE_COUNT: CacheKey.new_key(AvailableCacheKeys.POST_LIKE_COUNT, 1),
    AvailableCacheKeys.COMMENT_LIKE_COUNT: CacheKey.new_key(AvailableCacheKeys.COMMENT_LIKE_COUNT, 1),
}