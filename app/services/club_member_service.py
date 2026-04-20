import logging
from typing import Optional, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.club_member_repository import ClubMemberRepository
from app.cache.club_member_cache import ClubMemberCache
from app.cache.helpers.base import CacheWrapper
from app.globals.cache_duration import CacheDurartion
from app.schemas.club_member_schema import (
    ClubMemberCreate,
    ClubMemberUpdate,
    ClubMemberRead,
    ClubMemberListResponse,
    PaginatedClubMemberListResponse,
)
from app.db.models.enums import ClubMembersType
from app.globals.messages import Messages as msg
from app.services import ServiceResult

logger = logging.getLogger(__name__)


class ClubMemberService:
    def __init__(self, db: AsyncSession, cache: CacheWrapper):
        self.db = db
        self.member_repo = ClubMemberRepository(self.db)
        self.member_cache = ClubMemberCache(cache)

    # -------------------------------------------------------------------------
    # Helpers d'invalidation
    # -------------------------------------------------------------------------

    async def _invalidate_member_caches(
        self, member_id: UUID, club_id: UUID, cursor: Optional[UUID] = None, limit: int = 10
    ) -> None:
        """Invalide tous les caches liés à un membre après une mutation."""
        await self.member_cache.delete_member_from_cache(member_id)
        await self.member_cache.delete_members_list_from_cache(club_id)
        await self.member_cache.delete_members_paginated_from_cache(club_id, cursor=cursor, limit=limit)

    # -------------------------------------------------------------------------
    # Lecture
    # -------------------------------------------------------------------------

    async def service_get_member_by_id(self, member_id: UUID) -> ServiceResult[ClubMemberRead]:
        """Récupère un membre par son ID — cache en priorité."""

        # 1. Vérifier le cache
        cached = await self.member_cache.get_member_from_cache(member_id)
        if cached is not None:
            logger.info(f"Membre {member_id} trouvé en cache")
            if cached.is_deleted():
                return ServiceResult.service_error(
                    message=msg.NOT_FOUND,
                    status_code=404,
                    service_name=msg.CLUB_MEMBER_SERVICE
                )
            return ServiceResult.service_success(cached, status_code=200)

        # 2. Sinon, aller en base
        member = await self.member_repo.get_member_by_id(member_id=member_id)

        if member.is_error():
            logger.error(f"Erreur: {member.error}")
            return ServiceResult.service_error(
                message=member.error,
                status_code=member.status_code,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        validated = ClubMemberRead.model_validate(member.data)

        if validated.is_deleted():
            return ServiceResult.service_error(
                message=msg.NOT_FOUND,
                status_code=404,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        # 3. Mettre en cache
        await self.member_cache.set_member_in_cache(member_id, validated, CacheDurartion.CLUB_MEMBER_DURATION)

        return ServiceResult.service_success(validated, status_code=200)

    async def service_get_members_by_club(self, club_id: UUID) -> ServiceResult[ClubMemberListResponse]:
        """Récupère tous les membres actifs d'un club — cache en priorité."""

        # 1. Vérifier le cache
        cached = await self.member_cache.get_members_list_from_cache(club_id)
        if cached is not None:
            logger.info(f"Liste des membres du club {club_id} trouvée en cache")
            try:
                response = ClubMemberListResponse(members=cached)
                return ServiceResult.service_success(response, status_code=200)
            except Exception as e:
                logger.warning(f"Cache corrompu pour la liste membres: {e}. On force la lecture DB.")

        # 2. Sinon, aller en base
        members = await self.member_repo.get_members_by_club(club_id=club_id)

        if members.is_error():
            logger.error(f"Erreur: {members.error}")
            return ServiceResult.service_error(
                message=members.error,
                status_code=members.status_code,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        validated = [ClubMemberRead.model_validate(m) for m in members.data]
        response = ClubMemberListResponse(members=validated)

        # 3. Mettre en cache
        await self.member_cache.set_members_list_in_cache(club_id, validated, CacheDurartion.CLUB_MEMBER_DURATION)

        return ServiceResult.service_success(data=response, status_code=200)

    async def service_get_members_by_role(
        self, club_id: UUID, role: ClubMembersType
    ) -> ServiceResult[ClubMemberListResponse]:
        """Récupère les membres d'un club filtrés par rôle."""

        members = await self.member_repo.get_members_by_role(club_id=club_id, role=role)

        if members.is_error():
            logger.error(f"Erreur: {members.error}")
            return ServiceResult.service_error(
                message=members.error,
                status_code=members.status_code,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        validated = [ClubMemberRead.model_validate(m) for m in members.data]
        response = ClubMemberListResponse(members=validated)

        return ServiceResult.service_success(data=response, status_code=200)

    async def service_check_membership(self, club_id: UUID, user_id: UUID) -> ServiceResult[ClubMemberRead]:
        """Vérifie si un utilisateur est membre d'un club."""

        member = await self.member_repo.get_member_by_club_and_user(club_id=club_id, user_id=user_id)

        if member.is_error():
            return ServiceResult.service_error(
                message=member.error,
                status_code=member.status_code,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        validated = ClubMemberRead.model_validate(member.data)
        return ServiceResult.service_success(validated, status_code=200)

    async def service_get_members_paginated(
        self, club_id: UUID, cursor: Optional[UUID] = None, limit: int = 10
    ) -> ServiceResult[PaginatedClubMemberListResponse]:
        """Récupère les membres d'un club avec pagination — cache en priorité."""

        # 1. Vérifier le cache
        cached = await self.member_cache.get_members_paginated_from_cache(club_id, cursor, limit)
        if cached is not None:
            logger.info(f"Liste paginée membres du club {club_id} (cursor={cursor}) trouvée en cache")
            return ServiceResult.service_success(cached, status_code=200)

        # 2. Sinon, aller en base
        members = await self.member_repo.get_members_paginated(club_id=club_id, cursor=cursor, limit=limit)

        if members.is_error():
            logger.error(f"Erreur pagination membres: {members.error}")
            return ServiceResult.service_error(
                message=msg.INTERNAL_SERVER_ERROR,
                status_code=members.status_code,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        try:
            paginated_data = members.data
            validated_members = [ClubMemberRead.model_validate(m) for m in paginated_data["members"]]
        except Exception as e:
            logger.error(f"Erreur de validation pagination membres: {e}")
            return ServiceResult.service_error(
                message=msg.INTERNAL_SERVER_ERROR,
                status_code=500,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        # 3. Construire la réponse paginée
        list_response = PaginatedClubMemberListResponse(
            members=validated_members,
            next_cursor=paginated_data["next_cursor"]
        )

        # 4. Mettre en cache
        await self.member_cache.set_members_paginated_in_cache(
            club_id, cursor, limit, list_response, CacheDurartion.CLUB_MEMBER_DURATION
        )

        logger.info(f"Membres récupérés — count: {len(validated_members)}")
        return ServiceResult.service_success(data=list_response, status_code=200)

    # -------------------------------------------------------------------------
    # Mutations
    # -------------------------------------------------------------------------

    async def service_add_member(self, member_data: ClubMemberCreate) -> ServiceResult[ClubMemberRead]:
        """Ajoute un membre à un club et invalide les caches associés."""

        # 1. Vérifier que l'utilisateur n'est pas déjà membre
        existing = await self.member_repo.get_member_by_club_and_user(
            club_id=member_data.club_id, user_id=member_data.user_id
        )
        if not existing.is_error():
            return ServiceResult.service_error(
                message=msg.ALREADY_EXISTS,
                status_code=409,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        # 2. Appel au repository
        member_obj = await self.member_repo.add_member(member_data=member_data)

        if member_obj.is_error():
            return ServiceResult.service_error(
                message=member_obj.error,
                status_code=member_obj.status_code,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        # 3. Validation Pydantic
        try:
            created_member = ClubMemberRead.model_validate(member_obj.data)
        except Exception as e:
            logger.error(f"Erreur de validation Pydantic: {str(e)}")
            return ServiceResult.service_error(
                message=msg.INTERNAL_SERVER_ERROR,
                status_code=500,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        # 4. Invalidation des caches
        await self._invalidate_member_caches(
            member_id=created_member.id,
            club_id=created_member.club_id
        )

        logger.info(f"Membre ajouté au club {created_member.club_id} avec succès : {created_member.id}")
        return ServiceResult.service_success(
            data=created_member,
            status_code=201,
            service_name=msg.CLUB_MEMBER_SERVICE
        )

    async def service_update_member_role(
        self, club_id: UUID, member_id: UUID, data: ClubMemberUpdate
    ) -> ServiceResult[ClubMemberRead]:
        """Met à jour le rôle d'un membre et invalide tous ses caches."""

        updated = await self.member_repo.update_member_role(member_id=member_id, data=data)

        if updated.is_error():
            return ServiceResult.service_error(
                message=updated.error,
                status_code=updated.status_code,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        await self._invalidate_member_caches(member_id=member_id, club_id=club_id)

        validated = ClubMemberRead.model_validate(updated.data)

        logger.info(f"Rôle du membre {member_id} mis à jour avec succès")
        return ServiceResult.service_success(
            data=validated,
            status_code=200,
            service_name=msg.CLUB_MEMBER_SERVICE
        )

    async def service_remove_member(
        self, club_id: UUID, member_id: UUID
    ) -> ServiceResult[Any]:
        """Supprime (soft delete) un membre par son member_id — réservé aux admins."""

        deleted = await self.member_repo.soft_delete_member(member_id=member_id)

        if deleted.is_error():
            return ServiceResult.service_error(
                message=msg.DELETE_FAILED,
                status_code=deleted.status_code,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        await self._invalidate_member_caches(member_id=member_id, club_id=club_id)

        logger.info(f"Membre {member_id} retiré du club {club_id} avec succès")
        return ServiceResult.service_success(
            data={"message": msg.MEMBER_DELETE_SUCCESS},
            status_code=200,
            service_name=msg.CLUB_MEMBER_SERVICE
        )

    async def service_leave_club(
        self, club_id: UUID, user_id: UUID
    ) -> ServiceResult[Any]:
        """Permet à un utilisateur de se retirer lui-même d'un club via son user_id."""

        # 1. Vérifier que l'utilisateur est bien membre du club
        existing = await self.member_repo.get_member_by_club_and_user(
            club_id=club_id, user_id=user_id
        )
        if existing.is_error():
            return ServiceResult.service_error(
                message=existing.error,
                status_code=existing.status_code,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        member_id = existing.data.id

        # 2. Soft delete
        deleted = await self.member_repo.soft_delete_member(member_id=member_id)

        if deleted.is_error():
            return ServiceResult.service_error(
                message=msg.DELETE_FAILED,
                status_code=deleted.status_code,
                service_name=msg.CLUB_MEMBER_SERVICE
            )

        # 3. Invalider les caches
        await self._invalidate_member_caches(member_id=member_id, club_id=club_id)

        logger.info(f"Utilisateur {user_id} a quitté le club {club_id} avec succès")
        return ServiceResult.service_success(
            data={"message": msg.MEMBER_DELETE_SUCCESS},
            status_code=200,
            service_name=msg.CLUB_MEMBER_SERVICE
        )