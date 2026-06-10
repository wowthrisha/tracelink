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
            f"/api/viewer/page/{active_link.token}/1", headers={"X-Session-ID": sid}
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
                f"/api/viewer/page/{active_link.token}/1", headers={"X-Session-ID": sid}
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
                f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": sid}
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
            f"/api/viewer/page/{active_link.token}/1", headers={"X-Session-ID": sid}
        )
        assert "no-store" in r.headers.get("cache-control", "")
        assert r.headers.get("x-content-type-options") == "nosniff"

    @pytest.mark.asyncio
    async def test_watermark_exception_in_executor_propagates(self, client, active_link):
        """
        A RuntimeError raised inside run_in_executor must propagate — it must NOT
        be silently swallowed (which would allow watermark-free pages to be served).
        httpx ASGITransport re-raises server exceptions in test mode, so we assert
        the exception escapes rather than checking the HTTP status code.
        """
        body = await _validate(client, active_link.token)
        sid = body["session_id"]

        with patch.object(
            WatermarkService,
            "apply_visible_watermark",
            side_effect=RuntimeError("PIL exploded"),
        ):
            with pytest.raises(RuntimeError, match="PIL exploded"):
                await client.get(
                    f"/api/viewer/page/{active_link.token}/1", headers={"X-Session-ID": sid}
                )


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

        # AnalyticsService.log_event stores only session_id[:8] (SEC-05 truncation).
        result = await db_session.execute(
            select(AccessEvent).where(
                AccessEvent.link_id == active_link.id,
                AccessEvent.event_type == "opened",
                AccessEvent.session_id == sid[:8],
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
    async def test_validate_increments_view_count_atomically(
        self, db_session, ready_document
    ):
        """validate_link must increment view_count via atomic UPDATE and reflect the change."""
        from app.services.analytics_service import AnalyticsService
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(ready_document.id))
        initial = link.view_count  # 0

        await svc.validate_link(
            db=db_session,
            token=link.token,
            analytics_svc=AnalyticsService(),
            commit=True,
        )
        await db_session.refresh(link)
        assert link.view_count == initial + 1

    @pytest.mark.asyncio
    async def test_validate_does_not_exceed_max_views(
        self, db_session, ready_document
    ):
        """validate_link with max_views=1 must reject the second call with 410."""
        from app.services.analytics_service import AnalyticsService
        from fastapi import HTTPException
        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(ready_document.id),
            max_views=1,
        )

        # First validate: should succeed
        await svc.validate_link(
            db=db_session,
            token=link.token,
            analytics_svc=AnalyticsService(),
            commit=True,
        )

        # Second validate: must raise 410
        with pytest.raises(HTTPException) as exc_info:
            await svc.validate_link(
                db=db_session,
                token=link.token,
                analytics_svc=AnalyticsService(),
                commit=True,
            )
        assert exc_info.value.status_code == 410

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

    @pytest.mark.asyncio
    async def test_validate_all_three_writes_rollback_atomically(
        self, db_session, ready_document
    ):
        """
        Stage all three writes (session, view_count, event) with commit=False
        and then roll back — none must be visible in the DB.
        """
        from app.services.analytics_service import AnalyticsService
        svc = LinkService()
        analytics_svc = AnalyticsService()
        link = await svc.create_link(db_session, document_id=str(ready_document.id))
        initial_views = link.view_count  # 0

        # validate_link now atomically increments view_count inside a single call.
        # With commit=False, the session upsert and view_count update are staged
        # but not flushed; rollback undoes both.
        result = await svc.validate_link(
            db=db_session,
            token=link.token,
            analytics_svc=analytics_svc,
            commit=False,
        )
        sid = result.session_id

        await analytics_svc.log_event(
            db_session,
            link_id=link.id,
            event_type="opened",
            session_id=sid,
            commit=False,
        )

        # Roll back everything — none of the writes must be durable
        await db_session.rollback()

        session_row = await db_session.get(ViewerSession, sid)
        assert session_row is None, "session must not be present after rollback"

        await db_session.refresh(link)
        assert link.view_count == initial_views, "view_count must not be incremented after rollback"

        ev_result = await db_session.execute(
            select(AccessEvent).where(
                AccessEvent.link_id == link.id,
                AccessEvent.event_type == "opened",
            )
        )
        assert len(ev_result.scalars().all()) == 0, "opened event must not be present after rollback"

    @pytest.mark.asyncio
    async def test_validate_max_views_enforced_with_batch_commit(
        self, client, db_session, ready_document
    ):
        """
        With max_views=1: first validate must succeed and commit all three
        writes atomically; second validate must return 410 Max views reached.
        """
        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(ready_document.id),
            max_views=1,
        )

        # First validate must succeed
        body = await _validate(client, link.token)
        assert "session_id" in body

        # Confirm view_count was committed (batch commit path)
        await db_session.refresh(link)
        assert link.view_count == 1

        # Second validate must be rejected (max views exhausted)
        r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 410
        assert "max views" in r.json().get("detail", "").lower()


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
            f"/api/viewer/thumb/{active_link.token}/1", headers={"X-Session-ID": sid}
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
                f"/api/viewer/thumb/{link.token}/1", headers={"X-Session-ID": sid}
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
            f"/api/viewer/thumb/{active_link.token}/1", headers={"X-Session-ID": sid}
        )
        assert "no-store" in r.headers.get("cache-control", "")
