import os
from celery import Celery
from app.config import settings

if os.getenv("USE_DEMO_STORAGE") == "1":
    import demo_storage_patch  # noqa: F401

celery_app = Celery(
    "securedoc",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    # Re-queue task if the worker process is killed mid-execution so the document
    # does not remain stuck in "processing" permanently (pairs with acks_late=True).
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    # Per-task time limits (seconds).
    # soft_time_limit raises SoftTimeLimitExceeded inside the task coroutine,
    # allowing graceful cleanup before the hard limit kills the process.
    # 600 s / 10 min covers a 200-page PDF under normal R2 upload conditions.
    # The hard limit (660 s) gives the task 60 s to handle the soft exception
    # before the worker process is force-killed and the task re-queued.
    task_soft_time_limit=600,
    task_time_limit=660,
    beat_schedule={
        "purge-stale-sessions-every-30-min": {
            "task": "securedoc.purge_stale_sessions",
            "schedule": 1800,  # seconds (30 minutes)
        },
        "requeue-orphaned-uploads-every-5-min": {
            "task": "securedoc.requeue_orphaned_uploads",
            "schedule": 300,  # seconds (5 minutes)
        },
    },
)
