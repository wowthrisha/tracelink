"""
Phase D1 integration tests — DocumentAdapter architecture.

These tests verify that the adapter-driven dispatch produces exactly the same
observable behaviour as the pre-refactor if/elif chains.

Coverage:
  A. Worker dispatch — each format calls the correct pipeline via adapter
  B. Upload router — ALLOWED_CONTENT_TYPES derived from adapters; size/format
     validation delegated to adapter; content-type storage derived from adapter
  C. Viewer router — text/image mode separation; TOC sidecar routing
  D. TOC extractor — adapter-driven dispatch
  E. Behavioral regression — no changes to existing API contracts
"""
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from app.models.document import Document, DocumentPage
from app.workers.tasks import process_document_with_session
from app.services.adapters import get_adapter, allowed_content_types
from tests.conftest import TEST_USER_ID, _make_webp_bytes


# ── Shared helpers ────────────────────────────────────────────────────────────

@dataclass
class _FakePage:
    page_number: int
    image_bytes: bytes
    width_px: int = 595
    height_px: int = 842


def _make_mock_rasterizer(page_count: int = 1):
    r = MagicMock()
    pages = [_FakePage(page_number=i, image_bytes=_make_webp_bytes()) for i in range(1, page_count + 1)]
    def _side_effect(*args, **kwargs):
        async def _gen():
            for p in pages:
                yield p
        return _gen()
    r.stream_rasterized_pages = MagicMock(side_effect=_side_effect)
    return r


def _make_mock_watermark():
    wm = MagicMock()
    wm.apply_forensic_stamp = MagicMock(side_effect=lambda img, *_: img)
    return wm


def _make_mock_storage(download_return=None):
    s = MagicMock()
    s.download_bytes = AsyncMock(return_value=download_return or b"%PDF-1.4 fake pdf")
    s.upload_file = AsyncMock(return_value=None)
    return s


async def _insert_doc(db, *, file_type: str = "pdf", status: str = "uploaded") -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename=f"test.{file_type}",
        storage_key=f"originals/{uuid.uuid4()}.{file_type}",
        status=status,
        file_type=file_type,
        file_size_bytes=1024,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


# ── A. Worker dispatch ─────────────────────────────────────────────────────────

class TestWorkerDispatch:
    """process_document_with_session routes each file_type to the right pipeline."""

    @pytest.mark.asyncio
    async def test_pdf_dispatch_calls_pdf_pipeline(self, db_session):
        doc = await _insert_doc(db_session, file_type="pdf")
        storage = _make_mock_storage(download_return=b"%PDF-1.4 test")
        rasterizer = _make_mock_rasterizer(page_count=1)
        watermark = _make_mock_watermark()

        with patch("app.workers.pipeline.pdf.process_pdf_document") as mock_pipeline:
            mock_pipeline.return_value = {
                "document_id": str(doc.id), "page_count": 1, "status": "ready"
            }
            result = await process_document_with_session(
                db_session, str(doc.id), storage, rasterizer, watermark
            )
        mock_pipeline.assert_called_once()
        assert result["status"] == "ready"

    @pytest.mark.asyncio
    async def test_txt_dispatch_calls_text_pipeline(self, db_session):
        doc = await _insert_doc(db_session, file_type="txt")
        storage = _make_mock_storage(download_return=b"hello world\n")

        with patch("app.workers.pipeline.text.process_text_document") as mock_pipeline:
            mock_pipeline.return_value = {
                "document_id": str(doc.id), "page_count": 1, "status": "ready"
            }
            result = await process_document_with_session(
                db_session, str(doc.id), storage, None, None
            )
        mock_pipeline.assert_called_once()
        assert result["status"] == "ready"

    @pytest.mark.asyncio
    async def test_md_dispatch_calls_text_pipeline(self, db_session):
        doc = await _insert_doc(db_session, file_type="md")
        storage = _make_mock_storage(download_return=b"# Title\n")

        with patch("app.workers.pipeline.text.process_text_document") as mock_pipeline:
            mock_pipeline.return_value = {
                "document_id": str(doc.id), "page_count": 1, "status": "ready"
            }
            result = await process_document_with_session(
                db_session, str(doc.id), storage, None, None
            )
        mock_pipeline.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_dispatch_calls_text_pipeline(self, db_session):
        doc = await _insert_doc(db_session, file_type="log")
        storage = _make_mock_storage(download_return=b"2026-01-01 INFO started\n")

        with patch("app.workers.pipeline.text.process_text_document") as mock_pipeline:
            mock_pipeline.return_value = {
                "document_id": str(doc.id), "page_count": 1, "status": "ready"
            }
            result = await process_document_with_session(
                db_session, str(doc.id), storage, None, None
            )
        mock_pipeline.assert_called_once()

    @pytest.mark.asyncio
    async def test_docx_dispatch_calls_docx_pdf_pipeline(self, db_session):
        """Phase D2: DOCX dispatches to the LibreOffice-based image pipeline."""
        doc = await _insert_doc(db_session, file_type="docx")
        storage = _make_mock_storage(download_return=b"PK\x03\x04" + b"\x00" * 30)

        with patch("app.workers.pipeline.docx_pdf.process_docx_as_pdf") as mock_pipeline:
            mock_pipeline.return_value = {
                "document_id": str(doc.id), "page_count": 2, "status": "ready"
            }
            result = await process_document_with_session(
                db_session, str(doc.id), storage, None, None
            )
        mock_pipeline.assert_called_once()
        assert result["status"] == "ready"

    @pytest.mark.asyncio
    async def test_doc_dispatch_calls_doc_pipeline(self, db_session):
        doc = await _insert_doc(db_session, file_type="doc")
        storage = _make_mock_storage(
            download_return=b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" + b"\x00" * 10
        )

        with patch("app.workers.pipeline.word.process_doc_document") as mock_pipeline:
            mock_pipeline.return_value = {
                "document_id": str(doc.id), "page_count": 3, "status": "ready"
            }
            result = await process_document_with_session(
                db_session, str(doc.id), storage, None, None
            )
        mock_pipeline.assert_called_once()
        assert result["status"] == "ready"


