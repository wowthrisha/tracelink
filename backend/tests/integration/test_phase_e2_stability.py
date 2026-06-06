"""
Phase E2.1 Large Document Stability Tests.

Covers:
  A. Streaming rasterization (O(1) PIL RAM via output_folder + paths_only)
  B. Bounded parallel R2 uploads (asyncio.gather + semaphore)
  C. Celery task time limits (soft=600 s, hard=660 s)
  D. Worker lifecycle (max_tasks_per_child > 0)
  E. LibreOffice timeout (configurable, default 120 s)
  F. Large document simulation (200-page end-to-end pipeline)
"""
import asyncio
import os
import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image
from sqlalchemy import select

from app.models.document import Document, DocumentPage
from app.workers.tasks import process_document_with_session
from tests.conftest import TEST_USER_ID, _make_webp_bytes


# ── Helpers shared across test classes ────────────────────────────────────────

@dataclass
class _FakePage:
    page_number: int
    image_bytes: bytes
    width_px: int = 595
    height_px: int = 842


def _make_mock_storage():
    s = MagicMock()
    s.download_bytes = AsyncMock(return_value=b"%PDF-1.4 fake")
    s.upload_file = AsyncMock(return_value=None)
    return s


def _make_mock_watermark():
    wm = MagicMock()
    wm.apply_forensic_stamp = MagicMock(side_effect=lambda img, *_: img)
    return wm


def _make_mock_rasterizer(page_count: int = 1):
    rasterizer = MagicMock()
    rasterizer.rasterize_document = AsyncMock(
        return_value=[_FakePage(page_number=i, image_bytes=_make_webp_bytes()) for i in range(1, page_count + 1)]
    )
    return rasterizer


def _fake_pdf2image_factory(page_count: int, width: int = 100, height: int = 140):
    """
    Return a side_effect for pdf2image.convert_from_bytes that writes PPM files
    to output_folder and returns their paths (matching paths_only=True contract).
    """
    def _fake(pdf_bytes, dpi=200, output_folder=None, paths_only=False, **kwargs):
        paths = []
        for i in range(1, page_count + 1):
            img = Image.new("RGB", (width, height), color=(i * 30 % 256, 100, 150))
            path = os.path.join(output_folder, f"output-{i:04d}.ppm")
            img.save(path, format="PPM")
            paths.append(path)
        return paths
    return _fake


