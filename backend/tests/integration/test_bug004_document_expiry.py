"""
BUG-004 regression — document retention expiry must be enforced server-side,
immediately, at the access-control layer — not only via eventual deletion by
the once-a-day `securedoc.cleanup_expired_documents` Celery Beat task.

Before this fix, `Document.expires_at` / `Document.lifecycle_state` were never
read anywhere in the viewer access path:
  - `LinkService.validate_link()` (POST /api/viewer/validate, the endpoint that
    actually opens a Viewer session) never loaded the Document at all.
  - `_get_cached_link_and_doc()` (shared by /page, /thumb, /text, /toc, ...)
    only checked `Document.status` (the processing pipeline state), never
    `lifecycle_state`/`expires_at`.
  - `/api/viewer/gate/{token}` only checked the ShareLink's own expiry.

So a document whose retention date had passed remained fully viewable through
any still-valid share link — for up to 24h (the Beat schedule interval), or
indefinitely if the daily cleanup job wasn't actually running — exactly the
"expired document remains active" defect reported live. Verified locally by
inserting a disposable document row with `expires_at` in the past and
confirming `expire_and_delete_documents()` did correctly clean it up when
manually invoked (so the DB-level retention job itself was not the bug); the
gap was purely in the access-control checks these tests exercise.

Covers the fix in:
  - app/services/viewer_service.py  — _check_doc_not_expired()
  - app/routers/viewer.py           — _get_cached_link_and_doc(), /gate/{token}
  - app/services/link_service.py    — LinkService.validate_link()
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.models.document import Document, DocumentPage
from app.routers.viewer import clear_page_cache, clear_thumb_cache, clear_metadata_caches
from app.services.link_service import LinkService
from app.services.viewer_cache import doc_cache, DocSnapshot
from tests.conftest import TEST_USER_ID


async def _make_expiring_document(db_session, *, lifecycle_state="active", expires_at=None, page_count=2):
    doc = Document(
        id=uuid.uuid4(),
        filename="bug004.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status="ready",
        page_count=page_count,
        file_size_bytes=2048,
        user_id=uuid.UUID(TEST_USER_ID),
        lifecycle_state=lifecycle_state,
        expires_at=expires_at,
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


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_page_cache()
    clear_thumb_cache()
    clear_metadata_caches()
    yield
    clear_page_cache()
    clear_thumb_cache()
    clear_metadata_caches()


# ══════════════════════════════════════════════════════════════════════════════
# validate — the session-establishment endpoint
# ══════════════════════════════════════════════════════════════════════════════

class TestValidateBlocksExpiredDocument:

    @pytest.mark.asyncio
    async def test_lifecycle_state_expired_blocks_validate(self, client, db_session):
        doc = await _make_expiring_document(db_session, lifecycle_state="expired")
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))

        r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 410, r.text
        assert "expired" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_past_expires_at_blocks_validate_even_if_lifecycle_state_still_active(self, client, db_session):
        """The daily cleanup job hasn't run yet (lifecycle_state still 'active'),
        but expires_at has already passed — this is the exact production report:
        an ACTIVE document past its own expiry date, still fully viewable."""
        past = datetime.now(timezone.utc) - timedelta(days=27)
        doc = await _make_expiring_document(db_session, lifecycle_state="active", expires_at=past)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))

        r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 410, r.text
        assert "expired" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_future_expiry_does_not_block_validate(self, client, db_session):
        future = datetime.now(timezone.utc) + timedelta(days=10)
        doc = await _make_expiring_document(db_session, lifecycle_state="active", expires_at=future)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))

        r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200, r.text

    @pytest.mark.asyncio
    async def test_never_policy_no_expiry_does_not_block_validate(self, client, db_session):
        doc = await _make_expiring_document(db_session, lifecycle_state="active", expires_at=None)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))

        r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200, r.text


# ══════════════════════════════════════════════════════════════════════════════
# gate — the first, pre-credential check the viewer frontend hits
# ══════════════════════════════════════════════════════════════════════════════

class TestGateReportsExpiredDocument:

    @pytest.mark.asyncio
    async def test_gate_reports_expired_status_for_expired_document(self, client, db_session):
        doc = await _make_expiring_document(db_session, lifecycle_state="expired")
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))

        r = await client.get(f"/api/viewer/gate/{link.token}")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "expired"
        assert body["requires_password"] is False

    @pytest.mark.asyncio
    async def test_gate_reports_expired_status_for_past_expires_at(self, client, db_session):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        doc = await _make_expiring_document(db_session, lifecycle_state="active", expires_at=past)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))

        r = await client.get(f"/api/viewer/gate/{link.token}")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "expired"

    @pytest.mark.asyncio
    async def test_gate_reports_active_for_unexpired_document(self, client, db_session):
        doc = await _make_expiring_document(db_session, lifecycle_state="active", expires_at=None)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))

        r = await client.get(f"/api/viewer/gate/{link.token}")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "active"


# ══════════════════════════════════════════════════════════════════════════════
# page / content endpoints — _get_cached_link_and_doc shared enforcement
# ══════════════════════════════════════════════════════════════════════════════

class TestContentEndpointsBlockExpiredDocument:

    @pytest.mark.asyncio
    async def test_page_endpoint_returns_410_for_expired_document(self, client, db_session):
        doc = await _make_expiring_document(db_session, lifecycle_state="expired")
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))

        sid = "c" * 32
        r = await client.get(f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid})
        assert r.status_code == 410, r.text
        assert "expired" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_page_endpoint_returns_410_for_past_expires_at(self, client, db_session):
        past = datetime.now(timezone.utc) - timedelta(days=1)
        doc = await _make_expiring_document(db_session, lifecycle_state="active", expires_at=past)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))

        sid = "d" * 32
        r = await client.get(f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid})
        assert r.status_code == 410, r.text

    @pytest.mark.asyncio
    async def test_cached_doc_snapshot_with_expired_lifecycle_state_rejected_on_hit(self, client, db_session, ready_document):
        """Mirrors TestExpirySafetyOnCacheHit in test_phase3.py, but for the
        Document-level (not Link-level) expiry snapshot: a snapshot that was
        cached while the document was still active must be rejected the
        moment it reflects an expired lifecycle_state/expires_at, exactly
        like the existing link-expiry cache-safety contract."""
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(ready_document.id))

        expired_doc_snap = DocSnapshot(
            id=ready_document.id,
            status="ready",
            file_type="pdf",
            storage_key=ready_document.storage_key,
            page_count=ready_document.page_count,
            lifecycle_state="expired",
            expires_at=None,
        )
        doc_cache.put(str(ready_document.id), expired_doc_snap)

        sid = "e" * 32
        r = await client.get(f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid})
        assert r.status_code == 410, r.text

    @pytest.mark.asyncio
    async def test_thumb_endpoint_also_blocked_for_expired_document(self, client, db_session):
        doc = await _make_expiring_document(db_session, lifecycle_state="expired")
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))

        sid = "f" * 32
        r = await client.get(f"/api/viewer/thumb/{link.token}/1", headers={"X-Session-ID": sid})
        assert r.status_code == 410, r.text

    @pytest.mark.asyncio
    async def test_unexpired_document_page_still_loads(self, client, db_session, ready_document):
        """Baseline / no false-positive check: a normal, non-expired document
        must be completely unaffected by this fix."""
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(ready_document.id))

        validate_r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert validate_r.status_code == 200, validate_r.text
        sid = validate_r.json()["session_id"]

        r = await client.get(f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid})
        assert r.status_code == 200, r.text
