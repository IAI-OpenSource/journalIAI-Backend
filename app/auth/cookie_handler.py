from fastapi import Response, HTTPException, status
from app.core.config import ENVIRONMENT


class SetCookie:
  
  def __init__(self, id: str, value: str, age: int):
    self.cookie_id = id
    self.cookie_value = value
    self.cookie_age = age
    
    
  def add_cookie(self, res: Response):
    
    try:
      
      is_dev = ENVIRONMENT == "LOCAL"
      
      res.set_cookie(
        key=self.cookie_id,
        value=self.cookie_value,
        max_age=self.cookie_age,
        secure=True,
        httponly=True,
        samesite="strict" if is_dev else "none",
        path="/",
      )
      
    except Exception:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    

  