from dataclasses import dataclass
from logging import getLogger
from typing import List, Dict

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.story_views import StoryViews
from app.repositories import CRUDResult
from app.repositories.repositories_utils import RepositoriesUtils

logger = getLogger(__name__)


@dataclass
class StoryViewsRepository:
    """Repository pour la gestion des vues de stories en base de données."""

    db: AsyncSession

    async def add_many_views_by_bulk_insert(self, views: List[Dict[str, str]]) -> CRUDResult[str]:
        """
        Insère plusieurs vues de stories en base de données via bulk insert.

        Args:
            views: Liste de dictionnaires contenant user_id, story_id, viewed_at

        Returns:
            CRUDResult: Succès ou erreur de l'insertion
        """
        try:
            if not views:
                return CRUDResult.crud_error("Liste des vues à insérer vides")

            requete = insert(StoryViews).values(views)

            requete = requete.on_conflict_do_nothing()

            await self.db.execute(requete)

            await self.db.commit()

            return CRUDResult.crud_success("Insertion des vues réussi")
        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(e, self.db, logger, StoryViews)

