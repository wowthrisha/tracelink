"""
Phase C1 Production Readiness Tests.

Covers:
  A. Migration 012 — composite index on access_events(link_id, created_at)
  B. Analytics query correctness (count query fix, pagination)
  C. Worker configuration settings
  D. PDF download page limit (memory safety)
  E. Production startup validation (HSTS warning)
  F. Documents index (status + updated_at)
"""
import pathlib
import uuid
import importlib.util

import pytest

REPO_ROOT = pathlib.Path("/Users/thrisha/traceview/securedoc")
MIGRATIONS_DIR = REPO_ROOT / "backend" / "alembic" / "versions"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"


# ── A. Migration 012 ──────────────────────────────────────────────────────────

class TestMigration012:
    def _load_migration(self):
        path = MIGRATIONS_DIR / "012_analytics_performance_index.py"
        assert path.exists(), "Migration 012 file must exist"
        spec = importlib.util.spec_from_file_location("migration_012", path)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_migration_file_exists(self):
        assert (MIGRATIONS_DIR / "012_analytics_performance_index.py").exists()

    def test_revision_chain(self):
        m = self._load_migration()
        assert m.revision == "012"
        assert m.down_revision == "011"

    def test_upgrade_creates_composite_index(self):
        """Migration upgrade must create ix_access_events_link_id_created."""
        m = self._load_migration()
        import inspect
        source = inspect.getsource(m.upgrade)
        assert "ix_access_events_link_id_created" in source
        assert "access_events" in source
        assert "link_id" in source
        assert "created_at" in source

    def test_upgrade_creates_documents_status_index(self):
        """Migration upgrade must create ix_documents_status_updated."""
        m = self._load_migration()
        import inspect
        source = inspect.getsource(m.upgrade)
        assert "ix_documents_status_updated" in source
        assert "documents" in source

    def test_downgrade_removes_both_indexes(self):
        """Migration downgrade must drop both indexes it created."""
        m = self._load_migration()
        import inspect
        source = inspect.getsource(m.downgrade)
        assert "ix_access_events_link_id_created" in source
        assert "ix_documents_status_updated" in source

    def test_no_existing_index_duplication(self):
        """The composite index name must not duplicate the existing single-column index."""
        m = self._load_migration()
        import inspect
        source = inspect.getsource(m.upgrade)
        # The existing single-column index is ix_access_events_link_id
        # The new composite index must have a different name
        assert "ix_access_events_link_id_created" in source
        # Verify it is not trying to recreate the existing single-column index
        assert source.count("ix_access_events_link_id\n") == 0  # not exact match

    @pytest.mark.asyncio
    async def test_index_covers_analytics_query_pattern(self, db_session):
        """The access_events table must have the link_id foreign key for index coverage."""
        from app.models.event import AccessEvent
        # Verify the model has link_id column (prerequisite for composite index)
        assert hasattr(AccessEvent, "link_id")
        assert hasattr(AccessEvent, "created_at")


# ── B. Analytics query correctness ───────────────────────────────────────────

