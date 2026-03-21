from typing import Optional

from pydantic import BaseModel, Field

from uuid import UUID

from app.db.models.enums import MediaType, PostType
from app.schemas import ApiBaseResponse

class CreateVideoUploadIntent(BaseModel):
    """Schéma de validation pour un intent d'upload de fichier, contenant les informations nécessaires pour initier un upload de fichier, comme le nom du fichier, son type et sa taille"""

    file_name: str = Field(description="Le nom du fichier à uploader, incluant son extension, par exemple 'photo.jpg'")
    file_size: int = Field(description="La taille du fichier à uploader en octets, par exemple 1048576 pour un fichier de 1 Mo")
    event_id: Optional[UUID] = Field(None, description="L'ID de l'événement auquel le fichier est associé, si applicable")
    club_id: Optional[UUID] = Field(None, description="L'ID du club auquel le fichier est associé, si applicable")
    content: Optional[str] = Field(None, description="Le contenu textuel associé au post")

    class Config:
        from_attributes = True

class UploadURLSchema(BaseModel):
    upload_url: str = Field(description="L'url sur lequel l'Upload doit s'effectuer")
    intent_id: str = Field(
        description="Id de l'intent, cet id sera réutiliser pour les prochaines opérations, donc gardez çà jalousement,"
                    "vous allez faire beaucoup de choses avec🤣"
    )

class VideoUploadIntentResponse(ApiBaseResponse):

    result: UploadURLSchema