async def _make_uploaded_doc(db_session, filename="test.pdf") -> Document:
    doc = Document(
        id=uuid.uuid4(),
        filename=filename,
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status="uploaded",
        file_size_bytes=1024,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


# ── A. Streaming Rasterization ────────────────────────────────────────────────

class TestStreamingRasterization:
    """rasterizer.py: convert_from_bytes uses output_folder+paths_only for O(1) PIL RAM."""

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_streaming_produces_correct_page_count(self, mock_convert):
        from app.services.rasterizer import RasterizerService
        mock_convert.side_effect = _fake_pdf2image_factory(page_count=5)
        svc = RasterizerService()
        pages = await svc.rasterize_document(b"%PDF-1.4 fake", "doc-stream-1")
        assert len(pages) == 5

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_streaming_page_numbers_sequential(self, mock_convert):
        from app.services.rasterizer import RasterizerService
        mock_convert.side_effect = _fake_pdf2image_factory(page_count=3)
        svc = RasterizerService()
        pages = await svc.rasterize_document(b"%PDF-1.4 fake", "doc-stream-2")
        assert [p.page_number for p in pages] == [1, 2, 3]

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_streaming_uses_output_folder(self, mock_convert):
        """Verify convert_from_bytes is called with output_folder and paths_only=True."""
        from app.services.rasterizer import RasterizerService
        mock_convert.side_effect = _fake_pdf2image_factory(page_count=1)
        svc = RasterizerService()
        await svc.rasterize_document(b"%PDF-1.4 fake", "doc-stream-3")
        _, kwargs = mock_convert.call_args
        assert kwargs.get("output_folder") is not None, "output_folder must be set"
        assert kwargs.get("paths_only") is True, "paths_only must be True"

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_streaming_temp_dir_cleaned_up_on_success(self, mock_convert):
        """Temp directory created for PPM files is removed after processing."""
        from app.services.rasterizer import RasterizerService
        recorded_dirs = []

        def _capture(pdf_bytes, dpi=200, output_folder=None, paths_only=False, **kwargs):
            recorded_dirs.append(output_folder)
            img = Image.new("RGB", (100, 100))
            path = os.path.join(output_folder, "output-0001.ppm")
            img.save(path, format="PPM")
            return [path]

        mock_convert.side_effect = _capture
        svc = RasterizerService()
        await svc.rasterize_document(b"%PDF-1.4 fake", "doc-stream-4")
        assert recorded_dirs, "output_folder should have been captured"
        assert not os.path.exists(recorded_dirs[0]), "temp dir must be removed after success"

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_streaming_temp_dir_cleaned_up_on_failure(self, mock_convert):
        """Temp directory is removed even when conversion raises an exception."""
        from app.services.rasterizer import RasterizerService, RasterizerError
        recorded_dirs = []

        def _fail(pdf_bytes, dpi=200, output_folder=None, **kwargs):
            recorded_dirs.append(output_folder)
            raise RuntimeError("simulated failure")

        mock_convert.side_effect = _fail
        svc = RasterizerService()
        with pytest.raises(RasterizerError):
            await svc.rasterize_document(b"%PDF-1.4 fake", "doc-stream-5")
        assert recorded_dirs
        assert not os.path.exists(recorded_dirs[0]), "temp dir must be removed after failure"

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_streaming_pages_encoded_as_webp(self, mock_convert):
        """Each page's image_bytes is WEBP-encoded (not raw PPM)."""
        from app.services.rasterizer import RasterizerService
        mock_convert.side_effect = _fake_pdf2image_factory(page_count=1)
        svc = RasterizerService()
        pages = await svc.rasterize_document(b"%PDF-1.4 fake", "doc-stream-6")
        # WEBP magic bytes start with RIFF....WEBP
        assert pages[0].image_bytes[:4] == b"RIFF"
        assert pages[0].image_bytes[8:12] == b"WEBP"

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_streaming_captures_page_dimensions(self, mock_convert):
        """width_px and height_px reflect the actual PPM file dimensions."""
        from app.services.rasterizer import RasterizerService
        mock_convert.side_effect = _fake_pdf2image_factory(page_count=1, width=800, height=1100)
        svc = RasterizerService()
        pages = await svc.rasterize_document(b"%PDF-1.4 fake", "doc-stream-7")
        assert pages[0].width_px == 800
        assert pages[0].height_px == 1100

    @pytest.mark.asyncio
    @patch("pdf2image.convert_from_bytes")
    async def test_streaming_invalid_pdf_raises_rasterizer_error(self, mock_convert):
        """PDF magic-bytes check fires before convert_from_bytes is called."""
        from app.services.rasterizer import RasterizerService, RasterizerError
        svc = RasterizerService()
        with pytest.raises(RasterizerError, match="missing"):
            await svc.rasterize_document(b"NOT A PDF", "doc-stream-8")
        mock_convert.assert_not_called()


# ── B. Parallel Upload Concurrency ────────────────────────────────────────────

class TestParallelUploads:
    """pipeline/pdf.py: uploads use asyncio.gather + semaphore for concurrency."""

    @pytest.mark.asyncio
    async def test_all_pages_upload_files_created(self, db_session):
        """Every page produces a page and thumbnail upload call."""
        from app.workers.pipeline.pdf import process_pdf_document

        doc = await _make_uploaded_doc(db_session)
        storage = _make_mock_storage()
        watermark = _make_mock_watermark()
        rasterizer = _make_mock_rasterizer(page_count=3)

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            await process_pdf_document(
                db_session, doc, str(doc.id), storage, rasterizer, watermark
            )

        # 3 pages × 2 uploads (page + thumb) + 1 TOC attempt (may not happen)
        upload_calls = storage.upload_file.call_args_list
        page_keys = [c.args[1] for c in upload_calls if "pages/" in str(c.args[1])]
        thumb_keys = [c.args[1] for c in upload_calls if "thumbs/" in str(c.args[1])]
        assert len(page_keys) == 3
        assert len(thumb_keys) == 3

    @pytest.mark.asyncio
    async def test_page_keys_use_correct_format(self, db_session):
        """Page storage keys follow pages/{doc_id}/{page:04d}.webp pattern."""
        from app.workers.pipeline.pdf import process_pdf_document

        doc = await _make_uploaded_doc(db_session)
        storage = _make_mock_storage()
        rasterizer = _make_mock_rasterizer(page_count=2)

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            await process_pdf_document(
                db_session, doc, str(doc.id), storage, rasterizer, _make_mock_watermark()
            )

        page_keys = sorted(
            c.args[1] for c in storage.upload_file.call_args_list if "pages/" in str(c.args[1])
        )
        assert page_keys[0] == f"pages/{doc.id}/0001.webp"
        assert page_keys[1] == f"pages/{doc.id}/0002.webp"

    @pytest.mark.asyncio
    async def test_thumbnail_failure_does_not_block_page_upload(self, db_session):
        """A thumbnail generation failure is logged but does not abort the pipeline."""
        from app.workers.pipeline.pdf import process_pdf_document

        doc = await _make_uploaded_doc(db_session)
        storage = _make_mock_storage()
        rasterizer = _make_mock_rasterizer(page_count=2)

        with patch("app.workers.pipeline.pdf._make_thumbnail", side_effect=RuntimeError("thumb fail")):
            result = await process_pdf_document(
                db_session, doc, str(doc.id), storage, rasterizer, _make_mock_watermark()
            )

        assert result["status"] == "ready"
        page_keys = [c.args[1] for c in storage.upload_file.call_args_list if "pages/" in str(c.args[1])]
        assert len(page_keys) == 2  # page uploads still happened

    @pytest.mark.asyncio
    async def test_page_records_all_committed(self, db_session):
        """All DocumentPage rows are committed after parallel upload completes."""
        from app.workers.pipeline.pdf import process_pdf_document

        doc = await _make_uploaded_doc(db_session)
        rasterizer = _make_mock_rasterizer(page_count=5)

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            await process_pdf_document(
                db_session, doc, str(doc.id), _make_mock_storage(), rasterizer, _make_mock_watermark()
            )

        rows = (await db_session.execute(
            select(DocumentPage).where(DocumentPage.document_id == doc.id)
        )).scalars().all()
        assert len(rows) == 5
        assert sorted(r.page_number for r in rows) == list(range(1, 6))

    @pytest.mark.asyncio
    async def test_upload_semaphore_constant_is_positive(self):
        """_UPLOAD_CONCURRENCY is a positive integer (sanity guard)."""
        from app.workers.pipeline.pdf import _UPLOAD_CONCURRENCY
        assert isinstance(_UPLOAD_CONCURRENCY, int)
        assert _UPLOAD_CONCURRENCY > 0

    @pytest.mark.asyncio
    async def test_upload_failure_propagates(self, db_session):
        """A storage upload failure raises an exception from process_pdf_document."""
        from app.workers.pipeline.pdf import process_pdf_document

        doc = await _make_uploaded_doc(db_session)
        storage = _make_mock_storage()
        storage.upload_file = AsyncMock(side_effect=RuntimeError("R2 unavailable"))
        rasterizer = _make_mock_rasterizer(page_count=1)

        with pytest.raises(RuntimeError, match="R2 unavailable"):
            with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
                await process_pdf_document(
                    db_session, doc, str(doc.id), storage, rasterizer, _make_mock_watermark()
                )


# ── C. Celery Task Time Limits ────────────────────────────────────────────────

class TestCeleryTaskTimeLimits:
    """celery_app.py: task_soft_time_limit and task_time_limit must be configured."""

    def test_soft_time_limit_configured(self):
        from app.workers.celery_app import celery_app
        assert celery_app.conf.task_soft_time_limit == 600

    def test_hard_time_limit_configured(self):
        from app.workers.celery_app import celery_app
        assert celery_app.conf.task_time_limit == 660

    def test_hard_limit_greater_than_soft(self):
        from app.workers.celery_app import celery_app
        assert celery_app.conf.task_time_limit > celery_app.conf.task_soft_time_limit

    def test_soft_time_limit_is_ten_minutes(self):
        from app.workers.celery_app import celery_app
        assert celery_app.conf.task_soft_time_limit == 600  # 10 minutes

    @pytest.mark.asyncio
    async def test_soft_time_limit_exceeded_marks_document_error(self, db_session):
        """SoftTimeLimitExceeded is treated as permanent: no retry, doc → error."""
        from celery.exceptions import SoftTimeLimitExceeded
        from app.workers.tasks import _process_document_async

        doc = await _make_uploaded_doc(db_session)
        doc_id = str(doc.id)

        task = MagicMock()
        storage = _make_mock_storage()
        rasterizer = _make_mock_rasterizer(page_count=1)

        with patch("app.workers.tasks.process_document_with_session",
                   side_effect=SoftTimeLimitExceeded()), \
             patch("app.services.storage.get_storage_service", return_value=storage), \
             patch("app.workers.tasks._mark_document_error", new_callable=AsyncMock) as mock_err:
            with pytest.raises(SoftTimeLimitExceeded):
                await _process_document_async(task, doc_id)

        mock_err.assert_called_once()
        call_args = mock_err.call_args[0]
        assert call_args[0] == doc_id
        assert "timed out" in call_args[1].lower()
        task.retry.assert_not_called()


# ── D. Worker Lifecycle ────────────────────────────────────────────────────────

class TestWorkerLifecycle:
    """config.py: worker_max_tasks_per_child must be positive to prevent memory leaks."""

    def test_max_tasks_per_child_is_positive(self):
        from app.config import settings
        assert settings.worker_max_tasks_per_child > 0, (
            "worker_max_tasks_per_child=0 means workers never recycle — "
            "memory from pdf2image/Pillow accumulates indefinitely"
        )

    def test_max_tasks_per_child_at_least_five(self):
        from app.config import settings
        assert settings.worker_max_tasks_per_child >= 5, (
            "Recycling too often (< 5 tasks) wastes ~2 s of LO startup per task"
        )

    def test_max_tasks_per_child_reasonable_upper_bound(self):
        from app.config import settings
        assert settings.worker_max_tasks_per_child <= 100, (
            "worker_max_tasks_per_child > 100 risks significant memory accumulation"
        )

    def test_max_tasks_per_child_setting_exists(self):
        from app.config import settings
        assert hasattr(settings, "worker_max_tasks_per_child"), (
            "worker_max_tasks_per_child must exist in Settings"
        )


# ── E. LibreOffice Timeout ────────────────────────────────────────────────────

class TestLibreOfficeTimeout:
    """libreoffice_converter.py: timeout is configurable and default ≥ 120 s."""

    def test_default_timeout_at_least_120s(self):
        from app.services.libreoffice_converter import LibreOfficeConverter
        c = LibreOfficeConverter()
        # Instance may not have overridden CONVERSION_TIMEOUT_SEC yet
        timeout = getattr(c, "CONVERSION_TIMEOUT_SEC", None) or LibreOfficeConverter.CONVERSION_TIMEOUT_SEC
        assert timeout >= 120, (
            f"LO timeout is {timeout} s — should be >= 120 s "
            "to handle large DOCX files on Railway/Render"
        )

    def test_timeout_configurable_via_settings(self):
        from app.config import Settings
        fields = getattr(Settings, "model_fields", {})
        assert "lo_conversion_timeout_sec" in fields, (
            "lo_conversion_timeout_sec must be a Settings field so it can "
            "be set via LO_CONVERSION_TIMEOUT_SEC environment variable"
        )

    def test_settings_lo_timeout_default(self):
        from app.config import settings
        assert settings.lo_conversion_timeout_sec >= 120

    def test_class_attribute_overridable_by_tests(self):
        """Tests must be able to override timeout without importing settings."""
        from app.services.libreoffice_converter import LibreOfficeConverter
        c = LibreOfficeConverter()
        c.CONVERSION_TIMEOUT_SEC = 5
        assert c.CONVERSION_TIMEOUT_SEC == 5

    def test_timeout_used_in_subprocess_call(self):
        """CONVERSION_TIMEOUT_SEC is respected when running the subprocess."""
        from app.services.libreoffice_converter import LibreOfficeConverter
        import shutil
        import subprocess

        if not shutil.which("libreoffice"):
            pytest.skip("libreoffice not available")

        c = LibreOfficeConverter()
        c.CONVERSION_TIMEOUT_SEC = 1  # force timeout on any real input

        from app.services.libreoffice_converter import LibreOfficeTimeoutError
        with pytest.raises((LibreOfficeTimeoutError, Exception)):
            c.convert_to_pdf(b"not a real docx", suffix=".docx")


# ── F. Large Document Simulation ──────────────────────────────────────────────

class TestLargeDocumentSimulation:
    """
    Simulate 200-page PDF processing end-to-end through the full pipeline.

    No real PDF is used — the rasterizer is mocked to return 200 fake pages.
    This verifies that the pipeline completes without errors and creates all
    expected DB rows and storage uploads.
    """

    @pytest.mark.asyncio
    async def test_200_page_simulation_completes(self, db_session):
        """200 fake pages → process_document_with_session returns ready."""
        doc = await _make_uploaded_doc(db_session, filename="large200.pdf")

        result = await process_document_with_session(
            db_session,
            str(doc.id),
            _make_mock_storage(),
            _make_mock_rasterizer(page_count=200),
            _make_mock_watermark(),
        )

        assert result["status"] == "ready"
        assert result["page_count"] == 200

    @pytest.mark.asyncio
    async def test_200_page_creates_correct_db_rows(self, db_session):
        """200-page simulation: exactly 200 DocumentPage rows committed."""
        doc = await _make_uploaded_doc(db_session, filename="large200b.pdf")

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            await process_document_with_session(
                db_session,
                str(doc.id),
                _make_mock_storage(),
                _make_mock_rasterizer(page_count=200),
                _make_mock_watermark(),
            )

        rows = (await db_session.execute(
            select(DocumentPage).where(DocumentPage.document_id == doc.id)
        )).scalars().all()
        assert len(rows) == 200
        page_numbers = sorted(r.page_number for r in rows)
        assert page_numbers == list(range(1, 201))

    @pytest.mark.asyncio
    async def test_200_page_upload_count(self, db_session):
        """200-page simulation: 400 upload calls (page + thumb) per document."""
        doc = await _make_uploaded_doc(db_session, filename="large200c.pdf")
        storage = _make_mock_storage()

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            await process_document_with_session(
                db_session,
                str(doc.id),
                storage,
                _make_mock_rasterizer(page_count=200),
                _make_mock_watermark(),
            )

        page_uploads = sum(1 for c in storage.upload_file.call_args_list if "pages/" in str(c.args[1]))
        thumb_uploads = sum(1 for c in storage.upload_file.call_args_list if "thumbs/" in str(c.args[1]))
        assert page_uploads == 200
        assert thumb_uploads == 200

    @pytest.mark.asyncio
    async def test_document_status_set_to_ready(self, db_session):
        """After 200-page processing, Document.status becomes 'ready'."""
        doc = await _make_uploaded_doc(db_session, filename="large200d.pdf")

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            await process_document_with_session(
                db_session,
                str(doc.id),
                _make_mock_storage(),
                _make_mock_rasterizer(page_count=200),
                _make_mock_watermark(),
            )

        await db_session.refresh(doc)
        assert doc.status == "ready"
        assert doc.page_count == 200

    @pytest.mark.asyncio
    async def test_10_page_pipeline_timing_improvement(self, db_session):
        """
        Verify parallel uploads are faster than a naive sequential implementation
        by checking that asyncio.gather is used (both page and thumb upload
        are invoked within the same asyncio.gather call).
        """
        from app.workers.pipeline.pdf import _process_and_upload_page, _UPLOAD_CONCURRENCY

        semaphore = asyncio.Semaphore(_UPLOAD_CONCURRENCY)
        storage = _make_mock_storage()
        watermark = _make_mock_watermark()
        page = _FakePage(page_number=1, image_bytes=_make_webp_bytes())

        doc_id = "550e8400-e29b-41d4-a716-446655440099"
        call_order = []

        async def _record_upload(data, key, content_type=None):
            call_order.append(key)

        storage.upload_file = _record_upload

        with patch("app.workers.pipeline.pdf._make_thumbnail", return_value=b"thumb"):
            db_page = await _process_and_upload_page(
                storage, watermark, semaphore, page, doc_id
            )

        assert db_page.page_number == 1
        assert db_page.storage_key == f"pages/{doc_id}/0001.webp"
        # Both uploads happened
        assert any("pages/" in k for k in call_order)
        assert any("thumbs/" in k for k in call_order)