# ── B. Upload router ───────────────────────────────────────────────────────────

class TestUploadRouterAdapter:
    """Upload endpoint uses adapter-derived content types and validation."""

    @pytest.mark.asyncio
    async def test_allowed_content_types_derived_from_adapters(self):
        from app.routers.documents import ALLOWED_CONTENT_TYPES
        # Every adapter's MIME types should be in ALLOWED_CONTENT_TYPES
        for adapter in [get_adapter(ft) for ft in ("pdf", "txt", "md", "log", "docx", "doc")]:
            for mime in adapter.upload_mime_types():
                assert mime in ALLOWED_CONTENT_TYPES, f"{mime!r} missing from ALLOWED_CONTENT_TYPES"

    @pytest.mark.asyncio
    async def test_octet_stream_still_allowed(self):
        from app.routers.documents import ALLOWED_CONTENT_TYPES
        assert "application/octet-stream" in ALLOWED_CONTENT_TYPES

    @pytest.mark.asyncio
    async def test_pdf_upload_accepted(self, client, sample_pdf_bytes):
        r = await client.post(
            "/api/documents/upload",
            files={"file": ("doc.pdf", sample_pdf_bytes, "application/pdf")},
        )
        assert r.status_code == 202

    @pytest.mark.asyncio
    async def test_txt_upload_accepted(self, client):
        r = await client.post(
            "/api/documents/upload",
            files={"file": ("notes.txt", b"Hello world\n", "text/plain")},
        )
        assert r.status_code == 202

    @pytest.mark.asyncio
    async def test_docx_upload_accepted(self, client):
        docx_bytes = b"PK\x03\x04" + b"\x00" * 30
        ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        r = await client.post(
            "/api/documents/upload",
            files={"file": ("report.docx", docx_bytes, ct)},
        )
        assert r.status_code == 202

    @pytest.mark.asyncio
    async def test_non_pdf_magic_returns_400(self, client):
        r = await client.post(
            "/api/documents/upload",
            files={"file": ("fake.pdf", b"not a pdf content", "application/pdf")},
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_binary_txt_returns_400(self, client):
        r = await client.post(
            "/api/documents/upload",
            files={"file": ("bad.txt", b"hello\x00binary\x00data", "text/plain")},
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_jpeg_content_type_rejected(self, client):
        r = await client.post(
            "/api/documents/upload",
            files={"file": ("photo.jpg", b"\xff\xd8\xff\xe0", "image/jpeg")},
        )
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_response_never_contains_storage_key(self, client, sample_pdf_bytes):
        r = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")},
        )
        body = r.json()
        assert "storage_key" not in body
        assert "originals/" not in str(body)


# ── C. Viewer router ───────────────────────────────────────────────────────────

class TestViewerAdapterDispatch:
    """Viewer endpoints use adapter.viewer_mode instead of format lists."""

    @pytest.mark.asyncio
    async def test_text_chunk_endpoint_rejects_pdf(self, client, db_session):
        """GET /api/viewer/text/{token}/{chunk} must return 400 for PDF docs."""
        from app.models.link import ShareLink

        doc = await _insert_doc(db_session, file_type="pdf", status="ready")
        doc.page_count = 3
        await db_session.commit()

        from app.services.link_service import LinkService
        link = await LinkService().create_link(db_session, document_id=str(doc.id))

        # Validate session
        r = await client.post(
            "/api/viewer/validate",
            json={"token": link.token},
        )
        assert r.status_code == 200
        session_id = r.json()["session_id"]

        # Text endpoint should reject PDF
        r = await client.get(
            f"/api/viewer/text/{link.token}/1",
            params={"session_id": session_id},
        )
        assert r.status_code == 400
        assert "PDFs" in r.json()["detail"] or "page" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_text_chunk_endpoint_accepts_txt(self, client, db_session):
        """GET /api/viewer/text/{token}/{chunk} must succeed for TXT docs."""
        from app.models.link import ShareLink
        from app.services.viewer_cache import clear_all_caches

        clear_all_caches()

        lines = "\n".join(f"line {i}" for i in range(1, 101))
        doc = Document(
            id=uuid.uuid4(),
            filename="notes.txt",
            storage_key=f"originals/{uuid.uuid4()}.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=len(lines.encode()),
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        from app.services.link_service import LinkService
        link = await LinkService().create_link(db_session, document_id=str(doc.id))

        with patch(
            "app.services.storage.StorageService.download_bytes",
            new_callable=AsyncMock,
            return_value=lines.encode(),
        ):
            r_val = await client.post(
                "/api/viewer/validate", json={"token": link.token}
            )
            assert r_val.status_code == 200
            session_id = r_val.json()["session_id"]

            r = await client.get(
                f"/api/viewer/text/{link.token}/1",
                params={"session_id": session_id},
            )
        assert r.status_code == 200
        body = r.json()
        assert "content" in body
        assert body["doc_type"] == "txt"


# ── D. TOC extractor adapter dispatch ─────────────────────────────────────────

class TestTocExtractorAdapterDispatch:
    """extract_toc_for_document delegates to the registered adapter."""

    @pytest.mark.asyncio
    async def test_pdf_toc_delegates_to_pdf_adapter(self):
        from app.services.toc.extractor import extract_toc_for_document
        minimal_pdf = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
            b"xref\n0 1\n0000000000 65535 f\n"
            b"trailer\n<< /Size 1 >>\nstartxref\n9\n%%EOF"
        )
        result = await extract_toc_for_document("pdf", pdf_bytes=minimal_pdf)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_txt_toc_returns_entries(self):
        from app.services.toc.extractor import extract_toc_for_document
        text = "1. Introduction\nbody\n2. Methods\nbody2\n"
        result = await extract_toc_for_document("txt", text_content=text)
        assert isinstance(result, list)
        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_md_toc_returns_headings(self):
        from app.services.toc.extractor import extract_toc_for_document
        text = "# Title\n\nbody\n\n## Section 1\n\nmore\n"
        result = await extract_toc_for_document("md", text_content=text)
        assert isinstance(result, list)
        titles = [e["title"] for e in result]
        assert "Title" in titles

    @pytest.mark.asyncio
    async def test_log_toc_returns_entries(self):
        from app.services.toc.extractor import extract_toc_for_document
        text = "STARTUP\n\nServer started.\n\nSHUTDOWN\n\nServer stopped.\n"
        result = await extract_toc_for_document("log", text_content=text)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_docx_toc_adapter_fallback_accepts_text(self):
        from app.services.toc.extractor import extract_toc_for_document
        # The DOCXAdapter.extract_toc() defensive fallback still accepts text_content.
        # In production the viewer uses the heading-style sidecar instead.
        text = "# Chapter 1\n\nIntro.\n\n## Section 1.1\n\nDetails.\n"
        result = await extract_toc_for_document("docx", text_content=text)
        assert isinstance(result, list)
        titles = [e["title"] for e in result]
        assert "Chapter 1" in titles

    @pytest.mark.asyncio
    async def test_unknown_format_returns_empty(self):
        from app.services.toc.extractor import extract_toc_for_document
        result = await extract_toc_for_document("xyz", text_content="some text")
        assert result == []

    @pytest.mark.asyncio
    async def test_pdf_without_bytes_returns_empty(self):
        from app.services.toc.extractor import extract_toc_for_document
        result = await extract_toc_for_document("pdf")
        assert result == []


# ── E. Behavioral regression ──────────────────────────────────────────────────

class TestBehavioralRegression:
    """Verify that nothing observable changed after the refactor."""

    @pytest.mark.asyncio
    async def test_document_list_endpoint_unchanged(self, client, sample_pdf_bytes):
        r = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")},
        )
        assert r.status_code == 202
        r2 = await client.get("/api/documents")
        assert r2.status_code == 200
        body = r2.json()
        assert "documents" in body
        assert len(body["documents"]) == 1

    @pytest.mark.asyncio
    async def test_status_endpoint_still_works(self, client, sample_pdf_bytes):
        r = await client.post(
            "/api/documents/upload",
            files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")},
        )
        doc_id = r.json()["id"]
        r2 = await client.get(f"/api/documents/{doc_id}/status")
        assert r2.status_code == 200
        assert "status" in r2.json()

    @pytest.mark.asyncio
    async def test_validate_returns_doc_type_field(self, client, db_session):
        """validate response must still include doc_type."""
        doc = await _insert_doc(db_session, file_type="txt", status="ready")
        doc.page_count = 1
        await db_session.commit()

        from app.services.link_service import LinkService
        link = await LinkService().create_link(db_session, document_id=str(doc.id))

        r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200
        body = r.json()
        assert "doc_type" in body
        assert body["doc_type"] == "txt"

    @pytest.mark.asyncio
    async def test_validate_pdf_returns_image_doc_type(self, client, db_session):
        doc = await _insert_doc(db_session, file_type="pdf", status="ready")
        doc.page_count = 2
        await db_session.commit()

        from app.services.link_service import LinkService
        link = await LinkService().create_link(db_session, document_id=str(doc.id))

        r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200
        body = r.json()
        assert body["doc_type"] == "pdf"

    def test_adapter_content_types_superset_of_old_allowed_set(self):
        """
        The old ALLOWED_CONTENT_TYPES was a hardcoded set.
        Every type from it must still be present in the adapter-derived set.
        """
        old_types = {
            "application/pdf",
            "text/plain",
            "text/markdown",
            "text/x-log",
            "text/x-log-file",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        }
        derived = allowed_content_types() | {"application/octet-stream"}
        for ct in old_types:
            assert ct in derived, f"{ct!r} is missing from adapter-derived content types"

    def test_pdf_adapter_process_accepts_rasterizer_and_watermark_kwargs(self):
        """PDFAdapter.process signature must accept rasterizer= and watermark= kwargs."""
        import inspect
        adapter = get_adapter("pdf")
        sig = inspect.signature(adapter.process)
        assert "rasterizer" in sig.parameters
        assert "watermark" in sig.parameters

    @pytest.mark.parametrize("ft", ["txt", "md", "log", "doc"])
    def test_text_adapters_accept_rasterizer_watermark_kwargs(self, ft):
        """Text adapters accept but ignore rasterizer/watermark kwargs."""
        import inspect
        adapter = get_adapter(ft)
        sig = inspect.signature(adapter.process)
        assert "rasterizer" in sig.parameters
        assert "watermark" in sig.parameters

    def test_docx_adapter_uses_rasterizer_and_watermark(self):
        """Phase D2: DOCX is an image adapter and passes rasterizer/watermark to the pipeline."""
        import inspect
        adapter = get_adapter("docx")
        assert adapter.viewer_mode == "image"
        sig = inspect.signature(adapter.process)
        assert "rasterizer" in sig.parameters
        assert "watermark" in sig.parameters
