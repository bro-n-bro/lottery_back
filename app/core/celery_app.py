from celery import Celery

celery_app = Celery(
    "delegators",
    broker=f"redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

celery_app.conf.imports = ("app.tasks.tasks",)

celery_app.conf.beat_schedule = {
    "fetch_delegators_hourly": {
        "task": "app.tasks.tasks.sync_delegators",
        "schedule": 3600,
    }
}

celery_app.conf.timezone = "UTC"
