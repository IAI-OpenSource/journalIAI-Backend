from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.helpers.base import CacheWrapper
from app.cache.like_cache import LikeCache
from app.db.models.enums import UserRole
from app.globals.messages import Messages
from app.repositories.like_repository import LikeRepository
from app.schemas.global_schemas import StringMessage
from app.services import ServiceResult
from app.services.post_service import PostService


class LikeService:

	def __init__(self, bd: AsyncSession, cache: CacheWrapper):
		self._bd = LikeRepository(bd)
		self._raw_bd = bd
		self._cache = LikeCache(cache)

	async def save_post_like(
		self, post_id: UUID, user_id: str, user_classe_id: Optional[UUID], user_role: UserRole
	) -> ServiceResult[StringMessage]:
		verif_res = await PostService.verify_can_interract_with_post(
			post_id=post_id, user_classe_id=user_classe_id, is_admin=user_role == UserRole.ADMIN,
			bd_session=self._raw_bd
		)

		if verif_res.is_error():
			return ServiceResult.service_error(
				verif_res.error, status_code=verif_res.status_code, service_name=Messages.LIKE_SERVICE
			)

		self._cache.


