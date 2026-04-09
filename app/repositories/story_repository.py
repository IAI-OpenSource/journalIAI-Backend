"""
Repository pour la gestion des stories et des groupes de stories en base de données.
Contient les requêtes pour créer, récupérer et gérer les stories et leurs groupes.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, Select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.db.models.enums import StoryGroupsType
from app.db.models.stories import Story
from app.db.models.story_groups import StoryGroups
from app.repositories import CRUDResult

import logging

from app.repositories.repositories_utils import RepositoriesUtils
from app.schemas.story_upload_schemas import CreateStoryUploadIntentFullData

logger = logging.getLogger(__name__)


@dataclass
class StoryRepository:
    """Repository pour les opérations sur les stories et les groupes de stories."""

    db: AsyncSession

    async def save_story_group(self, group: StoryGroups, in_transaction: bool) -> CRUDResult[StoryGroups]:
        """
        Sauvegarde un groupe de stories en base de données.

        Args:
            group: L'objet StoryGroups à sauvegarder
            in_transaction: Si True, utilise une transaction existante

        Returns:
            CRUDResult contenant le groupe sauvegardé ou une erreur
        """
        try:
            self.db.add(group)

            if in_transaction:
                logger.info("En transaction, flush du groupe de story en cours sans commit")
                await self.db.flush()
            else:
                logger.info("Pas en transaction, commit du groupe de story en cours")
                await self.db.commit()

            await self.db.refresh(group)
            logger.info(f"Groupe de story sauvegardé avec succès, id: {group.id}")

            return CRUDResult.crud_success(data=group, status_code=status.HTTP_201_CREATED)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, StoryGroupsType
            )
    async def save_story(self, sto: Story, in_transaction: bool) -> CRUDResult[Story]:
        try:
            self.db.add(sto)

            if in_transaction:
                logger.info("En transaction, flush de la story en cours sans commit")
                await self.db.flush()

            else:
                logger.info("Pas en transaction, commit de la story en cours")
                await self.db.commit()

            await self.db.refresh(sto)
            logger.info(f"Story sauvegardée avec succès, id: {sto.id}")
            return CRUDResult.crud_success(data=sto, status_code=status.HTTP_201_CREATED)
        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, StoryGroupsType
            )
    async def get_active_story_group(self, user_id: UUID, infos: CreateStoryUploadIntentFullData) -> Optional[StoryGroups]:
        """
        Récupère le groupe actif (non expiré) d'un utilisateur.

        Args:
            user_id: L'ID de l'utilisateur
            infos: Les informations de l'intent d'upload pour déterminer le type de groupe à récupérer (user, classe, club)
        Returns:
            Le groupe si existant
        """
        query: Select = select(StoryGroups).where(
            (StoryGroups.expires_at >= datetime.now(timezone.utc)) &
            (StoryGroups.is_active == True) & (StoryGroups.group_type == infos.target_group_type)
        )

        if infos.target_group_type == StoryGroupsType.CLUB_GROUP:
            query = query.where(
                StoryGroups.club_id == infos.club_id
            )
        elif infos.target_group_type == StoryGroupsType.CLASSE_GROUP:
            query = query.where(
                StoryGroups.target_classe_id == infos.target_classe_id
            )
        else:
            query = query.where(
                StoryGroups.author_id == user_id
            )

        result = await self.db.execute(query)
        group = result.scalar_one_or_none()
        return group

    async def create_story_group(
        self, user_id: UUID, in_transaction: bool,
        infos: CreateStoryUploadIntentFullData
    ) -> CRUDResult[StoryGroups]:
        """
        Crée un nouveau groupe de stories pour un utilisateur.

        Args:
            user_id: L'ID de l'utilisateur
            in_transaction: Si true on est en mode Transac donc pas de commit, just flush
            infos: Infos supplémentyaires
        Returns:
            CRUDResult contenant le nouveau groupe ou une erreur
        """
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=infos.story_duration_hours)

            new_group = StoryGroups(
                author_id=user_id,
                expires_at=expires_at,
                is_active=True,
                group_type=infos.target_group_type,
                club_id=infos.club_id,
                target_classe_id=infos.target_classe_id
            )

            return await self.save_story_group(new_group, in_transaction)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, StoryGroupsType
            )

    async def get_or_create_active_story_group(
        self, user_id: UUID, in_transaction: bool, infos: CreateStoryUploadIntentFullData
    ) -> CRUDResult[StoryGroups]:
        """
        Récupère ou crée le groupe actif d'un utilisateur.
        Gère automatiquement la création si le groupe n'existe pas ou est expiré.

        Args:
            user_id: L'ID de l'utilisateur
            in_transaction: Si True, utilise une transaction existante
            infos: Les informations de l'intent d'upload pour déterminer le type de groupe à récupérer (user, classe, club)

        Returns:
            CRUDResult contenant le groupe actif (nouveau ou existant)
        """
        try:

            existing_group = await self.get_active_story_group(user_id, infos)

            if not existing_group:
                logger.info(
                    f"Aucun groupe de story actif trouvé pour l'utilisateur {user_id} et le"
                    f" type {infos.target_group_type}, création d'un nouveau groupe."
                )
                return await self.create_story_group(user_id, in_transaction, infos)


            return CRUDResult.crud_success(existing_group)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, StoryGroupsType
            )
