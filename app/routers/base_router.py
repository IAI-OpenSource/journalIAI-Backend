from fastapi import APIRouter
from app.routers.registration_jeton_router import router as registration_router


v1_api_router = APIRouter(prefix="/v1")

@v1_api_router.get("/hello")
async def hello():
    return {"message": "Hello World!"}

# On importe tous les routers de nos différentes ressources et on les inclut dans le router principal ici,
# pour que le main.py puisse juste inclure ce router principal et avoir accès à tous les endpoints de l'api

v1_api_router.include_router(router=registration_router)