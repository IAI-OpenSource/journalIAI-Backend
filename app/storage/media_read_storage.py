import logging
from dataclasses import dataclass
from typing import Optional

from app.core.config import MINIO_PUBLIC_URL
from app.storage.minio_config import BucketName

logger = logging.getLogger(__name__)

@dataclass
class MediaReadStorage:

    __PUBLIC_ASSET_TEMPLATE: str = "{base}/{bucket_name}/{file_path}"
    __HLS_VIDEO_MASTER_GET_TEMPLATE: str = "{base}/hls/{media_id}/master.m3u8?token={token}"
    __HIGH_QUALITY_POST_IMAGE_TEMPLATE: str = "{base}/images/{media_id}/full.webp?token={token}"
    __MEDIUM_QUALITY_POST_IMAGE_TEMPLATE: str = "{base}/images/{media_id}/medium.webp?token={token}"

    @classmethod
    def generate_read_hls_url(cls, media_path_in_bucket: str, access_token: str) -> str:
        return  cls.__HLS_VIDEO_MASTER_GET_TEMPLATE.format(
            base=MINIO_PUBLIC_URL,
            media_id=media_path_in_bucket,
            token=access_token,
        )

    @classmethod
    def generate_read_public_asset(cls, file_path: str) -> Optional[str]:
        if not file_path:
            return None
        return cls.__PUBLIC_ASSET_TEMPLATE.format(
            base=MINIO_PUBLIC_URL,
            bucket_name=BucketName.USER_IDENTITY_ASSETS.value,
            file_path=file_path,
        )

    @classmethod
    def generate_high_quality_post_image_url(cls, media_path_in_bucket: str, access_token: str) -> str:
        return cls.__HIGH_QUALITY_POST_IMAGE_TEMPLATE.format(
            base=MINIO_PUBLIC_URL,
            media_id=media_path_in_bucket,
            token=access_token,
        )

    @classmethod
    def generate_medium_post_image_url(cls, media_path_in_bucket: str, access_token: str) -> str:
        return cls.__MEDIUM_QUALITY_POST_IMAGE_TEMPLATE.format(
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
            bucket_name=BucketName.AVATARS.value,  
            file_path=avatar_path,
        )