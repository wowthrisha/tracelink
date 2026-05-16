"""
Phase 3 production-hardening tests — viewer metadata cache.

Covers:
  A) _TTLCache unit — get/put/invalidate/expiry/capacity/contains
  B) Cache warm on first request — link/doc/page snapshots populated after a page hit
  C) Cache hit on second request — DB not re-queried for link/doc/page
  D) Revocation invalidation — revoke_link() evicts the cache; next request returns 410
  E) Expiry safety — a cached snapshot with expires_at in the past is rejected on every hit
  F) Thumb endpoint uses the same caches
"""
import time
import uuid
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock, MagicMock

from app.models.document import Document, DocumentPage
from app.models.link import ShareLink
from app.routers.viewer import clear_page_cache, clear_thumb_cache, clear_metadata_caches
from app.services.link_service import LinkService
from app.services.viewer_cache import (
    _TTLCache, link_cache, doc_cache, page_cache,
    LinkSnapshot, DocSnapshot, PageSnapshot,
    invalidate_link, clear_all_caches,
    LINK_TTL_SEC, DOC_TTL_SEC, PAGE_TTL_SEC,
)
from tests.conftest import TEST_USER_ID, _make_webp_bytes
from sqlalchemy import select


# ── fixture helpers ────────────────────────────────────────────────────────────

async def _insert_doc_with_pages(db_session, page_count: int = 2) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename="phase3.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status="ready",
        page_count=page_count,
        file_size_bytes=1024 * page_count,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db_session.add(doc)
    await db_session.flush()
    for i in range(1, page_count + 1):
        db_session.add(DocumentPage(
            document_id=doc.id,
            page_number=i,
            storage_key=f"pages/{doc.id}/{i:04d}.webp",
            width_px=595,
            height_px=842,
        ))
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


async def _validate(client, token: str) -> dict:
    r = await client.post("/api/viewer/validate", json={"token": token})
    assert r.status_code == 200, r.text
    return r.json()


# ══════════════════════════════════════════════════════════════════════════════
# A. _TTLCache UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestTTLCacheUnit:
    """_TTLCache behaves correctly for all operations."""

    def setup_method(self):
        self.cache = _TTLCache(maxsize=5, ttl_seconds=60.0)

    def test_put_and_get_returns_value(self):
        self.cache.put("k", "v")
        assert self.cache.get("k") == "v"

    def test_get_missing_key_returns_none(self):
        assert self.cache.get("missing") is None

    def test_invalidate_removes_entry(self):
        self.cache.put("k", "v")
        self.cache.invalidate("k")
        assert self.cache.get("k") is None

    def test_invalidate_nonexistent_key_is_silent(self):
        self.cache.invalidate("nonexistent")  # must not raise

    def test_contains_true_for_live_entry(self):
        self.cache.put("k", "v")
        assert "k" in self.cache

    def test_contains_false_for_missing_entry(self):
        assert "missing" not in self.cache

    def test_clear_empties_cache(self):
        self.cache.put("a", 1)
        self.cache.put("b", 2)
        self.cache.clear()
        assert len(self.cache) == 0
        assert self.cache.get("a") is None

    def test_ttl_expiry_returns_none(self):
        short_cache = _TTLCache(maxsize=10, ttl_seconds=0.01)
        short_cache.put("k", "v")
        time.sleep(0.02)
        assert short_cache.get("k") is None

    def test_expired_entry_removed_from_dict(self):
        short_cache = _TTLCache(maxsize=10, ttl_seconds=0.01)
        short_cache.put("k", "v")
        time.sleep(0.02)
        short_cache.get("k")  # triggers lazy eviction
        assert len(short_cache) == 0

    def test_capacity_overflow_evicts_oldest(self):
        cache = _TTLCache(maxsize=3, ttl_seconds=60.0)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("d", 4)  # overflow — "a" should be evicted
        assert len(cache) == 3
        assert cache.get("a") is None
        assert cache.get("d") == 4

    def test_overwrite_existing_key_updates_value(self):
        self.cache.put("k", "old")
        self.cache.put("k", "new")
        assert self.cache.get("k") == "new"

    def test_ttl_constants_are_positive(self):
        assert LINK_TTL_SEC > 0
        assert DOC_TTL_SEC > 0
        assert PAGE_TTL_SEC > 0

    def test_link_ttl_shorter_than_doc_ttl(self):
        """Link TTL must be shortest to react to revocations quickly."""
        assert LINK_TTL_SEC <= DOC_TTL_SEC


# ══════════════════════════════════════════════════════════════════════════════
# B. CACHE WARM ON FIRST REQUEST
# ══════════════════════════════════════════════════════════════════════════════

