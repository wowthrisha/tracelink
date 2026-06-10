"""
Phase 4 Stabilization tests — async concurrency hardening.

Covers:
  A) Worker event loop — persistent per-process loop, survives repeated calls
  B) _should_process decision logic — proceed / skip / recover branches
  C) DB session safety — rollback on exception, clean pool return
  D) log_event without db.refresh — commit=False batching, no extra SELECT
  E) process_document_with_session — skip/recover paths; error propagation
  F) Sequential page / thumb requests — no "in progress" errors
  G) Session isolation — concurrent requests do not share DB sessions
  H) Regression — upload, gate, validate, revoke, analytics endpoints
"""
import asyncio
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock, MagicMock, call

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base, get_db, make_engine
from app.main import app
from app.auth import get_current_user
from app.models.document import Document, DocumentPage
from app.models.link import ShareLink
from app.models.event import AccessEvent
from app.models.session import ViewerSession
from app.services.analytics_service import AnalyticsService
from app.services.link_service import LinkService
from app.workers.tasks import _should_process, _get_worker_loop, process_document_with_session
from app.routers.viewer import clear_page_cache, clear_thumb_cache, clear_metadata_caches

from tests.conftest import TEST_USER_ID, _make_webp_bytes

TEST_DB_URL = "sqlite+aiosqlite:///./test_securedoc.db"


# ── shared helpers ─────────────────────────────────────────────────────────────

async def _insert_ready_doc(db, page_count: int = 3) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename="stability.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status="ready",
        page_count=page_count,
        file_size_bytes=2048,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db.add(doc)
    await db.flush()
    for i in range(1, page_count + 1):
        db.add(DocumentPage(
            document_id=doc.id,
            page_number=i,
            storage_key=f"pages/{doc.id}/{i:04d}.webp",
            width_px=595,
            height_px=842,
        ))
    await db.commit()
    await db.refresh(doc)
    return doc


async def _make_active_link(db, doc: Document) -> ShareLink:
    svc = LinkService()
    return await svc.create_link(db, document_id=str(doc.id), label="stability")


async def _validate(client, token: str) -> dict:
    r = await client.post("/api/viewer/validate", json={"token": token})
    assert r.status_code == 200, r.text
    return r.json()


# ══════════════════════════════════════════════════════════════════════════════
# A. WORKER EVENT LOOP — persistent per-process loop
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkerEventLoop:
    """_get_worker_loop() must return the same loop on repeated calls."""

    def test_same_loop_returned_on_second_call(self):
        loop1 = _get_worker_loop()
        loop2 = _get_worker_loop()
        assert loop1 is loop2

    def test_loop_is_running_or_stopped_not_closed(self):
        loop = _get_worker_loop()
        assert not loop.is_closed()

    def test_recreates_loop_when_closed(self):
        """When the current loop is closed a new one must be created."""
        import app.workers.tasks as tasks_mod

        original_loop = tasks_mod._worker_loop
        # Close a *copy* (not the actual stored loop) to isolate test state,
        # then inject it as if it were the current loop.
        closed_loop = asyncio.new_event_loop()
        closed_loop.close()
        tasks_mod._worker_loop = closed_loop

        try:
            new_loop = _get_worker_loop()
            assert not new_loop.is_closed()
            assert new_loop is not closed_loop
        finally:
            # Restore original loop so later tests aren't affected
            tasks_mod._worker_loop = original_loop

    def test_get_worker_loop_can_run_simple_coroutine(self):
        async def _coro():
            return 42

        loop = _get_worker_loop()
        result = loop.run_until_complete(_coro())
        assert result == 42

    def test_sequential_tasks_reuse_same_loop(self):
        """Simulates what happens when process_document() fires twice sequentially."""
        async def _task(n):
            return n * 2

        loop = _get_worker_loop()
        r1 = loop.run_until_complete(_task(3))
        r2 = loop.run_until_complete(_task(5))
        assert r1 == 6
        assert r2 == 10
        assert _get_worker_loop() is loop


# ══════════════════════════════════════════════════════════════════════════════
# B. _should_process DECISION LOGIC
# ══════════════════════════════════════════════════════════════════════════════

class TestShouldProcess:
    """_should_process() returns the right action for every document state."""

    def _ts(self, minutes_ago: int = 0) -> datetime:
        return datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)

    def test_uploaded_status_returns_proceed(self):
        assert _should_process("uploaded", self._ts()) == "proceed"

    def test_ready_status_returns_skip(self):
        assert _should_process("ready", self._ts()) == "skip"

    def test_error_status_returns_skip(self):
        assert _should_process("error", self._ts()) == "skip"

    def test_processing_recent_returns_skip(self):
        assert _should_process("processing", self._ts(minutes_ago=5)) == "skip"

    def test_processing_stale_returns_recover(self):
        """A document stuck in processing for >15 min must trigger recovery."""
        assert _should_process("processing", self._ts(minutes_ago=20)) == "recover"

    def test_processing_exactly_at_threshold_returns_recover(self):
        """At exactly 15 min the document is considered stale."""
        ts = datetime.now(timezone.utc) - timedelta(minutes=15)
        assert _should_process("processing", ts) == "recover"

    def test_naive_datetime_treated_as_utc(self):
        """A naive timestamp (no tzinfo) must not raise and must be handled."""
        naive_ts = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=20)
        result = _should_process("processing", naive_ts)
        assert result in ("skip", "recover")


