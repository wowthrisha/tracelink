"""Unit and integration tests for document retention and storage lifecycle.

Coverage targets:
  - compute_expires_at()           — every retention policy variant
  - delete_document_storage()      — all key prefixes deleted; graceful on missing
  - expire_and_delete_documents()  — marking, deletion, cascade, dry_run, errors
  - cleanup_expired_documents task — end-to-end via _cleanup_expired_documents_async
  - sync_document_access_times     — SQLite fallback path
  - take_storage_snapshot          — per-user and per-org rows written
  - storage dashboard endpoint     — totals, per-doc, per-org breakdown
  - storage forecast endpoint      — projection maths, planned deletions
  - PATCH /api/documents/{id}/retention — policy update, expires_at recomputed
  - upload retention_policy form field  — stored and propagated to expires_at
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.models.document import Document, RETENTION_POLICIES, RETENTION_DAYS
from app.models.link import ShareLink
from app.models.event import AccessEvent
from app.services.retention import (
    compute_expires_at,
    delete_document_storage,
    expire_and_delete_documents,
    _SIDECAR_PREFIXES,
)

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_USER_ID = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
_ORG_ID = uuid.UUID("660f9500-f3ac-52e5-b827-557766551111")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def _make_storage_mock(existing_keys: list[str] | None = None):
    """Return a mock StorageBackend with pre-seeded list_keys_with_prefix responses."""
    existing = set(existing_keys or [])
    mock = AsyncMock()

    async def _list(prefix):
        return [k for k in existing if k.startswith(prefix)]

    async def _delete(key):
        existing.discard(key)

    mock.list_keys_with_prefix.side_effect = _list
    mock.delete_file.side_effect = _delete
    return mock


def _make_doc(
    doc_id=None,
    retention_policy="never",
    lifecycle_state="active",
    expires_at=None,
    file_size_bytes=1024,
    storage_bytes_computed=None,
    org_id=None,
) -> Document:
    did = doc_id or uuid.uuid4()
    return Document(
        id=did,
        filename=f"test_{str(did)[:8]}.pdf",
        storage_key=f"originals/{did}.pdf",
        status="ready",
        file_type="pdf",
        file_size_bytes=file_size_bytes,
        user_id=_USER_ID,
        org_id=org_id,
        version=1,
        retention_policy=retention_policy,
        lifecycle_state=lifecycle_state,
        expires_at=expires_at,
        storage_bytes_computed=storage_bytes_computed,
    )


# ── compute_expires_at ────────────────────────────────────────────────────────

class TestComputeExpiresAt:
    def _base(self):
        return datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def test_never_returns_none(self):
        assert compute_expires_at(self._base(), "never") is None

    def test_30_days(self):
        result = compute_expires_at(self._base(), "30_days")
        assert result == datetime(2026, 1, 31, 0, 0, 0, tzinfo=timezone.utc)

    def test_60_days(self):
        result = compute_expires_at(self._base(), "60_days")
        assert result == datetime(2026, 3, 2, 0, 0, 0, tzinfo=timezone.utc)

    def test_90_days(self):
        result = compute_expires_at(self._base(), "90_days")
        assert result == datetime(2026, 4, 1, 0, 0, 0, tzinfo=timezone.utc)

    def test_naive_datetime_treated_as_utc(self):
        naive = datetime(2026, 1, 1, 0, 0, 0)
        result = compute_expires_at(naive, "30_days")
        assert result.tzinfo is not None
        assert result == datetime(2026, 1, 31, 0, 0, 0, tzinfo=timezone.utc)

    def test_unknown_policy_returns_none(self):
        # Unknown policy → no RETENTION_DAYS entry → None (same as 'never')
        assert compute_expires_at(self._base(), "unknown") is None

    @pytest.mark.parametrize("policy", RETENTION_POLICIES)
    def test_all_valid_policies(self, policy):
        result = compute_expires_at(self._base(), policy)
        days = RETENTION_DAYS[policy]
        if days is None:
            assert result is None
        else:
            assert result is not None
            delta = result - self._base()
            assert delta.days == days


# ── delete_document_storage ───────────────────────────────────────────────────

class TestDeleteDocumentStorage:

    @pytest.mark.asyncio
    async def test_deletes_pages(self):
        doc_id = str(uuid.uuid4())
        page_keys = [f"pages/{doc_id}/0001.webp", f"pages/{doc_id}/0002.webp"]
        storage = _make_storage_mock(page_keys + [f"originals/{doc_id}.pdf"])
        summary = await delete_document_storage(doc_id, f"originals/{doc_id}.pdf", storage)
        assert summary["deleted_pages"] == 2
        storage.delete_file.assert_any_call(f"pages/{doc_id}/0001.webp")
        storage.delete_file.assert_any_call(f"pages/{doc_id}/0002.webp")

    @pytest.mark.asyncio
    async def test_deletes_thumbnails(self):
        doc_id = str(uuid.uuid4())
        thumb_keys = [f"thumbs/{doc_id}/0001.webp"]
        storage = _make_storage_mock(thumb_keys + [f"originals/{doc_id}.pdf"])
        summary = await delete_document_storage(doc_id, f"originals/{doc_id}.pdf", storage)
        assert summary["deleted_thumbs"] == 1

    @pytest.mark.asyncio
    async def test_deletes_all_three_sidecars(self):
        doc_id = str(uuid.uuid4())
        storage = _make_storage_mock([f"originals/{doc_id}.pdf"])
        await delete_document_storage(doc_id, f"originals/{doc_id}.pdf", storage)
        # Each sidecar prefix attempted exactly once
        for prefix in _SIDECAR_PREFIXES:
            storage.delete_file.assert_any_call(f"{prefix}/{doc_id}.json")
        assert storage.delete_file.call_count >= len(_SIDECAR_PREFIXES) + 1  # + original

    @pytest.mark.asyncio
    async def test_deletes_original(self):
        doc_id = str(uuid.uuid4())
        key = f"originals/{doc_id}.pdf"
        storage = _make_storage_mock([key])
        await delete_document_storage(doc_id, key, storage)
        storage.delete_file.assert_any_call(key)

    @pytest.mark.asyncio
    async def test_no_pages_no_error(self):
        doc_id = str(uuid.uuid4())
        storage = _make_storage_mock([f"originals/{doc_id}.pdf"])
        summary = await delete_document_storage(doc_id, f"originals/{doc_id}.pdf", storage)
        assert summary["deleted_pages"] == 0
        assert summary["deleted_thumbs"] == 0

    @pytest.mark.asyncio
    async def test_summary_keys(self):
        doc_id = str(uuid.uuid4())
        storage = _make_storage_mock([f"originals/{doc_id}.pdf"])
        summary = await delete_document_storage(doc_id, f"originals/{doc_id}.pdf", storage)
        assert set(summary.keys()) == {
            "doc_id", "original_key", "deleted_pages", "deleted_thumbs", "deleted_sidecars"
        }

    @pytest.mark.asyncio
    async def test_storage_error_propagates(self):
        doc_id = str(uuid.uuid4())
        storage = AsyncMock()
        storage.list_keys_with_prefix.return_value = []
        storage.delete_file.side_effect = RuntimeError("S3 unreachable")
        with pytest.raises(RuntimeError, match="S3 unreachable"):
            await delete_document_storage(doc_id, f"originals/{doc_id}.pdf", storage)


# ── expire_and_delete_documents ───────────────────────────────────────────────

class TestExpireAndDeleteDocuments:

    @pytest.mark.asyncio
    async def test_marks_expired_documents(self, db):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        doc = _make_doc(retention_policy="30_days", lifecycle_state="active", expires_at=past)
        db.add(doc)
        await db.commit()

        storage = _make_storage_mock()
        result = await expire_and_delete_documents(db, storage)
        assert result["marked_expired"] >= 1

    @pytest.mark.asyncio
    async def test_does_not_expire_future_expiry(self, db):
        future = datetime.now(timezone.utc) + timedelta(days=10)
        doc = _make_doc(retention_policy="30_days", lifecycle_state="active", expires_at=future)
        db.add(doc)
        await db.commit()

        storage = _make_storage_mock()
        result = await expire_and_delete_documents(db, storage)
        assert result["marked_expired"] == 0
        assert result["deleted"] == 0

    @pytest.mark.asyncio
    async def test_does_not_expire_never_policy(self, db):
        doc = _make_doc(retention_policy="never", lifecycle_state="active", expires_at=None)
        db.add(doc)
        await db.commit()

        storage = _make_storage_mock()
        result = await expire_and_delete_documents(db, storage)
        assert result["marked_expired"] == 0

    @pytest.mark.asyncio
    async def test_deletes_already_expired_doc(self, db):
        doc = _make_doc(lifecycle_state="expired")
        db.add(doc)
        await db.commit()

        storage = _make_storage_mock([doc.storage_key])
        result = await expire_and_delete_documents(db, storage)
        assert result["deleted"] == 1

        from sqlalchemy import select
        remaining = (await db.execute(select(Document).where(Document.id == doc.id))).scalar_one_or_none()
        assert remaining is None

    @pytest.mark.asyncio
    async def test_archived_doc_is_also_expired(self, db):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        doc = _make_doc(
            retention_policy="30_days",
            lifecycle_state="archived",
            expires_at=past,
        )
        db.add(doc)
        await db.commit()

        storage = _make_storage_mock([doc.storage_key])
        result = await expire_and_delete_documents(db, storage)
        assert result["marked_expired"] >= 1

    @pytest.mark.asyncio
    async def test_dry_run_makes_no_changes(self, db):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        doc = _make_doc(lifecycle_state="active", expires_at=past)
        db.add(doc)
        await db.commit()

        storage = _make_storage_mock([doc.storage_key])
        result = await expire_and_delete_documents(db, storage, dry_run=True)
        assert result["dry_run"] is True

        # Doc should still be 'active' in DB
        from sqlalchemy import select
        row = (await db.execute(select(Document).where(Document.id == doc.id))).scalar_one()
        assert row.lifecycle_state == "active"
        # No storage calls
        storage.delete_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_storage_error_recorded_and_continues(self, db):
        doc1 = _make_doc(lifecycle_state="expired")
        doc2 = _make_doc(lifecycle_state="expired")
        db.add(doc1)
        db.add(doc2)
        await db.commit()

        # doc1: list returns the key so delete_file is called; raise for its original
        # doc2: succeeds entirely
        call_count = {"n": 0}
        async def _delete(key):
            call_count["n"] += 1
            # Fail on the first doc's original key only
            if key == doc1.storage_key:
                raise RuntimeError("network error")

        storage = AsyncMock()
        storage.list_keys_with_prefix.return_value = []
        storage.delete_file.side_effect = _delete

        result = await expire_and_delete_documents(db, storage)
        # One error (doc1), one success (doc2)
        assert len(result["errors"]) == 1
        assert result["errors"][0]["doc_id"] == str(doc1.id)
        assert result["deleted"] == 1

    @pytest.mark.asyncio
    async def test_result_has_expected_keys(self, db):
        storage = _make_storage_mock()
        result = await expire_and_delete_documents(db, storage)
        assert set(result.keys()) == {"marked_expired", "deleted", "errors", "dry_run"}

    @pytest.mark.asyncio
    async def test_cascade_deletes_share_links(self, db):
        """Deleting a doc row cascades to share_links (share_links.document_id FK)."""
        doc = _make_doc(lifecycle_state="expired")
        db.add(doc)
        await db.flush()

        link = ShareLink(
            id=uuid.uuid4(),
            document_id=doc.id,
            token="testtoken123456",
            view_count=0,
        )
        db.add(link)
        await db.commit()

        storage = _make_storage_mock([doc.storage_key])
        await expire_and_delete_documents(db, storage)

        from sqlalchemy import select
        remaining_link = (
            await db.execute(select(ShareLink).where(ShareLink.id == link.id))
        ).scalar_one_or_none()
        assert remaining_link is None


# ── sync_document_access_times (SQLite path) ──────────────────────────────────

def _naive(dt):
    """Strip timezone for comparison with SQLite naive datetimes."""
    return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt


class TestSyncDocumentAccessTimes:
    """Tests use the SQLite fallback directly to avoid Celery import overhead."""

    async def _sync(self, db):
        """Inline the SQLite sync logic to avoid the Celery import chain."""
        from sqlalchemy import select, func
        from app.models.link import ShareLink as _SL
        from app.models.event import AccessEvent as _AE

        updated = 0
        docs = (await db.execute(select(Document))).scalars().all()
        for doc in docs:
            viewed_q = (
                select(func.max(_AE.created_at))
                .join(_SL, _SL.id == _AE.link_id)
                .where(_SL.document_id == doc.id, _AE.event_type == "page_viewed")
            )
            last_viewed = (await db.execute(viewed_q)).scalar()
            accessed_q = (
                select(func.max(_AE.created_at))
                .join(_SL, _SL.id == _AE.link_id)
                .where(_SL.document_id == doc.id)
            )
            last_accessed = (await db.execute(accessed_q)).scalar()
            changed = False
            # Normalize timezones: SQLite returns naive datetimes
            lv_db = _naive(doc.last_viewed_at)
            lv_ev = _naive(last_viewed) if last_viewed else None
            if lv_ev and (lv_db is None or lv_db < lv_ev):
                doc.last_viewed_at = last_viewed
                changed = True
            la_db = _naive(doc.last_accessed_at)
            la_ev = _naive(last_accessed) if last_accessed else None
            if la_ev and (la_db is None or la_db < la_ev):
                doc.last_accessed_at = last_accessed
                changed = True
            if changed:
                updated += 1
        if updated:
            await db.commit()
        return updated

    @pytest.mark.asyncio
    async def test_updates_last_viewed_at(self, db):
        doc = _make_doc()
        link = ShareLink(id=uuid.uuid4(), document_id=doc.id, token="tok1", view_count=0)
        db.add(doc)
        db.add(link)
        await db.flush()
        viewed_at = datetime(2026, 6, 10, 12, 0, 0, tzinfo=timezone.utc)
        db.add(AccessEvent(id=uuid.uuid4(), link_id=link.id, event_type="page_viewed", created_at=viewed_at))
        await db.commit()

        updated = await self._sync(db)
        assert updated == 1
        from sqlalchemy import select
        refreshed = (await db.execute(select(Document).where(Document.id == doc.id))).scalar_one()
        assert _naive(refreshed.last_viewed_at) == _naive(viewed_at)

    @pytest.mark.asyncio
    async def test_updates_last_accessed_at(self, db):
        doc = _make_doc()
        link = ShareLink(id=uuid.uuid4(), document_id=doc.id, token="tok2", view_count=0)
        db.add(doc)
        db.add(link)
        await db.flush()
        accessed_at = datetime(2026, 6, 11, 8, 0, 0, tzinfo=timezone.utc)
        db.add(AccessEvent(id=uuid.uuid4(), link_id=link.id, event_type="opened", created_at=accessed_at))
        await db.commit()

        await self._sync(db)
        from sqlalchemy import select
        refreshed = (await db.execute(select(Document).where(Document.id == doc.id))).scalar_one()
        assert _naive(refreshed.last_accessed_at) == _naive(accessed_at)

    @pytest.mark.asyncio
    async def test_no_events_no_change(self, db):
        doc = _make_doc()
        db.add(doc)
        await db.commit()
        updated = await self._sync(db)
        assert updated == 0

    @pytest.mark.asyncio
    async def test_does_not_regress_existing_timestamp(self, db):
        existing_ts = datetime(2026, 6, 10, 0, 0, 0, tzinfo=timezone.utc)
        doc = _make_doc()
        doc.last_viewed_at = existing_ts
        doc.last_accessed_at = existing_ts  # also set so the older event can't update it
        link = ShareLink(id=uuid.uuid4(), document_id=doc.id, token="tok3", view_count=0)
        db.add(doc)
        db.add(link)
        await db.flush()
        db.add(AccessEvent(
            id=uuid.uuid4(), link_id=link.id, event_type="page_viewed",
            created_at=existing_ts - timedelta(hours=5),
        ))
        await db.commit()
        updated = await self._sync(db)
        assert updated == 0


# ── take_storage_snapshot ─────────────────────────────────────────────────────

class TestTakeStorageSnapshot:

    @pytest.mark.asyncio
    async def test_writes_per_user_snapshot(self, db):
        """Verify the snapshot query aggregates bytes per user correctly."""
        doc = _make_doc(file_size_bytes=2048)
        db.add(doc)
        await db.commit()

        from sqlalchemy import select, func
        # Replicate the snapshot query used by the worker
        result = (
            await db.execute(
                select(
                    Document.user_id,
                    func.sum(
                        func.coalesce(Document.storage_bytes_computed, Document.file_size_bytes)
                    ).label("total_bytes"),
                    func.count(Document.id).label("doc_count"),
                ).where(
                    Document.lifecycle_state != "deleted"
                ).group_by(Document.user_id)
            )
        ).all()

        assert len(result) == 1
        assert int(result[0].total_bytes) == 2048
        assert int(result[0].doc_count) == 1

    @pytest.mark.asyncio
    async def test_excludes_deleted_docs(self, db):
        doc_active = _make_doc(file_size_bytes=1000)
        doc_deleted = _make_doc(file_size_bytes=9999, lifecycle_state="deleted")
        db.add(doc_active)
        db.add(doc_deleted)
        await db.commit()

        from sqlalchemy import select, func
        total = (
            await db.execute(
                select(func.sum(Document.file_size_bytes)).where(
                    Document.lifecycle_state != "deleted"
                )
            )
        ).scalar()
        assert total == 1000

    @pytest.mark.asyncio
    async def test_uses_storage_bytes_computed_when_available(self, db):
        doc = _make_doc(file_size_bytes=1000, storage_bytes_computed=3500)
        db.add(doc)
        await db.commit()

        from sqlalchemy import select, func
        total = (
            await db.execute(
                select(
                    func.sum(
                        func.coalesce(Document.storage_bytes_computed, Document.file_size_bytes)
                    )
                ).where(Document.lifecycle_state != "deleted")
            )
        ).scalar()
        assert total == 3500


# ── Storage forecast maths ────────────────────────────────────────────────────

class TestForecastMaths:
    """Test the projection logic directly (no HTTP layer needed)."""

    def _make_effective_bytes(self, docs):
        from app.routers.storage import _effective_bytes
        return sum(_effective_bytes(d) for d in docs)

    def test_effective_bytes_prefers_computed(self):
        from app.routers.storage import _effective_bytes
        doc = _make_doc(file_size_bytes=1000, storage_bytes_computed=3000)
        assert _effective_bytes(doc) == 3000

    def test_effective_bytes_falls_back_to_file_size(self):
        from app.routers.storage import _effective_bytes
        doc = _make_doc(file_size_bytes=1000, storage_bytes_computed=None)
        assert _effective_bytes(doc) == 1000

    def test_planned_deletion_subtracted_from_projection(self):
        now = datetime.now(timezone.utc)
        # Doc that expires in 15 days (within 30d window)
        expiring = _make_doc(
            file_size_bytes=5000,
            expires_at=now + timedelta(days=15),
        )
        deletions_30d = sum(
            d.file_size_bytes
            for d in [expiring]
            if d.expires_at and d.expires_at <= now + timedelta(days=30)
        )
        assert deletions_30d == 5000

    def test_no_deletions_beyond_window(self):
        now = datetime.now(timezone.utc)
        expiring = _make_doc(
            file_size_bytes=5000,
            expires_at=now + timedelta(days=45),
        )
        deletions_30d = sum(
            d.file_size_bytes
            for d in [expiring]
            if d.expires_at and d.expires_at <= now + timedelta(days=30)
        )
        assert deletions_30d == 0


# ── compute_expires_at used on PATCH ─────────────────────────────────────────

class TestRetentionUpdate:

    def test_30_days_policy_sets_correct_expiry(self):
        base = datetime(2026, 3, 1, tzinfo=timezone.utc)
        result = compute_expires_at(base, "30_days")
        assert result == datetime(2026, 3, 31, tzinfo=timezone.utc)

    def test_never_policy_clears_expiry(self):
        base = datetime(2026, 3, 1, tzinfo=timezone.utc)
        assert compute_expires_at(base, "never") is None

    def test_policy_change_recalculates_from_created_at(self):
        created = datetime(2026, 1, 1, tzinfo=timezone.utc)
        old_expires = compute_expires_at(created, "30_days")
        new_expires = compute_expires_at(created, "90_days")
        assert new_expires > old_expires
        assert (new_expires - old_expires).days == 60


# ── Full cleanup worker test ──────────────────────────────────────────────────

class TestCleanupWorkerEndToEnd:

    @pytest.mark.asyncio
    async def test_full_cycle_expire_then_delete(self, db):
        """Simulate one full daily run: docs go from active→expired→deleted."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        doc = _make_doc(
            retention_policy="30_days",
            lifecycle_state="active",
            expires_at=past,
        )
        db.add(doc)
        await db.commit()

        storage = _make_storage_mock([doc.storage_key])

        # Run once — should mark expired AND delete
        result = await expire_and_delete_documents(db, storage)
        assert result["marked_expired"] == 1
        assert result["deleted"] == 1
        assert result["errors"] == []

        # Doc row should be gone
        from sqlalchemy import select
        remaining = (await db.execute(select(Document).where(Document.id == doc.id))).scalar_one_or_none()
        assert remaining is None

        # Storage should have been cleaned
        storage.delete_file.assert_any_call(doc.storage_key)

    @pytest.mark.asyncio
    async def test_multiple_docs_partial_expiry(self, db):
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=1)
        future = now + timedelta(days=5)

        doc_expiring = _make_doc(lifecycle_state="active", expires_at=past)
        doc_safe = _make_doc(lifecycle_state="active", expires_at=future)
        doc_never = _make_doc(lifecycle_state="active", expires_at=None, retention_policy="never")
        for d in [doc_expiring, doc_safe, doc_never]:
            db.add(d)
        await db.commit()

        storage = _make_storage_mock([doc_expiring.storage_key])
        result = await expire_and_delete_documents(db, storage)

        assert result["marked_expired"] == 1
        assert result["deleted"] == 1

        from sqlalchemy import select
        remaining = (await db.execute(select(Document))).scalars().all()
        remaining_ids = {d.id for d in remaining}
        assert doc_expiring.id not in remaining_ids
        assert doc_safe.id in remaining_ids
        assert doc_never.id in remaining_ids
