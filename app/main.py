try:
    import uvloop
    uvloop.install()  # Nouvelle event loop optimisé à mort
    print("uvloop installé avec succès.")
except Exception as exc:    # Désolé pour ceux qui sont sur Windows, uvloop n'est pas compatible avec ce système d'exploitation, du coup on catch l'erreur et on continue avec la boucle standard d'asyncio
    print(f"Erreur lors de l'installation d'uvloop: {exc.__class__.__name__}\nFallBack à la boucle standard Asyncio.")

from app.middlewares.request_logging_middleware import log_requests
import traceback
from app.routers.base_router import v1_api_router
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware



# Lifespan : C'est lui qui va réguler le démarrage et l'extinction de l'app
@asynccontextmanager
async def lifespan(_ : FastAPI):

    #Code qui s'executera au démarrage de l'app FastApi
    try:
        pass
    except Exception as e:
        print(f"Exception {e.__class__.__name__} lors du démarrade de l'application : {e}")
        traceback.print_exc()

    # On expose l'appplication jusqu'à sa fin
    yield

    #Code qui s'executera au stop de l'app FastApi
    try:
        # Après, on va rajouter des trucs si besoins
        print("Bye Bye")
    except Exception as e:
        print(f"Exception {e.__class__.__name__} lors du stop de l'application : {e}")
        traceback.print_exc()

app = FastAPI(
    lifespan=lifespan,
    title="Journal IAI Backend",
    version="1.0.0",
    root_path="/api"        # Permet compatibilité avec Nginx
)

# Liste des origines autorisées
origins = [
    "http://localhost:5173" ## url front par defaut de React, vu que c'est ce qu'ils vont surement utiliser pour le dev en local
]
app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials=True,
    allow_methods = ['*'],
    allow_headers=["*"]
)
app.middleware("http")(log_requests)



app.include_router(v1_api_router)

# Route de monitoring
@app.api_route("/health", methods=["GET", "HEAD", "POST"], include_in_schema=False)
def health():
    """Route de monitoring"""
    return {"message": "running"}


@app.get("/", include_in_schema=False)
async def root():
  return {"message": "Backend de Journal IAI, tout fonctionne bien ici :)"}

# Utile exclusivement pour debugger en local, ne s'execute pas si on lance le serveur via Docker normalement
if __name__ == "__main__":
    conf = uvicorn.Config(app, port=8000, log_level='info')
    server = uvicorn.Server(conf)
    server.run()