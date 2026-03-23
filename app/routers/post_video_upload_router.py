from typing import Annotated

from fastapi import APIRouter, Response, Depends, Query, WebSocket
from fastapi.websockets import WebSocketDisconnect
from time import time
from app.cache.helpers.base import CacheWrapper, get_redis
from app.db.models.user import User
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas.upload_schemas import VideoUploadIntentResponse, CreateVideoUploadIntent, WsPostProcessingInfoSchema, \
    WsPostProcessingInfoSchemaSteps, VideoUploadCompleteSchema, VideoUploadCompleteResponse
from app.services.video_upload_service import VideoUploadsService

router = APIRouter(prefix="/post_video_upload")


# TODO: Revoir tout ce fichier quand l'auth sera dispo et re-tester, principalement verifier si l'utilisateur peut post

@router.post(
    path="/intent", name="Générer un intent d'upload de vidéo pour un post",
    response_model=VideoUploadIntentResponse, tags=[ApiTags.POSTS, ApiTags.UPLOADS]
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

@router.post(
    path="/complete_video_post", name="Finaliser un post vidéo",
    tags=[ApiTags.POSTS, ApiTags.UPLOADS], response_model=VideoUploadCompleteResponse
)
async def complete_video_post(
    response: Response,
    intent_id = Annotated[str, Query(..., description="L'id d'intent recupéré précedemment")],
    cache : CacheWrapper = Depends(get_redis), bd = Depends(get_db)
):
    """
    Route pour confirmé l'upload du post vidéo, vous ferrez une requete
    sur cette route après avoir uploadé totalement le fichier
    """

    service = VideoUploadsService(cache=cache, bd=bd)

    verification = await service.service_verify_complete_video_upload("Sevtify44", str(intent_id))

    return verification.to_HTTP_api_base_response(response)


@router.websocket(path="/ws/post_processing_info", name="Websocket de suivi du post-traitement d'une vidéo uploadée")
async def ws_post_processing_info(
    websocket: WebSocket, intent_id: str = Query(..., description="L'id d'intent d'upload de vidéo pour lequel on veut suivre le post-traitement")
):
    """
    Websocket pour suivre le post-traitement d'une vidéo uploadée, vous devez vous connecter à ce
    websocket après avoir confirmé l'upload de la vidéo via l'endpoint /complete_video_post, et fournir
    l'id d'intent d'upload de vidéo pour lequel vous voulez suivre le post-traitement, vous recevrez des
    messages de suivi indiquant l'étape actuelle du post-traitement (verification ou processing), le pourcentage de
    progression et un timestamp, en cas d'échec vous recevrez un message d'erreur dans le champ 'error_message'
    et le suivi sera terminé
    """

    await websocket.accept()

    try:
        while True:
            # Simuler l'envoi périodique d'informations de suivi du post-traitement
            for progress in range(0, 101, 10):
                if progress < 50:
                    step = WsPostProcessingInfoSchemaSteps.VERIFICATION
                else:
                    step = WsPostProcessingInfoSchemaSteps.PROCESSING

                info = WsPostProcessingInfoSchema(
                    step=step,
                    progress=progress,
                    timestamp=int(time() * 1000)
                )
                await websocket.send_json(info.dict())
                await asyncio.sleep(1)

            # Simuler la fin du suivi après avoir atteint 100% de progression
            break

    except WebSocketDisconnect:
        print("Client déconnecté du websocket de suivi du post-traitement"
)