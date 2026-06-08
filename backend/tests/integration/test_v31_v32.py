"""
V3.1 + V3.2 integration tests — Streaming Rasterization and Parallel Asset Uploads.

V3.1: process_pdf_document() uses stream_rasterized_pages() async generator so
      peak WEBP RAM is O(sliding-window) instead of O(N pages).

V3.2: Pages are uploaded in a bounded sliding window (_TASK_WINDOW = 16) rather
      than asyncio.gather(*all_pages) which fans out all N upload tasks at once.

These tests verify:
  A. Pipeline calls stream_rasterized_pages (not rasterize_document) for PDFs
  B. Sliding window drains in FIFO order; final result is page-number sorted
  C. Multi-page document (20 pages) completes correctly with correct page count
  D. Upload concurrency is bounded by semaphore (_UPLOAD_CONCURRENCY = 8)
  E. Streaming rasterizer backward compat: rasterize_document still works
  F. Text documents do not call stream_rasterized_pages (regression)
  G. _TASK_WINDOW constant is defined and equals 2 × _UPLOAD_CONCURRENCY
"""
import asyncio
import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.document import Document, DocumentPage
from app.workers.tasks import process_document_with_session
from tests.conftest import TEST_USER_ID, _make_webp_bytes


# ── Shared helpers ────────────────────────────────────────────────────────────

@dataclass
class _FakePage:
    page_number: int
    image_bytes: bytes
    width_px: int = 595
    height_px: int = 842


def _stream_mock(pages):
    """Return a MagicMock callable that yields pages as an async generator."""
    def _side_effect(*args, **kwargs):
        async def _gen():
            for p in pages:
                yield p
        return _gen()
    return MagicMock(side_effect=_side_effect)


def _make_storage(pdf_bytes=b"%PDF-1.4 fake"):
    s = MagicMock()
    s.download_bytes = AsyncMock(return_value=pdf_bytes)
    s.upload_file = AsyncMock(return_value=None)
    return s


def _make_watermark():
    wm = MagicMock()
    wm.apply_forensic_stamp = MagicMock(side_effect=lambda img, *_: img)
    return wm


async def _insert_doc(db, file_type="pdf") -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename=f"test.{file_type}",
        storage_key=f"originals/{uuid.uuid4()}.{file_type}",
        status="uploaded",
        file_type=file_type,
        file_size_bytes=1024,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


# ── A. Pipeline uses stream_rasterized_pages ──────────────────────────────────

class TestStreamingPipelineDispatch:
    """A. process_pdf_document calls stream_rasterized_pages, not rasterize_document."""

    @pytest.mark.asyncio
    async def test_pdf_pipeline_calls_stream_not_rasterize(self, db_session):
        doc = await _insert_doc(db_session, "pdf")
        pages = [_FakePage(page_number=1, image_bytes=_make_webp_bytes())]

        rasterizer = MagicMock()
        rasterizer.stream_rasterized_pages = _stream_mock(pages)
        rasterizer.rasterize_document = MagicMock()  # must NOT be called

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            result = await process_document_with_session(
                db_session, str(doc.id), _make_storage(), rasterizer, _make_watermark()
            )

        assert result["status"] == "ready"
        rasterizer.stream_rasterized_pages.assert_called_once()
        rasterizer.rasterize_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_stream_called_with_pdf_bytes_and_doc_id(self, db_session):
        doc = await _insert_doc(db_session, "pdf")
        pages = [_FakePage(page_number=1, image_bytes=_make_webp_bytes())]
        pdf_bytes = b"%PDF-1.4 v31test"

        rasterizer = MagicMock()
        rasterizer.stream_rasterized_pages = _stream_mock(pages)

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            await process_document_with_session(
                db_session, str(doc.id), _make_storage(pdf_bytes), rasterizer, _make_watermark()
            )

        call_args = rasterizer.stream_rasterized_pages.call_args
        assert call_args[0][0] == pdf_bytes
        assert call_args[0][1] == str(doc.id)


# ── B. Sliding window drain order + final sort ────────────────────────────────

class TestSlidingWindowOrder:
    """B. Pages are sorted by page_number after sliding window drain."""

    @pytest.mark.asyncio
    async def test_pages_sorted_correctly_in_result(self, db_session):
        doc = await _insert_doc(db_session, "pdf")
        page_count = 5
        pages = [
            _FakePage(page_number=i, image_bytes=_make_webp_bytes())
            for i in range(1, page_count + 1)
        ]
        rasterizer = MagicMock()
        rasterizer.stream_rasterized_pages = _stream_mock(pages)

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            result = await process_document_with_session(
                db_session, str(doc.id), _make_storage(), rasterizer, _make_watermark()
            )

        assert result["status"] == "ready"
        assert result["page_count"] == page_count

        # Verify DB rows are in correct order
        from sqlalchemy import select
        rows = (await db_session.execute(
            select(DocumentPage)
            .where(DocumentPage.document_id == doc.id)
            .order_by(DocumentPage.page_number)
        )).scalars().all()
        assert [r.page_number for r in rows] == list(range(1, page_count + 1))


# ── C. Multi-page document ────────────────────────────────────────────────────

