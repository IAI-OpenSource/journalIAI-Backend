import asyncio
from logging import Logger
from typing import List
from uuid import UUID

from app.cache.feed_cache import FeedCache
from datetime import datetime

from app.db.session import AsyncSessionLocal
from app.repositories.post_views_repository import PostViewsRepository
from app.worker.tasks.tasks_utils.base import ProcessingResult


async def add_views_for_user(user_id: str, redis_conn: FeedCache, bd: PostViewsRepository, logger: Logger, mock_viewed_at: datetime) -> None:
    try:
        viewed_post = await redis_conn.get_daily_seen_post_ids(UUID(user_id))

        if not viewed_post:
            logger.info(f"Aucun post vu par le user : {user_id}")
            return None

        views_dict = [{"user_id": user_id, "post_id": p_id, "viewed_at": mock_viewed_at} for p_id in viewed_post]

        res = await bd.add_many_views_by_bulk_insert(views_dict)

        if res.is_error():
            logger.error(f"Erreur lors de l'insertion des vues pour user : {user_id} : {res.error}")
            return None

        logger.info(f"Insertion des vues réussi pour user : {user_id}")

        await redis_conn.clear_daily_seen_posts_for_user(UUID(user_id))
        return None
    except Exception as e:
        return logger.error(f"Erreur {e.__class__.__name__} lors de l'insertion des vu"
                                               f"s pour le user : {user_id} : {str(e)})")



async def insert_views_for_all_users(users: List[str], redis_conn: FeedCache, batch_size: int, logger: Logger) -> ProcessingResult[None]:
    try:
        async with AsyncSessionLocal() as session:
            repo: PostViewsRepository = PostViewsRepository(session)
            now = datetime.now()
            for i in range(0, len(users), batch_size):
                batch = users[i: i + batch_size]

                tasks = [
                    add_views_for_user(
                        user_id=user_id, redis_conn=redis_conn, bd=repo,
                        logger=logger, mock_viewed_at=now
                    ) for user_id in batch
                ]

                await asyncio.gather(*tasks)

            return ProcessingResult.ok_response(None)
    except Exception as e:
        return ProcessingResult.error_response(f"Erreur {e.__class__.__name__} lors des insertion des vu"
                                           f"s pour les users :{str(e)})")