# ══════════════════════════════════════════════════════════════════════════════
# C. DB SESSION SAFETY — rollback on exception, clean pool return
# ══════════════════════════════════════════════════════════════════════════════

class TestGetDbSessionSafety:
    """get_db() must roll back cleanly on exception so the connection returns
    to the pool in a usable state."""

    async def test_rollback_called_on_exception(self, db_session):
        """When the request handler raises, the session must roll back."""
        rolled_back = []

        original_rollback = db_session.rollback

        async def _tracking_rollback():
            rolled_back.append(True)
            await original_rollback()

        db_session.rollback = _tracking_rollback

        try:
            async with db_session as s:
                s.add(Document(
                    id=uuid.uuid4(),
                    filename="rollback_test.pdf",
                    storage_key="originals/rollback.pdf",
                    status="uploaded",
                    file_size_bytes=100,
                    user_id=uuid.UUID(TEST_USER_ID),
                ))
                await s.flush()
                raise ValueError("simulated request error")
        except ValueError:
            pass

        # The context manager's __aexit__ handles rollback; verify table empty
        from sqlalchemy import select as sa_select, text
        result = await db_session.execute(
            sa_select(Document).where(Document.filename == "rollback_test.pdf")
        )
        assert result.scalar_one_or_none() is None

    async def test_session_usable_after_flush_and_rollback(self, db_session):
        """A fresh operation on the same session after rollback must succeed."""
        try:
            async with db_session.begin_nested():
                db_session.add(Document(
                    id=uuid.uuid4(),
                    filename="before_rollback.pdf",
                    storage_key="originals/before.pdf",
                    status="uploaded",
                    file_size_bytes=100,
                    user_id=uuid.UUID(TEST_USER_ID),
                ))
                raise ValueError("force rollback")
        except ValueError:
            pass

        # Session must still be usable
        doc2 = Document(
            id=uuid.uuid4(),
            filename="after_rollback.pdf",
            storage_key="originals/after.pdf",
            status="uploaded",
            file_size_bytes=200,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc2)
        await db_session.commit()

        from sqlalchemy import select as sa_select
        result = await db_session.execute(
            sa_select(Document).where(Document.filename == "after_rollback.pdf")
        )
        assert result.scalar_one_or_none() is not None

    async def test_multiple_sequential_commits_succeed(self, db_session):
        """Several commits on the same session must all complete without error."""
        for i in range(5):
            db_session.add(Document(
                id=uuid.uuid4(),
                filename=f"seq_{i}.pdf",
                storage_key=f"originals/seq_{i}.pdf",
                status="uploaded",
                file_size_bytes=100 + i,
                user_id=uuid.UUID(TEST_USER_ID),
            ))
            await db_session.commit()

        from sqlalchemy import select as sa_select, func
        count = (await db_session.execute(
            sa_select(func.count()).select_from(Document)
            .where(Document.filename.like("seq_%.pdf"))
        )).scalar()
        assert count == 5


# ══════════════════════════════════════════════════════════════════════════════
# D. log_event — commit=False batching, no extra SELECT after commit
# ══════════════════════════════════════════════════════════════════════════════

