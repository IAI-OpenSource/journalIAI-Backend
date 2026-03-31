from typing import Annotated
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.helpers.base import CacheWrapper, get_redis
from app.db.session import get_db
from app.globals.api_tags import ApiTags
from app.schemas.post_schemas import (
    CreatePost,
    PostInfos,
    PostListInfos,
)
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
    return PostService(db)


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
    user_id:UUID,
    cursor: str | None = None,
    page_size: int = 20,
    post_service: PostService = Depends(get_post_service),
):
    """Retourne une page du feed.
 
    Les posts déjà vus par cet utilisateur sont automatiquement exclus
    grâce au cache Redis (SET user:{id}:seen_posts).
 
    - Première page : cursor absent
    - Page suivante : passer next_cursor reçu dans la réponse précédente
    - Pull-to-refresh : appeler sans cursor (efface le contexte de pagination)
    """
    result = await post_service.service_get_feed(
        user_id=user_id,
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
    "/feed/new-count",
    summary="Badge — nombre de nouveaux posts depuis un timestamp (spec §7.3)",
)
async def get_new_posts_count(
    response: Response,
    academic_year_id: UUID,
    since: datetime,
    post_service: PostService = Depends(get_post_service),
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
