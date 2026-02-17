from enum import Enum


class BaseCacheEntity(str, Enum):
    """Defininis toutes les entités qui peuvent être mises en cache avec leurs clés respectives"""
    USER = "entity:user:{id}"
    POST = "entity:post:{id}"
    COMMENT = "entity:comment:{id}"
    CLUB = "entity:club:{id}"
    EVENT = "entity:event:{id}"
    SESSION = "entity:session:{id}"
    NOTIFICATION = "entity:notification:{id}"
    FEED = "feed:user:{id}"
    LIKE = "entity:like:{id}"

class AvailableCacheKeys(str, Enum):
    """Definis toutes les clés de cache utilisées dans l'application, organisées par entité et par type de données"""

    # J'ai juste essayé d'imaginer quelques clés de cache qui pourraient être utiles pour les différentes entités,
    # mais on peut en ajouter ou en enlever selon les besoins spécifiques de l'application.

    # Clés de cache pour les utilisateurs
    USER_OBJECT = BaseCacheEntity.USER.value  # Clé pour un utilisateur spécifique
    USER_POSTS = BaseCacheEntity.USER.value + ":posts"  # Clé pour les posts d'un utilisateur

    # Clés de cache pour les posts
    POST_OBJECT = BaseCacheEntity.POST.value  # Clé pour un post spécifique
    POST_COMMENTS = BaseCacheEntity.POST.value + ":comments"  # Clé pour les commentaires d'un post

    # Clés de cache pour les clubs
    CLUB_OBJECT = BaseCacheEntity.CLUB.value  # Clé pour un club spécifique
    CLUB_MEMBERS = BaseCacheEntity.CLUB.value + ":members"  # Clé pour les membres d'un club

    # Clés de cache pour les événements
    EVENT_OBJECT = BaseCacheEntity.EVENT.value  # Clé pour un événement spécifique


    # Clés de cache pour les sessions
    SESSION_OBJECT = BaseCacheEntity.SESSION.value  # Clé pour une session spécifique

    # Clés de cache pour les notifications
    NOTIFICATION_OBJECT = BaseCacheEntity.NOTIFICATION.value  # Clé pour une notification spécifique

    # Clés de cache pour les feeds
    FEED_OBJECT = BaseCacheEntity.FEED.value  # Clé pour le feed d'un utilisateur spécifique

    # Clés pour les likes
    LIKE_OBJECT = BaseCacheEntity.LIKE.value  # Clé pour un like spécifique
    POST_LIKE_COUNT = BaseCacheEntity.POST.value + ":like_count"  # Clé pour le nombre de likes d'un post
    COMMENT_LIKE_COUNT = BaseCacheEntity.COMMENT.value + ":like_count"  # Clé pour le nombre de likes d'un commentaire

