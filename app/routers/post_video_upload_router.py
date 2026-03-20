from fastapi import APIRouter, Response, Depends

from app.cache.helpers.base import CacheWrapper, get_redis
from app.schemas.upload_schemas import VideoUploadIntentResponse, CreateVideoUploadIntent

router = APIRouter(prefix="/post_video_upload")

@router.post(
    path="/intent",
    name="Générer un intent d'upload de vidéo pour un post",
    response_model=VideoUploadIntentResponse
)
async def post_video_upload_intent(
    request_data: CreateVideoUploadIntent, response: Response, cache : CacheWrapper = Depends(get_redis)
):
    """
    Endpoint pour générer un intent d'upload de vidéo pour un post, en fournissant les informations nécessaires
    pour initier un upload de vidéo. L'endpoint valide les données d'entrée, génère une URL d'upload
    pré-signée, c'est sur cette Url que vous allez upload le fichier vidéo du post
    """
    pass



