import logging
from typing import Optional, Any, cast
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.comment_repository import CommentRepository, PaginatedCommentResult
from app.cache.comment_cache import CommentCache
from app.cache.helpers.base import CacheWrapper
from app.globals.cache_duration import CacheDurartion
from app.schemas.comment_schemas import (
    CommentCreate, CommentUpdate,
    PaginatedCommentListResponse, CommentRead, SimpleCommentListResponse
)
from app.globals.messages import Messages as msg
from app.services import ServiceResult
from app.schemas.global_schemas import StringMessage

logger = logging.getLogger(__name__)


class CommentService:
    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.db = db
        self.comment_repo = CommentRepository(self.db)
        self.comment_cache = CommentCache(cache)

    # -------------------------------------------------------------------------
    # Helpers d'invalidation
    # -------------------------------------------------------------------------

    async def _invalidate_comment_caches(
        self,
        comment_id: UUID,
        post_id: UUID,
        parent_comment_id: Optional[UUID] = None
    ) -> None:
        """
        Invalide tous les caches liés à un commentaire après une mutation.

        Args:
            comment_id (UUID): Identifiant du commentaire modifié.
            post_id (UUID): Identifiant du post auquel appartient le commentaire.
            parent_comment_id (Optional[UUID]): Identifiant du commentaire parent
                si c'est une réponse, afin d'invalider aussi le cache des réponses.
        """
        await self.comment_cache.delete_comment_from_cache(comment_id)
        await self.comment_cache.delete_comments_paginated_from_cache(post_id, cursor=None, limit=10)
        if parent_comment_id:
            await self.comment_cache.delete_replies_paginated_from_cache(parent_comment_id, cursor=None, limit=10)

    # -------------------------------------------------------------------------
    # Lecture
    # -------------------------------------------------------------------------

    async def service_find_comment_by_id(self, comment_id: UUID) -> ServiceResult[CommentRead]:
        """
        Récupère un commentaire par son ID — cache en priorité.

        Args:
            comment_id (UUID): Identifiant unique du commentaire à récupérer.

        Returns:
            ServiceResult[CommentRead]: Le commentaire trouvé, ou une erreur
                si introuvable ou déjà supprimé.
        """
        # 1. Vérifier le cache
        cached = cast(
            Optional[CommentRead],
            await self.comment_cache.get_comment_from_cache(comment_id)
        )
        if cached is not None:
            logger.info(f"Commentaire {comment_id} trouvé en cache")
            if cached.is_deleted():
                return ServiceResult.service_error(
                    message=msg.DELETED_COMMENT,
                    status_code=400,
                    service_name=msg.COMMENT_SERVICE
                )
            return ServiceResult.service_success(cached, status_code=200)

        # 2. Sinon, aller en base
        comment = await self.comment_repo.get_comment_by_id(comment_id=comment_id)

        if comment.is_error():
            logger.error(f"Erreur: {comment.error}")
            return ServiceResult.service_error(
                message=comment.error,
                status_code=comment.status_code,
                service_name=msg.COMMENT_SERVICE
            )

        validated: CommentRead = CommentRead.model_validate(comment.data)

        if validated.is_deleted():
            return ServiceResult.service_error(
                message=msg.DELETED_COMMENT,
                status_code=400,
                service_name=msg.COMMENT_SERVICE
            )

        # 3. Mettre en cache
        await self.comment_cache.set_comment_in_cache(comment_id, validated, CacheDurartion.COMMENT_DURATION)

        return ServiceResult.service_success(validated, status_code=200)

    async def service_get_comments_by_post(self, post_id: UUID) -> ServiceResult[SimpleCommentListResponse]:
        """
        Récupère tous les commentaires racines (non supprimés) d'un post.

        Args:
            post_id (UUID): Identifiant du post dont on veut les commentaires.

        Returns:
            ServiceResult[SimpleCommentListResponse]: La liste des commentaires,
                ou une erreur si la récupération échoue.
        """
        comments = await self.comment_repo.get_comments_by_post(post_id=post_id)

        if comments.is_error():
            logger.error(f"Erreur: {comments.error}")
            return ServiceResult.service_error(
                message=comments.error,
                status_code=comments.status_code,
                service_name=msg.COMMENT_SERVICE
            )

        validated = [CommentRead.model_validate(c) for c in comments.data]
        response = SimpleCommentListResponse(comments=validated)

        return ServiceResult.service_success(data=response, status_code=200, service_name=msg.COMMENT_SERVICE)

    async def service_get_replies_by_comment(self, parent_comment_id: UUID) -> ServiceResult[SimpleCommentListResponse]:
        """
        Récupère toutes les réponses (non supprimées) d'un commentaire parent.

        Args:
            parent_comment_id (UUID): Identifiant du commentaire parent.

        Returns:
            ServiceResult[SimpleCommentListResponse]: La liste des réponses,
                ou une erreur si la récupération échoue.
        """
        replies = await self.comment_repo.get_replies_by_comment(parent_comment_id=parent_comment_id)

        if replies.is_error():
            logger.error(f"Erreur: {replies.error}")
            return ServiceResult.service_error(
                message=replies.error,
                status_code=replies.status_code,
                service_name=msg.COMMENT_SERVICE
            )

        validated = [CommentRead.model_validate(c) for c in replies.data]
        response = SimpleCommentListResponse(comments=validated)

        return ServiceResult.service_success(data=response, status_code=200, service_name=msg.COMMENT_SERVICE)

    async def service_get_comments_paginated(
        self, post_id: UUID, cursor: Optional[UUID] = None, limit: int = 10
    ) -> ServiceResult[Any] | ServiceResult[BaseModel] | ServiceResult[PaginatedCommentListResponse]:
        """
        Récupère les commentaires racines d'un post avec pagination par curseur — cache en priorité.

        Args:
            post_id (UUID): Identifiant du post dont on veut les commentaires.
            cursor (Optional[UUID]): Identifiant du dernier commentaire récupéré.
                Si None, la pagination commence depuis le début.
            limit (int): Nombre maximum de commentaires à récupérer (défaut : 10).

        Returns:
            ServiceResult[PaginatedCommentListResponse]: La liste paginée des commentaires
                avec le curseur de la page suivante, ou une erreur si la récupération échoue.
        """
        # 1. Vérifier le cache
        cached = await self.comment_cache.get_comments_paginated_from_cache(post_id, cursor, limit)
        if cached is not None:
            logger.info(f"Commentaires paginés (post={post_id}, cursor={cursor}) trouvés en cache")
            return ServiceResult.service_success(cached, status_code=200)

        # 2. Sinon, aller en base
        result = await self.comment_repo.get_comments_paginated(post_id=post_id, cursor=cursor, limit=limit)

        if result.is_error():
            logger.error(f"Erreur pagination commentaires: {result.error}")
            return ServiceResult.service_error(
                message=msg.INTERNAL_SERVER_ERROR,
                status_code=result.status_code,
                service_name=msg.COMMENT_SERVICE
            )

        try:
            paginated_data: PaginatedCommentResult = result.data
            validated_comments = [CommentRead.model_validate(c) for c in paginated_data["comments"]]
        except Exception as e:
            logger.error(f"Erreur de validation commentaires paginés: {e}")
            return ServiceResult.service_error(
                message=msg.INTERNAL_SERVER_ERROR,
                status_code=500,
                service_name=msg.COMMENT_SERVICE
            )

        # 3. Construire la réponse paginée
        list_response = PaginatedCommentListResponse(
            comments=validated_comments,
            next_cursor=paginated_data["next_cursor"]
        )

        # 4. Mettre en cache
        await self.comment_cache.set_comments_paginated_in_cache(
            post_id, cursor, limit, list_response, int(CacheDurartion.COMMENT_DURATION)
        )

        logger.info(f"Commentaires récupérés — count: {len(validated_comments)}")
        return ServiceResult.service_success(data=list_response, status_code=200)

    async def service_get_replies_paginated(
        self, parent_comment_id: UUID, cursor: Optional[UUID] = None, limit: int = 10
    ) -> ServiceResult[Any] | ServiceResult[BaseModel] | ServiceResult[PaginatedCommentListResponse]:
        """
        Récupère les réponses d'un commentaire avec pagination par curseur — cache en priorité.

        Args:
            parent_comment_id (UUID): Identifiant du commentaire parent.
            cursor (Optional[UUID]): Identifiant de la dernière réponse récupérée.
                Si None, la pagination commence depuis le début.
            limit (int): Nombre maximum de réponses à récupérer (défaut : 10).

        Returns:
            ServiceResult[PaginatedCommentListResponse]: La liste paginée des réponses
                avec le curseur de la page suivante, ou une erreur si la récupération échoue.
        """
        # 1. Vérifier le cache
        cached = await self.comment_cache.get_replies_paginated_from_cache(parent_comment_id, cursor, limit)
        if cached is not None:
            logger.info(f"Réponses paginées (parent={parent_comment_id}, cursor={cursor}) trouvées en cache")
            return ServiceResult.service_success(cached, status_code=200)

        # 2. Sinon, aller en base
        result = await self.comment_repo.get_replies_paginated(
            parent_comment_id=parent_comment_id, cursor=cursor, limit=limit
        )

        if result.is_error():
            logger.error(f"Erreur pagination réponses: {result.error}")
            return ServiceResult.service_error(
                message=msg.INTERNAL_SERVER_ERROR,
                status_code=result.status_code,
                service_name=msg.COMMENT_SERVICE
            )

        try:
            paginated_data: PaginatedCommentResult = result.data
            validated_replies = [CommentRead.model_validate(c) for c in paginated_data["comments"]]
        except Exception as e:
            logger.error(f"Erreur de validation réponses paginées: {e}")
            return ServiceResult.service_error(
                message=msg.INTERNAL_SERVER_ERROR,
                status_code=500,
                service_name=msg.COMMENT_SERVICE
            )

        # 3. Construire la réponse paginée
        list_response = PaginatedCommentListResponse(
            comments=validated_replies,
            next_cursor=paginated_data["next_cursor"]
        )

        # 4. Mettre en cache
        await self.comment_cache.set_replies_paginated_in_cache(
            parent_comment_id, cursor, limit, list_response, int(CacheDurartion.COMMENT_DURATION)
        )

        logger.info(f"Réponses récupérées — count: {len(validated_replies)}")
        return ServiceResult.service_success(data=list_response, status_code=200)

    # -------------------------------------------------------------------------
    # Mutations
    # -------------------------------------------------------------------------

    async def service_create_comment(self, comment_data: CommentCreate) -> ServiceResult[CommentRead]:
        """
        Crée un commentaire (ou une réponse) et invalide les caches associés.

        Args:
            comment_data (CommentCreate): Données du commentaire à créer.
                Si `parent_comment_id` est renseigné, il s'agit d'une réponse.

        Returns:
            ServiceResult[CommentRead]: Le commentaire créé, ou une erreur
                si la création échoue (contrainte d'intégrité, validation, etc.).
        """
        # 1. Appel au repository
        comment_obj = await self.comment_repo.create_comment(comment_data=comment_data)

        # 2. Gestion des erreurs du repo
        if comment_obj.is_error():
            return ServiceResult.service_error(
                message=comment_obj.error,
                status_code=comment_obj.status_code,
                service_name=msg.COMMENT_SERVICE
            )

        # 3. Validation Pydantic
        try:
            created_comment: CommentRead = CommentRead.model_validate(comment_obj.data)
        except Exception as e:
            logger.error(f"Erreur de validation Pydantic: {str(e)}")
            return ServiceResult.service_error(
                message=msg.INTERNAL_SERVER_ERROR,
                status_code=500,
                service_name=msg.COMMENT_SERVICE
            )

        # 4. Invalidation des caches
        await self._invalidate_comment_caches(
            comment_id=created_comment.id,
            post_id=created_comment.post_id,
            parent_comment_id=created_comment.parent_comment_id
        )

        logger.info(f"{msg.COMMENT_CREATE_SUCCESS}: {created_comment.id}")
        return ServiceResult.service_success(data=created_comment, status_code=201, service_name=msg.COMMENT_SERVICE)

    async def service_update_comment(self, comment_id: UUID, comment_data: CommentUpdate) -> ServiceResult[CommentRead]:
        """
        Met à jour le contenu d'un commentaire et invalide tous ses caches.

        Args:
            comment_id (UUID): Identifiant du commentaire à mettre à jour.
            comment_data (CommentUpdate): Nouvelles données du commentaire.

        Returns:
            ServiceResult[CommentRead]: Le commentaire mis à jour, ou une erreur
                si introuvable ou si la mise à jour échoue.
        """
        # 1. Vérifier l'existence du commentaire
        existing = await self.comment_repo.get_comment_by_id(comment_id=comment_id)

        if existing.is_error():
            return ServiceResult.service_error(
                message=existing.error,
                status_code=existing.status_code,
                service_name=msg.COMMENT_SERVICE
            )

        # 2. Mettre à jour en base
        updated = await self.comment_repo.update_comment(comment_id=comment_id, data=comment_data)

        if updated.is_error():
            return ServiceResult.service_error(
                message=updated.error,
                status_code=updated.status_code,
                service_name=msg.COMMENT_SERVICE
            )

        # 3. Invalider les caches liés
        await self._invalidate_comment_caches(
            comment_id=comment_id,
            post_id=existing.data.post_id,
            parent_comment_id=existing.data.parent_comment_id
        )

        updated_comment: CommentRead = CommentRead.model_validate(updated.data)

        logger.info(f"{msg.COMMENT_UPDATE_SUCCESS}: {comment_id}")
        return ServiceResult.service_success(data=updated_comment, status_code=200, service_name=msg.COMMENT_SERVICE)

    async def service_delete_comment(self, comment_id: UUID) -> ServiceResult[StringMessage]:
        """
        Supprime (soft delete) un commentaire et invalide tous ses caches.

        Args:
            comment_id (UUID): Identifiant du commentaire à supprimer.

        Returns:
            ServiceResult[StringMessage]: Un message de confirmation, ou une erreur
                si introuvable ou si la suppression échoue.
        """
        # 1. Vérifier l'existence du commentaire
        existing = await self.comment_repo.get_comment_by_id(comment_id=comment_id)

        if existing.is_error():
            return ServiceResult.service_error(
                message=existing.error,
                status_code=existing.status_code,
                service_name=msg.COMMENT_SERVICE
            )

        # 2. Soft delete en base
        deleted = await self.comment_repo.soft_delete_comment(comment_id=comment_id)

        if deleted.is_error():
            return ServiceResult.service_error(
                message=msg.DELETE_FAILED,
                status_code=500,
                service_name=msg.COMMENT_SERVICE
            )

        # 3. Invalider les caches liés
        await self._invalidate_comment_caches(
            comment_id=comment_id,
            post_id=existing.data.post_id,
            parent_comment_id=existing.data.parent_comment_id
        )

        logger.info(f"{msg.COMMENT_DELETE_SUCCESS}: {comment_id}")
        return ServiceResult.service_success(
            data=StringMessage(message=msg.COMMENT_DELETE_SUCCESS),
            status_code=200,
            service_name=msg.COMMENT_SERVICE
        )

    async def service_count_comments_by_post(self, post_id: UUID) -> ServiceResult[int]:
        """
        Compte le nombre de commentaires racines (non supprimés) d'un post.

        Args:
            post_id (UUID): Identifiant du post dont on veut compter les commentaires.

        Returns:
            ServiceResult[int]: Le nombre de commentaires, ou une erreur
                si la récupération échoue.
        """
        result = await self.comment_repo.count_comments_by_post(post_id=post_id)

        if result.is_error():
            logger.error(f"Erreur comptage commentaires: {result.error}")
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=msg.COMMENT_SERVICE
            )

        logger.info(f"Nombre de commentaires du post {post_id} : {result.data}")
        return ServiceResult.service_success(data=result.data, status_code=200)

    async def service_count_replies_by_comment(self, parent_comment_id: UUID) -> ServiceResult[int]:
        """
        Compte le nombre de réponses (non supprimées) d'un commentaire parent.

        Args:
            parent_comment_id (UUID): Identifiant du commentaire parent.

        Returns:
            ServiceResult[int]: Le nombre de réponses, ou une erreur
                si la récupération échoue.
        """
        result = await self.comment_repo.count_replies_by_comment(
            parent_comment_id=parent_comment_id
        )

        if result.is_error():
            logger.error(f"Erreur comptage réponses: {result.error}")
            return ServiceResult.service_error(
                message=result.error,
                status_code=result.status_code,
                service_name=msg.COMMENT_SERVICE
            )

        logger.info(f"Nombre de réponses du commentaire {parent_comment_id} : {result.data}")
        return ServiceResult.service_success(data=result.data, status_code=200)