import logging
import os
from celery import Celery
from celery.signals import worker_process_init
from app.config import settings

if os.getenv("USE_DEMO_STORAGE") == "1":
    import demo_storage_patch  # noqa: F401

celery_app = Celery(
    "securedoc",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks", "app.workers.cleanup"],
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
        # Storage lifecycle — run in order: snapshot → sync → cleanup
        "take-storage-snapshot-daily": {
            "task": "securedoc.take_storage_snapshot",
            "schedule": 86400,  # once per day (01:00 UTC via crontab is not yet configured)
        },
        "sync-document-access-times-daily": {
            "task": "securedoc.sync_document_access_times",
            "schedule": 86400,
        },
        "cleanup-expired-documents-daily": {
            "task": "securedoc.cleanup_expired_documents",
            "schedule": 86400,
        },
    },
)


@worker_process_init.connect
def _configure_worker_logging(**kwargs):
    """Configure structured JSON logging in Celery worker processes.

    Called once per worker process after fork.  Mirrors the API server's
    logging setup so worker logs are parseable by the same log aggregators.
    Controlled by the same ENABLE_JSON_LOGGING config flag.
    """
    if settings.enable_json_logging:
        from app.middleware.json_logging import configure_json_logging
        configure_json_logging()
        logging.getLogger("securedoc.worker").info(
            "Worker JSON logging configured",
            extra={"event": "worker_startup"},
        )
