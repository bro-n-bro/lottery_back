from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "delegators",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.imports = ("app.tasks.tasks",)

celery_app.conf.beat_schedule = {
    "fetch_delegators_hourly": {
        "task": "app.tasks.tasks.sync_delegators",
        "schedule": 10,
    }
}

celery_app.conf.timezone = "UTC"
