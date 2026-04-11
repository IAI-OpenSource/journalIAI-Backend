from fastapi import APIRouter, Depends, Response, Query, Path

from app.auth.role_depends import RoleDepends
from app.cache.helpers.base import get_redis, CacheWrapper
from app.globals.api_tags import ApiTags
from app.schemas.global_schemas import GlobalStringMessage
from app.services.comment_service import CommentService
from app.schemas.comment_schemas import (
    CommentCreate, CommentUpdate, CommentInfo,
    ApiPaginatedCommentListResponse, ApiCommentListResponse, CommentCountResponse, ReplyCountResponse
)
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Any, Annotated, Optional
from app.auth.role_depends import RoleDepends


routeur = APIRouter(prefix="/comments", tags=[ApiTags.COMMENT], dependencies=[Depends(RoleDepends.all_authorize)])



# IMPORTANT : les routes statiques (/paginated, /) doivent être déclarées
# AVANT les routes dynamiques (/{comment_id}) pour éviter les conflits FastAPI

def get_comment_service(
    bd: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[CacheWrapper, Depends(get_redis)]
) -> CommentService:
    return CommentService(bd, redis)


# ── Lecture ────────────────────────────────────────────────────────────────────

@routeur.get(
    "/post/{post_id}",
    name="Récupérer tous les commentaires d'un post",
    response_model=ApiCommentListResponse,
    deprecated=True
)
async def get_comments_by_post(
    post_id: Annotated[UUID, Path(description="L'identifiant du post")],
    reponse: Response,
    comment_service: Annotated[CommentService, Depends(get_comment_service)]
) -> Any:
    """Endpoint pour récupérer tous les commentaires d'un post. PRIORISER LA REQUÊTE AVEC PAGINATION."""
    result = await comment_service.service_get_comments_by_post(post_id=post_id)
    return result.to_HTTP_api_base_response(reponse)

@routeur.get(
    "/post/{post_id}/count",
    name="Compter les commentaires d'un post",
    response_model=CommentCountResponse
)
async def count_comments_by_post(
    post_id: Annotated[UUID, Path(description="L'identifiant du post")],
    reponse: Response,
    comment_service: Annotated[CommentService, Depends(get_comment_service)]
) -> Any:
    """Endpoint pour compter le nombre de commentaires racines d'un post."""
    result = await comment_service.service_count_comments_by_post(post_id=post_id)
    return result.to_HTTP_api_base_response(reponse)


@routeur.get(
    "/{comment_id}/replies/count",
    name="Compter les réponses d'un commentaire",
    response_model=ReplyCountResponse
)
async def count_replies_by_comment(
    comment_id: Annotated[UUID, Path(description="L'identifiant du commentaire parent")],
    reponse: Response,
    comment_service: Annotated[CommentService, Depends(get_comment_service)]
) -> Any:
    """Endpoint pour compter le nombre de réponses d'un commentaire."""
    result = await comment_service.service_count_replies_by_comment(
        parent_comment_id=comment_id
    )
    return result.to_HTTP_api_base_response(reponse)


@routeur.get(
    "/post/{post_id}/paginated",
    name="Récupérer les commentaires d'un post avec pagination",
    response_model=ApiPaginatedCommentListResponse
)
async def get_comments_paginated(
    post_id: Annotated[UUID, Path(description="L'identifiant du post")],
    reponse: Response,
    comment_service: Annotated[CommentService, Depends(get_comment_service)],
    cursor: Annotated[Optional[UUID], Query(description="L'identifiant du dernier commentaire récupéré (Optionnel)")] = None,
    limit: Annotated[int, Query(description="Le nombre maximum de commentaires à récupérer, par défaut 10", gt=0, le=100)] = 10
) -> Any:
    """Endpoint pour récupérer les commentaires d'un post avec pagination par curseur."""
    result = await comment_service.service_get_comments_paginated(post_id=post_id, cursor=cursor, limit=limit)
    return result.to_HTTP_api_base_response(reponse)