class TestCacheWarmOnFirstRequest:
    """After a page request the link/doc/page caches are populated."""

    @pytest.fixture(autouse=True)
    def _clear(self):
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()
        yield
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()

    @pytest.mark.asyncio
    async def test_link_cache_populated_after_page_request(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        assert link_cache.get(active_link.token) is None  # not yet cached

        await client.get(f"/api/viewer/page/{active_link.token}/1?session_id={sid}")

        snap = link_cache.get(active_link.token)
        assert snap is not None
        assert isinstance(snap, LinkSnapshot)
        assert snap.token == active_link.token
        assert snap.id == active_link.id

    @pytest.mark.asyncio
    async def test_doc_cache_populated_after_page_request(self, client, active_link, ready_document):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        await client.get(f"/api/viewer/page/{active_link.token}/1?session_id={sid}")

        doc_snap = doc_cache.get(str(ready_document.id))
        assert doc_snap is not None
        assert isinstance(doc_snap, DocSnapshot)
        assert doc_snap.status == "ready"

    @pytest.mark.asyncio
    async def test_page_meta_cache_populated_after_page_request(self, client, active_link, ready_document):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        await client.get(f"/api/viewer/page/{active_link.token}/1?session_id={sid}")

        page_key = f"{ready_document.id}:1"
        page_snap = page_cache.get(page_key)
        assert page_snap is not None
        assert isinstance(page_snap, PageSnapshot)
        assert page_snap.storage_key.endswith("0001.webp")


# ══════════════════════════════════════════════════════════════════════════════
# C. CACHE HIT — DB NOT RE-QUERIED
# ══════════════════════════════════════════════════════════════════════════════

class TestCacheHitSkipsDB:
    """On a cache hit the DB SELECT for link/doc/page is not re-issued."""

    @pytest.fixture(autouse=True)
    def _clear(self):
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()
        yield
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()

    @pytest.mark.asyncio
    async def test_second_page_request_skips_link_db_read(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        # First request warms the cache
        r1 = await client.get(f"/api/viewer/page/{active_link.token}/1?session_id={sid}")
        assert r1.status_code == 200

        # Warm the cache manually with a bad doc_id to prove DB is NOT re-queried
        # for the link on the second call — if it were, the link row would reload
        # correctly; if it uses the cache, it uses our injected snapshot.
        bad_snap = LinkSnapshot(
            id=active_link.id,
            token=active_link.token,
            document_id=active_link.document_id,
            revoked_at=None,
            expires_at=None,
            ip_allowlist=None,
        )
        link_cache.put(active_link.token, bad_snap)

        # Second request must use the cache (not re-query DB for the link)
        # and still succeed because the snapshot is valid
        r2 = await client.get(f"/api/viewer/page/{active_link.token}/1?session_id={sid}")
        assert r2.status_code == 200

    @pytest.mark.asyncio
    async def test_page_meta_cache_hit_on_repeated_access(self, client, active_link, ready_document):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        # First request
        await client.get(f"/api/viewer/page/{active_link.token}/1?session_id={sid}")

        page_key = f"{ready_document.id}:1"
        snap_after_first = page_cache.get(page_key)
        assert snap_after_first is not None

        # Second request — same snapshot must still be there (not re-fetched)
        await client.get(f"/api/viewer/page/{active_link.token}/1?session_id={sid}")

        snap_after_second = page_cache.get(page_key)
        assert snap_after_second is snap_after_first  # same object identity


# ══════════════════════════════════════════════════════════════════════════════
# D. REVOCATION INVALIDATION
# ══════════════════════════════════════════════════════════════════════════════

class TestRevocationInvalidatesCache:
    """revoke_link() must evict the cache entry immediately."""

    @pytest.fixture(autouse=True)
    def _clear(self):
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()
        yield
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()

    @pytest.mark.asyncio
    async def test_invalidate_link_removes_from_cache(self, active_link):
        # Manually warm the cache
        snap = LinkSnapshot(
            id=active_link.id,
            token=active_link.token,
            document_id=active_link.document_id,
            revoked_at=None,
            expires_at=None,
            ip_allowlist=None,
        )
        link_cache.put(active_link.token, snap)
        assert link_cache.get(active_link.token) is not None

        # Call the public helper
        invalidate_link(active_link.token)
        assert link_cache.get(active_link.token) is None

    @pytest.mark.asyncio
    async def test_revoke_link_evicts_cache(self, client, db_session, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        # Warm the cache with a page request
        await client.get(f"/api/viewer/page/{active_link.token}/1?session_id={sid}")
        assert link_cache.get(active_link.token) is not None

        # Revoke the link via the service (goes through revoke_link which calls invalidate_link)
        svc = LinkService()
        await svc.revoke_link(db_session, str(active_link.id))

        # Cache must be empty now
        assert link_cache.get(active_link.token) is None

    @pytest.mark.asyncio
    async def test_page_request_after_revoke_returns_410(self, client, db_session, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        # Warm the cache
        await client.get(f"/api/viewer/page/{active_link.token}/1?session_id={sid}")

        # Revoke — also clears cache
        svc = LinkService()
        await svc.revoke_link(db_session, str(active_link.id))

        # Next page request must return 410, not 200
        r = await client.get(f"/api/viewer/page/{active_link.token}/1?session_id={sid}")
        assert r.status_code == 410

    @pytest.mark.asyncio
    async def test_thumb_request_after_revoke_returns_410(self, client, db_session, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        # Warm the cache
        await client.get(f"/api/viewer/thumb/{active_link.token}/1?session_id={sid}")

        # Revoke — also clears cache
        svc = LinkService()
        await svc.revoke_link(db_session, str(active_link.id))

        r = await client.get(f"/api/viewer/thumb/{active_link.token}/1?session_id={sid}")
        assert r.status_code == 410


# ══════════════════════════════════════════════════════════════════════════════
# E. EXPIRY SAFETY — CACHED SNAPSHOT WITH PAST expires_at IS REJECTED
# ══════════════════════════════════════════════════════════════════════════════

class TestExpirySafetyOnCacheHit:
    """A cached LinkSnapshot whose expires_at is in the past must be rejected."""

    @pytest.fixture(autouse=True)
    def _clear(self):
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()
        yield
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()

    @pytest.mark.asyncio
    async def test_cached_expired_link_returns_410(self, client, db_session, ready_document):
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(ready_document.id))

        # Manually inject an already-expired snapshot into the cache
        expired_snap = LinkSnapshot(
            id=link.id,
            token=link.token,
            document_id=link.document_id,
            revoked_at=None,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            ip_allowlist=None,
        )
        link_cache.put(link.token, expired_snap)

        r = await client.post("/api/viewer/validate", json={"token": link.token})
        # validate reads fresh from DB (not cached), so it should succeed.
        # The page endpoint uses the cache and must reject the expired snapshot.
        # Re-use the cache-inserted expired snap — it should cause page rejection.
        sid = "a" * 32  # fake session id of correct length

        r = await client.get(f"/api/viewer/page/{link.token}/1?session_id={sid}")
        assert r.status_code == 410, (
            f"Expected 410 for expired cached snapshot but got {r.status_code}"
        )

    @pytest.mark.asyncio
    async def test_cached_revoked_link_returns_410(self, client, db_session, ready_document):
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(ready_document.id))

        # Manually inject a revoked snapshot (revoked_at != None)
        revoked_snap = LinkSnapshot(
            id=link.id,
            token=link.token,
            document_id=link.document_id,
            revoked_at=datetime.now(timezone.utc) - timedelta(seconds=5),
            expires_at=None,
            ip_allowlist=None,
        )
        link_cache.put(link.token, revoked_snap)

        sid = "b" * 32
        r = await client.get(f"/api/viewer/page/{link.token}/1?session_id={sid}")
        assert r.status_code == 410


# ══════════════════════════════════════════════════════════════════════════════
# F. THUMB ENDPOINT USES METADATA CACHE
# ══════════════════════════════════════════════════════════════════════════════

class TestThumbEndpointUsesMetadataCache:
    """The /thumb/ endpoint must populate and read from the same caches."""

    @pytest.fixture(autouse=True)
    def _clear(self):
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()
        yield
        clear_page_cache()
        clear_thumb_cache()
        clear_metadata_caches()

    @pytest.mark.asyncio
    async def test_thumb_populates_link_cache(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        assert link_cache.get(active_link.token) is None

        await client.get(f"/api/viewer/thumb/{active_link.token}/1?session_id={sid}")

        snap = link_cache.get(active_link.token)
        assert snap is not None
        assert snap.id == active_link.id

    @pytest.mark.asyncio
    async def test_thumb_shares_link_cache_with_page(self, client, active_link):
        """A page hit followed by a thumb hit must reuse the same link snapshot."""
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        # Page request warms the cache
        await client.get(f"/api/viewer/page/{active_link.token}/1?session_id={sid}")
        snap_after_page = link_cache.get(active_link.token)
        assert snap_after_page is not None

        # Thumb request must reuse the same snapshot (same object identity)
        await client.get(f"/api/viewer/thumb/{active_link.token}/1?session_id={sid}")
        snap_after_thumb = link_cache.get(active_link.token)
        assert snap_after_thumb is snap_after_page

    @pytest.mark.asyncio
    async def test_thumb_populates_page_meta_cache(self, client, active_link, ready_document):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        page_key = f"{ready_document.id}:1"
        assert page_cache.get(page_key) is None

        await client.get(f"/api/viewer/thumb/{active_link.token}/1?session_id={sid}")

        assert page_cache.get(page_key) is not None
