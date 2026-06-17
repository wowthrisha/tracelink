"""
Tests for periodic Celery cleanup tasks.

Covers:
  - cleanup_orphaned_viewer_profiles: deletes profiles with no referencing
    sessions or annotations; preserves profiles that are still referenced.
  - _requeue_orphaned_uploads_async: re-queues documents stuck in 'uploaded'
    or 'processing' states past their respective staleness thresholds.
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.database import Base


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ago(minutes: int) -> datetime:
    return _now() - timedelta(minutes=minutes)


# ── TestCleanupOrphanedViewerProfiles ─────────────────────────────────────────

class TestCleanupOrphanedViewerProfiles:
    """_cleanup_orphaned_viewer_profiles_async must delete profiles with no
    remaining viewer_sessions or viewer_annotations referencing them."""

    @pytest.mark.asyncio
    async def test_deletes_unreferenced_profile(self):
        from app.models.viewer_profile import ViewerProfile
        from app.workers.cleanup import _cleanup_orphaned_viewer_profiles_async
        import app.workers.cleanup as cleanup_mod
        import app.workers.tasks as tasks_mod

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        profile_id = str(uuid.uuid4())
        now = _now()

        async with factory() as db:
            db.add(ViewerProfile(
                id=profile_id,
                email="orphan@example.com",
                first_seen_at=now,
                last_seen_at=now,
            ))
            await db.commit()

        # Patch both modules' factories (cleanup uses tasks._get_db_session_factory)
        orig_factory = tasks_mod._session_factory
        tasks_mod._session_factory = factory
        try:
            result = await _cleanup_orphaned_viewer_profiles_async()
        finally:
            tasks_mod._session_factory = orig_factory

        assert result["deleted"] == 1

        async with factory() as db:
            remaining = (await db.execute(select(ViewerProfile))).scalars().all()
        assert len(remaining) == 0

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_preserves_profile_referenced_by_session(self):
        from app.models.viewer_profile import ViewerProfile
        from app.models.session import ViewerSession
        from app.workers.cleanup import _cleanup_orphaned_viewer_profiles_async
        import app.workers.tasks as tasks_mod

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        profile_id = str(uuid.uuid4())
        link_id = uuid.uuid4()
        now = _now()

        async with factory() as db:
            db.add(ViewerProfile(
                id=profile_id,
                email="active@example.com",
                first_seen_at=now,
                last_seen_at=now,
            ))
            # SQLite doesn't enforce FKs by default; insert session referencing profile
            db.add(ViewerSession(
                session_id="activeprof" * 2 + "xx",
                link_id=link_id,
                viewer_profile_id=profile_id,
                created_at=now,
                last_seen_at=now,
            ))
            await db.commit()

        orig = tasks_mod._session_factory
        tasks_mod._session_factory = factory
        try:
            result = await _cleanup_orphaned_viewer_profiles_async()
        finally:
            tasks_mod._session_factory = orig

        assert result["deleted"] == 0

        async with factory() as db:
            remaining = (await db.execute(select(ViewerProfile))).scalars().all()
        assert len(remaining) == 1

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_mixed_deletes_only_unreferenced(self):
        """One referenced profile + one orphan: only orphan is deleted."""
        from app.models.viewer_profile import ViewerProfile
        from app.models.session import ViewerSession
        from app.workers.cleanup import _cleanup_orphaned_viewer_profiles_async
        import app.workers.tasks as tasks_mod

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        linked_id = str(uuid.uuid4())
        orphan_id = str(uuid.uuid4())
        link_id = uuid.uuid4()
        now = _now()

        async with factory() as db:
            db.add(ViewerProfile(
                id=linked_id, email="linked@example.com",
                first_seen_at=now, last_seen_at=now,
            ))
            db.add(ViewerProfile(
                id=orphan_id, email="orphan@example.com",
                first_seen_at=now, last_seen_at=now,
            ))
            db.add(ViewerSession(
                session_id="mixedtest" * 2 + "yy",
                link_id=link_id,
                viewer_profile_id=linked_id,
                created_at=now, last_seen_at=now,
            ))
            await db.commit()

        orig = tasks_mod._session_factory
        tasks_mod._session_factory = factory
        try:
            result = await _cleanup_orphaned_viewer_profiles_async()
        finally:
            tasks_mod._session_factory = orig

        assert result["deleted"] == 1

        async with factory() as db:
            remaining = (await db.execute(select(ViewerProfile))).scalars().all()
        assert len(remaining) == 1
        assert remaining[0].id == linked_id

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    def test_task_registered_in_beat_schedule(self):
        """cleanup_orphaned_viewer_profiles must be in celery_app beat_schedule."""
        from app.workers.celery_app import celery_app
        schedule = celery_app.conf.beat_schedule
        task_names = [v["task"] for v in schedule.values()]
        assert "securedoc.cleanup_orphaned_viewer_profiles" in task_names, (
            "cleanup_orphaned_viewer_profiles must be registered in celery beat_schedule"
        )


# ── TestRequeuOrphanedUploads ─────────────────────────────────────────────────

class TestRequeuOrphanedUploads:
    """_requeue_orphaned_uploads_async must re-queue documents stuck in
    'uploaded' past 10 min and 'processing' past 20 min."""

    @pytest.mark.asyncio
    async def test_requeues_stale_uploaded_document(self):
        from app.models.document import Document
        from app.workers.tasks import _requeue_orphaned_uploads_async
        import app.workers.tasks as tasks_mod

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        doc_id = uuid.uuid4()
        stale_time = _ago(15)  # 15 minutes ago — past the 10 min threshold

        async with factory() as db:
            db.add(Document(
                id=doc_id,
                filename="stale.pdf",
                storage_key="originals/stale.pdf",
                status="uploaded",
                file_size_bytes=1000,
                user_id=uuid.uuid4(),
                updated_at=stale_time,
            ))
            await db.commit()

        orig = tasks_mod._session_factory
        tasks_mod._session_factory = factory
        dispatched = []

        # Patch process_document.delay so we can capture calls without Celery
        import unittest.mock as mock
        with mock.patch("app.workers.tasks.process_document") as mock_task:
            mock_task.delay = mock.MagicMock(side_effect=lambda doc_id: dispatched.append(doc_id))
            try:
                result = await _requeue_orphaned_uploads_async()
            finally:
                tasks_mod._session_factory = orig

        assert result["requeued"] == 1
        assert str(doc_id) in dispatched

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_skips_recently_uploaded_document(self):
        """A document uploaded 2 minutes ago is not yet stale — must not be requeued."""
        from app.models.document import Document
        from app.workers.tasks import _requeue_orphaned_uploads_async
        import app.workers.tasks as tasks_mod

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with factory() as db:
            db.add(Document(
                id=uuid.uuid4(),
                filename="fresh.pdf",
                storage_key="originals/fresh.pdf",
                status="uploaded",
                file_size_bytes=1000,
                user_id=uuid.uuid4(),
                updated_at=_ago(2),  # 2 minutes ago — not yet stale
            ))
            await db.commit()

        orig = tasks_mod._session_factory
        tasks_mod._session_factory = factory
        import unittest.mock as mock
        with mock.patch("app.workers.tasks.process_document") as mock_task:
            mock_task.delay = mock.MagicMock()
            try:
                result = await _requeue_orphaned_uploads_async()
            finally:
                tasks_mod._session_factory = orig

        assert result["requeued"] == 0
        mock_task.delay.assert_not_called()

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    @pytest.mark.asyncio
    async def test_resets_stuck_processing_document_to_uploaded(self):
        """A document stuck in 'processing' for >20 min must be reset to 'uploaded' before re-queue."""
        from app.models.document import Document
        from app.workers.tasks import _requeue_orphaned_uploads_async
        import app.workers.tasks as tasks_mod
        from sqlalchemy import select

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        doc_id = uuid.uuid4()

        async with factory() as db:
            db.add(Document(
                id=doc_id,
                filename="stuck.pdf",
                storage_key="originals/stuck.pdf",
                status="processing",
                file_size_bytes=1000,
                user_id=uuid.uuid4(),
                updated_at=_ago(25),  # stuck for 25 min, past 20 min threshold
            ))
            await db.commit()

        orig = tasks_mod._session_factory
        tasks_mod._session_factory = factory
        import unittest.mock as mock
        with mock.patch("app.workers.tasks.process_document") as mock_task:
            mock_task.delay = mock.MagicMock()
            try:
                result = await _requeue_orphaned_uploads_async()
            finally:
                tasks_mod._session_factory = orig

        assert result["requeued"] == 1

        # Verify the document status was reset to 'uploaded' before re-queuing
        async with factory() as db:
            doc = (await db.execute(select(Document).where(Document.id == doc_id))).scalar_one()
        assert doc.status == "uploaded", "Stuck processing doc must be reset to 'uploaded'"

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
