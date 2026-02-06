from celery import Celery

celery_app = Celery(
    "fast_api_app",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)