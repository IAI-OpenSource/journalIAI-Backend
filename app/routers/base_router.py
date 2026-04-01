from fastapi import APIRouter
from app.routers.event_router import routeur as event_router

from app.routers.club_router import router as club_router
from app.routers.post_router import router as post_router
from app.routers.registration_jeton_router import router as registration_router
from app.routers.auth_router import router as authentification_router

v1_api_router = APIRouter(prefix="/v1")

@v1_api_router.get("/hello")
async def hello():
    return {"message": "Hello World!"}

# On importe tous les routers de nos différentes ressources et on les inclut dans le router principal ici,
# pour que le main.py puisse juste inclure ce router principal et avoir accès à tous les endpoints de l'api

v1_api_router.include_router(event_router)
v1_api_router.include_router(post_router)
v1_api_router.include_router(router=registration_router)
v1_api_router.include_router(router=club_router)
v1_api_router.include_router(router=authentification_router)
