from celery import Celery
from celery.schedules import crontab

from app.core.config import REDIS_URL
from app.worker.tasks import add_all_tasks

celery_app : Celery = Celery(
    "app",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    broker_url=REDIS_URL,
    task_reject_on_worker_lost=True,
)

add_all_tasks()
celery_app.autodiscover_tasks(["app.worker.tasks"])

celery_app.conf.beat_schedule = {
    'synchronisation-vues_posts_redis-bd': {
        'task': 'synchronize_post_view',
        'schedule': crontab(hour=2, minute=00), # Tous les jours à 2h00
    },
    'synchronisation-vues_story_redis-bd': {
        'task': 'synchronize_story_view',
        'schedule': crontab(hour=1, minute=00),  # Tous les jours à 1h00
    }
}