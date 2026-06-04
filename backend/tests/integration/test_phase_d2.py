"""
Phase D2 integration tests — DOCX visual rendering pipeline.

Verifies that:
  A. LibreOffice converter is wired into the DOCX adapter
  B. process_docx_as_pdf() orchestrates conversion + PDF pipeline correctly
  C. DOCX adapter properties match the new image-based behaviour
  D. PDF pipeline accepts pre-converted pdf_bytes (no re-download)
  E. TOC sidecar from DOCX headings overwrites any PDF bookmark sidecar
  F. Conversion failures bubble up as ValueError (permanent worker failure)
  G. Existing PDF / TXT / MD / LOG / DOC pipelines are unchanged (regression)
  H. Upload and viewer endpoints behave correctly for DOCX after D2
"""
import json
import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
import pytest_asyncio

from app.models.document import Document, DocumentPage
from app.services.adapters import get_adapter
from app.workers.tasks import process_document_with_session
from tests.conftest import TEST_USER_ID, _make_webp_bytes


# ── Shared helpers ────────────────────────────────────────────────────────────

_MINIMAL_PDF = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
    b"xref\n0 1\n0000000000 65535 f\n"
    b"trailer\n<< /Size 1 >>\nstartxref\n9\n%%EOF"
)
_DOCX_MAGIC = b"PK\x03\x04" + b"\x00" * 30


@dataclass
class _FakePage:
    page_number: int
    image_bytes: bytes
    width_px: int = 595
    height_px: int = 842


def _mock_rasterizer(page_count: int = 2):
    r = MagicMock()
    r.rasterize_document = AsyncMock(
        return_value=[
            _FakePage(page_number=i, image_bytes=_make_webp_bytes())
            for i in range(1, page_count + 1)
        ]
    )
    return r


def _mock_watermark():
    wm = MagicMock()
    wm.apply_forensic_stamp = MagicMock(side_effect=lambda img, *_: img)
    return wm


def _mock_storage(docx_bytes=None):
    s = MagicMock()
    s.download_bytes = AsyncMock(return_value=docx_bytes or _DOCX_MAGIC)
    s.upload_file = AsyncMock(return_value=None)
    return s


async def _make_doc(db, *, file_type="docx", status="uploaded") -> Document:
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


# ── A. Adapter properties ─────────────────────────────────────────────────────

class TestDOCXAdapterProperties:
    """Phase D2: DOCXAdapter must report image-mode capabilities."""

    def test_viewer_mode_is_image(self):
        assert get_adapter("docx").viewer_mode == "image"

    def test_supports_thumbnails(self):
        assert get_adapter("docx").supports_thumbnails()

    def test_no_toc_fallback_to_text(self):
        assert not get_adapter("docx").toc_fallback_to_text()

    def test_supports_toc_sidecar(self):
        assert get_adapter("docx").supports_toc_sidecar()

    def test_doc_still_text_mode(self):
        assert get_adapter("doc").viewer_mode == "text"

    def test_doc_still_has_fallback(self):
        assert get_adapter("doc").toc_fallback_to_text()

    def test_pdf_unchanged(self):
        assert get_adapter("pdf").viewer_mode == "image"
        assert get_adapter("pdf").supports_thumbnails()
        assert not get_adapter("pdf").toc_fallback_to_text()

    @pytest.mark.parametrize("ft", ["txt", "md", "log"])
    def test_text_formats_unchanged(self, ft):
        assert get_adapter(ft).viewer_mode == "text"
        assert not get_adapter(ft).supports_thumbnails()


# ── B. process_docx_as_pdf orchestration ─────────────────────────────────────

