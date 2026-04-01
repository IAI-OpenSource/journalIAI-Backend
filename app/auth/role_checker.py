
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.db.models.enums import ExecutiveRoleType, UserRole
from app.schemas.user_schemas import ReadUser


class RoleChecker:
  
  def __init__(self, allowed_roles: list):
    self._allowed_roles = allowed_roles
    
  async def __call__(self, current_user: Annotated[ReadUser, Depends(get_current_user)]):
    
    user_roles: list[UserRole | Optional[ExecutiveRoleType]] = [current_user.role, current_user.executive_role]

    if not any(role in self._allowed_roles for role in user_roles if role):
      raise HTTPException(
          status_code=status.HTTP_403_FORBIDDEN,
          detail="Accès Refusé : Rôle insuffisant"
      )
    
    return current_user