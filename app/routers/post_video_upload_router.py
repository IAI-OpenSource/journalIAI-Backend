import datetime
from uuid import UUID

from fastapi import APIRouter, Response, Depends, Query, WebSocket
from fastapi.websockets import WebSocketDisconnect

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.helpers.base import CacheWrapper, get_redis
from app.db.models.enums import SexeType
from app.db.models.user import User
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas.post_upload_schemas import PostMediaUploadIntentResponse, CreateMediaUploadIntent, PostMediaUploadCompleteResponse
from app.services.media_upload_service import MediaUploadsService

router = APIRouter(prefix="/post_video_upload")

async def get_mock_user():
    user = User(
        last_name="Adjovi",
        username="3f70c95e8e",
        email="akou.adjovi57@test.com",
        last_login_at=datetime.datetime.now(),
        classe_id=UUID("74910788-e47d-483d-b24f-750c7b24e3d6"),
        bio=None,
        access_jeton_id=UUID("42fc6492-4300-432f-b106-1304cebf86db"),
        avatar_url=None,
        first_name="Akou",
        password_hash="hashed_password",
        sexe=SexeType.M
    )
    user.id = UUID("0a58318e-3a4f-4354-bb6a-fed21a2e710b")

    return user

def get_post_upload_service(
    cache : CacheWrapper = Depends(get_redis), bd: AsyncSession = Depends(get_db)
) -> MediaUploadsService:
    return MediaUploadsService(cache=cache, bd=bd)

# TODO: Revoir tout ce fichier quand l'auth sera dispo et re-tester, principalement verifier si l'utilisateur peut post

@router.post(
    path="/intent", name="Générer un intent d'upload de média pour un post",
    response_model=PostMediaUploadIntentResponse, tags=[ApiTags.POSTS, ApiTags.UPLOADS]
)
async def post_unique_media_upload_intent(
    request_data: CreateMediaUploadIntent, response: Response, service = Depends(get_post_upload_service),
    current_user: User = Depends(get_mock_user)
):
    """
    Endpoint pour générer un intent d'upload de média pour un post, en fournissant les informations nécessaires
    pour initier un upload de média. L'endpoint valide les données d'entrée, génère une URL d'upload
    pré-signée, c'est sur cette Url que vous allez upload le fichier média du post
    """

    res = await service.service_process_media_upload_intent(current_user, request_data)

    return res.to_HTTP_api_base_response(response)

@router.post(
    path="/complete_video_post", name="Finaliser un post unique de média",
    tags=[ApiTags.POSTS, ApiTags.UPLOADS], response_model=PostMediaUploadCompleteResponse
)
async def complete_video_post(
    response: Response,
    intent_id: str = Query(..., description="L'id d'intent recupéré précedemment"),
    service = Depends(get_post_upload_service), current_user: User = Depends(get_mock_user)
):
    """
    Route pour confirmé l'upload du post média, vous ferrez une requete
    sur cette route après avoir uploadé totalement le fichier sur l'url délivré précedemment
    """

    verification = await service.service_verify_complete_media_upload(current_user, intent_id)

    return verification.to_HTTP_api_base_response(response)


@router.websocket(path="/ws/post_processing_info", name="Websocket de suivi du post-traitement d'une média uploadée")
async def ws_post_processing_info(
    websocket: WebSocket,
    intent_id: str = Query(..., description="L'id d'intent d'upload de média pour lequel on veut suivre le post-traitement"),
    service = Depends(get_post_upload_service), current_user: User = Depends(get_mock_user)
):
    """
    Websocket pour suivre le post-traitement d'un média uploadée, vous devez vous connecter à ce
    websocket après avoir confirmé l'upload de la média via l'endpoint `je mets çà après`, et fournir
    l'id d'intent d'upload de média pour lequel vous voulez suivre le post-traitement, vous recevrez des
    messages de suivi indiquant l'étape actuelle du post-traitement (verification, processing..), le pourcentage de
    progression et un timestamp, en cas d'échec vous recevrez un message d'erreur dans le champ `error_message`
    et le suivi sera terminé
    """

    await websocket.accept()

    try:
        await service.service_listen_media_processing_intent(current_user, intent_id, websocket)
    except WebSocketDisconnect:
        pass