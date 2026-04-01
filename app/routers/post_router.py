from typing import Annotated
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.helpers.base import CacheWrapper, get_redis
from app.db.models.enums import SexeType
from app.db.models.user import User
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.globals.routes_descriptions import (
    MEDIA_INTENT_ROUTE_DESCRIPTION, MEDIA_INTENT_CONFIRM_ROUTE_DESCRIPTION, GET_FEED_ROUTE_DESCRIPTION,

)
from app.schemas.post_schemas import (
    CreatePost,
    PostInfos,
    PostListInfos,
)
from app.schemas.post_upload_schemas import PostMediaUploadIntentResponse, CreateMediaUploadIntent, \
    PostMediaUploadCompleteResponse
from app.services.media_upload_service import MediaUploadsService
from fastapi import Depends, WebSocket, Query, WebSocketDisconnect, APIRouter, Response, Path
from app.services.post_service import PostService

router = APIRouter(prefix="/posts", tags=[ApiTags.POSTS])


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

def get_mock_user():
    user = User(
        last_name="Adjovi",
        username="3f70c95e8e",
        email="akou.adjovi57@test.com",
        last_login_at=datetime.now(),
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

# TODO: Revoir tout ce fichier quand l'auth sera dispo et re-tester, principalement verifier si l'utilisateur peut post

@router.post(
    path="/get-uploads-intent", name="Créer un post avec des médias (Images, Vidéos)",
    response_model=PostMediaUploadIntentResponse, tags=[ApiTags.POSTS_CREATION],
    description=MEDIA_INTENT_ROUTE_DESCRIPTION
)
async def post_unique_media_upload_intent(
    request_data: CreateMediaUploadIntent, response: Response,
    service: Annotated[MediaUploadsService, Depends(get_post_upload_service)],
    current_user: Annotated[User, Depends(get_mock_user)]
):
    res = await service.service_process_media_upload_intent(current_user, request_data)

    return res.to_HTTP_api_base_response(response)

@router.post(
    path="/complete_medias_post", name="Finaliser un post aves des médias",
    tags=[ApiTags.POSTS_CREATION], response_model=PostMediaUploadCompleteResponse,
    description=MEDIA_INTENT_CONFIRM_ROUTE_DESCRIPTION
)
async def complete_video_post(
    response: Response,
    intent_id:  Annotated[str, Query(..., description="L'id d'intent recupéré précedemment")],
    service: Annotated[MediaUploadsService, Depends(get_post_upload_service)],
    current_user: Annotated[User, Depends(get_mock_user)]
):

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

# ------------------------------------------------------------------
# Routes Posts
# ------------------------------------------------------------------

@router.post(
    "",
    response_model=PostInfos,
    status_code=201,
    summary="Créer un post",
)
async def create_post(
    post_data: CreatePost,
    response: Response,
    current_user: Annotated[User, Depends(get_mock_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
):
    """Crée un nouveau post.

    author_id et academic_year_id seront injectés depuis le token JWT
    une fois le middleware d'authentification branché.
    """
    result = await post_service.service_create_post(
        author_id=current_user.id,
        academic_year_id=academic_year_id,
        post_data=post_data,
    )

    if result.is_error():
        return PostInfos.error_response(
            error_message=result.error,
            status_code=result.status_code,
            response=response,
        )

    return PostInfos.success_response(
        data=result.data,
        response=response,
        status_code=result.status_code,
    )

# TODO : Ajouter optimisations Redis
@router.get(
    "/feed",
    response_model=PostListInfos,
    summary="Récupérer le feed paginé",
    description=GET_FEED_ROUTE_DESCRIPTION
)
async def get_feed(
    response: Response,
    current_user: Annotated[User, Depends(get_mock_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
    cursor: Annotated[str, Query(description="Le dernir curseur renvoyé")] = None,
    page_size: Annotated[int, Query(description="Le nombre de post sue vous voulez (entre 0-20 max)", gt=0, lt=20)] = 10,
):

    result = await post_service.service_get_feed(
        user_id=current_user.id,
        cursor=cursor,
        page_size=page_size,
    )

    return result.to_HTTP_api_base_response(response)


@router.get(
    "/feed/new-count",
    summary="Badge — nombre de nouveaux posts depuis un timestamp (spec §7.3)",
)
async def get_new_posts_count(
    response: Response,
    academic_year_id: UUID,
    since: datetime,
    post_service: Annotated[PostService, Depends(get_post_service)]
):
    """Compte les posts créés après `since`. Polling toutes les 60s.
 
    Requête ultra-légère (COUNT(*) uniquement, < 10ms).
 
    Paramètres :
    - since : datetime ISO 8601 du dernier refresh client
      Exemple : 2025-02-26T10:00:00Z
 
    Réponse : { "ok": true, "result": { "new_count": 3 } }
 
    Le frontend affiche le badge si new_count > 0.
    """
    result = await post_service.service_count_new_posts(
        academic_year_id=academic_year_id,
        since=since,
    )
    if result.is_error():
        return PostListInfos.error_response(
            error_message=result.error,
            status_code=result.status_code,
            response=response,
        )
    return PostListInfos.success_response(
        data=result.data, response=response, status_code=result.status_code,
    )
# TODO : Ajouter optimisations Redis
@router.get(
    "/{post_id}",
    response_model=PostInfos,
    summary="Récupérer un post par ID",
)
async def get_post(
    post_id: UUID,
    response: Response,
    post_service: Annotated[PostService, Depends(get_post_service)],
):
    result = await post_service.service_get_post(post_id=post_id)

    if result.is_error():
        return PostInfos.error_response(
            error_message=result.error,
            status_code=result.status_code,
            response=response,
        )

    return PostInfos.success_response(
        data=result.data,
        response=response,
        status_code=result.status_code,
    )

# ------------------------------------------------------------------
# Enregistrement d'une vue
# ------------------------------------------------------------------
# TODO : Ajouter optimisations Redis
@router.post(
    "/{post_id}/view",
    response_model=None,
    status_code=200,
    summary="Enregistrer une vue sur un post",
)
async def record_view(
    post_id: Annotated[UUID, Path(..., description="L'id du post vu")],
    response: Response,
    current_user: Annotated[User, Depends(get_mock_user)],
    post_service: Annotated[PostService, Depends(get_post_service)],
):
    """Enregistre la vue d'un post. Opération idempotente —
    une deuxième vue du même utilisateur est ignorée silencieusement.
    """
    await post_service.service_record_view(
        post_id=post_id,
        user_id=current_user.id,
    )
    response.status_code = 200