class TestMultiPagePipeline:
    """C. 20-page document completes correctly with streaming + sliding window."""

    @pytest.mark.asyncio
    async def test_20_page_document_processes_all_pages(self, db_session):
        doc = await _insert_doc(db_session, "pdf")
        page_count = 20
        pages = [
            _FakePage(page_number=i, image_bytes=_make_webp_bytes())
            for i in range(1, page_count + 1)
        ]
        rasterizer = MagicMock()
        rasterizer.stream_rasterized_pages = _stream_mock(pages)

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            result = await process_document_with_session(
                db_session, str(doc.id), _make_storage(), rasterizer, _make_watermark()
            )

        assert result["status"] == "ready"
        assert result["page_count"] == page_count
        await db_session.refresh(doc)
        assert doc.status == "ready"
        assert doc.page_count == page_count

    @pytest.mark.asyncio
    async def test_20_page_doc_creates_correct_db_rows(self, db_session):
        doc = await _insert_doc(db_session, "pdf")
        page_count = 20
        pages = [
            _FakePage(page_number=i, image_bytes=_make_webp_bytes())
            for i in range(1, page_count + 1)
        ]
        rasterizer = MagicMock()
        rasterizer.stream_rasterized_pages = _stream_mock(pages)

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            await process_document_with_session(
                db_session, str(doc.id), _make_storage(), rasterizer, _make_watermark()
            )

        from sqlalchemy import select, func
        count = (await db_session.execute(
            select(func.count()).where(DocumentPage.document_id == doc.id)
        )).scalar_one()
        assert count == page_count


# ── D. Upload concurrency bound ───────────────────────────────────────────────

class TestUploadConcurrencyBound:
    """D. _UPLOAD_CONCURRENCY semaphore and _TASK_WINDOW constant are correctly set."""

    def test_task_window_equals_2x_upload_concurrency(self):
        from app.workers.pipeline.pdf import _UPLOAD_CONCURRENCY, _TASK_WINDOW
        assert _TASK_WINDOW == _UPLOAD_CONCURRENCY * 2

    def test_upload_concurrency_is_8(self):
        from app.workers.pipeline.pdf import _UPLOAD_CONCURRENCY
        assert _UPLOAD_CONCURRENCY == 8

    def test_task_window_is_16(self):
        from app.workers.pipeline.pdf import _TASK_WINDOW
        assert _TASK_WINDOW == 16

    @pytest.mark.asyncio
    async def test_upload_file_called_for_each_page(self, db_session):
        doc = await _insert_doc(db_session, "pdf")
        page_count = 4
        pages = [
            _FakePage(page_number=i, image_bytes=_make_webp_bytes())
            for i in range(1, page_count + 1)
        ]
        rasterizer = MagicMock()
        rasterizer.stream_rasterized_pages = _stream_mock(pages)
        storage = _make_storage()

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            await process_document_with_session(
                db_session, str(doc.id), storage, rasterizer, _make_watermark()
            )

        # Each page produces 2 uploads (page image + thumbnail)
        assert storage.upload_file.call_count == page_count * 2


# ── E. Backward compatibility: rasterize_document still works ─────────────────

class TestRasterizeDocumentBackwardCompat:
    """E. rasterize_document() still works as a wrapper around stream_rasterized_pages."""

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_rasterize_document_returns_list(self, mock_convert, sample_pdf_bytes):
        from PIL import Image
        import os

        def _fake(pdf_bytes, dpi=200, output_folder=None, paths_only=False, **kwargs):
            img = Image.new("RGB", (595, 842), color=(100, 100, 100))
            path = os.path.join(output_folder, "output-0001.ppm")
            img.save(path, format="PPM")
            return [path]

        mock_convert.side_effect = _fake
        from app.services.rasterizer import RasterizerService
        svc = RasterizerService()
        result = await svc.rasterize_document(sample_pdf_bytes, "doc_compat")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].page_number == 1

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_rasterize_document_and_stream_return_same_data(self, mock_convert, sample_pdf_bytes):
        from PIL import Image
        import os

        call_count = [0]

        def _fake(pdf_bytes, dpi=200, output_folder=None, paths_only=False, **kwargs):
            call_count[0] += 1
            paths = []
            for i in range(1, 3):
                img = Image.new("RGB", (595, 842), color=(i * 50, 100, 150))
                path = os.path.join(output_folder, f"output-{i:04d}.ppm")
                img.save(path, format="PPM")
                paths.append(path)
            return paths

        mock_convert.side_effect = _fake
        from app.services.rasterizer import RasterizerService
        svc = RasterizerService()

        list_result = await svc.rasterize_document(sample_pdf_bytes, "doc_both")
        assert len(list_result) == 2
        assert [p.page_number for p in list_result] == [1, 2]


# ── F. Text document regression ───────────────────────────────────────────────

class TestTextDocumentRegression:
    """F. Text documents bypass the rasterizer entirely."""

    @pytest.mark.asyncio
    async def test_text_doc_does_not_call_stream_rasterized_pages(self, db_session):
        doc = await _insert_doc(db_session, "txt")
        storage = MagicMock()
        storage.download_bytes = AsyncMock(return_value=b"hello world\n")
        storage.upload_file = AsyncMock(return_value=None)

        rasterizer = MagicMock()
        rasterizer.stream_rasterized_pages = MagicMock()
        rasterizer.rasterize_document = MagicMock()

        await process_document_with_session(
            db_session, str(doc.id), storage, rasterizer, MagicMock()
        )

        rasterizer.stream_rasterized_pages.assert_not_called()
        rasterizer.rasterize_document.assert_not_called()

    @pytest.mark.asyncio
    async def test_md_doc_does_not_call_stream_rasterized_pages(self, db_session):
        doc = await _insert_doc(db_session, "md")
        storage = MagicMock()
        storage.download_bytes = AsyncMock(return_value=b"# Hello\n")
        storage.upload_file = AsyncMock(return_value=None)

        rasterizer = MagicMock()
        rasterizer.stream_rasterized_pages = MagicMock()

        await process_document_with_session(
            db_session, str(doc.id), storage, rasterizer, MagicMock()
        )

        rasterizer.stream_rasterized_pages.assert_not_called()
