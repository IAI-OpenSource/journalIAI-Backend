from dataclasses import dataclass
from enum import Enum

@dataclass
class BaseCacheEntity:
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
    OTP = "entity:otp:{email}"
    CLUB_MEMBER = "entity:club_member:{id}"



class AvailableCacheKeys(str, Enum):
    """Definis toutes les clés de cache utilisées dans l'application, organisées par entité et par type de données"""

    # J'ai juste essayé d'imaginer quelques clés de cache qui pourraient être utiles pour les différentes entités,
    # mais on peut en ajouter ou en enlever selon les besoins spécifiques de l'application.

    # Clés de cache pour les utilisateurs
    USER_OBJECT = BaseCacheEntity.USER  # Clé pour un utilisateur spécifique
    USER_POSTS = BaseCacheEntity.USER + ":posts"  # Clé pour les posts d'un utilisateur

    # Clés de cache pour les posts
    POST_OBJECT = BaseCacheEntity.POST  # Clé pour un post spécifique
    POST_COMMENTS = BaseCacheEntity.POST + ":comments"  # Clé pour les commentaires d'un post

    # Clés de cache pour les clubs
    CLUB_OBJECT = BaseCacheEntity.CLUB  # Clé pour un club spécifique
    CLUB_MEMBERS = BaseCacheEntity.CLUB + ":members"  # Liste des membres d'un club (par club_id)
    CLUB_MEMBER_LIST = BaseCacheEntity.CLUB_MEMBER + ":list"  # Liste paginée des membres
    CLUB_MEMBER_OBJECT = BaseCacheEntity.CLUB + ":member:{id}"
    CLUB_MEMBER_PAGINATED = BaseCacheEntity.CLUB_MEMBER + ":paginated"

    
    # Clés de cache pour les événements
    EVENT_OBJECT = BaseCacheEntity.EVENT  # Clé pour un événement spécifique
    EVENT_LIST = BaseCacheEntity.EVENT + ":list"               # pagination
    EVENT_BY_STATUS = BaseCacheEntity.EVENT + ":status"        # filtrage par statut


    # Clés de cache pour les sessions
    SESSION_OBJECT = BaseCacheEntity.SESSION  # Clé pour une session spécifique

    # Clés de cache pour les notifications
    NOTIFICATION_OBJECT = BaseCacheEntity.NOTIFICATION  # Clé pour une notification spécifique

    # Clés de cache pour les feeds
    FEED_OBJECT = BaseCacheEntity.FEED  # Clé pour le feed d'un utilisateur spécifique

    # Clés pour les likes
    LIKE_OBJECT = BaseCacheEntity.LIKE  # Clé pour un like spécifique
    POST_LIKE_COUNT = BaseCacheEntity.POST + ":like_count"  # Clé pour le nombre de likes d'un post
    COMMENT_LIKE_COUNT = BaseCacheEntity.COMMENT + ":like_count"  # Clé pour le nombre de likes d'un commentaire

    FILE_UPLOAD_INTENT_KEY = "upload_intent:{user_id}:{intent_id}" # Clé pour stocker les intent d'upload

    FILE_UPLOAD_PROGRESS_STREAM_KEY = "upload_progress_stream:{user_id}:{intent_id}" # Clé pour le stream sur l'anvancement du traitemenr d'un upload

    ## Clés pour le OTP
    USER_OTP = BaseCacheEntity.OTP 
