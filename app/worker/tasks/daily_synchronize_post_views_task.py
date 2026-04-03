from logging import getLogger

from celery import shared_task

from app.cache.feed_cache import FeedCache
from app.cache.helpers.base import cache_manager
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.tasks_utils.base import ProcessingResult
from app.worker.tasks.tasks_utils.synchronize_view_task_utils import insert_views_for_all_users
from app.worker.tasks.workers_task_names import WorkersTaskNames

logger = getLogger(__name__)

@shared_task(name=WorkersTaskNames.SYNCHRONIZE_POST_VIEW)
def synchronize_post_view():
    logger.info("Début de la task de synchronisation des vues de post Redis ver BD")
    redis_cache = cache_manager.get_redis_connection_from_pool()
    feed_cache = FeedCache(redis_cache)

    try:
        users_has_seen_posts = task_async_loop_manager.run_async(feed_cache.get_daily_users_seen_posts_set())

        task_async_loop_manager.run_async(feed_cache.restart_daily_users_seen_posts_set())

        if not users_has_seen_posts:
            logger.info("Aucune vu de post, fin de la task")
            return

        logger.info(f"Utilisateurs ayant vu des posts récupoérés avec succès : {len(users_has_seen_posts)}")
        users_has_seen_posts = list(users_has_seen_posts)

        INSERT_BATCH_SIZE = 5

        res: ProcessingResult[None] = task_async_loop_manager.run_async(
            insert_views_for_all_users(
                users_has_seen_posts, feed_cache, INSERT_BATCH_SIZE, logger
            )
        )

        if res.is_error():
            logger.error(res.error)
            return
        logger.info("Vues des posts synchronisées avec succès")
    except Exception as e:
        logger.exception(f"Exception {e.__class__.__name__} inattendue lors de l'insertion des vus pour les users: {e}")
    finally:
        task_async_loop_manager.run_async(redis_cache.close())
        logger.info("Fin de la task de synchronisation des vues de post")



