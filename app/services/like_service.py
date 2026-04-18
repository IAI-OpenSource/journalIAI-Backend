from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.helpers.base import CacheWrapper
from app.cache.like_cache import LikeCache
from app.db.models.enums import UserRole
from app.globals.messages import Messages
from app.repositories.like_repository import LikeRepository
from app.repositories.post_repository import PostRepository
from app.schemas.global_schemas import StringMessage
from app.services import ServiceResult
from app.services.post_service import PostService


class LikeService:

	def __init__(self, bd: AsyncSession, cache: CacheWrapper):
		self._bd = LikeRepository(bd)
		self._raw_bd = bd
		self._cache = LikeCache(cache)

	async def save_post_like(
		self, post_id: UUID, user_id: UUID, user_classe_id: Optional[UUID], user_role: UserRole
	) -> ServiceResult[StringMessage]:
		"""
		Like d'un post par un utilisateur
		Args:
			post_id: Id du post
			user_id: Id de l'user
			user_classe_id: Id de la classe de l'utilisateur
			user_role: role de l'utilisateur

		Returns:
			ServiceResult[StringMessage] : Le resultat
		"""
		verif_res = await PostService.verify_can_interract_with_post(
			post_id=post_id, user_classe_id=user_classe_id, is_admin=user_role == UserRole.ADMIN,
			bd_session=self._raw_bd
		)

		if verif_res.is_error():
			return ServiceResult.service_error(
				verif_res.error, status_code=verif_res.status_code, service_name=Messages.LIKE_SERVICE
			)
		save_res = await self._bd.save_post_like(post_id=post_id, user_id=user_id)

		if save_res.is_error():
			return save_res.to_service_error(service_name=Messages.LIKE_SERVICE)

		incr_result = await PostRepository.increment_post_like_count(post_id=post_id, bd_session=self._raw_bd)

		if incr_result.is_error():
			return incr_result.to_service_error(service_name=Messages.LIKE_SERVICE)

		return ServiceResult.service_success(
			service_name=Messages.LIKE_SERVICE,
			data=StringMessage(
				message=Messages.LIKE_SAVED_SUCCESSFULLY,
			)
		)

	async def delete_post_like(
		self, post_id: UUID, user_id: UUID, user_classe_id: Optional[UUID], user_role: UserRole
	) -> ServiceResult[StringMessage]:
		"""
		Unlike d'un post par un utilisateur
		Args:
			post_id: Id du post
			user_id: Id de l'user
			user_classe_id: Id de la classe de l'utilisateur
			user_role: role de l'utilisateur

		Returns:
			ServiceResult[StringMessage] : Le resultat
		"""

		verif_res = await PostService.verify_can_interract_with_post(
			post_id=post_id, user_classe_id=user_classe_id, is_admin=user_role == UserRole.ADMIN,
			bd_session=self._raw_bd
		)

		if verif_res.is_error():
			return ServiceResult.service_error(
				verif_res.error, status_code=verif_res.status_code, service_name=Messages.LIKE_SERVICE
			)

		save_res = await self._bd.save_post_unlike(post_id=post_id, user_id=user_id)
		if save_res.is_error():
			return save_res.to_service_error(service_name=Messages.LIKE_SERVICE)

		decr_res = await PostRepository.decrement_post_like_count(post_id=post_id, bd_session=self._raw_bd)

		if decr_res.is_error():
			return decr_res.to_service_error(service_name=Messages.LIKE_SERVICE)

		return ServiceResult.service_success(
			service_name=Messages.LIKE_SERVICE,
			data=StringMessage(
				message=Messages.LIKE_DELETE_SUCCESSFULLY,
			)
		)