@routeur.get(
    "/{comment_id}/replies",
    name="Récupérer toutes les réponses d'un commentaire",
    response_model=ApiCommentListResponse,
    deprecated=True
)
async def get_replies_by_comment(
    comment_id: Annotated[UUID, Path(description="L'identifiant du commentaire parent")],
    reponse: Response,
    comment_service: Annotated[CommentService, Depends(get_comment_service)]
) -> Any:
    """Endpoint pour récupérer toutes les réponses d'un commentaire. PRIORISER LA REQUÊTE AVEC PAGINATION."""
    result = await comment_service.service_get_replies_by_comment(parent_comment_id=comment_id)
    return result.to_HTTP_api_base_response(reponse)


@routeur.get(
    "/{comment_id}/replies/paginated",
    name="Récupérer les réponses d'un commentaire avec pagination",
    response_model=ApiPaginatedCommentListResponse
)
async def get_replies_paginated(
    comment_id: Annotated[UUID, Path(description="L'identifiant du commentaire parent")],
    reponse: Response,
    comment_service: Annotated[CommentService, Depends(get_comment_service)],
    cursor: Annotated[Optional[UUID], Query(description="L'identifiant du dernier commentaire récupéré (Optionnel)")] = None,
    limit: Annotated[int, Query(description="Le nombre maximum de réponses à récupérer, par défaut 10", gt=0, le=100)] = 10
) -> Any:
    """Endpoint pour récupérer les réponses d'un commentaire avec pagination par curseur."""
    result = await comment_service.service_get_replies_paginated(
        parent_comment_id=comment_id, cursor=cursor, limit=limit
    )
    return result.to_HTTP_api_base_response(reponse)


@routeur.get(
    "/{comment_id}",
    name="Récupérer un commentaire par son ID",
    response_model=CommentInfo
)
async def get_comment_by_id(
    comment_id: Annotated[UUID, Path(description="L'identifiant du commentaire à récupérer")],
    reponse: Response,
    comment_service: Annotated[CommentService, Depends(get_comment_service)]
) -> Any:
    """Endpoint pour récupérer un commentaire par son ID."""
    result = await comment_service.service_find_comment_by_id(comment_id=comment_id)
    return result.to_HTTP_api_base_response(reponse)


# ── Mutations ──────────────────────────────────────────────────────────────────

# POST — créer
@routeur.post("/", name="Créer un commentaire", response_model=CommentInfo)
async def create_comment(
    payload: CommentCreate,
    reponse: Response,
    comment_service: Annotated[CommentService, Depends(get_comment_service)],
    current_user: Annotated[UUID, Depends(RoleDepends.get_current_user_id)]
) -> Any:
    result = await comment_service.service_create_comment(
        comment_data=payload,
        current_user_id=current_user
    )
    return result.to_HTTP_api_base_response(reponse)


# PUT — modifier (propriétaire seulement)
@routeur.put("/{comment_id}", name="Mettre à jour un commentaire", response_model=CommentInfo)
async def update_comment(
    comment_id: Annotated[UUID, Path(description="L'identifiant du commentaire")],
    payload: CommentUpdate,
    reponse: Response,
    comment_service: Annotated[CommentService, Depends(get_comment_service)],
    current_user: Annotated[UUID, Depends(RoleDepends.get_current_user_id)]
) -> Any:
    result = await comment_service.service_update_comment(
        comment_id=comment_id,
        comment_data=payload,
        current_user_id=current_user
    )
    return result.to_HTTP_api_base_response(reponse)


# DELETE — propriétaire ou admin
@routeur.delete("/{comment_id}", name="Supprimer un commentaire", response_model=GlobalStringMessage)
async def delete_comment(
    comment_id: Annotated[UUID, Path(description="L'identifiant du commentaire")],
    reponse: Response,
    comment_service: Annotated[CommentService, Depends(get_comment_service)],
    current_user: Annotated[UUID, Depends(RoleDepends.get_current_user_id)],
    is_admin: Annotated[bool, Depends(RoleDepends.is_admin)]
) -> Any:
    result = await comment_service.service_delete_comment(
        comment_id=comment_id,
        current_user_id=current_user,
        is_admin=is_admin
    )
    return result.to_HTTP_api_base_response(reponse)

