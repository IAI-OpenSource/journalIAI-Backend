from typing import Annotated, Callable, Any, Coroutine, Optional
from uuid import UUID

from fastapi import Depends, status, HTTPException, Response, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.helpers.base import CacheWrapper
from app.db.models.enums import ExecutiveRoleType, UserRole
from app.db.session import get_db
from app.routers.auth_router import get_redis_cache
from app.schemas.user_schemas import ReadUser
from app.services.session_service import SessionService
from app.auth.cookie_handler import CookieManager
from app.auth.jwt_handler import JWTManager
from app.core.config import JWT_COOKIE_ACCESS_ID, ACCESS_SECRET_KEY
from app.services.user_service import UserService
from app.globals.status_codes import StatusCode as custom_status


class UserAuthDependencies:
  
    def __init__(self, db: AsyncSession, response: Response, request: Request, cache: CacheWrapper):
      self.db = db
      self.cookie = CookieManager(response=response, request=request)
      self.session_service = SessionService(self.db, cache)
      self.user_service = UserService(self.db, cache)

    async def get_current_user(self) -> Optional[ReadUser]:

        """function permettant de return le user actuellement connecter.
          Elle sera utiliser pr securiser certaine routes en exigant le token
          d'authentificatiion obtenu lors du login


          Args:
              self: Comme argument on prend par défaut l'objet UserAuthDependencies()
              comme ça on a accès a une session de la bd et une instance cookie de la 
              class CookieManager()

          Raises:
              HTTPException: Aucun clé d'access fourni !
              HTTPException: Clé d'accès invalide
              HTTPException: user.error
          Returns:
              ReadUser: return un objet ReadUser qui est les infos de user actuellement connecter
        """
      
        access_token = self.cookie.get_cookie(id=JWT_COOKIE_ACCESS_ID)

        if access_token is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Aucun clé d'access fourni !"
            )
        
        payload = JWTManager.decode_access_token(token=access_token, cle=ACCESS_SECRET_KEY)

        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clé d'accès invalide"
            )
        
        user_session = await self.session_service.service_find_session_by_sid(sid=UUID(payload["sid"]))
        
        if user_session.is_error():
            raise HTTPException(
                status_code=user_session.status_code,
                detail=user_session.error
            )
            
        user = await self.user_service.service_find_user_by_id(user_session.data.user_id)
        
        if user.is_error():
            if user.status_code == custom_status._404_STATUS_NOT_FOUND.value:
                raise HTTPException(
                    status_code=user.status_code,
                    detail=user.error
                ) 
            
            raise HTTPException(
                detail=user.error,
                status_code=user.status_code
            )
            
        return user.data
                


### fonction utilitaires pour gérer la classe UserAuthDepends

# Fonction pour instancier ta classe avec tout ce qu'il faut
def get_user_auth_deps(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    cache: CacheWrapper = Depends(get_redis_cache)
) -> UserAuthDependencies:
    return UserAuthDependencies(db=db, response=response, request=request, cache=cache)

# Dépendance finale pour récupérer le user
async def get_current_user(
    auth_deps: UserAuthDependencies = Depends(get_user_auth_deps)
) -> Optional[ReadUser]:
    return await auth_deps.get_current_user()