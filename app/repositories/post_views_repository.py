from dataclasses import dataclass
from datetime import datetime
from logging import getLogger
from typing import List, Dict
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.post_views import PostViews
from app.repositories import CRUDResult
from app.repositories.repositories_utils import RepositoriesUtils

logger = getLogger(__name__)


@dataclass
class PostViewsRepository:

    db: AsyncSession

    async def add_many_views_by_bulk_insert(
        self, views: List[Dict[str, str | UUID | datetime]]
    ) -> CRUDResult[str]:
        try:
            if not views:
                return CRUDResult.crud_error("Liste des vues à insérer vides")

            requete = insert(PostViews).values(views)

            requete = requete.on_conflict_do_nothing()

            await self.db.execute(requete)

            await self.db.commit()

            return CRUDResult.crud_success("Insertion des vues réussi")
        except Exception as e:
            return await RepositoriesUtils.traiter_errors_en_global(
                e, self.db, logger, PostViews
            )
