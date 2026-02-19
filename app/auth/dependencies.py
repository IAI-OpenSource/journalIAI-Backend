from typing import Annotated, Callable, Any, Coroutine
from uuid import UUID

from fastapi import Depends, status, HTTPException, Cookie
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_handler import JWTManager
from app.core.config import ACCESS_IDENTIFIER, SECRET_KEY


class UserAuthDependencies:
  
  def __init__(self, db):
      self.db = db

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


  async def get_current_user(self, token: Annotated[str | None, Cookie(alias=ACCESS_IDENTIFIER)] = None) :

      """function permettant de return le user actuellement connecter.
          Elle sera utiliser pr securiser certaine routes en exigant le token
          d'authentificatiion obtenu lors du login


          Args:
              token (Annotated[str, Depends): Extait directement le token dans le Header avec Bearer
              db (AsyncSession): Une session asynchrone de la db

          Raises:
              HTTPException: Token invalide ou expiré
              HTTPException: Token invalide ou expiré
              HTTPException: Cet utilisateur n'existe pas

          Returns:
              Personnel | Professeur: return un objet Personnel ou Professeur qui est les infos de user actuellement connecter
      """
      
      pass


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