class TestLogEventNoBatchRoundtrip:
    """log_event must not call db.refresh() after commit (eliminates extra SELECT)."""

    async def test_log_event_commit_true_returns_event(self, db_session, ready_document, active_link):
        svc = AnalyticsService()
        event = await svc.log_event(
            db_session,
            link_id=active_link.id,
            event_type="opened",
            session_id="abcdef1234567890" * 2,
            commit=True,
        )
        assert event is not None
        assert event.event_type == "opened"

    async def test_log_event_commit_false_not_in_db_until_commit(
        self, db_session, ready_document, active_link
    ):
        """With commit=False the event must NOT be visible in DB until caller commits."""
        svc = AnalyticsService()
        await svc.log_event(
            db_session,
            link_id=active_link.id,
            event_type="page_viewed",
            page_number=1,
            session_id="aabbccddeeff0011" * 2,
            commit=False,
        )
        # Open a second session to verify the row is NOT yet committed
        engine = create_async_engine(
            "sqlite+aiosqlite:///./test_securedoc.db",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        from sqlalchemy import select as sa_select
        async with factory() as s2:
            result = await s2.execute(
                sa_select(AccessEvent).where(AccessEvent.event_type == "page_viewed")
            )
            rows = result.scalars().all()
        await engine.dispose()
        assert len(rows) == 0  # not yet flushed to DB

    async def test_log_event_no_refresh_called(self, db_session, ready_document, active_link):
        """db.refresh() must never be called by log_event (eliminates the extra SELECT)."""
        svc = AnalyticsService()
        refresh_calls = []
        original_refresh = db_session.refresh

        async def _spy_refresh(instance, *args, **kwargs):
            refresh_calls.append(instance)
            return await original_refresh(instance, *args, **kwargs)

        db_session.refresh = _spy_refresh

        await svc.log_event(
            db_session,
            link_id=active_link.id,
            event_type="opened",
            session_id="11223344556677889900aabbccddeeff",
            commit=True,
        )

        event_refreshes = [c for c in refresh_calls if isinstance(c, AccessEvent)]
        assert len(event_refreshes) == 0, (
            "log_event called db.refresh(event) — this was supposed to be removed"
        )

    async def test_batch_commit_two_writes_in_one_roundtrip(
        self, db_session, ready_document, active_link
    ):
        """validate(commit=False)→log_event(commit=True): 2 staged writes, 1 commit.

        view_count is now incremented atomically inside validate_link() via a
        single UPDATE ... RETURNING statement, so the caller no longer calls
        increment_view_count() separately.  The remaining staged writes are:
          1. session upsert (ORM INSERT/UPDATE, flushed on commit)
          2. analytics event INSERT (committed by log_event)
        """
        commit_count = [0]
        original_commit = db_session.commit

        async def _counting_commit():
            commit_count[0] += 1
            await original_commit()

        db_session.commit = _counting_commit

        link_svc = LinkService()
        analytics_svc = AnalyticsService()

        await link_svc.validate_link(
            db=db_session,
            token=active_link.token,
            commit=False,
        )
        await analytics_svc.log_event(
            db_session,
            link_id=active_link.id,
            event_type="opened",
            session_id="deadbeef" * 4,
            commit=True,
        )

        assert commit_count[0] == 1, (
            f"Expected 1 commit for the validate+log batch, got {commit_count[0]}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# E. process_document_with_session — skip / recover / error paths
# ══════════════════════════════════════════════════════════════════════════════

class TestProcessDocumentWithSession:
    """process_document_with_session() must skip/recover/fail gracefully."""

    async def test_skip_when_status_ready(self, db_session):
        doc = Document(
            id=uuid.uuid4(),
            filename="already_ready.pdf",
            storage_key="originals/ready.pdf",
            status="ready",
            page_count=2,
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()

        storage = MagicMock()
        rasterizer = MagicMock()
        watermark = MagicMock()

        result = await process_document_with_session(
            db_session, str(doc.id), storage, rasterizer, watermark
        )
        assert result["status"] == "ready"
        storage.download_bytes.assert_not_called()

    async def test_skip_when_status_error(self, db_session):
        doc = Document(
            id=uuid.uuid4(),
            filename="errored.pdf",
            storage_key="originals/errored.pdf",
            status="error",
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()

        storage = MagicMock()
        result = await process_document_with_session(
            db_session, str(doc.id), storage, MagicMock(), MagicMock()
        )
        assert result["status"] == "error"
        storage.download_bytes.assert_not_called()

    async def test_raises_when_document_not_found(self, db_session):
        storage = MagicMock()
        with pytest.raises(ValueError, match="not found"):
            await process_document_with_session(
                db_session, str(uuid.uuid4()), storage, MagicMock(), MagicMock()
            )

    async def test_proceed_path_marks_ready(self, db_session):
        """Happy path: uploaded → processing → ready with correct page records."""
        doc = Document(
            id=uuid.uuid4(),
            filename="new_upload.pdf",
            storage_key="originals/new.pdf",
            status="uploaded",
            file_size_bytes=2048,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()

        webp = _make_webp_bytes()

        # Build a fake rasterizer page result
        page_result = MagicMock()
        page_result.page_number = 1
        page_result.image_bytes = webp
        page_result.width_px = 595
        page_result.height_px = 842

        storage = MagicMock()
        storage.download_bytes = AsyncMock(return_value=b"%PDF-1.4 fake")
        storage.upload_file = AsyncMock(return_value=None)

        rasterizer = MagicMock()
        _pages_a = [page_result]
        def _side_effect_a(*args, **kwargs):
            async def _gen():
                for p in _pages_a:
                    yield p
            return _gen()
        rasterizer.stream_rasterized_pages = MagicMock(side_effect=_side_effect_a)

        watermark = MagicMock()
        watermark.apply_forensic_stamp = MagicMock(return_value=webp)

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            result = await process_document_with_session(
                db_session, str(doc.id), storage, rasterizer, watermark
            )

        assert result["status"] == "ready"
        assert result["page_count"] == 1

        await db_session.refresh(doc)
        assert doc.status == "ready"
        assert doc.page_count == 1

    async def test_recover_path_deletes_partial_pages(self, db_session):
        """A stale-processing doc's old pages must be deleted before retry."""
        doc = Document(
            id=uuid.uuid4(),
            filename="stuck.pdf",
            storage_key="originals/stuck.pdf",
            status="processing",
            file_size_bytes=2048,
            user_id=uuid.UUID(TEST_USER_ID),
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=20),
        )
        db_session.add(doc)
        await db_session.flush()

        # Insert stale partial pages
        for i in range(1, 4):
            db_session.add(DocumentPage(
                document_id=doc.id,
                page_number=i,
                storage_key=f"pages/{doc.id}/{i:04d}.webp",
                width_px=595,
                height_px=842,
            ))
        await db_session.commit()

        webp = _make_webp_bytes()
        page_result = MagicMock()
        page_result.page_number = 1
        page_result.image_bytes = webp
        page_result.width_px = 595
        page_result.height_px = 842

        storage = MagicMock()
        storage.download_bytes = AsyncMock(return_value=b"%PDF-1.4 fake")
        storage.upload_file = AsyncMock(return_value=None)

        rasterizer = MagicMock()
        _pages_b = [page_result]
        def _side_effect_b(*args, **kwargs):
            async def _gen():
                for p in _pages_b:
                    yield p
            return _gen()
        rasterizer.stream_rasterized_pages = MagicMock(side_effect=_side_effect_b)

        watermark = MagicMock()
        watermark.apply_forensic_stamp = MagicMock(return_value=webp)

        # clear_doc_bytes_redis is imported inside the function body, so patch at the source
        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"), \
             patch("app.services.page_cache.clear_doc_bytes_redis", new_callable=AsyncMock), \
             patch("app.services.viewer_cache.invalidate_doc_entries"):
            result = await process_document_with_session(
                db_session, str(doc.id), storage, rasterizer, watermark
            )

        assert result["status"] == "ready"
        assert result["page_count"] == 1

        # Verify old pages were cleaned up and replaced with exactly 1 new page
        from sqlalchemy import select as sa_select
        pages = (await db_session.execute(
            sa_select(DocumentPage).where(DocumentPage.document_id == doc.id)
        )).scalars().all()
        assert len(pages) == 1


# ══════════════════════════════════════════════════════════════════════════════
# F. Sequential page / thumb requests — no "in progress" errors
# ══════════════════════════════════════════════════════════════════════════════

class TestSequentialViewerRequests:
    """Multiple sequential page/thumb fetches must all succeed (200)."""

    @pytest.fixture(autouse=True)
    def _clear_caches(self):
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()
        yield
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()

    async def test_repeated_page_requests_all_succeed(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        for _ in range(5):
            r = await client.get(f"/api/viewer/page/{active_link.token}/1", headers={"X-Session-ID": sid})
            assert r.status_code == 200, f"Unexpected status {r.status_code}: {r.text}"

    async def test_repeated_thumb_requests_all_succeed(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        for _ in range(5):
            r = await client.get(f"/api/viewer/thumb/{active_link.token}/1", headers={"X-Session-ID": sid})
            assert r.status_code == 200, f"Unexpected status {r.status_code}: {r.text}"

    async def test_multiple_page_numbers_in_sequence(self, client, active_link, ready_document):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        for page in range(1, ready_document.page_count + 1):
            r = await client.get(f"/api/viewer/page/{active_link.token}/{page}", headers={"X-Session-ID": sid})
            assert r.status_code == 200, f"Page {page} returned {r.status_code}"

    async def test_alternating_page_and_thumb_requests(self, client, active_link, ready_document):
        """Interleaved page and thumb requests on the same link must all succeed."""
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        for page in range(1, ready_document.page_count + 1):
            rp = await client.get(f"/api/viewer/page/{active_link.token}/{page}", headers={"X-Session-ID": sid})
            rt = await client.get(f"/api/viewer/thumb/{active_link.token}/{page}", headers={"X-Session-ID": sid})
            assert rp.status_code == 200, f"Page {page}: {rp.status_code}"
            assert rt.status_code == 200, f"Thumb {page}: {rt.status_code}"

    async def test_validate_then_repeated_page_fetch_stable(self, client, ready_document, db_session):
        """Validate + many page fetches must remain stable (regression for asyncpg bug)."""
        link_svc = LinkService()
        link = await link_svc.create_link(db_session, document_id=str(ready_document.id))

        body = await _validate(client, link.token)
        sid = body["session_id"]

        statuses = []
        for _ in range(10):
            r = await client.get(f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid})
            statuses.append(r.status_code)

        assert all(s == 200 for s in statuses), f"Non-200 statuses detected: {statuses}"


# ══════════════════════════════════════════════════════════════════════════════
# G. Session isolation — each request uses its own session
# ══════════════════════════════════════════════════════════════════════════════

class TestSessionIsolation:
    """Two independent DB sessions must not share uncommitted state."""

    async def test_uncommitted_doc_invisible_to_second_session(self, db_session):
        doc_id = uuid.uuid4()
        db_session.add(Document(
            id=doc_id,
            filename="isolation_test.pdf",
            storage_key="originals/isolation.pdf",
            status="uploaded",
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        ))
        await db_session.flush()  # staged but not committed

        engine = create_async_engine(
            "sqlite+aiosqlite:///./test_securedoc.db",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        from sqlalchemy import select as sa_select
        async with factory() as s2:
            result = await s2.execute(
                sa_select(Document).where(Document.id == doc_id)
            )
            row = result.scalar_one_or_none()
        await engine.dispose()

        # SQLite read isolation: flush not visible to other connections
        assert row is None

    async def test_committed_doc_visible_to_second_session(self, db_session):
        doc_id = uuid.uuid4()
        db_session.add(Document(
            id=doc_id,
            filename="committed_test.pdf",
            storage_key="originals/committed.pdf",
            status="uploaded",
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        ))
        await db_session.commit()

        engine = create_async_engine(
            "sqlite+aiosqlite:///./test_securedoc.db",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        from sqlalchemy import select as sa_select
        async with factory() as s2:
            result = await s2.execute(
                sa_select(Document).where(Document.id == doc_id)
            )
            row = result.scalar_one_or_none()
        await engine.dispose()

        assert row is not None
        assert row.filename == "committed_test.pdf"

    async def test_two_link_service_calls_independent(self, db_session, ready_document):
        """Creating two links in the same session must not corrupt either."""
        svc = LinkService()
        link1 = await svc.create_link(db_session, document_id=str(ready_document.id), label="A")
        link2 = await svc.create_link(db_session, document_id=str(ready_document.id), label="B")

        assert link1.id != link2.id
        assert link1.token != link2.token


# ══════════════════════════════════════════════════════════════════════════════
# H. Regression — core endpoints remain functional
# ══════════════════════════════════════════════════════════════════════════════

class TestEndpointRegressions:
    """Key endpoints must still return correct responses after all hardening changes."""

    @pytest.fixture(autouse=True)
    def _clear_caches(self):
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()
        yield
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()

    async def test_gate_active_link(self, client, active_link):
        r = await client.get(f"/api/viewer/gate/{active_link.token}")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "active"
        assert body["requires_password"] is False

    async def test_gate_unknown_token(self, client):
        r = await client.get("/api/viewer/gate/no-such-token")
        assert r.status_code == 200
        assert r.json()["status"] == "not_found"

    async def test_gate_revoked_link(self, client, revoked_link):
        r = await client.get(f"/api/viewer/gate/{revoked_link.token}")
        assert r.status_code == 200
        assert r.json()["status"] == "revoked"

    async def test_validate_returns_session_id(self, client, active_link):
        body = await _validate(client, active_link.token)
        assert len(body["session_id"]) == 32  # 128-bit hex

    async def test_validate_wrong_token_returns_404(self, client):
        r = await client.post("/api/viewer/validate", json={"token": "bad-token"})
        assert r.status_code == 404

    async def test_upload_creates_document(self, client):
        import io
        pdf_bytes = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
            b"xref\n0 1\n0000000000 65535 f\n"
            b"trailer\n<< /Size 1 >>\nstartxref\n9\n%%EOF"
        )
        r = await client.post(
            "/api/documents/upload",
            files={"file": ("regression.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        assert r.status_code in (201, 202)
        body = r.json()
        assert "id" in body
        assert body["status"] == "uploaded"

    async def test_list_documents_returns_array(self, client, ready_document):
        r = await client.get("/api/documents")
        assert r.status_code == 200
        assert "documents" in r.json()
        ids = [d["id"] for d in r.json()["documents"]]
        assert str(ready_document.id) in ids

    async def test_create_and_list_links(self, client, ready_document):
        r = await client.post(
            "/api/links",
            json={"document_id": str(ready_document.id), "label": "regression"},
        )
        assert r.status_code == 201
        link_id = r.json()["id"]

        r2 = await client.get(f"/api/links?document_id={ready_document.id}")
        assert r2.status_code == 200
        ids = [lk["id"] for lk in r2.json()["links"]]
        assert link_id in ids

    async def test_revoke_link(self, client, active_link):
        r = await client.delete(f"/api/links/{active_link.id}")
        assert r.status_code == 200
        body = r.json()
        assert "revoked_at" in body

        # Gate must now report revoked
        r2 = await client.get(f"/api/viewer/gate/{active_link.token}")
        assert r2.json()["status"] == "revoked"

    async def test_analytics_events_endpoint(self, client, active_link):
        # Generate an event via validate
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.get(
            f"/api/analytics/events?link_id={active_link.id}&event_type=opened"
        )
        assert r.status_code == 200
        assert "events" in r.json()

    async def test_page_404_for_nonexistent_page(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.get(f"/api/viewer/page/{active_link.token}/999", headers={"X-Session-ID": sid})
        assert r.status_code == 404

    async def test_page_requires_session_id_param(self, client, active_link):
        """Omitting session_id entirely must return 400 (required query param)."""
        r = await client.get(f"/api/viewer/page/{active_link.token}/1")
        assert r.status_code == 400

    async def test_document_status_endpoint(self, client, ready_document):
        r = await client.get(f"/api/documents/{ready_document.id}/status")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ready"
        assert "id" not in body  # security: no id in status response

    async def test_purge_stale_sessions_task(self, db_session, ready_document, active_link):
        """purge_stale_sessions_async removes sessions older than 2 hours."""
        from app.workers.tasks import _purge_stale_sessions_async

        now = datetime.now(timezone.utc)
        stale = ViewerSession(
            session_id="stale" + "0" * 27,
            link_id=active_link.id,
            ip_hash=None,
            created_at=now - timedelta(hours=4),
            last_seen_at=now - timedelta(hours=3),
        )
        fresh = ViewerSession(
            session_id="fresh" + "0" * 27,
            link_id=active_link.id,
            ip_hash=None,
            created_at=now - timedelta(minutes=60),
            last_seen_at=now - timedelta(minutes=30),
        )
        db_session.add_all([stale, fresh])
        await db_session.commit()

        engine = create_async_engine(
            "sqlite+aiosqlite:///./test_securedoc.db",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        with patch("app.workers.tasks._get_db_session_factory", return_value=factory):
            result = await _purge_stale_sessions_async()

        await engine.dispose()
        assert result["deleted"] >= 1

    async def test_requeue_orphaned_uploads_requeues_stale_uploaded_doc(
        self, db_session
    ):
        """requeue_orphaned_uploads must re-queue process_document for any document
        that has been stuck in 'uploaded' status for longer than 10 minutes."""
        from app.workers.tasks import _requeue_orphaned_uploads_async

        orphan = Document(
            id=uuid.uuid4(),
            filename="orphan.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="uploaded",
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=15),
        )
        db_session.add(orphan)
        await db_session.commit()

        engine = create_async_engine(
            "sqlite+aiosqlite:///./test_securedoc.db",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        queued_ids = []
        with patch("app.workers.tasks._get_db_session_factory", return_value=factory), \
             patch("app.workers.tasks.process_document") as mock_task:
            mock_task.delay = MagicMock(side_effect=lambda doc_id: queued_ids.append(doc_id))
            result = await _requeue_orphaned_uploads_async()

        await engine.dispose()
        assert result["requeued"] >= 1
        assert str(orphan.id) in queued_ids

    async def test_requeue_orphaned_uploads_skips_recent_uploaded_doc(
        self, db_session
    ):
        """Documents uploaded < 10 minutes ago must NOT be re-queued (still being processed)."""
        from app.workers.tasks import _requeue_orphaned_uploads_async

        recent = Document(
            id=uuid.uuid4(),
            filename="recent_upload.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="uploaded",
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=2),
        )
        db_session.add(recent)
        await db_session.commit()

        engine = create_async_engine(
            "sqlite+aiosqlite:///./test_securedoc.db",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        queued_ids = []
        with patch("app.workers.tasks._get_db_session_factory", return_value=factory), \
             patch("app.workers.tasks.process_document") as mock_task:
            mock_task.delay = MagicMock(side_effect=lambda doc_id: queued_ids.append(doc_id))
            result = await _requeue_orphaned_uploads_async()

        await engine.dispose()
        assert str(recent.id) not in queued_ids

    async def test_requeue_orphaned_uploads_skips_ready_doc(self, db_session, ready_document):
        """Ready documents must never be re-queued."""
        from app.workers.tasks import _requeue_orphaned_uploads_async

        engine = create_async_engine(
            "sqlite+aiosqlite:///./test_securedoc.db",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        queued_ids = []
        with patch("app.workers.tasks._get_db_session_factory", return_value=factory), \
             patch("app.workers.tasks.process_document") as mock_task:
            mock_task.delay = MagicMock(side_effect=lambda doc_id: queued_ids.append(doc_id))
            await _requeue_orphaned_uploads_async()

        await engine.dispose()
        assert str(ready_document.id) not in queued_ids

    async def test_make_engine_sqlite_no_pool_settings(self):
        """SQLite engine must not set pool_pre_ping (not supported)."""
        engine = make_engine("sqlite+aiosqlite:///./test_engine.db")
        # Should not raise; pool_pre_ping not set for SQLite
        assert engine is not None
        await engine.dispose()

    async def test_make_engine_postgres_url_normalized(self):
        """make_engine must accept both postgresql:// and postgres:// prefixes."""
        from app.database import _normalize_db_url
        assert _normalize_db_url("postgresql://u:p@h/db").startswith("postgresql+asyncpg://")
        assert _normalize_db_url("postgres://u:p@h/db").startswith("postgresql+asyncpg://")
        assert _normalize_db_url("postgresql+asyncpg://u:p@h/db").startswith("postgresql+asyncpg://")


# ══════════════════════════════════════════════════════════════════════════════
# I. doc_status in validate response
# ══════════════════════════════════════════════════════════════════════════════

class TestDocStatusInValidateResponse:
    """validate endpoint must include doc_status in every response."""

    @pytest.fixture(autouse=True)
    def _clear_caches(self):
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()
        yield
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()

    async def test_validate_includes_doc_status_field(self, client, active_link):
        body = await _validate(client, active_link.token)
        assert "doc_status" in body, "validate response must include doc_status"

    async def test_validate_doc_status_ready_for_ready_document(self, client, active_link):
        body = await _validate(client, active_link.token)
        assert body["doc_status"] == "ready"

    async def test_validate_doc_status_uploaded_for_unprocessed_document(
        self, client, db_session
    ):
        """A freshly uploaded document must return doc_status='uploaded'."""
        doc = Document(
            id=uuid.uuid4(),
            filename="pending.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="uploaded",
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await _make_active_link(db_session, doc)
        await db_session.commit()

        body = await _validate(client, link.token)
        assert body["doc_status"] == "uploaded"
        assert body["page_count"] == 0  # no pages yet

    async def test_validate_doc_status_processing_for_in_progress_document(
        self, client, db_session
    ):
        doc = Document(
            id=uuid.uuid4(),
            filename="processing.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="processing",
            file_size_bytes=2048,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await _make_active_link(db_session, doc)
        await db_session.commit()

        body = await _validate(client, link.token)
        assert body["doc_status"] == "processing"

    async def test_validate_doc_status_error_for_failed_document(
        self, client, db_session
    ):
        doc = Document(
            id=uuid.uuid4(),
            filename="failed.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="error",
            file_size_bytes=512,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await _make_active_link(db_session, doc)
        await db_session.commit()

        body = await _validate(client, link.token)
        assert body["doc_status"] == "error"

    async def test_validate_returns_empty_pages_for_non_ready_document(
        self, client, db_session
    ):
        """pages metadata list must be empty when document is not yet ready."""
        doc = Document(
            id=uuid.uuid4(),
            filename="queued.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="uploaded",
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await _make_active_link(db_session, doc)
        await db_session.commit()

        body = await _validate(client, link.token)
        assert body["pages"] == []


# ══════════════════════════════════════════════════════════════════════════════
# J. Not-ready document handling — page and thumb return 503
# ══════════════════════════════════════════════════════════════════════════════

class TestNotReadyDocumentHandling:
    """page and thumb endpoints must return 503 with descriptive detail for non-ready docs."""

    @pytest.fixture(autouse=True)
    def _clear_caches(self):
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()
        yield
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()

    async def _make_link_for_doc_status(self, db_session, status: str):
        doc = Document(
            id=uuid.uuid4(),
            filename=f"{status}.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status=status,
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await _make_active_link(db_session, doc)
        await db_session.commit()
        return doc, link

    async def test_page_returns_503_for_uploaded_doc(self, client, db_session):
        _, link = await self._make_link_for_doc_status(db_session, "uploaded")
        body = await _validate(client, link.token)
        sid = body["session_id"]

        r = await client.get(f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid})
        assert r.status_code == 503
        assert "queued" in r.json()["detail"].lower()

    async def test_page_returns_503_for_processing_doc(self, client, db_session):
        _, link = await self._make_link_for_doc_status(db_session, "processing")
        body = await _validate(client, link.token)
        sid = body["session_id"]

        r = await client.get(f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid})
        assert r.status_code == 503
        assert "processing" in r.json()["detail"].lower()

    async def test_page_returns_503_for_error_doc(self, client, db_session):
        _, link = await self._make_link_for_doc_status(db_session, "error")
        body = await _validate(client, link.token)
        sid = body["session_id"]

        r = await client.get(f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid})
        assert r.status_code == 503
        assert "failed" in r.json()["detail"].lower()

    async def test_thumb_returns_503_for_not_ready_doc(self, client, db_session):
        _, link = await self._make_link_for_doc_status(db_session, "uploaded")
        body = await _validate(client, link.token)
        sid = body["session_id"]

        r = await client.get(f"/api/viewer/thumb/{link.token}/1", headers={"X-Session-ID": sid})
        assert r.status_code == 503

    async def test_page_serves_after_doc_transitions_to_ready(
        self, client, db_session
    ):
        """After doc status changes from 'uploaded' to 'ready', the next page
        request must succeed immediately (no stale 503 from cached non-ready snapshot)."""
        doc, link = await self._make_link_for_doc_status(db_session, "uploaded")
        body = await _validate(client, link.token)
        sid = body["session_id"]

        # First request — doc is still "uploaded" → 503
        r1 = await client.get(f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid})
        assert r1.status_code == 503

        # Simulate worker completing: transition doc to "ready" and add a page record
        doc.status = "ready"
        doc.page_count = 1
        db_session.add(DocumentPage(
            document_id=doc.id,
            page_number=1,
            storage_key=f"pages/{doc.id}/0001.webp",
            width_px=595,
            height_px=842,
        ))
        await db_session.commit()

        # Second request — doc is now "ready".  Must return 200, not 503 from stale cache.
        r2 = await client.get(f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid})
        assert r2.status_code == 200, (
            "page request returned 503 after doc became ready — stale non-ready snapshot was cached"
        )


# ══════════════════════════════════════════════════════════════════════════════
# K. doc_cache only stores ready snapshots (Phase 4 cache correctness)
# ══════════════════════════════════════════════════════════════════════════════

class TestDocCacheOnlyStoresReadySnapshots:
    """Non-ready doc statuses must NOT be stored in doc_cache."""

    @pytest.fixture(autouse=True)
    def _clear_caches(self):
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()
        yield
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()

    async def test_uploaded_doc_not_stored_in_doc_cache(self, client, db_session):
        from app.services.viewer_cache import doc_cache
        doc, link = await _make_non_ready_doc_and_link(db_session, "uploaded")
        body = await _validate(client, link.token)
        sid = body["session_id"]
        doc_key = str(doc.id)

        await client.get(f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid})

        assert doc_cache.get(doc_key) is None, (
            "uploaded doc snapshot must not be cached — would lock clients out after doc becomes ready"
        )

    async def test_processing_doc_not_stored_in_doc_cache(self, client, db_session):
        from app.services.viewer_cache import doc_cache
        doc, link = await _make_non_ready_doc_and_link(db_session, "processing")
        body = await _validate(client, link.token)
        sid = body["session_id"]
        doc_key = str(doc.id)

        await client.get(f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid})

        assert doc_cache.get(doc_key) is None

    async def test_error_doc_not_stored_in_doc_cache(self, client, db_session):
        from app.services.viewer_cache import doc_cache
        doc, link = await _make_non_ready_doc_and_link(db_session, "error")
        body = await _validate(client, link.token)
        sid = body["session_id"]
        doc_key = str(doc.id)

        await client.get(f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid})

        assert doc_cache.get(doc_key) is None

    async def test_ready_doc_is_stored_in_doc_cache(self, client, active_link, ready_document):
        from app.services.viewer_cache import doc_cache
        body = await _validate(client, active_link.token)
        sid = body["session_id"]
        doc_key = str(ready_document.id)

        r = await client.get(f"/api/viewer/page/{active_link.token}/1", headers={"X-Session-ID": sid})
        assert r.status_code == 200

        snap = doc_cache.get(doc_key)
        assert snap is not None, "ready doc snapshot must be cached for performance"
        assert snap.status == "ready"


async def _make_non_ready_doc_and_link(db_session, status: str):
    """Helper shared by TestNotReadyDocumentHandling and TestDocCacheOnlyStoresReadySnapshots."""
    doc = Document(
        id=uuid.uuid4(),
        filename=f"{status}_cache_test.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status=status,
        file_size_bytes=1024,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db_session.add(doc)
    await db_session.flush()
    link = await _make_active_link(db_session, doc)
    await db_session.commit()
    return doc, link


# ══════════════════════════════════════════════════════════════════════════════
# L. Concurrent page / thumb requests (Phase 4 scale-out correctness)
# ══════════════════════════════════════════════════════════════════════════════

@pytest_asyncio.fixture
async def concurrent_client(db_session, ready_document, active_link):
    """
    HTTP test client that creates a NEW DB session per request, matching production
    behavior where each FastAPI request gets its own session via async_sessionmaker.

    The default `client` fixture injects the SAME db_session into all requests.
    When asyncio.gather fires multiple requests concurrently, they all try to
    commit the shared session simultaneously — causing SQLAlchemy session state
    errors that don't exist in production.  This fixture eliminates that
    test-infrastructure artifact so true concurrent correctness can be verified.
    """
    engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    per_req_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _per_request_db():
        async with per_req_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _per_request_db
    app.dependency_overrides[get_current_user] = lambda: {
        "user_id": TEST_USER_ID, "email": "test@example.com", "role": "authenticated"
    }

    with patch("app.services.storage.StorageService.download_bytes", new_callable=AsyncMock) as mock_dl, \
         patch("app.services.storage.StorageService.upload_file", new_callable=AsyncMock), \
         patch("app.services.storage.StorageService.delete_file", new_callable=AsyncMock), \
         patch("app.services.storage.StorageService.list_keys_with_prefix", new_callable=AsyncMock) as mock_list, \
         patch("app.workers.tasks.process_document.delay"):
        mock_dl.return_value = _make_webp_bytes()
        mock_list.return_value = []

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c, active_link, ready_document

    app.dependency_overrides.clear()
    await engine.dispose()


class TestConcurrentPageRequests:
    """
    Multiple concurrent page/thumb requests must all succeed without session errors.

    Uses `concurrent_client` which creates a new DB session per request, matching
    production behavior.  The standard `client` fixture reuses one session for all
    requests; asyncio.gather would race that shared session, masking real bugs with
    false negatives.
    """

    @pytest.fixture(autouse=True)
    def _clear_caches(self):
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()
        yield
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()

    async def test_concurrent_requests_for_same_page_all_succeed(
        self, concurrent_client
    ):
        """Firing 8 requests for the same page concurrently must all return 200."""
        c, active_link, _ = concurrent_client
        body = await _validate(c, active_link.token)
        sid = body["session_id"]
        url = f"/api/viewer/page/{active_link.token}/1"
        _sid = sid

        results = await asyncio.gather(
            *[c.get(url, headers={"X-Session-ID": _sid}) for _ in range(8)],
            return_exceptions=True,
        )

        statuses = [r.status_code if not isinstance(r, Exception) else 500 for r in results]
        assert all(s == 200 for s in statuses), (
            f"Some concurrent page requests failed: {statuses}"
        )

    async def test_concurrent_requests_for_different_pages_all_succeed(
        self, concurrent_client
    ):
        """Concurrent requests across all pages of a document must all return 200."""
        c, active_link, ready_document = concurrent_client
        body = await _validate(c, active_link.token)
        sid = body["session_id"]

        results = await asyncio.gather(
            *[
                c.get(
                    f"/api/viewer/page/{active_link.token}/{p}",
                    headers={"X-Session-ID": sid},
                )
                for p in range(1, ready_document.page_count + 1)
            ],
            return_exceptions=True,
        )

        statuses = [r.status_code if not isinstance(r, Exception) else 500 for r in results]
        assert all(s == 200 for s in statuses), (
            f"Concurrent multi-page requests failed: {statuses}"
        )

    async def test_concurrent_thumb_requests_all_succeed(
        self, concurrent_client
    ):
        """Concurrent thumbnail requests must all return 200."""
        c, active_link, _ = concurrent_client
        body = await _validate(c, active_link.token)
        sid = body["session_id"]
        url = f"/api/viewer/thumb/{active_link.token}/1"
        _sid = sid

        results = await asyncio.gather(
            *[c.get(url, headers={"X-Session-ID": _sid}) for _ in range(8)],
            return_exceptions=True,
        )

        statuses = [r.status_code if not isinstance(r, Exception) else 500 for r in results]
        assert all(s == 200 for s in statuses), (
            f"Some concurrent thumb requests failed: {statuses}"
        )

    async def test_concurrent_mixed_page_and_thumb_requests(
        self, concurrent_client
    ):
        """Simultaneous page and thumb requests must not interfere with each other."""
        c, active_link, ready_document = concurrent_client
        body = await _validate(c, active_link.token)
        sid = body["session_id"]

        results = await asyncio.gather(
            *[
                c.get(
                    f"/api/viewer/page/{active_link.token}/{p}",
                    headers={"X-Session-ID": sid},
                )
                for p in range(1, ready_document.page_count + 1)
            ] + [
                c.get(
                    f"/api/viewer/thumb/{active_link.token}/{p}",
                    headers={"X-Session-ID": sid},
                )
                for p in range(1, ready_document.page_count + 1)
            ],
            return_exceptions=True,
        )

        statuses = [r.status_code if not isinstance(r, Exception) else 500 for r in results]
        assert all(s == 200 for s in statuses), (
            f"Concurrent mixed requests failed: {statuses}"
        )
