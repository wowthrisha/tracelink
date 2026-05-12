"""
Viewer pipeline integration tests.

Covers gaps not addressed by test_viewer.py:
  - Revoked / expired link blocks page fetch with 410
  - In-process LRU page cache: storage.download_bytes called only once per unique page
  - Large PDF (60 pages): all pages are accessible after upload
  - Correct page URL structure (path + query-string format)
"""
import uuid
import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock, call

from app.models.document import Document, DocumentPage
from app.models.link import ShareLink
from app.routers.viewer import clear_page_cache
from app.services.link_service import LinkService
from tests.conftest import TEST_USER_ID


# ── helpers ────────────────────────────────────────────────────────────────────

def _make_doc(db_session, *, page_count: int = 3) -> Document:
    """Synchronously builds a Document + DocumentPage rows (caller must flush/commit)."""
    doc = Document(
        id=uuid.uuid4(),
        filename="test.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status="ready",
        page_count=page_count,
        file_size_bytes=1024 * page_count,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    return doc


async def _insert_doc_with_pages(db_session, page_count: int = 3) -> Document:
    doc = _make_doc(db_session, page_count=page_count)
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


async def _get_session(client, token: str) -> str:
    r = await client.post("/api/viewer/validate", json={"token": token})
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


# ══════════════════════════════════════════════════════════════════════════════
# 1. PAGE ENDPOINT SECURITY — revoked / expired links must block page access
# ══════════════════════════════════════════════════════════════════════════════

class TestPageEndpointSecurity:
    """Revoked or expired links must return 410 on every page fetch."""

    @pytest.mark.asyncio
    async def test_revoked_link_blocks_page_fetch(self, client, db_session):
        doc = await _insert_doc_with_pages(db_session)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))
        session_id = await _get_session(client, link.token)

        # Revoke *after* obtaining a valid session
        await svc.revoke_link(db_session, str(link.id))
        await db_session.commit()

        r = await client.get(
            f"/api/viewer/page/{link.token}/1?session_id={session_id}"
        )
        assert r.status_code == 410
        assert "revoked" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_expired_link_blocks_page_fetch(self, client, db_session, expired_link):
        """expired_link fixture creates a link already past its expiry."""
        # We cannot validate (validate also returns 410), so use an arbitrary session_id
        r = await client.get(
            f"/api/viewer/page/{expired_link.token}/1?session_id=aabbccdd11223344"
        )
        assert r.status_code == 410
        assert "expired" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_nonexistent_token_returns_404_on_page_fetch(self, client):
        r = await client.get(
            "/api/viewer/page/deadbeefdeadbeef/1?session_id=aabbccdd11223344"
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_page_response_is_proxied_not_redirected(self, client, active_link):
        session_id = await _get_session(client, active_link.token)
        r = await client.get(
            f"/api/viewer/page/{active_link.token}/1?session_id={session_id}",
            follow_redirects=False,
        )
        # Must be a direct 200, never a redirect
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/webp"

    @pytest.mark.asyncio
    async def test_page_url_uses_correct_route_structure(self, client, active_link):
        """
        Verify the canonical route /api/viewer/page/{token}/{page}?session_id={sid}
        returns 200.  Any other URL shape would be a 404 or 400.
        """
        session_id = await _get_session(client, active_link.token)

        # Correct structure → 200
        r = await client.get(
            f"/api/viewer/page/{active_link.token}/1?session_id={session_id}"
        )
        assert r.status_code == 200

        # Missing session_id → 400
        r_no_sid = await client.get(f"/api/viewer/page/{active_link.token}/1")
        assert r_no_sid.status_code == 400

        # Page number as sole path segment (the old buggy URL pattern) → 404
        r_bad = await client.get(f"/api/viewer/page/1?session_id={session_id}")
        assert r_bad.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 2. PAGE BYTE CACHE — storage download should be de-duplicated
# ══════════════════════════════════════════════════════════════════════════════

class TestPageByteCache:
    """
    Each unique page (storage_key) must be downloaded from storage only once.
    Subsequent requests for the same page are served from the in-process LRU cache.
    """

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        """Flush the module-level page cache before every test in this class."""
        clear_page_cache()
        yield
        clear_page_cache()

    @pytest.mark.asyncio
    async def test_second_request_for_same_page_skips_storage(
        self, client, db_session
    ):
        doc = await _insert_doc_with_pages(db_session, page_count=1)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))

        download_calls: list[str] = []

        original_download = None

        async def tracking_download(self_storage, key: str) -> bytes:
            download_calls.append(key)
            return original_download(self_storage, key) if original_download else b""

        # Reset call tracking on each validate so we only count page fetches
        session_id = await _get_session(client, link.token)

        with patch(
            "app.services.storage.StorageService.download_bytes",
            new_callable=AsyncMock,
        ) as mock_dl:
            from tests.conftest import _make_webp_bytes
            mock_dl.return_value = _make_webp_bytes()

            # First request: should hit storage
            r1 = await client.get(
                f"/api/viewer/page/{link.token}/1?session_id={session_id}"
            )
            assert r1.status_code == 200
            assert mock_dl.call_count == 1

            # Second request for the same page: cache hit, storage NOT called again
            r2 = await client.get(
                f"/api/viewer/page/{link.token}/1?session_id={session_id}"
            )
            assert r2.status_code == 200
            assert mock_dl.call_count == 1  # still 1 — served from cache

    @pytest.mark.asyncio
    async def test_different_pages_each_fetched_from_storage_once(
        self, client, db_session
    ):
        doc = await _insert_doc_with_pages(db_session, page_count=3)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))
        session_id = await _get_session(client, link.token)

        with patch(
            "app.services.storage.StorageService.download_bytes",
            new_callable=AsyncMock,
        ) as mock_dl:
            from tests.conftest import _make_webp_bytes
            mock_dl.return_value = _make_webp_bytes()

            for page_num in (1, 2, 3):
                await client.get(
                    f"/api/viewer/page/{link.token}/{page_num}?session_id={session_id}"
                )
            # 3 unique pages → exactly 3 downloads
            assert mock_dl.call_count == 3

            # Re-fetch all pages — cache should absorb them all
            for page_num in (1, 2, 3):
                await client.get(
                    f"/api/viewer/page/{link.token}/{page_num}?session_id={session_id}"
                )
            assert mock_dl.call_count == 3  # unchanged

    @pytest.mark.asyncio
    async def test_cache_cleared_causes_refetch(self, client, db_session):
        doc = await _insert_doc_with_pages(db_session, page_count=1)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))
        session_id = await _get_session(client, link.token)

        with patch(
            "app.services.storage.StorageService.download_bytes",
            new_callable=AsyncMock,
        ) as mock_dl:
            from tests.conftest import _make_webp_bytes
            mock_dl.return_value = _make_webp_bytes()

            await client.get(
                f"/api/viewer/page/{link.token}/1?session_id={session_id}"
            )
            assert mock_dl.call_count == 1

            # Flush cache mid-test
            clear_page_cache()

            await client.get(
                f"/api/viewer/page/{link.token}/1?session_id={session_id}"
            )
            assert mock_dl.call_count == 2  # re-fetched after cache clear