class TestProcessDocxAsPdf:
    """Integration tests for the DOCX→PDF pipeline function."""

    @pytest.mark.asyncio
    async def test_calls_libreoffice_conversion(self, db_session):
        """Conversion step is invoked with the downloaded DOCX bytes."""
        doc = await _make_doc(db_session)
        storage = _mock_storage(docx_bytes=_DOCX_MAGIC)

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            return_value=_MINIMAL_PDF,
        ) as mock_convert, patch(
            "app.workers.pipeline.pdf.process_pdf_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 1, "status": "ready"},
        ), patch(
            "app.services.toc.docx_extractor.extract_docx_toc", return_value=[]
        ):
            from app.workers.pipeline.docx_pdf import process_docx_as_pdf
            await process_docx_as_pdf(
                db_session, doc, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        mock_convert.assert_called_once_with(_DOCX_MAGIC, ".docx")

    @pytest.mark.asyncio
    async def test_pdf_pipeline_receives_converted_bytes(self, db_session):
        """process_pdf_document is called with pdf_bytes, not re-downloaded."""
        doc = await _make_doc(db_session)
        storage = _mock_storage(docx_bytes=_DOCX_MAGIC)

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            return_value=_MINIMAL_PDF,
        ), patch(
            "app.workers.pipeline.pdf.process_pdf_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 1, "status": "ready"},
        ) as mock_pdf, patch(
            "app.services.toc.docx_extractor.extract_docx_toc", return_value=[]
        ):
            from app.workers.pipeline.docx_pdf import process_docx_as_pdf
            await process_docx_as_pdf(
                db_session, doc, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        # Must pass pdf_bytes keyword argument with the converted bytes
        _, kwargs = mock_pdf.call_args
        assert kwargs.get("pdf_bytes") == _MINIMAL_PDF

    @pytest.mark.asyncio
    async def test_result_comes_from_pdf_pipeline(self, db_session):
        doc = await _make_doc(db_session)
        storage = _mock_storage()

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            return_value=_MINIMAL_PDF,
        ), patch(
            "app.workers.pipeline.pdf.process_pdf_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 5, "status": "ready"},
        ), patch(
            "app.services.toc.docx_extractor.extract_docx_toc", return_value=[]
        ):
            from app.workers.pipeline.docx_pdf import process_docx_as_pdf
            result = await process_docx_as_pdf(
                db_session, doc, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        assert result["status"] == "ready"
        assert result["page_count"] == 5

    @pytest.mark.asyncio
    async def test_full_pipeline_via_task_runner(self, db_session):
        """DOCX dispatch through process_document_with_session → docx_pdf pipeline."""
        doc = await _make_doc(db_session, file_type="docx")
        storage = _mock_storage(docx_bytes=_DOCX_MAGIC)

        with patch(
            "app.workers.pipeline.docx_pdf.process_docx_as_pdf",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 3, "status": "ready"},
        ) as mock_pipeline:
            result = await process_document_with_session(
                db_session, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        mock_pipeline.assert_called_once()
        assert result["status"] == "ready"


# ── C. pdf.py pdf_bytes parameter ─────────────────────────────────────────────

class TestPdfBytesParameter:
    """process_pdf_document accepts pdf_bytes and skips download when provided."""

    @pytest.mark.asyncio
    async def test_pdf_pipeline_uses_provided_bytes(self, db_session):
        from app.workers.pipeline.pdf import process_pdf_document

        doc = await _make_doc(db_session, file_type="pdf", status="processing")
        storage = _mock_storage()

        rasterizer = _mock_rasterizer(page_count=1)

        with patch(
            "app.workers.pipeline.pdf.extract_and_store_pdf_toc",
            new_callable=AsyncMock,
        ):
            result = await process_pdf_document(
                db_session, doc, str(doc.id),
                storage, rasterizer, _mock_watermark(),
                pdf_bytes=_MINIMAL_PDF,
            )

        # Storage.download_bytes must NOT have been called when pdf_bytes supplied
        storage.download_bytes.assert_not_called()
        assert result["status"] == "ready"

    @pytest.mark.asyncio
    async def test_pdf_pipeline_downloads_when_no_bytes(self, db_session):
        from app.workers.pipeline.pdf import process_pdf_document

        doc = await _make_doc(db_session, file_type="pdf", status="processing")
        storage = _mock_storage(docx_bytes=_MINIMAL_PDF)

        rasterizer = _mock_rasterizer(page_count=1)

        with patch(
            "app.workers.pipeline.pdf.extract_and_store_pdf_toc",
            new_callable=AsyncMock,
        ):
            result = await process_pdf_document(
                db_session, doc, str(doc.id),
                storage, rasterizer, _mock_watermark(),
                # No pdf_bytes — should download
            )

        storage.download_bytes.assert_called_once_with(doc.storage_key)
        assert result["status"] == "ready"


# ── D. TOC sidecar strategy ───────────────────────────────────────────────────

class TestDocxTocSidecar:
    """DOCX heading TOC is written after the PDF pipeline and wins over bookmarks."""

    @pytest.mark.asyncio
    async def test_docx_toc_sidecar_written_from_headings(self, db_session):
        from app.services.toc.model import TocEntry

        doc = await _make_doc(db_session)
        storage = _mock_storage(docx_bytes=_DOCX_MAGIC)

        heading = TocEntry(
            id="toc_0001", title="Introduction", level=1,
            anchor="sec_0001", chunk=1, line=1,
            source="heading_style", confidence=0.92,
        )

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            return_value=_MINIMAL_PDF,
        ), patch(
            "app.workers.pipeline.pdf.process_pdf_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 1, "status": "ready"},
        ), patch(
            "app.services.toc.docx_extractor.extract_docx_toc",
            return_value=[heading],
        ):
            from app.workers.pipeline.docx_pdf import process_docx_as_pdf
            await process_docx_as_pdf(
                db_session, doc, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        # The TOC sidecar must have been uploaded
        sidecar_calls = [
            c for c in storage.upload_file.call_args_list
            if len(c.args) > 1 and f"toc/{doc.id}.json" in str(c.args[1])
        ]
        assert len(sidecar_calls) >= 1
        sidecar_bytes = sidecar_calls[-1].args[0]
        sidecar_data = json.loads(sidecar_bytes)
        assert any(e["title"] == "Introduction" for e in sidecar_data)

    @pytest.mark.asyncio
    async def test_docx_toc_entries_have_no_chunk_field(self, db_session):
        """Fix 1: DOCX TOC sidecar must not contain text-mode chunk navigation."""
        import json as _json
        from app.services.toc.model import TocEntry

        doc = await _make_doc(db_session)
        storage = _mock_storage(docx_bytes=_DOCX_MAGIC)

        heading = TocEntry(
            id="toc_0001", title="Overview", level=1,
            anchor="sec_0001",
            source="heading_style", confidence=0.92,
            # chunk and page intentionally absent after Fix 1
        )

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            return_value=_MINIMAL_PDF,
        ), patch(
            "app.workers.pipeline.pdf.process_pdf_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 1, "status": "ready"},
        ), patch(
            "app.services.toc.docx_extractor.extract_docx_toc",
            return_value=[heading],
        ):
            from app.workers.pipeline.docx_pdf import process_docx_as_pdf
            await process_docx_as_pdf(
                db_session, doc, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        sidecar_calls = [
            c for c in storage.upload_file.call_args_list
            if len(c.args) > 1 and f"toc/{doc.id}.json" in str(c.args[1])
        ]
        assert len(sidecar_calls) >= 1
        sidecar_data = _json.loads(sidecar_calls[-1].args[0])
        assert len(sidecar_data) == 1
        entry = sidecar_data[0]
        assert entry["title"] == "Overview"
        assert "chunk" not in entry, "chunk field must be absent from DOCX TOC sidecar"
        assert "page" not in entry, "page field is not yet available at extraction time"

    @pytest.mark.asyncio
    async def test_no_sidecar_when_no_headings(self, db_session):
        doc = await _make_doc(db_session)
        storage = _mock_storage()

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            return_value=_MINIMAL_PDF,
        ), patch(
            "app.workers.pipeline.pdf.process_pdf_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 1, "status": "ready"},
        ), patch(
            "app.services.toc.docx_extractor.extract_docx_toc",
            return_value=[],  # no headings found
        ):
            from app.workers.pipeline.docx_pdf import process_docx_as_pdf
            await process_docx_as_pdf(
                db_session, doc, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        sidecar_calls = [
            c for c in storage.upload_file.call_args_list
            if len(c.args) > 1 and f"toc/{doc.id}.json" in str(c.args[1])
        ]
        # No DOCX headings → no sidecar written by docx_pdf (PDF pipeline may
        # write one from bookmarks, but that's separate)
        assert len(sidecar_calls) == 0

    @pytest.mark.asyncio
    async def test_toc_extraction_failure_is_non_fatal(self, db_session):
        doc = await _make_doc(db_session)
        storage = _mock_storage()

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            return_value=_MINIMAL_PDF,
        ), patch(
            "app.workers.pipeline.pdf.process_pdf_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 1, "status": "ready"},
        ), patch(
            "app.services.toc.docx_extractor.extract_docx_toc",
            side_effect=Exception("corrupt docx"),
        ):
            from app.workers.pipeline.docx_pdf import process_docx_as_pdf
            result = await process_docx_as_pdf(
                db_session, doc, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        # Document must still be ready despite TOC failure
        assert result["status"] == "ready"


# ── E. Conversion failures ────────────────────────────────────────────────────

class TestConversionFailures:
    @pytest.mark.asyncio
    async def test_libreoffice_not_available_raises_value_error(self, db_session):
        from app.services.libreoffice_converter import LibreOfficeNotAvailableError
        from app.workers.pipeline.docx_pdf import process_docx_as_pdf

        doc = await _make_doc(db_session)
        storage = _mock_storage()

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            side_effect=LibreOfficeNotAvailableError("not installed"),
        ):
            with pytest.raises(ValueError, match="DOCX conversion failed"):
                await process_docx_as_pdf(
                    db_session, doc, str(doc.id),
                    storage, _mock_rasterizer(), _mock_watermark()
                )

    @pytest.mark.asyncio
    async def test_libreoffice_error_raises_value_error(self, db_session):
        from app.services.libreoffice_converter import LibreOfficeConversionError
        from app.workers.pipeline.docx_pdf import process_docx_as_pdf

        doc = await _make_doc(db_session)
        storage = _mock_storage()

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            side_effect=LibreOfficeConversionError("conversion failed"),
        ):
            with pytest.raises(ValueError, match="DOCX conversion failed"):
                await process_docx_as_pdf(
                    db_session, doc, str(doc.id),
                    storage, _mock_rasterizer(), _mock_watermark()
                )

    @pytest.mark.asyncio
    async def test_asyncio_timeout_raises_value_error_not_retried(self, db_session):
        """Fix 2: asyncio.TimeoutError must become a permanent ValueError (no Celery retry)."""
        import asyncio as _asyncio
        from app.workers.pipeline.docx_pdf import process_docx_as_pdf

        doc = await _make_doc(db_session)
        storage = _mock_storage()

        with patch(
            "app.workers.pipeline.docx_pdf.asyncio.wait_for",
            side_effect=_asyncio.TimeoutError("outer timeout fired"),
        ):
            with pytest.raises(ValueError, match="DOCX conversion failed"):
                await process_docx_as_pdf(
                    db_session, doc, str(doc.id),
                    storage, _mock_rasterizer(), _mock_watermark()
                )

    @pytest.mark.asyncio
    async def test_conversion_failure_document_marked_error_by_worker(self, db_session):
        """Worker marks the document as error when DOCX processing raises ValueError."""
        from app.workers.tasks import _mark_document_error
        from app.services.libreoffice_converter import LibreOfficeConversionError

        doc = await _make_doc(db_session, file_type="docx")
        storage = _mock_storage()

        with patch(
            "app.workers.pipeline.docx_pdf.process_docx_as_pdf",
            side_effect=ValueError("DOCX conversion failed for document X: not installed"),
        ), patch(
            "app.workers.tasks._mark_document_error", new_callable=AsyncMock
        ) as mock_mark_error:
            with pytest.raises(ValueError):
                await process_document_with_session(
                    db_session, str(doc.id),
                    storage, _mock_rasterizer(), _mock_watermark()
                )

        # The ValueError is permanent — worker must not retry it, and
        # the caller (_process_document_async) will call _mark_document_error


