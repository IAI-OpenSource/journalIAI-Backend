from sqlalchemy.ext.asyncio import AsyncSession
import logging
from sqlalchemy import select, update, insert
from app.db.models.club_member import ClubMember
from app.db.models.enums import ClubMembersType
from app.repositories.repositories_utils import RepositoriesUtils
from app.schemas.club_member_schema import ClubMemberCreate, ClubMemberUpdate
from typing import List, Optional, Any
from uuid import UUID
from datetime import datetime, timezone
from . import CRUDResult
from app.globals.messages import Messages as msg
from dataclasses import dataclass
from sqlalchemy.exc import IntegrityError


logger = logging.getLogger(__name__)


@dataclass
class ClubMemberRepository:
    """
    Repository gérant les opérations liées aux membres des clubs.

    Fournit des méthodes CRUD et de récupération des membres
    avec support de pagination et filtrage.
    """

    db: AsyncSession

    async def get_members_by_club(self, club_id: UUID) -> CRUDResult[List[ClubMember]]:
        """
        Récupère tous les membres actifs d'un club.

        Args:
            club_id (UUID): Identifiant du club.

        Returns:
            CRUDResult[List[ClubMember]]: Liste des membres trouvés.
        """
        try:
            stmt = (
                select(ClubMember)
                .where(ClubMember.club_id == club_id)
                .where(ClubMember.deleted_at == None)
                .order_by(ClubMember.joined_at)
            )
            result = await self.db.execute(stmt)
            members = list(result.scalars().all())

            logger.info(f"Membres du club {club_id} récupérés avec succès !")
            return CRUDResult.crud_success(members)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, ClubMember)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def get_member_by_id(self, member_id: UUID) -> CRUDResult[ClubMember]:
        """
        Récupère un membre par son identifiant.

        Args:
            member_id (UUID): Identifiant unique du membre.

        Returns:
            CRUDResult[ClubMember]: Le membre trouvé.
        """
        try:
            stmt = (
                select(ClubMember)
                .where(ClubMember.id == member_id)
                .where(ClubMember.deleted_at == None)
            )
            result = await self.db.execute(stmt)
            member = result.scalar_one_or_none()

            if member is None:
                logger.info(f"Aucun membre trouvé pour l'id {member_id}")
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=404)

            assert isinstance(member, ClubMember)
            logger.info("Membre récupéré avec succès !")
            return CRUDResult.crud_success(member)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, ClubMember)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def get_member_by_club_and_user(self, club_id: UUID, user_id: UUID) -> CRUDResult:
        """
        Vérifie si un utilisateur est déjà membre d'un club.

        Args:
            club_id (UUID): Identifiant du club.
            user_id (UUID): Identifiant de l'utilisateur.

        Returns:
            CRUDResult: Le membre trouvé ou NOT_FOUND.
        """
        try:
            stmt = (
                select(ClubMember)
                .where(ClubMember.club_id == club_id)
                .where(ClubMember.user_id == user_id)
                .where(ClubMember.deleted_at == None)
            )
            result = await self.db.execute(stmt)
            member = result.scalar_one_or_none()

            if member is None:
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=404)

            return CRUDResult.crud_success(member)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, ClubMember)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def get_members_by_role(self, club_id: UUID, role: ClubMembersType) -> CRUDResult[List[ClubMember]]:
        """
        Récupère les membres d'un club filtrés par rôle.

        Args:
            club_id (UUID): Identifiant du club.
            role (ClubMembersType): Rôle à filtrer.

        Returns:
            CRUDResult[List[ClubMember]]: Liste des membres correspondant au rôle.
        """
        try:
            stmt = (
                select(ClubMember)
                .where(ClubMember.club_id == club_id)
                .where(ClubMember.role_in_club == role)
                .where(ClubMember.deleted_at == None)
                .order_by(ClubMember.joined_at)
            )
            result = await self.db.execute(stmt)
            members = list(result.scalars().all())

            logger.info(f"Membres avec rôle '{role.value}' récupérés avec succès !")
            return CRUDResult.crud_success(members)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, ClubMember)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def add_member(self, member_data: ClubMemberCreate) -> CRUDResult[ClubMember]:
        """
        Ajoute un membre à un club.

        Args:
            member_data (ClubMemberCreate): Données du membre à ajouter.

        Returns:
            CRUDResult[ClubMember]: Le membre ajouté.
        """
        try:
            stmt = (
                insert(ClubMember)
                .values(**member_data.model_dump())
                .returning(ClubMember)
            )
            result = await self.db.execute(stmt)
            db_member = result.scalar_one_or_none()

            if db_member is None:
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=500)

            await self.db.commit()

            logger.info(f"Membre ajouté au club {member_data.club_id} avec succès !")
            return CRUDResult.crud_success(db_member)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, ClubMember)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def update_member_role(self, member_id: UUID, data: ClubMemberUpdate) -> CRUDResult[ClubMember]:
        """
        Met à jour le rôle d'un membre dans un club.

        Args:
            member_id (UUID): Identifiant du membre à mettre à jour.
            data (ClubMemberUpdate): Nouvelles données du membre.

        Returns:
            CRUDResult[ClubMember]: Le membre mis à jour.
        """
        try:

            values: dict[str, Any] = data.model_dump(exclude_unset=True)
            if not values:
                return CRUDResult.crud_error("Aucune donnée à mettre à jour", status_code=400)

            stmt = (
                update(ClubMember)
                .where(ClubMember.id == member_id)
                .where(ClubMember.deleted_at == None)
                .values(**values)
                .returning(ClubMember)
            )
            result = await self.db.execute(stmt)
            updated_member = result.scalar_one_or_none()

            if updated_member is None:
                logger.info(f"Membre {member_id} introuvable pour la mise à jour")
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=404)

            await self.db.commit()

            logger.info(f"Rôle du membre {member_id} mis à jour avec succès !")
            return CRUDResult.crud_success(updated_member)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, ClubMember)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def soft_delete_member(self, member_id: UUID) -> CRUDResult[ClubMember]:
        """
        Supprime logiquement un membre d'un club (soft delete).

        Args:
            member_id (UUID): Identifiant du membre à supprimer.

        Returns:
            CRUDResult[ClubMember]: Le membre supprimé.
        """
        try:
            stmt = (
                update(ClubMember)
                .where(ClubMember.id == member_id)
                .where(ClubMember.deleted_at == None)
                .values(deleted_at=datetime.now(timezone.utc))
                .returning(ClubMember)
            )
            result = await self.db.execute(stmt)
            deleted_member = result.scalar_one_or_none()

            if deleted_member is None:
                logger.info(f"Membre {member_id} introuvable pour la suppression")
                return CRUDResult.crud_error(msg.NOT_FOUND, status_code=404)

            await self.db.commit()

            logger.info(f"Membre {member_id} supprimé avec succès !")
            return CRUDResult.crud_success(deleted_member)

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, ClubMember)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)

    async def get_members_paginated(
        self, club_id: UUID, cursor: Optional[UUID] = None, limit: int = 10
    ) -> CRUDResult:
        """
        Récupère les membres d'un club avec pagination basée sur un curseur.

        Args:
            club_id (UUID): Identifiant du club.
            cursor (Optional[UUID]): Identifiant du dernier membre récupéré.
            limit (int): Nombre maximum de membres à récupérer.

        Returns:
            CRUDResult: dict avec members et next_cursor.
        """
        try:
            query = (
                select(ClubMember)
                .where(ClubMember.club_id == club_id)
                .where(ClubMember.deleted_at == None)
                .order_by(ClubMember.id)
            )

            if cursor:
                query = query.where(ClubMember.id > cursor)

            query = query.limit(limit)

            result = await self.db.execute(query)
            members = result.scalars().all()

            next_cursor = members[-1].id if members else None

            logger.info(f"Membres paginés du club {club_id} récupérés avec succès !")
            return CRUDResult.crud_success({
                "members": members,
                "next_cursor": next_cursor
            })

        except IntegrityError as ie:
            return await RepositoriesUtils.traiter_integrity_error(ie, self.db, logger, ClubMember)
        except Exception as e:
            return await RepositoriesUtils.traiter_exception_inconnue(e, self.db, logger)