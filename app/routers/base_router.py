from fastapi import APIRouter

from app.routers.post_video_upload_router import router as post_video_upload_router
from app.routers.registration_jeton_router import router as registration_router
from app.routers.auth_router import router as authentification_router

v1_api_router = APIRouter(prefix="/v1")

@v1_api_router.get("/hello")
async def hello():
    return {"message": "Hello World!"}

v1_api_router.include_router(post_video_upload_router)
v1_api_router.include_router(router=registration_router)
v1_api_router.include_router(router=authentification_router)