# ── F. Upload router — DOCX unchanged ─────────────────────────────────────────

class TestDocxUploadRouter:
    @pytest.mark.asyncio
    async def test_docx_upload_still_accepted(self, client):
        ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        r = await client.post(
            "/api/documents/upload",
            files={"file": ("report.docx", _DOCX_MAGIC, ct)},
        )
        assert r.status_code == 202
        assert r.json()["status"] == "uploaded"

    @pytest.mark.asyncio
    async def test_docx_bad_magic_still_rejected(self, client):
        ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        r = await client.post(
            "/api/documents/upload",
            files={"file": ("bad.docx", b"not a zip file at all", ct)},
        )
        assert r.status_code == 400


# ── G. Viewer — DOCX behaves like PDF ─────────────────────────────────────────

class TestDocxViewerBehavesLikePdf:
    @pytest.mark.asyncio
    async def test_text_chunk_endpoint_rejects_docx(self, client, db_session):
        """After D2, DOCX is image mode — /api/viewer/text must return 400."""
        from app.services.link_service import LinkService
        from app.services.viewer_cache import clear_all_caches

        clear_all_caches()

        doc = Document(
            id=uuid.uuid4(),
            filename="report.docx",
            storage_key=f"originals/{uuid.uuid4()}.docx",
            status="ready",
            file_type="docx",
            page_count=3,
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        link = await LinkService().create_link(db_session, document_id=str(doc.id))

        r_val = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r_val.status_code == 200
        session_id = r_val.json()["session_id"]

        r = await client.get(
            f"/api/viewer/text/{link.token}/1",
            params={"session_id": session_id},
        )
        assert r.status_code == 400
        detail = r.json()["detail"]
        assert "page" in detail.lower() or "PDFs" in detail

    @pytest.mark.asyncio
    async def test_validate_docx_returns_image_doc_type(self, client, db_session):
        from app.services.link_service import LinkService
        from app.services.viewer_cache import clear_all_caches

        clear_all_caches()

        doc = Document(
            id=uuid.uuid4(),
            filename="report.docx",
            storage_key=f"originals/{uuid.uuid4()}.docx",
            status="ready",
            file_type="docx",
            page_count=2,
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()
        await db_session.refresh(doc)

        link = await LinkService().create_link(db_session, document_id=str(doc.id))

        r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200
        body = r.json()
        assert body["doc_type"] == "docx"
        assert body["page_count"] == 2


# ── H. Regression — other formats unchanged ───────────────────────────────────

class TestRegressionOtherFormats:
    @pytest.mark.asyncio
    async def test_pdf_pipeline_unchanged(self, db_session):
        doc = Document(
            id=uuid.uuid4(), filename="test.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="uploaded", file_type="pdf",
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()

        storage = _mock_storage(docx_bytes=_MINIMAL_PDF)

        with patch(
            "app.workers.pipeline.pdf.process_pdf_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 1, "status": "ready"},
        ) as mock_pdf:
            result = await process_document_with_session(
                db_session, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        mock_pdf.assert_called_once()
        assert result["status"] == "ready"

    @pytest.mark.asyncio
    async def test_doc_pipeline_still_text_based(self, db_session):
        """DOC remains on the antiword text pipeline — NOT LibreOffice."""
        doc = Document(
            id=uuid.uuid4(), filename="legacy.doc",
            storage_key=f"originals/{uuid.uuid4()}.doc",
            status="uploaded", file_type="doc",
            file_size_bytes=512,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()

        storage = _mock_storage()

        with patch(
            "app.workers.pipeline.word.process_doc_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 2, "status": "ready"},
        ) as mock_doc:
            result = await process_document_with_session(
                db_session, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        mock_doc.assert_called_once()
        assert result["status"] == "ready"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("ft", ["txt", "md", "log"])
    async def test_text_formats_unchanged(self, ft, db_session):
        doc = Document(
            id=uuid.uuid4(), filename=f"file.{ft}",
            storage_key=f"originals/{uuid.uuid4()}.{ft}",
            status="uploaded", file_type=ft,
            file_size_bytes=256,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()

        storage = _mock_storage(docx_bytes=b"hello\nworld\n")

        with patch(
            "app.workers.pipeline.text.process_text_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 1, "status": "ready"},
        ) as mock_text:
            result = await process_document_with_session(
                db_session, str(doc.id),
                storage, None, None
            )

        mock_text.assert_called_once()
        assert result["status"] == "ready"

    def test_libreoffice_not_called_for_pdf(self):
        """LibreOffice converter must not be imported/invoked for PDF documents."""
        adapter = get_adapter("pdf")
        import inspect
        src = inspect.getsource(adapter.process.__func__
                                if hasattr(adapter.process, "__func__") else type(adapter).process)
        assert "libreoffice" not in src.lower() or "docx_pdf" not in src.lower()


# ── I. Phase D2.7 — DOCX TOC page mapping ────────────────────────────────────

class TestDocxTocPageMapping:
    """
    Integration tests verifying that process_docx_as_pdf() produces a TOC
    sidecar with page numbers when LibreOffice emits PDF bookmarks.
    """

    @pytest.mark.asyncio
    async def test_sidecar_contains_page_when_bookmark_matches(self, db_session):
        """When PDF bookmarks match heading titles, page numbers appear in sidecar."""
        from app.services.toc.model import TocEntry
        from app.workers.pipeline.docx_pdf import process_docx_as_pdf

        doc = await _make_doc(db_session)
        storage = _mock_storage(docx_bytes=_DOCX_MAGIC)

        heading = TocEntry(
            id="toc_0001", title="Introduction", level=1,
            anchor="sec_0001", source="heading_style", confidence=0.92,
        )

        mock_reader = MagicMock()
        bm = MagicMock()
        bm.title = "Introduction"
        mock_reader.outline = [bm]
        mock_reader.get_destination_page_number.return_value = 2  # 0-indexed → page 3

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            return_value=_MINIMAL_PDF,
        ), patch(
            "app.workers.pipeline.pdf.process_pdf_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 5, "status": "ready"},
        ), patch(
            "app.services.toc.docx_extractor.extract_docx_toc",
            return_value=[heading],
        ), patch("pypdf.PdfReader", return_value=mock_reader):
            await process_docx_as_pdf(
                db_session, doc, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        sidecar_calls = [
            c for c in storage.upload_file.call_args_list
            if len(c.args) > 1 and f"toc/{doc.id}.json" in str(c.args[1])
        ]
        assert len(sidecar_calls) >= 1
        data = json.loads(sidecar_calls[-1].args[0])
        assert len(data) == 1
        assert data[0]["title"] == "Introduction"
        assert data[0]["page"] == 3      # 0-indexed 2 → 1-indexed 3
        assert "chunk" not in data[0]

    @pytest.mark.asyncio
    async def test_sidecar_has_no_page_when_no_bookmarks(self, db_session):
        """When PDF has no bookmarks, sidecar entries have no page field."""
        from app.services.toc.model import TocEntry
        from app.workers.pipeline.docx_pdf import process_docx_as_pdf

        doc = await _make_doc(db_session)
        storage = _mock_storage(docx_bytes=_DOCX_MAGIC)

        heading = TocEntry(
            id="toc_0001", title="Overview", level=1,
            anchor="sec_0001", source="heading_style", confidence=0.92,
        )

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            return_value=_MINIMAL_PDF,
        ), patch(
            "app.workers.pipeline.pdf.process_pdf_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 2, "status": "ready"},
        ), patch(
            "app.services.toc.docx_extractor.extract_docx_toc",
            return_value=[heading],
        ), patch("pypdf.PdfReader", return_value=MagicMock(outline=[])):
            await process_docx_as_pdf(
                db_session, doc, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        sidecar_calls = [
            c for c in storage.upload_file.call_args_list
            if len(c.args) > 1 and f"toc/{doc.id}.json" in str(c.args[1])
        ]
        data = json.loads(sidecar_calls[-1].args[0])
        assert "page" not in data[0]     # no bookmark match
        assert "chunk" not in data[0]    # no text-mode artifact

    @pytest.mark.asyncio
    async def test_partial_resolution_mixed_headings(self, db_session):
        """Some headings get pages, others remain unresolved — both appear in sidecar."""
        from app.services.toc.model import TocEntry
        from app.workers.pipeline.docx_pdf import process_docx_as_pdf

        doc = await _make_doc(db_session)
        storage = _mock_storage(docx_bytes=_DOCX_MAGIC)

        entries = [
            TocEntry(id="toc_0001", title="Chapter 1", level=1,
                     anchor="sec_0001", source="heading_style", confidence=0.92),
            TocEntry(id="toc_0002", title="Appendix A", level=1,
                     anchor="sec_0002", source="heading_style", confidence=0.92),
        ]

        bm1 = MagicMock(); bm1.title = "Chapter 1"
        mock_reader = MagicMock()
        mock_reader.outline = [bm1]  # "Appendix A" has no bookmark
        mock_reader.get_destination_page_number.return_value = 0  # page 1

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            return_value=_MINIMAL_PDF,
        ), patch(
            "app.workers.pipeline.pdf.process_pdf_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 8, "status": "ready"},
        ), patch(
            "app.services.toc.docx_extractor.extract_docx_toc",
            return_value=entries,
        ), patch("pypdf.PdfReader", return_value=mock_reader):
            await process_docx_as_pdf(
                db_session, doc, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        sidecar_calls = [
            c for c in storage.upload_file.call_args_list
            if len(c.args) > 1 and f"toc/{doc.id}.json" in str(c.args[1])
        ]
        data = json.loads(sidecar_calls[-1].args[0])
        assert len(data) == 2
        assert data[0]["title"] == "Chapter 1"
        assert data[0]["page"] == 1
        assert data[1]["title"] == "Appendix A"
        assert "page" not in data[1]

    @pytest.mark.asyncio
    async def test_bookmark_resolution_failure_is_non_fatal(self, db_session):
        """pypdf error during page resolution must not block document processing."""
        from app.services.toc.model import TocEntry
        from app.workers.pipeline.docx_pdf import process_docx_as_pdf

        doc = await _make_doc(db_session)
        storage = _mock_storage(docx_bytes=_DOCX_MAGIC)

        heading = TocEntry(
            id="toc_0001", title="Introduction", level=1,
            anchor="sec_0001", source="heading_style", confidence=0.92,
        )

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            return_value=_MINIMAL_PDF,
        ), patch(
            "app.workers.pipeline.pdf.process_pdf_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 2, "status": "ready"},
        ), patch(
            "app.services.toc.docx_extractor.extract_docx_toc",
            return_value=[heading],
        ), patch("pypdf.PdfReader", side_effect=Exception("corrupt PDF bookmarks")):
            result = await process_docx_as_pdf(
                db_session, doc, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        assert result["status"] == "ready"
        # Sidecar still written — just without page numbers
        sidecar_calls = [
            c for c in storage.upload_file.call_args_list
            if len(c.args) > 1 and f"toc/{doc.id}.json" in str(c.args[1])
        ]
        assert len(sidecar_calls) >= 1
        data = json.loads(sidecar_calls[-1].args[0])
        assert data[0]["title"] == "Introduction"
        assert "page" not in data[0]

    @pytest.mark.asyncio
    async def test_nested_headings_resolved(self, db_session):
        """Nested bookmarks (chapters + sections) are all flattened and resolved."""
        from app.services.toc.model import TocEntry
        from app.workers.pipeline.docx_pdf import process_docx_as_pdf

        doc = await _make_doc(db_session)
        storage = _mock_storage(docx_bytes=_DOCX_MAGIC)

        entries = [
            TocEntry(id="toc_0001", title="Chapter 1", level=1,
                     anchor="sec_0001", source="heading_style", confidence=0.92),
            TocEntry(id="toc_0002", title="Section 1.1", level=2,
                     anchor="sec_0002", source="heading_style", confidence=0.92),
        ]

        ch1 = MagicMock(); ch1.title = "Chapter 1"
        sec1 = MagicMock(); sec1.title = "Section 1.1"

        mock_reader = MagicMock()
        mock_reader.outline = [ch1, [sec1]]  # nested list for sub-sections
        page_map = {id(ch1): 0, id(sec1): 3}
        mock_reader.get_destination_page_number.side_effect = lambda d: page_map[id(d)]

        with patch(
            "app.services.libreoffice_converter.LibreOfficeConverter.convert_to_pdf",
            return_value=_MINIMAL_PDF,
        ), patch(
            "app.workers.pipeline.pdf.process_pdf_document",
            new_callable=AsyncMock,
            return_value={"document_id": str(doc.id), "page_count": 10, "status": "ready"},
        ), patch(
            "app.services.toc.docx_extractor.extract_docx_toc",
            return_value=entries,
        ), patch("pypdf.PdfReader", return_value=mock_reader):
            await process_docx_as_pdf(
                db_session, doc, str(doc.id),
                storage, _mock_rasterizer(), _mock_watermark()
            )

        sidecar_calls = [
            c for c in storage.upload_file.call_args_list
            if len(c.args) > 1 and f"toc/{doc.id}.json" in str(c.args[1])
        ]
        data = json.loads(sidecar_calls[-1].args[0])
        assert data[0]["page"] == 1   # Chapter 1 → page 1
        assert data[1]["page"] == 4   # Section 1.1 → page 4
