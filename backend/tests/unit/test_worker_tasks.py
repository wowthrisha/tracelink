"""
Unit tests for the Celery worker task helpers.

_should_process() is a pure function with no I/O, so it can be tested without
any mocking or database fixtures.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.workers.tasks import _should_process, _STALE_PROCESSING_THRESHOLD


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ago(minutes: int) -> datetime:
    return _now() - timedelta(minutes=minutes)


class TestShouldProcess:
    """_should_process(status, updated_at) → "proceed" | "skip" | "recover" """

    # ── uploaded ───────────────────────────────────────────────────────────────

    def test_uploaded_always_proceeds(self):
        assert _should_process("uploaded", _now()) == "proceed"

    def test_uploaded_with_old_timestamp_still_proceeds(self):
        assert _should_process("uploaded", _ago(60)) == "proceed"

    # ── ready / error — finished states must be skipped ──────────────────────

    def test_ready_is_skipped(self):
        assert _should_process("ready", _now()) == "skip"

    def test_error_is_skipped(self):
        assert _should_process("error", _now()) == "skip"

    # ── processing — active jobs must be skipped ──────────────────────────────

    def test_recent_processing_is_skipped(self):
        """A job that started 1 minute ago is still active — skip it."""
        assert _should_process("processing", _ago(1)) == "skip"

    def test_processing_just_under_threshold_is_skipped(self):
        margin = _STALE_PROCESSING_THRESHOLD - timedelta(seconds=30)
        assert _should_process("processing", _now() - margin) == "skip"

    # ── processing — stale jobs must trigger recovery ─────────────────────────

    def test_processing_exactly_at_threshold_triggers_recovery(self):
        assert _should_process("processing", _now() - _STALE_PROCESSING_THRESHOLD) == "recover"

    def test_processing_well_past_threshold_triggers_recovery(self):
        assert _should_process("processing", _ago(60)) == "recover"

    def test_processing_one_day_old_triggers_recovery(self):
        assert _should_process("processing", _ago(60 * 24)) == "recover"

    # ── timezone-naive updated_at ─────────────────────────────────────────────

    def test_naive_datetime_treated_as_utc_for_recent_processing(self):
        """Postgres sometimes returns tz-naive datetimes; worker must handle them."""
        # Use UTC-equivalent naive datetime: .replace(tzinfo=None) strips tzinfo
        # while keeping the numeric value in UTC, matching what Postgres returns.
        naive_recent = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
        assert naive_recent.tzinfo is None
        assert _should_process("processing", naive_recent) == "skip"

    def test_naive_datetime_treated_as_utc_for_stale_processing(self):
        naive_stale = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        assert naive_stale.tzinfo is None
        assert _should_process("processing", naive_stale) == "recover"

    # ── threshold is configurable ─────────────────────────────────────────────

    def test_threshold_is_15_minutes(self):
        assert _STALE_PROCESSING_THRESHOLD == timedelta(minutes=15)


class TestPurgeStaleSessionsAsync:
    """_purge_stale_sessions_async must delete sessions inactive >2 hours."""

    @pytest.mark.asyncio
    async def test_deletes_stale_sessions_and_keeps_active(self):
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
        from sqlalchemy import select
        from app.database import Base
        from app.models.session import ViewerSession
        from app.workers.tasks import _purge_stale_sessions_async
        import uuid

        engine = create_async_engine(
            "sqlite+aiosqlite:///./test_purge_sessions.db",
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        link_id = uuid.uuid4()
        stale_time = datetime.now(timezone.utc) - timedelta(hours=3)
        active_time = datetime.now(timezone.utc) - timedelta(minutes=5)

        # Need a link row because ViewerSession has FK to share_links
        # We skip the FK constraint by using SQLite without FK enforcement
        # (SQLite doesn't enforce FKs by default) so we can insert sessions directly.
        async with factory() as db:
            db.add(ViewerSession(
                session_id="stale000" * 2,
                link_id=link_id,
                created_at=stale_time,
                last_seen_at=stale_time,
            ))
            db.add(ViewerSession(
                session_id="active00" * 2,
                link_id=link_id,
                created_at=active_time,
                last_seen_at=active_time,
            ))
            await db.commit()

        # Patch the module-level factory to use our test DB
        import app.workers.tasks as tasks_module
        original_factory = tasks_module._session_factory
        tasks_module._session_factory = factory

        try:
            result = await _purge_stale_sessions_async()
        finally:
            tasks_module._session_factory = original_factory

        assert result["deleted"] == 1

        async with factory() as db:
            remaining = (await db.execute(select(ViewerSession))).scalars().all()
        assert len(remaining) == 1
        assert remaining[0].session_id == "active00" * 2

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


class TestTaskRegistration:
    """
    Regression test for a real bug: celery_app.py's `include=` list determines
    which task modules the Celery *worker* process imports at boot (via
    `celery_app.loader.import_default_modules()`), separately from whatever
    the FastAPI/test process happens to import. `app.workers.webhook_tasks`
    was missing from that list, so `@celery_app.task(name="securedoc.deliver_webhook")`
    never ran in a real worker process — webhook_service.py/webhooks.py's
    `send_task("securedoc.deliver_webhook", ...)` calls would enqueue a task
    name no worker had ever registered. Passed silently because tests import
    the task modules directly, which masks an `include=` omission.
    """

    def test_all_task_modules_are_registered_with_the_worker(self):
        from app.workers.celery_app import celery_app

        # Mirrors what a real `celery -A app.workers.celery_app worker` boot does —
        # importing task modules directly (as other tests/callers do) does NOT
        # exercise this path and would not have caught the missing include=.
        celery_app.loader.import_default_modules()

        expected = {
            "securedoc.process_document",
            "securedoc.purge_stale_sessions",
            "securedoc.requeue_orphaned_uploads",
            "securedoc.take_storage_snapshot",
            "securedoc.sync_document_access_times",
            "securedoc.cleanup_expired_documents",
            "securedoc.cleanup_orphaned_viewer_profiles",
            "securedoc.deliver_webhook",
        }
        missing = expected - set(celery_app.tasks)
        assert not missing, f"Task(s) not registered with the worker: {missing}"
