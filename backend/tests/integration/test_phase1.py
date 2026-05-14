"""
Phase 1 production-hardening tests.

Covers:
  A) Watermark offload — page endpoint still returns correct watermarked bytes
     after moving PIL work to a thread-pool executor.
  B) Validate batch commit — session upsert, view count increment, and opened
     event are all written in a single DB round-trip.
  C) Thumbnail endpoint wiring — backend thumb route is accessible and returns
     correct bytes; fallback still works when thumbnail asset is absent.
"""
import uuid
import pytest
from unittest.mock import patch, AsyncMock

from app.models.document import Document, DocumentPage
from app.models.event import AccessEvent
from app.models.session import ViewerSession
from app.routers.viewer import clear_page_cache, clear_thumb_cache
from app.services.link_service import LinkService
from app.services.watermark import WatermarkService
from tests.conftest import TEST_USER_ID, _make_webp_bytes
from sqlalchemy import select


# ── helpers ────────────────────────────────────────────────────────────────────

async def _insert_doc_with_pages(db_session, page_count: int = 3) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename="phase1.pdf",
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
# A. WATERMARK OFFLOAD
# ══════════════════════════════════════════════════════════════════════════════

class TestWatermarkOffload:
    """
    After moving apply_visible_watermark to run_in_executor, the page endpoint
    must still return valid watermarked WebP bytes and the watermark function
    must be called exactly once per request.
    """

    @pytest.fixture(autouse=True)
    def _clear(self):
        clear_page_cache()
        yield
        clear_page_cache()

    @pytest.mark.asyncio
    async def test_page_returns_webp_after_executor_offload(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.get(
            f"/api/viewer/page/{active_link.token}/1?session_id={sid}"
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/webp"
        assert len(r.content) > 0

    @pytest.mark.asyncio
    async def test_watermark_function_called_via_executor(self, client, active_link):
        """WatermarkService.apply_visible_watermark must be called once per page request."""
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        # patch.object replaces the class method; side_effect does NOT receive self,
        # so use return_value and inspect call_args instead.
        with patch.object(
            WatermarkService, "apply_visible_watermark", return_value=_make_webp_bytes()
        ) as mock_wm:
            r = await client.get(
                f"/api/viewer/page/{active_link.token}/1?session_id={sid}"
            )

        assert r.status_code == 200
        assert mock_wm.call_count == 1
        # Second positional arg is the watermark text (after image_bytes)
        watermark_text_arg = mock_wm.call_args[0][1]
        assert f"sess:{sid[:6]}" in watermark_text_arg

    @pytest.mark.asyncio
    async def test_page_bytes_differ_from_raw_storage_bytes(self, client, db_session):
        """Returned bytes must differ from the raw storage bytes (watermark was applied)."""
        doc = await _insert_doc_with_pages(db_session, page_count=1)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))
        body = await _validate(client, link.token)
        sid = body["session_id"]

        raw_webp = _make_webp_bytes()

        with patch(
            "app.services.storage.StorageService.download_bytes",
            new_callable=AsyncMock,
            return_value=raw_webp,
        ):
            r = await client.get(
                f"/api/viewer/page/{link.token}/1?session_id={sid}"
            )

        assert r.status_code == 200
        # Watermarked output must differ from the raw input
        assert r.content != raw_webp

    @pytest.mark.asyncio
    async def test_page_no_cache_headers_preserved(self, client, active_link):
        """Security headers must be present after the executor change."""
        body = await _validate(client, active_link.token)
        sid = body["session_id"]
        r = await client.get(
            f"/api/viewer/page/{active_link.token}/1?session_id={sid}"
        )
        assert "no-store" in r.headers.get("cache-control", "")
        assert r.headers.get("x-content-type-options") == "nosniff"


# ══════════════════════════════════════════════════════════════════════════════
# B. VALIDATE BATCH COMMIT
# ══════════════════════════════════════════════════════════════════════════════

