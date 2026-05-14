"""
Auth enforcement regression tests.

Validates three guarantees that must NEVER regress:

  1. Every admin route returns 401 when called without credentials.
  2. Public routes (viewer, analytics event logging) work with no credentials.
  3. Authenticated user A cannot access or mutate user B's resources.
"""
import secrets
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from PIL import Image
import io
from unittest.mock import AsyncMock, MagicMock, patch

from app.auth import get_current_user
from app.database import get_db
from app.main import app
from app.models.document import Document
from app.models.link import ShareLink
from app.models.event import AccessEvent
from tests.conftest import TEST_USER_ID, TEST_USER_B_ID


# ── helpers ────────────────────────────────────────────────────────────────

def _webp():
    img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()


_SAMPLE_PDF = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"xref\n0 1\n0000000000 65535 f\n"
    b"trailer\n<< /Size 1 >>\nstartxref\n9\n%%EOF"
)


# ── fixtures ───────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def unauth_client(db_session):
    """
    Test client with storage/celery mocked but get_current_user NOT overridden.
    Any request that reaches a protected route without an Authorization header
    will receive 401 from the real get_current_user dependency.
    """
    async def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    # Deliberately do NOT override get_current_user

    with patch("app.services.storage.StorageService.upload_file", new_callable=AsyncMock), \
         patch("app.services.storage.StorageService.generate_presigned_url", new_callable=AsyncMock), \
         patch("app.services.storage.StorageService.download_bytes", new_callable=AsyncMock) as mock_dl, \
         patch("app.services.storage.StorageService.delete_file", new_callable=AsyncMock), \
         patch("app.services.storage.StorageService.list_keys_with_prefix", new_callable=AsyncMock) as mock_list, \
         patch("app.workers.tasks.process_document.delay") as mock_celery:

        mock_dl.return_value = _webp()
        mock_list.return_value = []
        mock_celery.return_value = MagicMock(id="fake-task-id")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as c:
            yield c

    app.dependency_overrides.clear()


async def _make_doc(db_session, user_id=TEST_USER_ID) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename="test.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status="ready",
        page_count=3,
        file_size_bytes=1024,
        user_id=uuid.UUID(user_id),
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


async def _make_link(db_session, doc: Document) -> ShareLink:
    link = ShareLink(
        id=uuid.uuid4(),
        document_id=doc.id,
        token=secrets.token_hex(32),
        view_count=0,
    )
    db_session.add(link)
    await db_session.flush()
    return link


async def _make_event(db_session, link: ShareLink) -> AccessEvent:
    event = AccessEvent(
        id=uuid.uuid4(),
        link_id=link.id,
        event_type="opened",
    )
    db_session.add(event)
    await db_session.flush()
    return event


# ══════════════════════════════════════════════════════════════════════════
# 1. UNAUTHORIZED ACCESS → 401
# ══════════════════════════════════════════════════════════════════════════

