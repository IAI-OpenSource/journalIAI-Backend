## fichier contenant les routes FastAPI pour les posts
## pattern identique à auth.py : dépendances → service → réponse ApiBaseResponse

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models.enums import MediaType
from app.globals.api_tags import ApiTags
from app.schemas.post_schemas import (
    CreatePost,
    PostInfos,
    PostListInfos,
    PostMediaInfos,
    PresignedUrlInfos,
    RequestMediaUploadUrl,
    ConfirmMediaUpload,
)
from app.services.post_service import PostService

router = APIRouter(prefix="/posts", tags=[ApiTags.POSTS])


# ------------------------------------------------------------------
# Dépendances
# ------------------------------------------------------------------

def get_post_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostService:
    return PostService(db)


# ------------------------------------------------------------------
# Routes Posts
# ------------------------------------------------------------------

@router.post(
    "",
    response_model=PostInfos,
    summary="Créer un post",
)
async def create_post(
    post_data: CreatePost,
    response: Response,
    # TODO : remplacer ces UUID par les dépendances JWT quand auth sera prête
    author_id: UUID,
    academic_year_id: UUID,
    post_service: Annotated[PostService, Depends(get_post_service)],
):
    """Crée un nouveau post.

    author_id et academic_year_id seront injectés depuis le token JWT
    une fois le middleware d'authentification branché.
    """
    result = await post_service.service_create_post(
        author_id=author_id,
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


@router.get(
    "/feed",
    response_model=PostListInfos,
    summary="Récupérer le feed paginé",
)
async def get_feed(
    response: Response,
    academic_year_id: UUID,
    cursor: str | None = None,
    page_size: int = 20,
    post_service: PostService = Depends(get_post_service),
):
    """Retourne une page du feed (cursor-based pagination).

    Passer le next_cursor reçu dans la réponse précédente pour
    obtenir la page suivante. NULL = première page.
    """
    result = await post_service.service_get_feed(
        academic_year_id=academic_year_id,
        cursor=cursor,
        page_size=page_size,
    )

    if result.is_error():
        return PostListInfos.error_response(
            error_message=result.error,
            status_code=result.status_code,
            response=response,
        )

    return PostListInfos.success_response(
        data=result.data,
        response=response,
        status_code=result.status_code,
    )


@router.get(
    "/{post_id}",
    response_model=PostInfos,
    summary="Récupérer un post par ID",
)
async def get_post(
    post_id: UUID,
    response: Response,
    post_service: PostService = Depends(get_post_service),
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
# Routes Médias (flow upload en 3 étapes)
# ------------------------------------------------------------------

@router.post(
    "/{post_id}/media/upload-url",
    response_model=PresignedUrlInfos,
    summary="Étape 1 — Demander une URL d'upload MinIO",
)
async def request_upload_url(
    post_id: UUID,
    upload_request: RequestMediaUploadUrl,
    response: Response,
    post_service: PostService = Depends(get_post_service),
):
    """Génère une presigned PUT URL valable 15 minutes.

    Le client doit ensuite faire un PUT directement sur cette URL
    avec le fichier binaire en body — sans passer par l'API.
    Une fois l'upload terminé, appeler /confirm pour créer l'entrée DB.

    Retourne :
    - upload_url : URL PUT présignée MinIO (pointe vers MINIO_PUBLIC_URL)
    - object_key : clé à conserver et renvoyer lors de la confirmation
    """
    result = await post_service.service_request_upload_url(
        post_id=post_id,
        filename=upload_request.filename,
        media_type=upload_request.media_type,
    )

    if result.is_error():
        return PresignedUrlInfos.error_response(
            error_message=result.error,
            status_code=result.status_code,
            response=response,
        )

    return PresignedUrlInfos.success_response(
        data=result.data,
        response=response,
        status_code=result.status_code,
    )


@router.post(
    "/{post_id}/media/confirm",
    response_model=PostMediaInfos,
    status_code=201,
    summary="Étape 3 — Confirmer l'upload et déclencher le worker",
)
async def confirm_media_upload(
    post_id: UUID,
    media_data: ConfirmMediaUpload,
    response: Response,
    post_service: PostService = Depends(get_post_service),
):
    """Confirme qu'un upload MinIO a réussi.

    Le service :
    1. Vérifie que l'objet existe dans MinIO (évite les entrées DB orphelines)
    2. Crée l'entrée PostMedia en base (is_processed=False)
    3. Déclenche le worker Celery pour conversion WebP + thumbnail

    Le champ is_processed passera à True une fois le worker terminé.
    """
    result = await post_service.service_confirm_media_upload(
        post_id=post_id,
        media_data=media_data,
    )

    if result.is_error():
        return PostMediaInfos.error_response(
            error_message=result.error,
            status_code=result.status_code,
            response=response,
        )

    return PostMediaInfos.success_response(
        data=result.data,
        response=response,
        status_code=result.status_code,
    )


# ------------------------------------------------------------------
# Enregistrement d'une vue
# ------------------------------------------------------------------

@router.post(
    "/{post_id}/view",
    response_model=None,
    status_code=200,
    summary="Enregistrer une vue sur un post",
)
async def record_view(
    post_id: UUID,
    response: Response,
    # TODO : injecter user_id depuis JWT
    user_id: UUID,
    post_service: PostService = Depends(get_post_service),
):
    """Enregistre la vue d'un post. Opération idempotente —
    une deuxième vue du même utilisateur est ignorée silencieusement.
    """
    await post_service.service_record_view(
        post_id=post_id,
        user_id=user_id,
    )
    response.status_code = 200