class TestValidateBatchCommit:
    """
    The validate endpoint must write session, view count, and opened event in a
    single DB commit.  Each write must be durable after the response returns.
    """

    @pytest.mark.asyncio
    async def test_validate_writes_session_to_db(self, client, db_session, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        session = await db_session.get(ViewerSession, sid)
        assert session is not None
        assert str(session.link_id) == str(active_link.id)

    @pytest.mark.asyncio
    async def test_validate_increments_view_count(self, client, db_session, active_link):
        initial = active_link.view_count
        await _validate(client, active_link.token)
        await db_session.refresh(active_link)
        assert active_link.view_count == initial + 1

    @pytest.mark.asyncio
    async def test_validate_logs_opened_event(self, client, db_session, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        result = await db_session.execute(
            select(AccessEvent).where(
                AccessEvent.link_id == active_link.id,
                AccessEvent.event_type == "opened",
                AccessEvent.session_id == sid,
            )
        )
        events = result.scalars().all()
        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_validate_all_three_writes_durable_after_response(
        self, client, db_session, active_link
    ):
        """All three writes (session, view_count, event) must be visible after response."""
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        # Session present
        session = await db_session.get(ViewerSession, sid)
        assert session is not None

        # View count incremented
        await db_session.refresh(active_link)
        assert active_link.view_count == 1

        # Event present
        ev_result = await db_session.execute(
            select(AccessEvent).where(
                AccessEvent.link_id == active_link.id,
                AccessEvent.event_type == "opened",
            )
        )
        assert len(ev_result.scalars().all()) == 1

    @pytest.mark.asyncio
    async def test_increment_view_count_commit_false_defers_write(
        self, db_session, ready_document
    ):
        """increment_view_count(commit=False) must stage the update without committing it."""
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(ready_document.id))
        initial = link.view_count  # 0

        await svc.increment_view_count(db_session, str(link.id), commit=False)

        # Roll back the un-committed write; count must return to initial
        await db_session.rollback()
        await db_session.refresh(link)
        assert link.view_count == initial

    @pytest.mark.asyncio
    async def test_increment_view_count_commit_true_persists(
        self, db_session, ready_document
    ):
        """increment_view_count(commit=True) must persist the increment immediately."""
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(ready_document.id))
        await svc.increment_view_count(db_session, str(link.id), commit=True)
        await db_session.refresh(link)
        assert link.view_count == 1

    @pytest.mark.asyncio
    async def test_validate_link_commit_false_defers_session(
        self, db_session, ready_document
    ):
        """validate_link(commit=False) must stage session upsert without committing."""
        from app.services.analytics_service import AnalyticsService
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(ready_document.id))

        result = await svc.validate_link(
            db=db_session,
            token=link.token,
            analytics_svc=AnalyticsService(),
            commit=False,
        )
        sid = result.session_id

        # Roll back the un-committed session; it must not be found in DB
        await db_session.rollback()
        session_row = await db_session.get(ViewerSession, sid)
        assert session_row is None


# ══════════════════════════════════════════════════════════════════════════════
# C. THUMBNAIL ENDPOINT WIRING (backend contract)
# ══════════════════════════════════════════════════════════════════════════════

class TestThumbnailBackendContract:
    """
    Verify the thumbnail URL contract that the frontend now depends on.
    These complement the broader TestThumbnailEndpoint suite in test_viewer_pipeline.py.
    """

    @pytest.fixture(autouse=True)
    def _clear(self):
        clear_page_cache()
        clear_thumb_cache()
        yield
        clear_page_cache()
        clear_thumb_cache()

    @pytest.mark.asyncio
    async def test_thumb_url_matches_expected_pattern(self, client, active_link):
        """Verify the route /api/viewer/thumb/{token}/{page}?session_id={sid} returns 200."""
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        r = await client.get(
            f"/api/viewer/thumb/{active_link.token}/1?session_id={sid}"
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/webp"

    @pytest.mark.asyncio
    async def test_thumb_fallback_to_full_res_when_thumbnail_absent(
        self, client, db_session
    ):
        """
        When the thumbnail asset does not exist in storage, the endpoint must fall
        back to the full-resolution page bytes rather than returning 503.
        """
        doc = await _insert_doc_with_pages(db_session, page_count=1)
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(doc.id))
        body = await _validate(client, link.token)
        sid = body["session_id"]

        call_order: list = []

        async def selective_download(self_storage, key: str) -> bytes:
            call_order.append(key)
            if key.startswith("thumbs/"):
                raise FileNotFoundError("thumb not found")
            return _make_webp_bytes()

        with patch(
            "app.services.storage.StorageService.download_bytes",
            new=selective_download,
        ):
            r = await client.get(
                f"/api/viewer/thumb/{link.token}/1?session_id={sid}"
            )

        assert r.status_code == 200
        assert r.headers["content-type"] == "image/webp"
        # Must have tried thumb key first, then fallen back to full-res key
        assert any(k.startswith("thumbs/") for k in call_order)
        assert any(k.startswith("pages/") for k in call_order)

    @pytest.mark.asyncio
    async def test_thumb_session_id_required(self, client, active_link):
        r = await client.get(f"/api/viewer/thumb/{active_link.token}/1")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_thumb_no_cache_headers(self, client, active_link):
        body = await _validate(client, active_link.token)
        sid = body["session_id"]
        r = await client.get(
            f"/api/viewer/thumb/{active_link.token}/1?session_id={sid}"
        )
        assert "no-store" in r.headers.get("cache-control", "")
