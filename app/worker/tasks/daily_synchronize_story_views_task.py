from logging import getLogger

from celery import shared_task

from app.cache.story_cache import StoryCache
from app.cache.helpers.base import cache_manager
from app.worker.tasks.async_loop_manager import task_async_loop_manager
from app.worker.tasks.tasks_utils.base import ProcessingResult
from app.worker.tasks.tasks_utils.synchronize_story_view_task_utils import insert_views_for_all_users
from app.worker.tasks.workers_task_names import WorkersTaskNames

logger = getLogger(__name__)


@shared_task(name=WorkersTaskNames.SYNCHRONIZE_STORY_VIEW)
def synchronize_story_view():
    """
    Synchronise les vues de stories depuis Redis vers la bd
    """
    logger.info("Début de la task de synchronisation des vues de story Redis vers BD")
    redis_cache = cache_manager.get_redis_connection_from_pool()
    story_cache = StoryCache(redis_cache)

    try:
        users_has_seen_stories = task_async_loop_manager.run_async(story_cache.get_daily_users_seen_posts_set())

        task_async_loop_manager.run_async(story_cache.restart_daily_users_seen_posts_set())

        if not users_has_seen_stories:
            logger.info("Aucune vue de story, fin de la task")
            return

        logger.info(f"Utilisateurs ayant vu des stories récupérés avec succès : {len(users_has_seen_stories)}")
        users_has_seen_stories = list(users_has_seen_stories)

        INSERT_BATCH_SIZE = 5

        res: ProcessingResult[None] = task_async_loop_manager.run_async(
            insert_views_for_all_users(
                users_has_seen_stories, story_cache, INSERT_BATCH_SIZE, logger
            )
        )

        if res.is_error():
            logger.error(res.error)
            return
        logger.info("Vues des stories synchronisées avec succès")
    except Exception as e:
        logger.exception(f"Exception {e.__class__.__name__} inattendue lors de l'insertion des vues pour les users: {e}")
    finally:
        task_async_loop_manager.run_async(redis_cache.close())
        logger.info("Fin de la task de synchronisation des vues de story")

