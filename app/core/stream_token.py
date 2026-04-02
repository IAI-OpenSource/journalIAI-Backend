from time import time

from jose import jwt

from app.core.config import STREAM_JWT_SECRET, ALGORITHM

def create_stream_token(media_id: str, user_id: str, duration_hours: int = 4) -> str:
    return jwt.encode({
        "media_id": media_id,
        "user_id":  user_id,
        "exp":      int(time()) + duration_hours * 3600,
        "emitted_ts":      int(time()),
    }, STREAM_JWT_SECRET, algorithm=ALGORITHM)