class TestAnalyticsQueryFix:
    @pytest.mark.asyncio
    async def test_get_events_returns_correct_total(self, client):
        """GET /api/analytics/events must return accurate total count."""
        r = await client.get("/api/analytics/events")
        assert r.status_code == 200
        body = r.json()
        assert "events" in body
        assert "total" in body
        assert isinstance(body["total"], int)
        assert body["total"] >= 0

    @pytest.mark.asyncio
    async def test_get_events_pagination_respects_limit(self, client):
        """Paginated events must respect the limit parameter."""
        r = await client.get("/api/analytics/events?limit=5&offset=0")
        assert r.status_code == 200
        body = r.json()
        assert len(body["events"]) <= 5

    @pytest.mark.asyncio
    async def test_get_events_count_does_not_use_subquery(self):
        """The count query must not use a subquery over the paginated result set."""
        import inspect
        import app.routers.analytics as analytics_module
        source = inspect.getsource(analytics_module.get_events)
        # The old code: sa_select(func.count()).select_from(query.subquery())
        # The new code: select(func.count()).select_from(AccessEvent).where(...)
        assert "query.subquery()" not in source, (
            "Count query must not wrap the paginated SELECT in a subquery. "
            "Use a direct COUNT on the filtered table instead."
        )

    @pytest.mark.asyncio
    async def test_get_events_total_matches_unfiltered_count(self, client, db_session):
        """total in GET /api/analytics/events must match actual row count for user's links."""
        from app.models.document import Document
        from app.models.link import ShareLink
        from app.models.event import AccessEvent

        # Create doc + link
        doc = Document(
            id=uuid.uuid4(), filename="count_test.pdf",
            storage_key="originals/count_test.pdf",
            status="ready", page_count=1,
            file_size_bytes=100,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()

        link = ShareLink(
            id=uuid.uuid4(),
            document_id=doc.id,
            token=f"count-test-token-{uuid.uuid4().hex[:8]}",
            view_count=0,
        )
        db_session.add(link)
        await db_session.flush()

        # Add 3 events
        for _ in range(3):
            ev = AccessEvent(
                id=uuid.uuid4(),
                link_id=link.id,
                event_type="opened",
            )
            db_session.add(ev)
        await db_session.commit()

        r = await client.get(f"/api/analytics/events?document_id={doc.id}&limit=50")
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 3
        assert len(body["events"]) == 3


# ── C. Worker configuration settings ─────────────────────────────────────────

class TestWorkerConfig:
    def test_worker_concurrency_has_default(self):
        """Settings must have a worker_concurrency field with a sensible default."""
        from app.config import Settings
        s = Settings()
        assert hasattr(s, "worker_concurrency")
        assert isinstance(s.worker_concurrency, int)
        assert s.worker_concurrency >= 1

    def test_worker_max_tasks_per_child_has_default(self):
        """Settings must have worker_max_tasks_per_child field."""
        from app.config import Settings
        s = Settings()
        assert hasattr(s, "worker_max_tasks_per_child")
        assert isinstance(s.worker_max_tasks_per_child, int)
        assert s.worker_max_tasks_per_child >= 0

    def test_worker_concurrency_env_override(self, monkeypatch):
        """WORKER_CONCURRENCY env var must override the default."""
        import app.config as config_module
        monkeypatch.setenv("WORKER_CONCURRENCY", "6")
        # Force fresh settings read
        from pydantic_settings import BaseSettings
        s = config_module.Settings()
        assert s.worker_concurrency == 6

    def test_max_download_pages_pdf_has_default(self):
        """Settings must have max_download_pages_pdf field."""
        from app.config import Settings
        s = Settings()
        assert hasattr(s, "max_download_pages_pdf")
        assert isinstance(s.max_download_pages_pdf, int)

    def test_default_worker_concurrency_is_conservative(self):
        """Default worker concurrency must be ≤ 4 to prevent OOM on small containers."""
        from app.config import Settings
        s = Settings()
        assert s.worker_concurrency <= 4, (
            f"Default worker_concurrency={s.worker_concurrency} is too high for a default. "
            "Use 2 for development safety; increase in production via WORKER_CONCURRENCY env var."
        )

    def test_env_example_documents_worker_concurrency(self):
        """The .env.example must document WORKER_CONCURRENCY."""
        env_example = (REPO_ROOT / "backend" / ".env.example").read_text()
        assert "WORKER_CONCURRENCY" in env_example
        assert "WORKER_MAX_TASKS_PER_CHILD" in env_example


# ── D. PDF download page limit ────────────────────────────────────────────────

class TestDownloadPageLimit:
    @pytest.mark.asyncio
    async def test_download_enforces_page_limit(self, client, db_session):
        """PDF download must return 413 when page count exceeds max_download_pages_pdf."""
        from app.models.document import Document
        from app.models.link import ShareLink
        from app.models.session import ViewerSession
        from unittest.mock import patch

        # Create a doc with page_count exceeding the limit
        doc = Document(
            id=uuid.uuid4(), filename="big.pdf",
            storage_key="originals/big.pdf",
            status="ready", page_count=200,  # exceeds default limit of 100
            file_size_bytes=1000,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()

        link = ShareLink(
            id=uuid.uuid4(),
            document_id=doc.id,
            token=f"big-pdf-token-{uuid.uuid4().hex[:8]}",
            view_count=0,
            permissions='{"can_download": true}',
        )
        db_session.add(link)
        await db_session.flush()

        session_id = "a" * 32
        vs = ViewerSession(
            session_id=session_id,
            link_id=link.id,
            created_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            last_seen_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
        db_session.add(vs)
        await db_session.commit()

        # Patch settings to ensure limit is set to 100
        with patch("app.routers.viewer.settings") as mock_settings:
            mock_settings.max_download_pages_pdf = 100
            mock_settings.max_concurrent_sessions_per_link = 50

            r = await client.get(
                f"/api/viewer/download/{link.token}",
                params={"session_id": session_id},
            )

        assert r.status_code == 413, (
            f"Expected 413 for oversized PDF download, got {r.status_code}: {r.text}"
        )
        assert "100" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_download_zero_limit_disables_check(self, client, db_session):
        """When max_download_pages_pdf=0, page limit check must be skipped."""
        from app.models.document import Document
        from app.models.link import ShareLink
        from app.models.session import ViewerSession
        from unittest.mock import patch, AsyncMock
        import datetime

        doc = Document(
            id=uuid.uuid4(), filename="nolimit.pdf",
            storage_key="originals/nolimit.pdf",
            status="ready", page_count=300,
            file_size_bytes=1000,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()

        link = ShareLink(
            id=uuid.uuid4(),
            document_id=doc.id,
            token=f"nolimit-token-{uuid.uuid4().hex[:8]}",
            view_count=0,
            permissions='{"can_download": true}',
        )
        db_session.add(link)
        await db_session.flush()

        session_id = "b" * 32
        now = datetime.datetime.now(datetime.timezone.utc)
        vs = ViewerSession(
            session_id=session_id, link_id=link.id,
            created_at=now, last_seen_at=now,
        )
        db_session.add(vs)
        await db_session.commit()

        # With limit=0 the guard should not raise 413
        with patch("app.routers.viewer.settings") as mock_settings:
            mock_settings.max_download_pages_pdf = 0
            mock_settings.max_concurrent_sessions_per_link = 50

            r = await client.get(
                f"/api/viewer/download/{link.token}",
                params={"session_id": session_id},
            )

        # Should NOT be 413 — may be 404 (no pages rows in DB) or other, but not page-limit error
        assert r.status_code != 413, (
            "max_download_pages_pdf=0 must disable the page limit check"
        )

    def test_max_download_pages_default_is_safe(self):
        """Default max_download_pages_pdf must be ≤ 500 to protect API memory.

        Phase 6 streaming download raised this from 100 → 500: pages are now
        assembled one-at-a-time via pypdf, so peak RSS is O(1 page) not O(N).
        """
        from app.config import Settings
        s = Settings()
        assert 0 < s.max_download_pages_pdf <= 500, (
            f"Default max_download_pages_pdf={s.max_download_pages_pdf} is outside safe range. "
            "Must be > 0 (disabled is unsafe) and ≤ 500."
        )


# ── E. Production startup validation ─────────────────────────────────────────

class TestProductionStartupValidation:
    def test_hsts_warning_present_in_startup_code(self):
        """Production startup must warn when HSTS_MAX_AGE is 0."""
        import inspect
        import app.main as main_module
        source = inspect.getsource(main_module)
        assert "HSTS_MAX_AGE" in source or "hsts_max_age" in source
        assert "HSTS" in source

    def test_real_ip_header_warning_in_startup_code(self):
        """Production startup must warn when REAL_IP_HEADER is not set."""
        import inspect
        import app.main as main_module
        source = inspect.getsource(main_module)
        assert "REAL_IP_HEADER" in source or "real_ip_header" in source

    def test_https_redirect_warning_in_startup_code(self):
        """Production startup must warn when HTTPS_REDIRECT is disabled."""
        import inspect
        import app.main as main_module
        source = inspect.getsource(main_module)
        assert "HTTPS_REDIRECT" in source or "https_redirect" in source

    def test_production_errors_block_startup(self):
        """RuntimeError must be raised on startup if production has critical misconfigs."""
        import inspect
        import app.main as main_module
        source = inspect.getsource(main_module)
        assert "RuntimeError" in source
        assert "production" in source.lower()
        assert "Refusing to start" in source


# ── F. Documents index ────────────────────────────────────────────────────────

class TestDocumentsStatusIndex:
    def test_migration_adds_status_updated_index(self):
        """Migration 012 must also add ix_documents_status_updated."""
        path = MIGRATIONS_DIR / "012_analytics_performance_index.py"
        content = path.read_text()
        assert "ix_documents_status_updated" in content
        assert "documents" in content
        assert "status" in content
        assert "updated_at" in content

    def test_worker_orphan_query_benefits_from_index(self):
        """The requeue_orphaned task queries documents by status+updated_at."""
        import inspect
        import app.workers.tasks as tasks_module
        source = inspect.getsource(tasks_module._requeue_orphaned_uploads_async)
        assert "status" in source
        assert "updated_at" in source
        assert "uploaded" in source
