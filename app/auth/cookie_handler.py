from typing import Annotated, Optional
import logging

from fastapi import Cookie, Request, Response, HTTPException, status
from app.core.config import ENVIRONMENT

logger = logging.getLogger(__name__)

class CookieManager:
  
  def __init__(self, response: Response, request: Request):
    self.response = response
    self.request =  request
    
    
  def add_cookie(self, id: str, value: Optional[str], age: Optional[int]):
    
    try:
      
      is_dev = ENVIRONMENT == "LOCAL"
      
      self.response.set_cookie(
        key=id,
        value=value,
        max_age=age,
        secure=True,
        httponly=True,
        samesite="strict" if is_dev else "none",
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
    
    if cookie_value is None:
      raise HTTPException
    
    return cookie_value
  