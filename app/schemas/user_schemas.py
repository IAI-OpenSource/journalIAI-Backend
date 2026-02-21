## Ce fichier contient les différents schémas concernant les opérations 
# sur la table utilisateur/user


from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

from uuid import UUID

from app.db.models.enums import ClasseType, UserRole
from app.schemas import ApiBaseResponse


class CreateUser(BaseModel):
  
  first_name: str
  last_name: str
  email: EmailStr
  username: str
  password: str
  