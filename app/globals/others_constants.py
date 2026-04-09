from app.schemas.others_schemas import AuthErrorMessage


class OtherConstants:
    HLS_PLAYLIST_MASTER_NAME: str = "master.m3u8"
    HLS_SEGMENTS_DURATION: int = 4      # 4 secondes
    HLS_DOWNLOAD_FILE_NAME: str = "download.mp4"
    HLS_PLAYLIST_TYPE: str = "mp4"
    MEDIA_PROCESSING_WORKER_QUEUE_NAME: str = "media_processing"
    MAX_UPLOAD_FILE_SIZE: int = 100 * 1024 * 1024  # 100 Mo
    COMMON_API_RESPONSES = {
        401: {"description": "Unauthorized", "model": AuthErrorMessage},
        403: {"description": "Forbidden", "model": AuthErrorMessage},
    }