"""
Integration tests for the document processing pipeline.

These tests exercise process_document_with_session() directly — no Celery,
no Redis, no real S3.  Storage and rasterizer are mocked so tests remain
deterministic and fast.

Coverage:
  1. Happy path: uploaded → ready, correct page records created
  2. Multi-page PDF: N pages → N DocumentPage rows
  3. Recovery: document stuck in processing is cleaned up and re-processed
  4. Skip: already-ready document is not re-processed
  5. Viewer returns 503 (not 404) when document is not yet processed
  6. Viewer returns 503 when document is still processing
  7. Viewer returns 200 once document is ready
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.document import Document, DocumentPage
from app.models.link import ShareLink
from app.services.link_service import LinkService
from app.workers.tasks import process_document_with_session, _STALE_PROCESSING_THRESHOLD
from tests.conftest import TEST_USER_ID, _make_webp_bytes


# ── fixtures ───────────────────────────────────────────────────────────────────

@dataclass
class _FakePage:
    page_number: int
    image_bytes: bytes
    width_px: int = 595
    height_px: int = 842


def _make_mock_rasterizer(page_count: int = 1):
    """Return a mock rasterizer whose stream_rasterized_pages yields fake pages."""
    rasterizer = MagicMock()
    pages = [_FakePage(page_number=i, image_bytes=_make_webp_bytes()) for i in range(1, page_count + 1)]
    def _side_effect(*args, **kwargs):
        async def _gen():
            for p in pages:
                yield p
        return _gen()
    rasterizer.stream_rasterized_pages = MagicMock(side_effect=_side_effect)
    return rasterizer


def _make_mock_storage():
    storage = MagicMock()
    storage.download_bytes = AsyncMock(return_value=b"%PDF-1.4 fake pdf")
    storage.upload_file = AsyncMock(return_value=None)
    return storage


def _make_mock_watermark():
    wm = MagicMock()
    wm.apply_forensic_stamp = MagicMock(side_effect=lambda img, *_: img)
    return wm


async def _make_uploaded_doc(db_session, *, page_count_hint: int = 1) -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename="pipeline_test.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status="uploaded",
        file_size_bytes=1024,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


# ── 1. Happy path ──────────────────────────────────────────────────────────────

class TestProcessDocumentWithSession:

    @pytest.mark.asyncio
    async def test_uploaded_doc_becomes_ready(self, db_session):
        doc = await _make_uploaded_doc(db_session)

        result = await process_document_with_session(
            db_session,
            str(doc.id),
            _make_mock_storage(),
            _make_mock_rasterizer(page_count=1),
            _make_mock_watermark(),
        )

        assert result["status"] == "ready"
        assert result["page_count"] == 1
        await db_session.refresh(doc)
        assert doc.status == "ready"
        assert doc.page_count == 1

    @pytest.mark.asyncio
    async def test_document_page_records_are_created(self, db_session):
        doc = await _make_uploaded_doc(db_session)

        await process_document_with_session(
            db_session,
            str(doc.id),
            _make_mock_storage(),
            _make_mock_rasterizer(page_count=1),
            _make_mock_watermark(),
        )

        pages_result = await db_session.execute(
            select(DocumentPage)
            .where(DocumentPage.document_id == doc.id)
            .order_by(DocumentPage.page_number)
        )
        pages = pages_result.scalars().all()
        assert len(pages) == 1
        assert pages[0].page_number == 1
        assert pages[0].storage_key == f"pages/{doc.id}/0001.webp"

    # ── 2. Multi-page ──────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_multipage_pdf_creates_correct_page_records(self, db_session):
        PAGE_COUNT = 5
        doc = await _make_uploaded_doc(db_session)

        result = await process_document_with_session(
            db_session,
            str(doc.id),
            _make_mock_storage(),
            _make_mock_rasterizer(page_count=PAGE_COUNT),
            _make_mock_watermark(),
        )

        assert result["page_count"] == PAGE_COUNT

        pages_result = await db_session.execute(
            select(DocumentPage)
            .where(DocumentPage.document_id == doc.id)
            .order_by(DocumentPage.page_number)
        )
        pages = pages_result.scalars().all()
        assert len(pages) == PAGE_COUNT
        for i, page in enumerate(pages, start=1):
            assert page.page_number == i
            assert page.storage_key == f"pages/{doc.id}/{i:04d}.webp"

    @pytest.mark.asyncio
    async def test_storage_upload_called_twice_per_page(self, db_session):
        """Each page produces 2 uploads: full-res + thumbnail."""
        PAGE_COUNT = 3
        doc = await _make_uploaded_doc(db_session)
        storage = _make_mock_storage()

        await process_document_with_session(
            db_session,
            str(doc.id),
            storage,
            _make_mock_rasterizer(page_count=PAGE_COUNT),
            _make_mock_watermark(),
        )

        # 1 full-res + 1 thumbnail per page
        assert storage.upload_file.call_count == PAGE_COUNT * 2

        # Full-res keys: pages/{doc_id}/{page:04d}.webp
        # Thumbnail keys: thumbs/{doc_id}/{page:04d}.webp
        upload_keys = [c.args[1] for c in storage.upload_file.call_args_list]
        page_keys = [k for k in upload_keys if k.startswith("pages/")]
        thumb_keys = [k for k in upload_keys if k.startswith("thumbs/")]
        assert len(page_keys) == PAGE_COUNT
        assert len(thumb_keys) == PAGE_COUNT

    # ── 3. Recovery ────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_stale_processing_doc_is_recovered(self, db_session):
        """Document stuck in processing past threshold is reprocessed."""
        doc = Document(
            id=uuid.uuid4(),
            filename="stuck.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="processing",
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()

        # Back-date updated_at past the threshold
        stale_ts = datetime.now(timezone.utc) - _STALE_PROCESSING_THRESHOLD - timedelta(minutes=1)
        doc.updated_at = stale_ts
        await db_session.commit()
        await db_session.refresh(doc)

        result = await process_document_with_session(
            db_session,
            str(doc.id),
            _make_mock_storage(),
            _make_mock_rasterizer(page_count=2),
            _make_mock_watermark(),
        )

        assert result["status"] == "ready"
        assert result["page_count"] == 2

    @pytest.mark.asyncio
    async def test_stale_processing_deletes_partial_pages_before_reprocessing(
        self, db_session
    ):
        """Partial pages from a crashed run must be removed before reprocessing."""
        doc = Document(
            id=uuid.uuid4(),
            filename="partial.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="processing",
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()

        # Insert a stale partial page
        stale_page = DocumentPage(
            document_id=doc.id,
            page_number=1,
            storage_key=f"pages/{doc.id}/0001.webp",
            width_px=595,
            height_px=842,
        )
        db_session.add(stale_page)
        stale_ts = datetime.now(timezone.utc) - _STALE_PROCESSING_THRESHOLD - timedelta(minutes=1)
        doc.updated_at = stale_ts
        await db_session.commit()
        await db_session.refresh(doc)

        await process_document_with_session(
            db_session,
            str(doc.id),
            _make_mock_storage(),
            _make_mock_rasterizer(page_count=3),
            _make_mock_watermark(),
        )

        pages_result = await db_session.execute(
            select(DocumentPage).where(DocumentPage.document_id == doc.id)
        )
        pages = pages_result.scalars().all()
        # Old stale page gone; 3 fresh pages present
        assert len(pages) == 3

    # ── 3b. Thumbnails ─────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_thumbnail_uploaded_for_each_page(self, db_session):
        """Each page must have a corresponding thumbnail at thumbs/{doc_id}/{page:04d}.webp."""
        PAGE_COUNT = 2
        doc = await _make_uploaded_doc(db_session)
        storage = _make_mock_storage()

        await process_document_with_session(
            db_session,
            str(doc.id),
            storage,
            _make_mock_rasterizer(page_count=PAGE_COUNT),
            _make_mock_watermark(),
        )

        upload_keys = [c.args[1] for c in storage.upload_file.call_args_list]
        for i in range(1, PAGE_COUNT + 1):
            expected_thumb = f"thumbs/{doc.id}/{i:04d}.webp"
            assert expected_thumb in upload_keys, f"Missing thumbnail key: {expected_thumb}"

    @pytest.mark.asyncio
    async def test_thumbnail_failure_does_not_abort_processing(self, db_session):
        """If thumbnail generation raises, document still becomes ready."""
        from unittest.mock import patch

        doc = await _make_uploaded_doc(db_session)

        with patch(
            "app.workers.pipeline.pdf._make_thumbnail",
            side_effect=RuntimeError("thumbnail codec error"),
        ):
            result = await process_document_with_session(
                db_session,
                str(doc.id),
                _make_mock_storage(),
                _make_mock_rasterizer(page_count=1),
                _make_mock_watermark(),
            )

        assert result["status"] == "ready"
        await db_session.refresh(doc)
        assert doc.status == "ready"

    # ── 4. Skip ────────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_ready_document_is_skipped(self, db_session):
        doc = Document(
            id=uuid.uuid4(),
            filename="already_ready.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="ready",
            page_count=2,
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        storage = _make_mock_storage()
        result = await process_document_with_session(
            db_session,
            str(doc.id),
            storage,
            _make_mock_rasterizer(),
            _make_mock_watermark(),
        )

        assert result["status"] == "ready"
        storage.download_bytes.assert_not_called()
        storage.upload_file.assert_not_called()


# ── 5 & 6 & 7. Viewer status guards ──────────────────────────────────────────

class TestViewerDocumentStatusGuard:
    """
    Viewer /page endpoint must return 503 (not 404) when the document has not
    yet been fully processed, and 200 once it is ready.
    """

    async def _make_link_for_doc(self, db_session, doc: Document) -> ShareLink:
        svc = LinkService()
        return await svc.create_link(db_session, document_id=str(doc.id))

    async def _validate(self, client, token: str) -> str:
        r = await client.post("/api/viewer/validate", json={"token": token})
        # validate may itself return non-200 if doc not found — that's fine for these tests
        if r.status_code == 200:
            return r.json()["session_id"]
        return "fallback-session-id"

    @pytest.mark.asyncio
    async def test_uploaded_doc_returns_503_on_page_fetch(self, client, db_session):
        doc = Document(
            id=uuid.uuid4(),
            filename="not_ready.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="uploaded",
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        link = await self._make_link_for_doc(db_session, doc)
        session_id = await self._validate(client, link.token)

        r = await client.get(
            f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": session_id}
        )
        assert r.status_code == 503
        assert "queued" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_processing_doc_returns_503_on_page_fetch(self, client, db_session):
        doc = Document(
            id=uuid.uuid4(),
            filename="in_progress.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="processing",
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        link = await self._make_link_for_doc(db_session, doc)
        session_id = await self._validate(client, link.token)

        r = await client.get(
            f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": session_id}
        )
        assert r.status_code == 503
        assert "processing" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_error_doc_returns_503_on_page_fetch(self, client, db_session):
        doc = Document(
            id=uuid.uuid4(),
            filename="failed.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="error",
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        link = await self._make_link_for_doc(db_session, doc)
        session_id = await self._validate(client, link.token)

        r = await client.get(
            f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": session_id}
        )
        assert r.status_code == 503
        assert "failed" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_ready_doc_returns_200_on_page_fetch(self, client, db_session):
        """End-to-end: simulate post-processing state and confirm 200."""
        # Insert a ready document with one page
        doc = Document(
            id=uuid.uuid4(),
            filename="done.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="ready",
            page_count=1,
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        db_session.add(DocumentPage(
            document_id=doc.id,
            page_number=1,
            storage_key=f"pages/{doc.id}/0001.webp",
            width_px=595,
            height_px=842,
        ))
        await db_session.commit()
        await db_session.refresh(doc)

        link = await self._make_link_for_doc(db_session, doc)
        r_validate = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r_validate.status_code == 200
        session_id = r_validate.json()["session_id"]

        r = await client.get(
            f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": session_id}
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/webp"
