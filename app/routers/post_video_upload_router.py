from typing import Annotated

from fastapi import APIRouter, Response, Depends, Query, WebSocket
from starlette.websockets import WebSocketDisconnect
from time import time
from app.cache.helpers.base import CacheWrapper, get_redis
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas.upload_schemas import VideoUploadIntentResponse, CreateVideoUploadIntent, WsPostProcessingInfoSchema, \
    WsPostProcessingInfoSchemaSteps
from app.services.video_upload_service import VideoUploadsService

router = APIRouter(prefix="/post_video_upload")


# TODO: Revoir tout ce fichier quand l'auth sera dispo et re-tester, principalement verifier si l'utilisateur peut post

@router.post(
    path="/intent",
    name="Générer un intent d'upload de vidéo pour un post",
    response_model=VideoUploadIntentResponse,
    tags=[ApiTags.POSTS, ApiTags.UPLOADS]
)
async def post_video_upload_intent(
    request_data: CreateVideoUploadIntent, response: Response, cache : CacheWrapper = Depends(get_redis),
    bd = Depends(get_db)
):
    """
    Endpoint pour générer un intent d'upload de vidéo pour un post, en fournissant les informations nécessaires
    pour initier un upload de vidéo. L'endpoint valide les données d'entrée, génère une URL d'upload
    pré-signée, c'est sur cette Url que vous allez upload le fichier vidéo du post
    """

    service = VideoUploadsService(cache=cache, bd=bd)

    res = await service.service_process_video_upload_intent("Sevtify44", request_data)

    return res.to_HTTP_api_base_response(response)

@router.websocket(
    path="/ws/complete_video_post",
    name="Finaliser un post vidéo"
)
async def ws_complete_video_post(
    websocket: WebSocket,
    intent_id = Annotated[str, Query(..., description="L'id d'intent recupéré précedemment")],
    cache : CacheWrapper = Depends(get_redis), bd = Depends(get_db)
):
    """Je suis pas inspiré pour le moment"""

    await websocket.accept()

    service = VideoUploadsService(cache=cache, bd=bd)

    message_de_suivi: WsPostProcessingInfoSchema = WsPostProcessingInfoSchema(
        step=WsPostProcessingInfoSchemaSteps.VERIFICATION, progress=0, error_message=None,
        timestamp=time()
    )

    verification = await service.service_verify_complete_video_upload("Sevtify44", str(intent_id))

    if verification.is_error():
        message_de_suivi.timestamp = time()
        message_de_suivi.error_message = verification.error
        await websocket.send_json(message_de_suivi.model_dump_json())
        await websocket.close()
        return

    # Lancer la tache de traitement du fichier
    try:
        while True:
            # Tenir le front informé de l'avancé du traitement
            continue
    except WebSocketDisconnect:
        pass






