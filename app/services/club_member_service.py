import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.club_member_repository import ClubMemberRepository
from app.cache.club_member_cache import ClubMemberCache
from app.cache.helpers.base import CacheWrapper
from app.globals.cache_duration import CacheDurartion
from app.schemas.club_member_schema import ClubMemberCreate, ClubMemberInfo, ApiClubMemberListResponse, ClubMemberUpdate
from app.db.models.enums import ClubMembersType
from app.globals.messages import Messages as msg

from . import ServiceResult

logger = logging.getLogger(__name__)


class ClubMemberService:
    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.db = db
        self.member_repo = ClubMemberRepository(self.db)
        self.member_cache = ClubMemberCache(cache)

    # -------------------------------------------------------------------------
    # Helpers d'invalidation
    # -------------------------------------------------------------------------

    async def _invalidate_member_caches(self, member_id: UUID, club_id: UUID) -> None:
        """Invalide les caches liés à un membre après une mutation."""
        await self.member_cache.delete_member_from_cache(member_id)
        await self.member_cache.delete_members_list_from_cache(club_id)

    # -------------------------------------------------------------------------
    # Lecture
    # -------------------------------------------------------------------------

    async def service_get_member_by_id(self, member_id: UUID) -> ServiceResult[ClubMemberInfo]:
        """Récupère un membre par son ID — cache en priorité."""

        # 1. Vérifier le cache
        cached = await self.member_cache.get_member_from_cache(member_id)
        if cached is not None:
            logger.info(f"Membre {member_id} trouvé en cache")
            return ServiceResult.service_success(cached, status_code=200)

        # 2. Sinon, aller en base
        member = await self.member_repo.get_member_by_id(member_id=member_id)

        if member.is_error():
            logger.error(f"Erreur: {member.error}")
            return ServiceResult.service_error(
                message=member.error,
                status_code=member.status_code,
                service_name=msg.CLUB_SERVICE
            )

        validated = ClubMemberInfo.model_validate(member.data)

        # 3. Mettre en cache
        await self.member_cache.set_member_in_cache(member_id, validated, CacheDurartion.EVENT_DURATION)

        return ServiceResult.service_success(validated, status_code=200)

    async def service_get_members_by_club(self, club_id: UUID) -> ServiceResult[ApiClubMemberListResponse]:
        """Récupère tous les membres d'un club — cache en priorité."""

        # 1. Vérifier le cache
        cached = await self.member_cache.get_members_list_from_cache(club_id)
        if cached is not None:
            logger.info(f"Membres du club {club_id} trouvés en cache")
            return ServiceResult.service_success(cached, status_code=200)

        # 2. Sinon, aller en base
        members = await self.member_repo.get_members_by_club(club_id=club_id)

        if members.is_error():
            logger.error(f"Erreur: {members.error}")
            return ServiceResult.service_error(
                message=members.error,
                status_code=members.status_code,
                service_name=msg.CLUB_SERVICE
            )

        validated = [ClubMemberInfo.model_validate(m) for m in members.data]

        # 3. Mettre en cache
        await self.member_cache.set_members_list_in_cache(club_id, validated, CacheDurartion.EVENT_DURATION)

        return ServiceResult.service_success(validated or [], status_code=200)

    async def service_get_members_by_role(
        self, club_id: UUID, role: ClubMembersType
    ) -> ServiceResult[ApiClubMemberListResponse]:
        """Récupère les membres d'un club filtrés par rôle."""

        members = await self.member_repo.get_members_by_role(club_id=club_id, role=role)

        if members.is_error():
            logger.error(f"Erreur: {members.error}")
            return ServiceResult.service_error(
                message=members.error,
                status_code=members.status_code,
                service_name=msg.CLUB_SERVICE
            )

        return ServiceResult.service_success(members.data or [], status_code=200)

    # -------------------------------------------------------------------------
    # Mutations
    # -------------------------------------------------------------------------

    async def service_add_member(self, member_data: ClubMemberCreate) -> ServiceResult[ClubMemberInfo]:
        """Ajoute un membre à un club."""

        # Vérifier si l'utilisateur est déjà membre
        existing = await self.member_repo.get_member_by_club_and_user(
            club_id=member_data.club_id,
            user_id=member_data.user_id
        )

        if not existing.is_error():
            return ServiceResult.service_error(
                message=msg.CLUB_MEMBER_ALREADY_EXISTS,
                status_code=409,
                service_name=msg.CLUB_SERVICE
            )

        member_obj = await self.member_repo.add_member(member_data=member_data)

        if member_obj.is_error():
            return ServiceResult.service_error(
                message=member_obj.error,
                status_code=member_obj.status_code,
                service_name=msg.CLUB_SERVICE
            )

        try:
            created_member = ClubMemberInfo.model_validate(member_obj.data)
        except Exception as e:
            return ServiceResult.service_error(message=str(e), status_code=500, service_name=msg.CLUB_SERVICE)

        # Invalider le cache de la liste
        await self.member_cache.delete_members_list_from_cache(member_data.club_id)

        logger.info(f"Membre ajouté au club {member_data.club_id} avec succès")
        return ServiceResult.service_success(data=created_member, status_code=201, service_name=msg.CLUB_SERVICE)

    async def service_update_member_role(
        self, member_id: UUID, club_id: UUID, data: ClubMemberUpdate
    ) -> ServiceResult[ClubMemberInfo]:
        """Met à jour le rôle d'un membre."""

        existing = await self.member_repo.get_member_by_id(member_id=member_id)

        if existing.is_error():
            return ServiceResult.service_error(
                message=existing.error,
                status_code=existing.status_code,
                service_name=msg.CLUB_SERVICE
            )

        updated = await self.member_repo.update_member_role(member_id=member_id, data=data)

        if updated.is_error():
            return ServiceResult.service_error(
                message=updated.error,
                status_code=updated.status_code,
                service_name=msg.CLUB_SERVICE
            )

        await self._invalidate_member_caches(member_id, club_id)

        logger.info(f"Rôle du membre {member_id} mis à jour avec succès")
        return ServiceResult.service_success(data=updated.data, status_code=200, service_name=msg.CLUB_SERVICE)

    async def service_remove_member(self, member_id: UUID, club_id: UUID) -> ServiceResult[ClubMemberInfo]:
        """Supprime (soft delete) un membre d'un club."""

        existing = await self.member_repo.get_member_by_id(member_id=member_id)

        if existing.is_error():
            return ServiceResult.service_error(
                message=existing.error,
                status_code=existing.status_code,
                service_name=msg.CLUB_SERVICE
            )

        deleted = await self.member_repo.soft_delete_member(member_id=member_id)

        if deleted.is_error():
            return ServiceResult.service_error(
                message=msg.DELETE_FAILED,
                status_code=500,
                service_name=msg.CLUB_SERVICE
            )

        await self._invalidate_member_caches(member_id, club_id)

        logger.info(f"Membre {member_id} supprimé du club {club_id} avec succès")
        return ServiceResult.service_success(
            data={"message": msg.CLUB_MEMBER_REMOVED, "id": str(member_id)},
            status_code=200,
            service_name=msg.CLUB_SERVICE
        )