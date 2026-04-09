"""
Repository pour la gestion des stories et des groupes de stories en base de données.
Contient les requêtes pour créer, récupérer et gérer les stories et leurs groupes.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from app.db.models.stories import Story
from app.db.models.story_groups import StoryGroups
from app.repositories import CRUDResult
from app.globals.messages import Messages

import logging

logger = logging.getLogger(__name__)


@dataclass
class StoryRepository:
    """Repository pour les opérations sur les stories et les groupes de stories."""

    db: AsyncSession

    async def save_story(self, story: Story, in_transaction: bool = False) -> CRUDResult[Story]:
        """
        Sauvegarde une story en base de données.

        Args:
            story: L'objet Story à sauvegarder
            in_transaction: Si True, utilise une transaction existante

        Returns:
            CRUDResult contenant la story sauvegardée ou une erreur
        """
        try:
            self.db.add(story)
            if not in_transaction:
                await self.db.commit()
            await self.db.refresh(story)
            return CRUDResult.crud_success(data=story, status_code=status.HTTP_201_CREATED)
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = story.translate_integrity_error(e)
            logger.error(f"Erreur d'intégrité lors de la sauvegarde de la story : {error_msg}")
            return CRUDResult.crud_error(message=error_msg or Messages.INTERNAL_SERVER_ERROR, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            await self.db.rollback()
            error_msg = f"Exception {e.__class__.__name__} lors de la sauvegarde de la story : {e}"
            logger.exception(error_msg)
            return CRUDResult.crud_error(message=Messages.INTERNAL_SERVER_ERROR, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def save_story_group(self, group: StoryGroups, in_transaction: bool = False) -> CRUDResult[StoryGroups]:
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


            if not in_transaction:
                await self.db.commit()

            await self.db.flush()

            await self.db.refresh(group)

            return CRUDResult.crud_success(data=group, status_code=status.HTTP_201_CREATED)
        except IntegrityError as e:
            await self.db.rollback()
            error_msg = group.translate_integrity_error(e)
            logger.error(f"Erreur d'intégrité lors de la sauvegarde du groupe de stories : {error_msg}")
            return CRUDResult.crud_error(message=error_msg or Messages.INTERNAL_SERVER_ERROR, status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            await self.db.rollback()
            error_msg = f"Exception {e.__class__.__name__} lors de la sauvegarde du groupe de stories : {e}"
            logger.exception(error_msg)
            return CRUDResult.crud_error(message=Messages.INTERNAL_SERVER_ERROR, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def get_active_story_group(self, user_id: UUID) -> CRUDResult[Optional[StoryGroups]]:
        """
        Récupère le groupe actif (non expiré) d'un utilisateur.

        Args:
            user_id: L'ID de l'utilisateur

        Returns:
            CRUDResult contenant le groupe actif ou None s'il n'existe pas
        """
        try:
            query = select(StoryGroups).where(
                (StoryGroups.author_id == user_id) &
                (StoryGroups.expires_at >= datetime.now(timezone.utc)) &
                (StoryGroups.is_expired == False)
            )
            result = await self.db.execute(query)
            group = result.scalar_one_or_none()
            if not group:
                return CRUDResult.crud_error(message="Pas de groupe actif", status_code=status.HTTP_200_OK)

            return CRUDResult.crud_success(data=group)
        except Exception as e:
            error_msg = f"Exception {e.__class__.__name__} lors de la récupération du groupe actif de stories : {e}"
            logger.exception(error_msg)
            return CRUDResult.crud_error(message=Messages.INTERNAL_SERVER_ERROR, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def create_story_group(self, user_id: UUID, in_transaction: bool) -> CRUDResult[StoryGroups]:
        """
        Crée un nouveau groupe de stories pour un utilisateur.

        Args:
            user_id: L'ID de l'utilisateur
            in_transaction:
        Returns:
            CRUDResult contenant le nouveau groupe ou une erreur
        """
        try:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

            new_group = StoryGroups(
                author_id=user_id,
                expires_at=expires_at,
                is_expired=False
            )

            return await self.save_story_group(new_group, in_transaction)
        except Exception as e:
            error_msg = f"Exception {e.__class__.__name__} lors de la création du groupe de stories : {e}"
            logger.exception(error_msg)
            return CRUDResult.crud_error(message=Messages.INTERNAL_SERVER_ERROR, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    async def get_or_create_active_story_group(self, user_id: UUID, in_transaction: bool) -> CRUDResult[Optional[StoryGroups]]:
        """
        Récupère ou crée le groupe actif d'un utilisateur.
        Gère automatiquement la création si le groupe n'existe pas ou est expiré.

        Args:
            user_id: L'ID de l'utilisateur
            in_transaction: Si True, utilise une transaction existante

        Returns:
            CRUDResult contenant le groupe actif (nouveau ou existant)
        """
        try:
            # Essayer de récupérer le groupe existant
            existing_group_result = await self.get_active_story_group(user_id)

            if existing_group_result.is_error():
                return await self.create_story_group(user_id, in_transaction)

            return existing_group_result

        except Exception as e:
            error_msg = f"Exception {e.__class__.__name__} lors de get_or_create_active_story_group : {e}"
            logger.exception(error_msg)
            return CRUDResult.crud_error(message=Messages.INTERNAL_SERVER_ERROR, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

