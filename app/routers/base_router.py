from fastapi import APIRouter
from app.routers.post_video_upload_router import router as post_video_upload_router

v1_api_router = APIRouter(prefix="/v1")

@v1_api_router.get("/hello")
async def hello():
    return {"message": "Hello World!"}

v1_api_router.include_router(post_video_upload_router)
# On importe tous les routers de nos différentes ressources et on les inclut dans le router principal ici,
# pour que le main.py puisse juste inclure ce router principal et avoir accès à tous les endpoints de l'api
