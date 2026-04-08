from fastapi import APIRouter
from app.routers.event_router import routeur as event_router
from app.routers.club_member_router import routeur as club_member_router
from app.routers.classe_router import router as classe_router
from app.routers.club_router import router as club_router
from app.routers.post_router import router as post_router
from app.routers.registration_jeton_router import router as registration_router
from app.routers.auth_router import router as authentification_router
from app.routers.academic_year_router import router as academic_year_router
from app.routers.user_router import router as user_router
from app.routers.comment_router import routeur as comment_router

v1_api_router = APIRouter(prefix="/v1")

@v1_api_router.get("/hello")
async def hello():
    return {"message": "Hello World!"}

# On importe tous les routers de nos différentes ressources et on les inclut dans le router principal ici,
# pour que le main.py puisse juste inclure ce router principal et avoir accès à tous les endpoints de l'api

v1_api_router.include_router(event_router)
v1_api_router.include_router(post_router)
v1_api_router.include_router(router=registration_router)
v1_api_router.include_router(router=authentification_router)
v1_api_router.include_router(club_member_router)
v1_api_router.include_router(router=academic_year_router)
v1_api_router.include_router(router=classe_router)
v1_api_router.include_router(router=user_router)
v1_api_router.include_router(router=club_router)
v1_api_router.include_router(router=comment_router)

