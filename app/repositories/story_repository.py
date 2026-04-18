"""
Repository pour la gestion des stories et des groupes de stories en base de données.
Contient les requêtes pour créer, récupérer et gérer les stories et leurs groupes.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Any
from uuid import UUID

from sqlalchemy import select, Select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload, with_loader_criteria
from fastapi import status

from app.db.models.enums import StoryGroupsType
from app.db.models.stories import Story
from app.db.models.story_groups import StoryGroups
from app.db.models.story_views import StoryViews
from app.db.models.user import User
from app.db.models.club import Club
from app.db.models.classe import Classe
from app.globals.messages import Messages
from app.repositories import CRUDResult
from app.utils.pagination_cursor_utils import PaginationCursorUtils

import logging

from app.repositories.repositories_utils import RepositoriesUtils
from app.schemas.story_upload_schemas import CreateStoryUploadIntentFullData

logger = logging.getLogger(__name__)

# Nombre de groupes par défaut retournés par page dans le feed
DEFAULT_PAGE_SIZE = 10


@dataclass
class StoryRepository:
    """Repository pour les opérations sur les stories et les groupes de stories."""

    db: AsyncSession

    @staticmethod
    def _get_story_groups_base_query(
        filter_expired_stories: bool = True,
    ) -> Select:
        """
        Squelette de base pour récupérer les groupes de stories avec toutes leurs infos utiles.

        Args:
            filter_expired_stories: Si True, exclut les stories expirées via with_loader_criteria.

        Returns:
            Select: Statement SQLAlchemy prêt à recevoir des .where() / .limit() etc.
        """
        story_options: List[Any] = [selectinload(StoryGroups.stories).selectinload(Story.author)]
        if filter_expired_stories:
            story_options.append(
                with_loader_criteria(Story, Story.expires_at >= datetime.now(timezone.utc))
            )

        return (
            select(StoryGroups)
            .options(
                joinedload(StoryGroups.author).load_only(
                    User.id,
                    User.username,
                    User.first_name,
                    User.last_name,
                    User.avatar_url,
                    User.role,
                    User.executive_role
                ),
                joinedload(StoryGroups.club).load_only(
                    Club.id,
                    Club.name,
                    Club.slug,
                    Club.logo_url,
                ),
                joinedload(StoryGroups.classe).load_only(
                    Classe.id,
                    Classe.classe_prefix,
                    Classe.classe_suffix,
                ),
                *story_options,
            )
        )

    async def get_story_groups_feed(
        self,
        user_id: UUID,
        user_classe_id: Optional[UUID] = None,
        cursor: Optional[str] = None,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> CRUDResult[dict]:
        """Récupère un feed de groupes de stories paginé par curseur.

        Args:
            user_id: ID de l'utilisateur courant.
            user_classe_id: Classe de l'utilisateur (pour filtrer CLASSE_GROUP).
            cursor: Curseur opaque de la page précédente.
            page_size: Nombre de groupes par page.

        Returns:
            CRUDResult[dict]: Feed paginé avec items, next_cursor, has_more, et user_viewed_story_ids.
        """
        try:
            requete = self._get_story_groups_base_query()

            requete = requete.where(
                StoryGroups.expires_at >= datetime.now(timezone.utc)
            )

            if user_classe_id:
                requete = requete.where(
                    or_(
                        StoryGroups.group_type == StoryGroupsType.USER_GROUP,
                        StoryGroups.group_type == StoryGroupsType.CLUB_GROUP,
                        and_(
                            StoryGroups.group_type == StoryGroupsType.CLASSE_GROUP,
                            StoryGroups.target_classe_id == user_classe_id
                        )
                    )
                )
            else:   # L'utilisateur n'a pas de classe, genre ADMIN ou un bug, on sait jamais

                requete = requete.where(
                    or_(
                        StoryGroups.group_type == StoryGroupsType.USER_GROUP,
                        StoryGroups.group_type == StoryGroupsType.CLUB_GROUP,
                    )
                )

            requete = requete.order_by(
                StoryGroups.updated_at.desc(), StoryGroups.id.desc()
            ).limit(page_size + 1)

            # Appliquer le curseur si fourni
            if cursor:
                cursor_id, cursor_updated_at = PaginationCursorUtils.decode_pagination_cursor(cursor)
                requete = requete.where(
                    (StoryGroups.updated_at < cursor_updated_at)
                    | (
                        (StoryGroups.updated_at == cursor_updated_at)
                        & (StoryGroups.id < cursor_id)
                    )
                )

            result = await self.db.execute(requete)

            # .unique() est obligatoire dès qu'on utilise joinedload
            groups = result.unique().scalars().all()

            has_more = len(groups) > page_size
            items: List[StoryGroups] = list(groups[:page_size])

            next_cursor = None
            if has_more and items:
                last = items[-1]
                next_cursor = PaginationCursorUtils.encode_pagination_cursor(last.id, last.updated_at)

            # Ici on recup les vues si présent
            user_viewed_story_ids: set[UUID] = set()
            story_ids = [s.id for g in items for s in g.stories]

            if story_ids:
                views_query = select(StoryViews.story_id).where(
                    and_(
                        StoryViews.story_id.in_(story_ids),
                        StoryViews.user_id == user_id
                    )
                )
                views_result = await self.db.execute(views_query)
                user_viewed_story_ids = set(views_result.scalars().all())

            logger.info(
                "Feed de stories récupéré : %d groupes, has_more=%s, %d vues de l'utilisateur",
                len(items), has_more, len(user_viewed_story_ids)
            )
            return CRUDResult.crud_success(
                {
                    "items": items,
                    "next_cursor": next_cursor,
                    "has_more": has_more,
                    "user_viewed_story_ids": user_viewed_story_ids
                },
                status.HTTP_200_OK,
            )

        except ValueError as ve:
            # Curseur malformé
            return CRUDResult.crud_error(str(ve), status_code=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(e, self.db, logger, StoryGroups)

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
                e, self.db, logger, StoryGroups
            )

    async def save_story(self, sto: Story, in_transaction: bool) -> CRUDResult[Story]:
        """Sauvegarde une story en base de données.

        Args:
            sto: L'objet Story à sauvegarder
            in_transaction: Si True, utilise une transaction existante

        Returns:
            CRUDResult contenant la story sauvegardée ou une erreur
        """
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

    async def get_story_group_by_id(self, group_id: UUID) -> CRUDResult[StoryGroups]:
        try:
            requete = self._get_story_groups_base_query().where(
                StoryGroups.id == group_id
            )

            result = await self.db.execute(requete)

            # .unique() est obligatoire dès qu'on utilise joinedload
            group: Optional[StoryGroups] = result.unique().scalar_one_or_none()

            if group is None:
                return CRUDResult.crud_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=Messages.STORY_GROUP_NOT_FOUND
                )
            return CRUDResult.crud_success(group, status_code=status.HTTP_200_OK)
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
            # Pas d'user_id sur le group si ce n'est pas un groupe d'un user simple
            # nsm ce truc devient trop complexe

            if infos.target_group_type != StoryGroupsType.USER_GROUP:
                new_group.author_id = None


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