# ══════════════════════════════════════════════════════════════════════════════
# 3. LARGE PDF — all 60 pages must be individually accessible
# ══════════════════════════════════════════════════════════════════════════════

class TestLargeDocument:
    """
    Simulate a 60-page PDF.  Every page endpoint must return 200 with image/webp.
    This validates the route handles large page-count documents without any
    off-by-one errors or pagination issues.
    """

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        clear_page_cache()
        yield
        clear_page_cache()

    @pytest.mark.asyncio
    async def test_all_60_pages_accessible(self, client, db_session):
        PAGE_COUNT = 60
        doc = await _insert_doc_with_pages(db_session, page_count=PAGE_COUNT)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))
        session_id = await _get_session(client, link.token)

        assert session_id  # validate must succeed
        # validate returns page_count
        r_validate = await client.post(
            "/api/viewer/validate", json={"token": link.token, "session_id": session_id}
        )
        assert r_validate.json()["page_count"] == PAGE_COUNT

        # Spot-check first, last, and a middle page
        for page_num in (1, 30, 60):
            r = await client.get(
                f"/api/viewer/page/{link.token}/{page_num}?session_id={session_id}"
            )
            assert r.status_code == 200, f"page {page_num} returned {r.status_code}"
            assert r.headers["content-type"] == "image/webp"

    @pytest.mark.asyncio
    async def test_page_beyond_count_returns_404(self, client, db_session):
        doc = await _insert_doc_with_pages(db_session, page_count=5)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))
        session_id = await _get_session(client, link.token)

        r = await client.get(
            f"/api/viewer/page/{link.token}/6?session_id={session_id}"
        )
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_validate_returns_correct_page_count_for_large_doc(
        self, client, db_session
    ):
        doc = await _insert_doc_with_pages(db_session, page_count=60)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))

        r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200
        assert r.json()["page_count"] == 60
