import asyncio
from logging import Logger
from typing import List
from uuid import UUID

from app.cache.story_cache import StoryCache
from datetime import datetime

from app.db.session import AsyncSessionLocal
from app.repositories.story_views_repository import StoryViewsRepository
from app.worker.tasks.tasks_utils.base import ProcessingResult


async def add_views_for_user(user_id: str, redis_conn: StoryCache, db: StoryViewsRepository, logger: Logger, mock_viewed_at: datetime) -> None:
    """
    Insère les vues de stories d'un utilisateur depuis Redis vers PostgreSQL.

    Args:
        user_id: ID de l'utilisateur
        redis_conn: Cache Redis pour les stories
        db: Repository pour les vues de stories
        logger: Logger pour les messages
        mock_viewed_at: Timestamp de la vue (pour tous les records du batch)

    Returns:
        None
    """
    try:
        viewed_stories = await redis_conn.get_daily_seen_story_ids(UUID(user_id))

        if not viewed_stories:
            logger.info(f"Aucune story vue par le user : {user_id}")
            return None

        views_dict = [{"user_id": user_id, "story_id": str(s_id), "viewed_at": mock_viewed_at} for s_id in viewed_stories]

        res = await db.add_many_views_by_bulk_insert(views_dict)

        if res.is_error():
            logger.error(f"Erreur lors de l'insertion des vues pour user : {user_id} : {res.error}")
            return None

        logger.info(f"Insertion des vues réussi pour user : {user_id}")

        await redis_conn.clear_daily_seen_stories_for_user(UUID(user_id))
        return None
    except Exception as e:
        logger.error(f"Erreur {e.__class__.__name__} lors de l'insertion des vues pour le user : {user_id} : {str(e)}")
        return None


async def insert_views_for_all_users(users: List[str], redis_conn: StoryCache, batch_size: int, logger: Logger) -> ProcessingResult[None]:
    """
    Insère les vues de stories pour tous les utilisateurs par batch.

    Traite les utilisateurs par batches pour optimiser les performances
    et éviter de surcharger la base de données.

    Args:
        users: Liste des IDs utilisateurs ayant vu des stories
        redis_conn: Cache Redis pour les stories
        batch_size: Nombre d'utilisateurs à traiter par batch
        logger: Logger pour les messages

    Returns:
        ProcessingResult: Succès ou erreur de l'insertion globale
    """
    try:
        async with AsyncSessionLocal() as session:
            repo: StoryViewsRepository = StoryViewsRepository(session)
            now = datetime.now()
            for i in range(0, len(users), batch_size):
                batch = users[i: i + batch_size]

                tasks = [
                    add_views_for_user(
                        user_id=user_id, redis_conn=redis_conn, db=repo,
                        logger=logger, mock_viewed_at=now
                    ) for user_id in batch
                ]

                await asyncio.gather(*tasks)

            return ProcessingResult.ok_response(None)
    except Exception as e:
        return ProcessingResult.error_response(f"Erreur {e.__class__.__name__} lors des insertions des vues pour les users : {str(e)}")



