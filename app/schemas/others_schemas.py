from pydantic import BaseModel, Field


class AuthErrorMessage(BaseModel):
    detail: str = Field(
        description="Message d'erreur en cas de probleme d'authentification ou d'autorisation"
    )