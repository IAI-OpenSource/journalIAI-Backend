from typing import Optional
import logging

from fastapi import Request, Response, HTTPException, status
from starlette.requests import HTTPConnection

from app.core.config import ENVIRONMENT

logger = logging.getLogger(__name__)

class CookieManager:
  
  def __init__(self, response: Response, request: HTTPConnection):
    self.response = response
    self.request =  request
    
    
  def add_cookie(self, id: str, value: str, age: Optional[int]):
    
    try:
      
      is_dev = ENVIRONMENT == "LOCAL"
      
      self.response.set_cookie(
        key=id,
        value=value,
        max_age=age,
        secure=not is_dev ,
        httponly=True,
        samesite="lax" if is_dev else "none",
        path="/",
      )
      
    except Exception:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    
    
  def get_cookie(self, id: str) -> Optional[str]:
    """function pour lire la valeur d'un cookie"""    
    
    try:
      
      cookie_value = self.request.cookies.get(id)
      
    except Exception:
      logger.exception("Erreur de lecture de cookie")
      raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, 
        detail="Erreur de lecture de cookie"
      )
    
    return cookie_value
  
  
  def delete_cookie(self, id: str):
    """fonction pour supprimer un cookie"""

    try:
      
      self.response.delete_cookie(key=id)
      
    except Exception:
      raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Erreur lors de la suppression du cookie"
      )
      
  