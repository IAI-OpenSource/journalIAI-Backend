from typing import Annotated, Callable, Any, Coroutine, Optional
from uuid import UUID

from fastapi import status, HTTPException, Response, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user_schemas import ReadUser
from app.services.session_service import SessionService
from app.auth.cookie_handler import CookieManager
from app.auth.jwt_handler import JWTManager
from app.core.config import JWT_COOKIE_ACCESS_ID, ACCESS_SECRET_KEY
from app.services.user_service import UserService
from app.globals.status_codes import StatusCode as custom_status


class UserAuthDependencies:
  
  def __init__(self, db: AsyncSession):
      self.db = db
      self.cookie = CookieManager()
      self.session_service = SessionService(self.db)
      self.user_service = UserService(self.db)

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
              Personnel | Professeur: return un objet Personnel ou Professeur qui est les infos de user actuellement connecter
        """
      
        access_token = self.cookie.get_cookie(id=JWT_COOKIE_ACCESS_ID)

        if access_token is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Aucun clé d'access fourni !"
            )
        
        sid = JWTManager.decode_access_token(access_token, ACCESS_SECRET_KEY)

        if sid is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clé d'accès invalide"
            )
        
        user_session = await self.session_service.service_find_session_by_sid(sid=sid)
        
        if user_session.is_error():
            raise HTTPException(
                status_code=user_session.status_code,
                detail=user_session.error
            )
            
        user = await self.user_service.service_find_user_by_id(user_session.data.user_id)
        
        if user.is_error():
            if user.status_code == custom_status._404_STATUS_NOT_FOUND.value:
                return {"Message": "Utilisateur Non Trouvé"}
            
            raise HTTPException(
                detail=user.error,
                status_code=user.status_code
            )
            
        return user.data
                
            
        


  @staticmethod
  def requires_roles(*role_autorises: str) -> Callable[[str], Coroutine[Any, Any, str]]:
      """function pour restraindre les accès uniquement aux admis

          Args:
              *role_autorises: recuperere les role des personne autorisées. ex: ("directeur", "secretaire")
          Raises:
              HTTPException: lever une exection si c'est pas un role correspondant

          Returns:
              Professeur | Personnel: return tjrs les infos de current_user Prof ou Personnel
      """

      # def verify_role(
      #     current_user_token_data: Annotated[TokenData, Depends(get_token_data)]
      #     ) :
          
      #     role = current_user_token_data.role
          
      #     if role.lower() not in role_autorises :
      #         raise HTTPException(
      #             status_code=status.HTTP_401_UNAUTHORIZED,
      #             detail="Accès Refusé"
      #         ) 
              
      #     return current_user_token_data
      # return verify_role
      pass


