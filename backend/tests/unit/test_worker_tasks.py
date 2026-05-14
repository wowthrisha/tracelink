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
        naive_recent = datetime.utcnow() - timedelta(minutes=1)
        assert naive_recent.tzinfo is None
        assert _should_process("processing", naive_recent) == "skip"

    def test_naive_datetime_treated_as_utc_for_stale_processing(self):
        naive_stale = datetime.utcnow() - timedelta(hours=1)
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
        from app.models.document import Document  # noqa: ensure tables exist
        from app.models.link import ShareLink     # noqa: ensure tables exist
        from app.models.event import AccessEvent  # noqa: ensure tables exist
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
