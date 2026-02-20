from celery import Celery

from app.core.config import REDIS_URL


celery_app : Celery = Celery(
    "app",
    broker=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

celery_app.autodiscover_tasks(["app.worker.tasks"])