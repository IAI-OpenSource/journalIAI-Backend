from sqlalchemy.ext.asyncio import AsyncSession
import logging
from sqlalchemy import select, update, insert, func
from app.db.models.comment import Comment
from app.repositories.repositories_utils import RepositoriesUtils
from app.schemas.comment_schemas import CommentCreate, CommentUpdate
from typing import List, Optional, Sequence, TypedDict, cast
from uuid import UUID
from datetime import datetime, timezone
from . import CRUDResult
from app.globals.messages import Messages as msg
from dataclasses import dataclass
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


class PaginatedCommentResult(TypedDict):
    comments: Sequence[Comment]
    next_cursor: Optional[UUID]


@dataclass
class CommentRepository:
    """
    Repository gérant les opérations liées aux commentaires.

    Fournit des méthodes CRUD et de récupération des commentaires
    avec support de pagination par curseur et filtrage par post.
    """

    db: AsyncSession

    async def get_comments_by_post(self, post_id: UUID) -> CRUDResult[List[Comment]]:
        """
        Récupère tous les commentaires racines (non supprimés) d'un post.

        Args:
            post_id (UUID): Identifiant du post.

        Returns:
            CRUDResult[List[Comment]]: Liste des commentaires racines trouvés.
        """
        try:
            stmt = (
                select(Comment)
                .where(Comment.post_id == post_id)
                .where(Comment.deleted_at == None)
                .where(Comment.parent_comment_id == None)
                .order_by(Comment.created_at)
            )
            result = await self.db.execute(stmt)
            comments = cast(List[Comment], result.scalars().all())
            logger.info(f"Commentaires du post {post_id} récupérés avec succès !")
            return CRUDResult.crud_success(comments)
        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Comment)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def get_comment_by_id(self, comment_id: UUID) -> CRUDResult[Comment]:
        """
        Récupère un commentaire par son identifiant.

        Args:
            comment_id (UUID): Identifiant unique du commentaire.

        Returns:
            CRUDResult[Comment]: Le commentaire trouvé.
        """
        try:
            stmt = (
                select(Comment)
                .where(Comment.id == comment_id)
                .where(Comment.deleted_at == None)
            )
            result = await self.db.execute(stmt)
            comment = cast(Comment, result.scalar_one_or_none())
            if comment is None:
                logger.info(f"Aucun commentaire trouvé pour l'id {comment_id}")
                return CRUDResult.crud_error(msg.COMMENT_NOT_FOUND, status_code=404)
            logger.info("Commentaire récupéré avec succès !")
            return CRUDResult.crud_success(comment)
        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Comment)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def get_replies_by_comment(self, parent_comment_id: UUID) -> CRUDResult[List[Comment]]:
        """
        Récupère toutes les réponses (non supprimées) d'un commentaire parent.

        Args:
            parent_comment_id (UUID): Identifiant du commentaire parent.

        Returns:
            CRUDResult[List[Comment]]: Liste des réponses trouvées.
        """
        try:
            stmt = (
                select(Comment)
                .where(Comment.parent_comment_id == parent_comment_id)
                .where(Comment.deleted_at == None)
                .order_by(Comment.created_at)
            )
            result = await self.db.execute(stmt)
            replies = cast(List[Comment], result.scalars().all())
            logger.info(f"Réponses du commentaire {parent_comment_id} récupérées avec succès !")
            return CRUDResult.crud_success(replies)
        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Comment)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def create_comment(self, comment_data: CommentCreate) -> CRUDResult[Comment]:
        """
        Crée un nouveau commentaire.

        Args:
            comment_data (CommentCreate): Données du commentaire à créer.

        Returns:
            CRUDResult[Comment]: Le commentaire créé.
        """
        try:
            stmt = (
                insert(Comment)
                .values(**comment_data.model_dump())
                .returning(Comment)
            )
            result = await self.db.execute(stmt)
            db_comment = result.scalar_one_or_none()
            if db_comment is None:
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=500)
            await self.db.commit()
            logger.info("Commentaire créé avec succès !")
            return CRUDResult.crud_success(db_comment)
        except IntegrityError as ie:
            await self.db.rollback()
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Comment)
        except Exception as e:
            await self.db.rollback()
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def update_comment(self, comment_id: UUID, data: CommentUpdate) -> CRUDResult[Comment]:
        """
        Met à jour le contenu d'un commentaire existant.

        Args:
            comment_id (UUID): Identifiant du commentaire à mettre à jour.
            data (CommentUpdate): Données à mettre à jour.

        Returns:
            CRUDResult[Comment]: Le commentaire mis à jour.
        """
        try:
            stmt = (
                update(Comment)
                .where(Comment.id == comment_id)
                .where(Comment.deleted_at == None)
                .values(**data.model_dump(exclude_unset=True))
                .returning(Comment)
            )
            result = await self.db.execute(stmt)
            updated_comment = result.scalar_one_or_none()
            if updated_comment is None:
                logger.info(f"Commentaire {comment_id} introuvable pour la mise à jour")
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=404)
            await self.db.commit()
            logger.info(f"Commentaire {comment_id} mis à jour avec succès !")
            return CRUDResult.crud_success(updated_comment)
        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Comment)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def soft_delete_comment(self, comment_id: UUID) -> CRUDResult[Comment]:
        """
        Supprime logiquement un commentaire (soft delete).

        Args:
            comment_id (UUID): Identifiant du commentaire à supprimer.

        Returns:
            CRUDResult[Comment]: Le commentaire supprimé.
        """
        try:
            stmt = (
                update(Comment)
                .where(Comment.id == comment_id)
                .where(Comment.deleted_at == None)
                .values(deleted_at=datetime.now(timezone.utc))
                .returning(Comment)
            )
            result = await self.db.execute(stmt)
            deleted_comment = result.scalar_one_or_none()
            if deleted_comment is None:
                logger.info(f"Commentaire {comment_id} introuvable pour la suppression")
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=404)
            await self.db.commit()
            logger.info(f"Commentaire {comment_id} supprimé avec succès !")
            return CRUDResult.crud_success(deleted_comment)
        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Comment)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def get_comments_paginated(
        self, post_id: UUID, cursor: Optional[UUID] = None, limit: int = 10
    ) -> CRUDResult[PaginatedCommentResult]:
        """
        Récupère les commentaires racines d'un post avec pagination par curseur.

        Args:
            post_id (UUID): Identifiant du post.
            cursor (Optional[UUID]): Identifiant du dernier commentaire récupéré.
            limit (int): Nombre maximum de commentaires à récupérer.

        Returns:
            CRUDResult[PaginatedCommentResult]: Dict avec comments et next_cursor.
        """
        try:
            query = (
                select(Comment)
                .where(Comment.post_id == post_id)
                .where(Comment.deleted_at == None)
                .where(Comment.parent_comment_id == None)
                .order_by(Comment.id)
            )
            if cursor:
                query = query.where(Comment.id > cursor)
            query = query.limit(limit)
            result = await self.db.execute(query)
            comments = result.scalars().all()
            next_cursor: Optional[UUID] = comments[-1].id if comments else None
            logger.info("Commentaires paginés récupérés avec succès !")
            return CRUDResult.crud_success(PaginatedCommentResult(comments=comments, next_cursor=next_cursor))
        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Comment)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def get_replies_paginated(
        self, parent_comment_id: UUID, cursor: Optional[UUID] = None, limit: int = 10
    ) -> CRUDResult[PaginatedCommentResult]:
        """
        Récupère les réponses d'un commentaire avec pagination par curseur.

        Args:
            parent_comment_id (UUID): Identifiant du commentaire parent.
            cursor (Optional[UUID]): Identifiant du dernier commentaire récupéré.
            limit (int): Nombre maximum de réponses à récupérer.

        Returns:
            CRUDResult[PaginatedCommentResult]: Dict avec comments et next_cursor.
        """
        try:
            query = (
                select(Comment)
                .where(Comment.parent_comment_id == parent_comment_id)
                .where(Comment.deleted_at == None)
                .order_by(Comment.id)
            )
            if cursor:
                query = query.where(Comment.id > cursor)
            query = query.limit(limit)
            result = await self.db.execute(query)
            replies = result.scalars().all()
            next_cursor: Optional[UUID] = replies[-1].id if replies else None
            logger.info("Réponses paginées récupérées avec succès !")
            return CRUDResult.crud_success(PaginatedCommentResult(comments=replies, next_cursor=next_cursor))
        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, Comment)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def count_comments_by_post(self, post_id: UUID) -> CRUDResult[int]:
        """
        Compte le nombre de commentaires racines (non supprimés) d'un post.

        Args:
            post_id (UUID): Identifiant du post.

        Returns:
            CRUDResult[int]: Le nombre de commentaires trouvés.
        """
        try:
            stmt = (
                select(func.count())
                .select_from(Comment)
                .where(Comment.post_id == post_id)
                .where(Comment.deleted_at == None)
                .where(Comment.parent_comment_id == None)
            )
            result = await self.db.execute(stmt)
            count = result.scalar_one()

            logger.info(f"Nombre de commentaires du post {post_id} : {count}")
            return CRUDResult.crud_success(count)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def count_replies_by_comment(self, parent_comment_id: UUID) -> CRUDResult[int]:
        """
        Compte le nombre de réponses (non supprimées) d'un commentaire parent.

        Args:
            parent_comment_id (UUID): Identifiant du commentaire parent.

        Returns:
            CRUDResult[int]: Le nombre de réponses trouvées.
        """
        try:
            stmt = (
                select(func.count())
                .select_from(Comment)
                .where(Comment.parent_comment_id == parent_comment_id)
                .where(Comment.deleted_at == None)
            )
            result = await self.db.execute(stmt)
            count = result.scalar_one()

            logger.info(f"Nombre de réponses du commentaire {parent_comment_id} : {count}")
            return CRUDResult.crud_success(count)

        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)