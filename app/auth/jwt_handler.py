import logging
import traceback
from datetime import datetime, timedelta, UTC

from jose import jwt, JWTError

from app.core.config import (
    JWT_EXPIRES_MINUTES, ALGORITHM
)


logger = logging.getLogger(__name__)


class JWTManager:
  
  @staticmethod
  def create_access_token(
    data_to_encode: dict, 
    cle: str,
    expire_delta: timedelta | None = None) -> str | dict[str, JWTError] :
    
      """function pour generer un access token
        Args:
            data_to_encode (dict): contient la donnée de l'utilisateur qu'on
            use pour coder le token: ex: {"SID": session_id}

            expire_delta (timedelta): le temps avant l'expiration du jwt.
            si c'est None alors on prendre un par defaut

        Returns:
            str: retourne un str qui contient le token creer
      """
          
      to_encode = (data_to_encode.copy()) ## on fait une copy des données a encoder

      expiration_time = datetime.now(UTC) + (
        expire_delta or timedelta(minutes=JWT_EXPIRES_MINUTES)
      )  ## on defini le durée du token avant expiration

      to_encode.update(
        {
          "exp": expiration_time
        }
      )  ## on ajoute le temsp d'espiration aux données a encoder

      try:
        
        encoded_jwt = jwt.encode(to_encode, key=cle, algorithm=ALGORITHM)
        logger.info("JWT créé avec succès !")
        return encoded_jwt

      except JWTError as err:
        logger.exception(f"Error {err.__class__.__name__} : {err}")
        return {"message": err}

  
  @staticmethod
  def decode_access_token(token: str, cle: str) -> dict | None:
      """function pour decoder le token et verifier si le token
        est toujours valid: le SID et expiration

        Args:
            token (str): Il prend en argument le token generer en str

        Returns:
            dict | None: retourne un dict qui contient les infos utiliser au debut pour
            creer le token si toutes les données sont valid sinon retourne None dans le cas contraire
        """

      try:
        
        claims_data = jwt.decode(token=token, key=cle, algorithms=[ALGORITHM])
        logger.info("JWT décodé avec succès !")
        return claims_data

      except JWTError as err:
        logger.exception(f"Error {err.__class__.__name__} : {err}")
        traceback.print_exc()
        return None  ## on retun None, l'erreur sera gerer dans le login