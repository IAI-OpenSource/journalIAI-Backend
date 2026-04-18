from logging import getLogger
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.like import Like
from app.repositories import CRUDResult
from app.repositories.repositories_utils import RepositoriesUtils

logger = getLogger(__name__)


class LikeRepository:
	def __init__(self, bd: AsyncSession):
		self._bd = bd

	async def save_post_like(self, post_id: UUID, user_id: UUID) -> CRUDResult[str]:
		"""
		Enregistre le like d'un post
		Args:
			post_id: Id du post
			user_id: Id de l'user

		Returns:
			CRUDResult[str]: pffff
		"""

		le_like = Like(post_id=post_id, user_id=user_id, comment_id=None)
		try:
			self._bd.add(le_like)
			await self._bd.commit()
			return CRUDResult.crud_success("Like enregistré avec succès")
		except Exception as e:
			return await RepositoriesUtils.traiter_errors_en_global(e, self._bd, logger, Like)

	async def save_post_unlike(self, post_id: UUID, user_id: UUID) -> CRUDResult[str]:
		"""
		Enregistre le unlike d'un post
		Args:
			post_id: Id du post
			user_id: Id de l'user

		Returns:
			CRUDResult[str]: pffff
		"""

		try:
			query = delete(Like).where(
				Like.post_id == post_id,
				Like.user_id == user_id,
				Like.comment_id == None,
			)
			result: CursorResult[Any] = cast(CursorResult[Any], await self._bd.execute(query))  # Petit hack
			await self._bd.commit()

			if result.rowcount == 0:
				return CRUDResult.crud_error("Aucun like trouvé pour ce post et cet utilisateur", status_code=404)
			return CRUDResult.crud_success("Like supprimé avec succès")
		except Exception as e:
			return await RepositoriesUtils.traiter_errors_en_global(e, self._bd, logger, Like)

	async def save_comment_like(self, comment_id: UUID, user_id: UUID) -> CRUDResult[str]:
		"""
		Enregistre le like d'un comment
		Args:
			comment_id: Id du comment
			user_id: Id de l'user

		Returns:
			CRUDResult[str]: pffff
		"""

		le_like = Like(post_id=None, user_id=user_id, comment_id=comment_id)
		try:
			self._bd.add(le_like)
			await self._bd.commit()
			return CRUDResult.crud_success("Like enregistré avec succès")
		except Exception as e:
			return await RepositoriesUtils.traiter_errors_en_global(e, self._bd, logger, Like)

	async def save_comment_unlike(self, comment_id: UUID, user_id: UUID) -> CRUDResult[str]:
		"""
		Enregistre le unlike d'un comment
		Args:
			comment_id: Id du comment
			user_id: Id de l'user

		Returns:
			CRUDResult[str]: pffff
		"""

		try:
			query = delete(Like).where(
				Like.comment_id == comment_id,
				Like.user_id == user_id,
				Like.post_id == None,
			)
			await self._bd.execute(query)
			await self._bd.commit()
			return CRUDResult.crud_success("Like supprimé avec succès")
		except Exception as e:
			return await RepositoriesUtils.traiter_errors_en_global(e, self._bd, logger, Like)
