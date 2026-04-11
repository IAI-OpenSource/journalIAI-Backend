import logging
from dataclasses import dataclass
from typing import Optional

from app.core.config import MINIO_PUBLIC_URL
from app.storage.minio_config import BucketName

logger = logging.getLogger(__name__)

@dataclass
class MediaReadStorage:

    __PUBLIC_ASSET_URL_TEMPLATE: str = "{base}/{bucket_name}/{file_path}"
    __POSTS_HLS_VIDEO_MASTER_GET_URL_TEMPLATE: str = "{base}/posts-hls/{media_id}/master.m3u8?token={token}"
    __POSTS_HIGH_QUALITY_IMAGE_URL_TEMPLATE: str = "{base}/posts-images/{media_id}/full.webp?token={token}"
    __POSTS_MEDIUM_QUALITY_IMAGE_URL_TEMPLATE: str = "{base}/posts-images/{media_id}/medium.webp?token={token}"
    __STORIES_HLS_VIDEO_MASTER_GET_URL_TEMPLATE: str = "{base}/stories-hls/{media_id}/master.m3u8?token={token}"
    __STORIES_HIGH_QUALITY_IMAGE_URL_TEMPLATE: str = "{base}/stories-images/{media_id}/full.webp?token={token}"
    __STORIES_MEDIUM_QUALITY_IMAGE_URL_TEMPLATE: str = "{base}/stories-images/{media_id}/medium.webp?token={token}"

    @classmethod
    def generate_post_read_hls_url(cls, media_path_in_bucket: str, access_token: str) -> str:
        return  cls.__POSTS_HLS_VIDEO_MASTER_GET_URL_TEMPLATE.format(
            base=MINIO_PUBLIC_URL,
            media_id=media_path_in_bucket,
            token=access_token,
        )

    @classmethod
    def generate_story_read_hls_url(cls, media_path_in_bucket: str, access_token: str) -> str:
        return  cls.__STORIES_HLS_VIDEO_MASTER_GET_URL_TEMPLATE.format(
            base=MINIO_PUBLIC_URL,
            media_id=media_path_in_bucket,
            token=access_token,
        )

    @classmethod
    def generate_read_public_asset(cls, file_path: str) -> Optional[str]:
        if not file_path:
            return None
        return cls.__PUBLIC_ASSET_URL_TEMPLATE.format(
            base=MINIO_PUBLIC_URL,
            bucket_name=BucketName.USER_IDENTITY_ASSETS.value,
            file_path=file_path,
        )

    @classmethod
    def generate_post_high_quality_post_image_url(cls, media_path_in_bucket: str, access_token: str) -> str:
        return cls.__POSTS_HIGH_QUALITY_IMAGE_URL_TEMPLATE.format(
            base=MINIO_PUBLIC_URL,
            media_id=media_path_in_bucket,
            token=access_token,
        )

    @classmethod
    def generate_story_high_quality_post_image_url(cls, media_path_in_bucket: str, access_token: str) -> str:
        return cls.__STORIES_HIGH_QUALITY_IMAGE_URL_TEMPLATE.format(
            base=MINIO_PUBLIC_URL,
            media_id=media_path_in_bucket,
            token=access_token,
        )

    @classmethod
    def generate_post_medium_post_image_url(cls, media_path_in_bucket: str, access_token: str) -> str:
        return cls.__POSTS_MEDIUM_QUALITY_IMAGE_URL_TEMPLATE.format(
            base=MINIO_PUBLIC_URL,
            media_id=media_path_in_bucket,
            token=access_token,
        )

    @classmethod
    def generate_story_medium_post_image_url(cls, media_path_in_bucket: str, access_token: str) -> str:
        return cls.__STORIES_MEDIUM_QUALITY_IMAGE_URL_TEMPLATE.format(
            base=MINIO_PUBLIC_URL,
            media_id=media_path_in_bucket,
            token=access_token,
        )
        
    @classmethod
    def generate_avatar_url(cls, avatar_path: str) -> Optional[str]:
        """
        Génère l'URL publique pour l'avatar à partir du chemin stocké en base de données.
        Exemple : avatar_path = "avatars/uuid_utilisateur/medium.webp"
        """
        if not avatar_path:
            return None
            
        return cls.__PUBLIC_ASSET_TEMPLATE.format(
            base=MINIO_PUBLIC_URL,
            bucket_name=BucketName.USER_IDENTITY_ASSETS.value,  
            file_path=avatar_path,
        )