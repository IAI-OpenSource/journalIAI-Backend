"""
Routeur pour les opérations liées aux stories (création, uploads, suivi).
Endpoints pour l'upload de médias et la gestion des stories.
"""

from typing import Annotated

from fastapi import Depends, WebSocket, Query, WebSocketDisconnect, APIRouter, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.role_depends import RoleDepends
from app.cache.helpers.base import CacheWrapper, get_redis
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.auth.dependencies import get_current_user
from app.globals.routes_descriptions import STORY_INTENT_ROUTE_DESCRIPTION
from app.schemas.story_upload_schemas import (
    StoryMediaUploadIntentResponse, CreateStoryUploadIntent,
    StoryMediaUploadCompleteResponse
)
from app.schemas.user_schemas import ReadUser
from app.services.processing_service import ProcessingService
from app.services.story_upload_service import StoryMediaUploadsService

router = APIRouter(prefix="/stories", tags=[ApiTags.STORY], dependencies=[Depends(RoleDepends.all_authorize)])

def get_story_upload_service(
    cache: CacheWrapper = Depends(get_redis), bd: AsyncSession = Depends(get_db)
) -> StoryMediaUploadsService:
    """Crée une instance du service d'upload de stories."""
    return StoryMediaUploadsService(cache=cache, bd=bd)

def get_prcessing_service(
        cache: Annotated[CacheWrapper, Depends(get_redis)]
) -> ProcessingService:
    return ProcessingService(cache=cache)

@router.post(
    path="/get-uploads-intent",
    name="Créer une story avec un média (Image, Vidéo)",
    response_model=StoryMediaUploadIntentResponse,
    tags=[ApiTags.STORY_CREATION],
    description=STORY_INTENT_ROUTE_DESCRIPTION,
    dependencies=[Depends(RoleDepends.only_those_can_post_authorize)]
)
async def story_media_upload_intent(
    request_data: CreateStoryUploadIntent,
    response: Response,
    service: Annotated[StoryMediaUploadsService, Depends(get_story_upload_service)],
    current_user: Annotated[ReadUser, Depends(get_current_user)]
):
    res = await service.service_process_media_upload_intent(current_user, request_data)
    return res.to_HTTP_api_base_response(response)


@router.post(
    path="/complete_media",
    name="Finaliser un upload de story",
    tags=[ApiTags.STORY_CREATION],
    response_model=StoryMediaUploadCompleteResponse,
    description="Finalise un upload de story et lance le traitement. Retourne l'ID du job de traitement.",
    dependencies=[Depends(RoleDepends.only_those_can_post_authorize)]
)
async def complete_story_upload(
    response: Response,
    intent_id: Annotated[str, Query(..., description="L'ID d'intent récupéré précédemment via /get-uploads-intent")],
    service: Annotated[StoryMediaUploadsService, Depends(get_story_upload_service)],
    current_user: Annotated[ReadUser, Depends(get_current_user)]
):

    verification = await service.service_verify_complete_media_upload(current_user, intent_id)
    return verification.to_HTTP_api_base_response(response)


@router.websocket(
    path="/ws/processing_info",
    name="Websocket de suivi du traitement d'une story",
    dependencies=[Depends(RoleDepends.only_those_can_post_authorize)]
)
async def ws_story_processing_info(
    websocket: WebSocket,
    current_user: Annotated[ReadUser, Depends(get_current_user)],
    service : Annotated[ProcessingService, Depends(get_prcessing_service)],
    intent_id: str = Query(..., description="L'ID d'intent d'upload de la story pour lequel on veut suivre la progression"),
):
    """
    Websocket pour suivre la progression du traitement d'une story.

    Établit une connexion WebSocket pour recevoir les mises à jour de progression
    du traitement d'une story uploadée. Les messages incluent l'étape actuelle,
    le pourcentage de progression et tout message d'erreur.
    """
    await websocket.accept()

    try:
        await service.service_listen_media_processing_intent(current_user, intent_id, websocket)
    except WebSocketDisconnect:
        pass