class TestUnauthorizedReturns401:
    """Every admin-facing route must reject requests with no token."""

    # ── Documents ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_upload_without_token_returns_401(self, unauth_client):
        r = await unauth_client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", _SAMPLE_PDF, "application/pdf")},
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_list_documents_without_token_returns_401(self, unauth_client):
        r = await unauth_client.get("/api/documents")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_get_document_without_token_returns_401(self, unauth_client, db_session):
        doc = await _make_doc(db_session)
        await db_session.commit()
        r = await unauth_client.get(f"/api/documents/{doc.id}")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_document_status_without_token_returns_401(self, unauth_client, db_session):
        doc = await _make_doc(db_session)
        await db_session.commit()
        r = await unauth_client.get(f"/api/documents/{doc.id}/status")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_document_without_token_returns_401(self, unauth_client, db_session):
        doc = await _make_doc(db_session)
        await db_session.commit()
        r = await unauth_client.delete(f"/api/documents/{doc.id}")
        assert r.status_code == 401

    # ── Links ──────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_create_link_without_token_returns_401(self, unauth_client, db_session):
        doc = await _make_doc(db_session)
        await db_session.commit()
        r = await unauth_client.post(
            "/api/links", json={"document_id": str(doc.id)}
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_list_links_without_token_returns_401(self, unauth_client, db_session):
        doc = await _make_doc(db_session)
        await db_session.commit()
        r = await unauth_client.get(f"/api/links?document_id={doc.id}")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_revoke_link_without_token_returns_401(self, unauth_client, db_session):
        doc = await _make_doc(db_session)
        link = await _make_link(db_session, doc)
        await db_session.commit()
        r = await unauth_client.delete(f"/api/links/{link.id}")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_patch_link_without_token_returns_401(self, unauth_client, db_session):
        doc = await _make_doc(db_session)
        link = await _make_link(db_session, doc)
        await db_session.commit()
        r = await unauth_client.patch(
            f"/api/links/{link.id}", json={"label": "changed"}
        )
        assert r.status_code == 401

    # ── Analytics GET routes ────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_analytics_overview_without_token_returns_401(self, unauth_client):
        r = await unauth_client.get("/api/analytics/overview")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_analytics_documents_without_token_returns_401(self, unauth_client):
        r = await unauth_client.get("/api/analytics/documents")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_analytics_events_get_without_token_returns_401(self, unauth_client):
        r = await unauth_client.get("/api/analytics/events")
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_analytics_groups_without_token_returns_401(self, unauth_client):
        r = await unauth_client.get("/api/analytics/groups")
        assert r.status_code == 401


# ══════════════════════════════════════════════════════════════════════════
# 2. PUBLIC ROUTES — work with no credentials
# ══════════════════════════════════════════════════════════════════════════

class TestPublicRoutesRequireNoAuth:
    """Viewer validate, page proxy, and analytics event logging are public."""

    @pytest.mark.asyncio
    async def test_viewer_validate_works_without_token(
        self, unauth_client, db_session
    ):
        """POST /api/viewer/validate must succeed for any valid share link."""
        doc = await _make_doc(db_session)
        link = await _make_link(db_session, doc)
        await db_session.commit()

        r = await unauth_client.post(
            "/api/viewer/validate", json={"token": link.token}
        )
        assert r.status_code == 200
        assert "session_id" in r.json()

    @pytest.mark.asyncio
    async def test_analytics_events_post_works_without_jwt(
        self, unauth_client, db_session
    ):
        """POST /api/analytics/events works without a JWT auth header.
        Requires only a valid share-link token + active viewer session.
        """
        doc = await _make_doc(db_session)
        link = await _make_link(db_session, doc)
        await db_session.commit()

        # First establish a real viewer session
        val = await unauth_client.post("/api/viewer/validate", json={"token": link.token})
        assert val.status_code == 200
        session_id = val.json()["session_id"]

        r = await unauth_client.post("/api/analytics/events", json={
            "token": link.token,
            "session_id": session_id,
            "event_type": "print_attempt",
            "page_number": 1,
        })
        assert r.status_code == 200
        assert r.json()["logged"] is True

    @pytest.mark.asyncio
    async def test_analytics_events_post_rejects_fake_session(
        self, unauth_client, db_session
    ):
        """A valid token with an inactive/fake session_id must be rejected with 403."""
        doc = await _make_doc(db_session)
        link = await _make_link(db_session, doc)
        await db_session.commit()

        r = await unauth_client.post("/api/analytics/events", json={
            "token": link.token,
            "session_id": "b" * 16,  # fake, never registered
            "event_type": "print_attempt",
        })
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_analytics_events_post_rejects_server_events(
        self, unauth_client, db_session
    ):
        """Server-side event types must return 400, not 401."""
        doc = await _make_doc(db_session)
        link = await _make_link(db_session, doc)
        await db_session.commit()

        val = await unauth_client.post("/api/viewer/validate", json={"token": link.token})
        session_id = val.json()["session_id"]

        r = await unauth_client.post("/api/analytics/events", json={
            "token": link.token,
            "session_id": session_id,
            "event_type": "opened",  # server-side only
        })
        assert r.status_code == 400


# ══════════════════════════════════════════════════════════════════════════
# 3. CROSS-USER ACCESS — blocked at every link operation
# ══════════════════════════════════════════════════════════════════════════

class TestCrossUserLinkAccess:
    """User A must not create, list, revoke, or patch links on User B's documents."""

    @pytest_asyncio.fixture
    async def user_b_doc(self, db_session) -> Document:
        doc = await _make_doc(db_session, user_id=TEST_USER_B_ID)
        await db_session.commit()
        return doc

    @pytest_asyncio.fixture
    async def user_b_link(self, db_session, user_b_doc) -> ShareLink:
        link = await _make_link(db_session, user_b_doc)
        await db_session.commit()
        return link

    @pytest.mark.asyncio
    async def test_user_a_cannot_create_link_for_user_b_document(
        self, client, user_b_doc
    ):
        r = await client.post(
            "/api/links", json={"document_id": str(user_b_doc.id)}
        )
        assert r.status_code == 404  # user B's doc is invisible to user A

    @pytest.mark.asyncio
    async def test_user_a_cannot_list_links_for_user_b_document(
        self, client, user_b_doc
    ):
        r = await client.get(f"/api/links?document_id={user_b_doc.id}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_user_a_cannot_revoke_user_b_link(
        self, client, user_b_link
    ):
        r = await client.delete(f"/api/links/{user_b_link.id}")
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_user_a_cannot_patch_user_b_link(
        self, client, user_b_link
    ):
        r = await client.patch(
            f"/api/links/{user_b_link.id}", json={"label": "hijacked"}
        )
        assert r.status_code == 403


class TestCrossUserDocumentAccess:
    """Verify document-level isolation (supplements TestDocumentOwnership)."""

    @pytest.mark.asyncio
    async def test_user_b_document_invisible_in_list(self, client, db_session):
        doc_b = await _make_doc(db_session, user_id=TEST_USER_B_ID)
        await db_session.commit()
        r = await client.get("/api/documents")
        assert r.status_code == 200
        assert str(doc_b.id) not in [d["id"] for d in r.json()["documents"]]

    @pytest.mark.asyncio
    async def test_user_b_document_returns_404_on_get(self, client, db_session):
        doc_b = await _make_doc(db_session, user_id=TEST_USER_B_ID)
        await db_session.commit()
        r = await client.get(f"/api/documents/{doc_b.id}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_user_b_document_returns_404_on_status(self, client, db_session):
        doc_b = await _make_doc(db_session, user_id=TEST_USER_B_ID)
        await db_session.commit()
        r = await client.get(f"/api/documents/{doc_b.id}/status")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_user_b_document_returns_404_on_delete(self, client, db_session):
        doc_b = await _make_doc(db_session, user_id=TEST_USER_B_ID)
        await db_session.commit()
        r = await client.delete(f"/api/documents/{doc_b.id}")
        assert r.status_code == 404  # must not leak document existence


class TestCrossUserAnalyticsAccess:
    """User A must not see user B's data in any analytics GET response."""

    @pytest.mark.asyncio
    async def test_user_b_events_not_visible_to_user_a(
        self, client, db_session
    ):
        doc_b = await _make_doc(db_session, user_id=TEST_USER_B_ID)
        link_b = await _make_link(db_session, doc_b)
        event_b = await _make_event(db_session, link_b)
        await db_session.commit()

        r = await client.get("/api/analytics/events")
        assert r.status_code == 200
        assert str(event_b.id) not in [e["id"] for e in r.json()["events"]]

    @pytest.mark.asyncio
    async def test_user_b_doc_not_in_analytics_documents(
        self, client, db_session
    ):
        doc_b = await _make_doc(db_session, user_id=TEST_USER_B_ID)
        await db_session.commit()

        r = await client.get("/api/analytics/documents")
        assert r.status_code == 200
        assert str(doc_b.id) not in [d["id"] for d in r.json()["documents"]]

    @pytest.mark.asyncio
    async def test_overview_does_not_count_user_b_documents(
        self, client, db_session
    ):
        # Empty DB for user A; create one doc for user B
        await _make_doc(db_session, user_id=TEST_USER_B_ID)
        await db_session.commit()

        r = await client.get("/api/analytics/overview")
        assert r.status_code == 200
        assert r.json()["total_documents"] == 0

    @pytest.mark.asyncio
    async def test_querying_user_b_doc_events_returns_empty(
        self, client, db_session
    ):
        doc_b = await _make_doc(db_session, user_id=TEST_USER_B_ID)
        link_b = await _make_link(db_session, doc_b)
        await _make_event(db_session, link_b)
        await db_session.commit()

        r = await client.get(f"/api/analytics/events?document_id={doc_b.id}")
        assert r.status_code == 200
        assert r.json()["events"] == []
        assert r.json()["total"] == 0
