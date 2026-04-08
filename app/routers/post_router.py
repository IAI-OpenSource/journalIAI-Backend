from typing import Annotated
from uuid import UUID

from fastapi.params import Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.role_depends import RoleDepends
from app.cache.helpers.base import CacheWrapper, get_redis
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.globals.routes_descriptions import (
    MEDIA_INTENT_ROUTE_DESCRIPTION, MEDIA_INTENT_CONFIRM_ROUTE_DESCRIPTION, GET_FEED_ROUTE_DESCRIPTION,
    CREATE_TEXT_POST_ROUTE_DESCRIPTION, GET_POST_ROUTE_DESCRIPTION,

)
from app.schemas.post_schemas import (
    CreatePost,
    PostInfos,
    PostListInfos, CreatePostView,
)
from app.auth.dependencies import get_current_user
from app.schemas.post_upload_schemas import PostMediaUploadIntentResponse, CreateMediaUploadIntent, \
    PostMediaUploadCompleteResponse
from app.schemas.user_schemas import ReadUser
from app.services.media_upload_service import MediaUploadsService
from fastapi import Depends, WebSocket, Query, WebSocketDisconnect, APIRouter, Response
from app.services.post_service import PostService

router = APIRouter(prefix="/posts", tags=[ApiTags.POSTS], dependencies=[Depends(RoleDepends.all_authorize)])


# ------------------------------------------------------------------
# Dépendances
# ------------------------------------------------------------------

def get_redis_cache(redis: CacheWrapper = Depends(get_redis)) -> CacheWrapper:
    return redis

def get_post_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    cache: CacheWrapper = Depends(get_redis_cache),
) -> PostService:
    return PostService(db, cache)

def get_post_upload_service(
    cache : CacheWrapper = Depends(get_redis), bd: AsyncSession = Depends(get_db)
) -> MediaUploadsService:
    return MediaUploadsService(cache=cache, bd=bd)


# TODO: Revoir tout ce fichier quand l'auth sera dispo et re-tester, principalement verifier si l'utilisateur peut post

@router.post(
    path="/get-uploads-intent", name="Créer un post avec des médias (Images, Vidéos)",
    response_model=PostMediaUploadIntentResponse, tags=[ApiTags.POSTS_CREATION],
    description=MEDIA_INTENT_ROUTE_DESCRIPTION,
    dependencies=[Depends(RoleDepends.only_those_can_post_authorize)]
)
async def post_media_upload_intent(
    request_data: CreateMediaUploadIntent, response: Response,
    service: Annotated[MediaUploadsService, Depends(get_post_upload_service)],
    current_user: Annotated[ReadUser, Depends(get_current_user)]
):
    res = await service.service_process_media_upload_intent(current_user, request_data)

    return res.to_HTTP_api_base_response(response)

@router.post(
    path="/complete_medias_post", name="Finaliser un post aves des médias",
    tags=[ApiTags.POSTS_CREATION], response_model=PostMediaUploadCompleteResponse,
    description=MEDIA_INTENT_CONFIRM_ROUTE_DESCRIPTION,
    dependencies=[Depends(RoleDepends.only_those_can_post_authorize)]
)
async def complete_video_post(
    response: Response,
    intent_id:  Annotated[str, Query(..., description="L'id d'intent recupéré précedemment")],
    service: Annotated[MediaUploadsService, Depends(get_post_upload_service)],
    current_user: Annotated[ReadUser, Depends(get_current_user)]
):

    verification = await service.service_verify_complete_media_upload(current_user, intent_id)

    return verification.to_HTTP_api_base_response(response)


@router.websocket(
    path="/ws/post_processing_info",
    name="Websocket de suivi du post-traitement d'une création de post",
    dependencies=[Depends(RoleDepends.only_those_can_post_authorize)]
)
async def ws_post_processing_info(
    websocket: WebSocket,
    current_user: Annotated[ReadUser, Depends(get_current_user)],
    intent_id: str = Query(..., description="L'id d'intent d'upload de média pour lequel on veut suivre le post-traitement"),
    service = Depends(get_post_upload_service),
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

# ------------------------------------------------------------------
# Routes Posts
# ------------------------------------------------------------------

@router.post(
    "",
    response_model=PostInfos,
    summary="Créer un post Tectuel Simple sans médias",
    description=CREATE_TEXT_POST_ROUTE_DESCRIPTION,
    tags=[ApiTags.POSTS_CREATION],
    dependencies=[Depends(RoleDepends.only_those_can_post_authorize)]
)
async def create_post(
    post_data: CreatePost,
    response: Response,
    current_user: Annotated[ReadUser, Depends(get_current_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
):
    result = await post_service.service_create_text_post(user=current_user, post_data=post_data)

    return result.to_HTTP_api_base_response(response)

# TODO : Ajouter optimisations Redis
@router.get(
    "/feed",
    response_model=PostListInfos,
    summary="Récupérer le feed paginé",
    description=GET_FEED_ROUTE_DESCRIPTION,
)
async def get_feed(
    response: Response,
    current_user: Annotated[ReadUser, Depends(get_current_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
    cursor: Annotated[str, Query(description="Le dernir curseur renvoyé")] = None,
    limit: Annotated[int, Query(description="Le nombre de post sue vous voulez (entre 0-20 max)", gt=0, lt=20)] = 10,
):

    result = await post_service.service_get_feed(
        user_id=current_user.id,
        cursor=cursor,
        page_size=limit,
        user_classe_id=current_user.classe.id if current_user.classe else None
    )

    return result.to_HTTP_api_base_response(response)


# TODO : Ajouter optimisations Redis
@router.get(
    "/{post_id}",
    response_model=PostInfos,
    summary="Récupérer un post par ID",
    description=GET_POST_ROUTE_DESCRIPTION
)
async def get_post(
    post_id: Annotated[UUID, Path(description="l'id du post")],
    response: Response,
    current_user: Annotated[ReadUser, Depends(get_current_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
):
    result = await post_service.service_get_post(
        post_id=post_id, user_class_id=current_user.classe.id if current_user.classe else None,
        user_id=current_user.id
    )

    return result.to_HTTP_api_base_response(response)


@router.post(
    "/add-views",
    response_model=None,
    status_code=200,
    summary="Marquer des posts comme vu par l'utilisateur"
)
async def record_view(
    data: CreatePostView,
    response: Response,
    current_user: Annotated[ReadUser, Depends(get_current_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
):
    """Enregistre la vue d'un post. Opération idempotente —
    une deuxième vue du même utilisateur est ignorée silencieusement.
    """
    await post_service.service_record_view(
        post_ids=data.posts_ids,
        user_id=current_user.id,
    )
    response.status_code = 200
