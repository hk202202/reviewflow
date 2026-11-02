from celery import Celery
from celery.schedules import crontab
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("reviewflow", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    imports=("app.tasks.sync_reviews", "app.tasks.review_requests"),
    beat_schedule={
        "sync-all-platforms": {
            "task": "app.tasks.sync_reviews.sync_all_platforms",
            "schedule": crontab(minute="*/15"),
        },
        "send-review-requests": {
            "task": "app.tasks.review_requests.send_pending_requests",
            "schedule": crontab(minute="0", hour="*/1"),
        },
    },
)
