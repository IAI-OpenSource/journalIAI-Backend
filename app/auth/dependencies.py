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

    async def get_token_data(self, token: Annotated[str | None, Cookie(alias=ACCESS_IDENTIFIER)] = None):
      """Fonction permettant de return les données contenues dans le token, on utilisera si on n'a pas forcément besoin de
          toutes les infos de l'utilisateur actuellement connecté (dans ce cas, on ne fait pas de requete bd), ça sera
          surtout utile pour les routes ou on a besoin de seulement de l'id de l'etablissement pour les requetes bd.

          Args:
              token (Annotated[str, Depends): Extait directement le token dans le Header avec Bearer

          Raises:
              HTTPException: Token invalide ou expiré
              HTTPException: Token invalide ou expiré
              HTTPException: Cet utilisateur n'existe pas

          Returns:
              TokenData: return un objet TokenData qui contient les données du token
      """
      
      pass


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
                
            
        


    @staticmethod
    def requires_roles(*role_autorises: str, response: Response, request: Request) -> Callable[[ReadUser], Coroutine[Any, Any, ReadUser]]:
        """function pour restraindre les accès uniquement aux utilisateurs en fonction de leurs 
            roles (autorisaions)

            Args:
                *role_autorises: recuperere les role des personne autorisées. ex: ("directeur", "secretaire")
            Raises:
                HTTPException: lever une exection si c'est pas un role correspondant

            Returns:
                Professeur | Personnel: return tjrs les infos de current_user Prof ou Personnel
        """
        
        user_dependence = UserAuthDependencies(
            db=Depends(get_db), 
            response=response,
            request=request,
            cache=Depends(get_redis_cache)
            )

        def verify_role(
          current_user: Annotated[ReadUser, Depends(user_dependence.get_current_user)]
        ) :
          
            role: list[UserRole | Optional[ExecutiveRoleType]] = [current_user.role, current_user.executive_role]
          
            if role[0] not in role_autorises and role[1] :
                    raise HTTPException(
                  status_code=status.HTTP_401_UNAUTHORIZED,
                  detail="Accès Refusé"
                ) 
              
            return current_user
        return verify_role


