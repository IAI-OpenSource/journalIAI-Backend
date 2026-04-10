from time import time

from jose import jwt

from app.core.config import STREAM_JWT_SECRET, ALGORITHM

def create_stream_token(
        media_id: str,
        user_id: str,
        ressource_type: str,
        duration_hours: int = 4
) -> str:
    now = int(time())
    return jwt.encode({
        "media_id": media_id,
        "resource_type": ressource_type,
        "user_id":  user_id,
        "exp":      now + duration_hours * 3600,
        "emitted_ts":      now,
    }, STREAM_JWT_SECRET, algorithm=ALGORITHM)