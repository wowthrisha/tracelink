"""
Unit tests for the DocumentAdapter registry and all six built-in adapters.

These tests exercise the adapter layer in complete isolation — no DB, no storage,
no HTTP.  They verify:
  - All six format types are registered
  - Each adapter reports the correct viewer_mode, capabilities, and MIME types
  - validate_bytes() accepts valid content and rejects invalid content
  - extract_toc() delegates correctly (no network/storage I/O)
  - allowed_content_types() is a superset of all adapter MIME types
  - The registry fallback for unknown types returns the PDF adapter
"""
import pytest

from app.services.adapters import get_adapter, all_adapters, allowed_content_types


# ── A. Registry completeness ──────────────────────────────────────────────────

class TestRegistry:
    def test_all_six_types_registered(self):
        for ft in ("pdf", "txt", "md", "log", "docx", "doc"):
            adapter = get_adapter(ft)
            assert adapter.file_type == ft

    def test_unknown_type_falls_back_to_pdf(self):
        adapter = get_adapter("unknown_format_xyz")
        assert adapter.file_type == "pdf"

    def test_all_adapters_returns_eight_entries(self):
        assert len(all_adapters()) == 8

    def test_allowed_content_types_contains_pdf(self):
        assert "application/pdf" in allowed_content_types()

    def test_allowed_content_types_contains_text_plain(self):
        assert "text/plain" in allowed_content_types()

    def test_allowed_content_types_contains_markdown(self):
        assert "text/markdown" in allowed_content_types()

    def test_allowed_content_types_contains_log_types(self):
        cts = allowed_content_types()
        assert "text/x-log" in cts
        assert "text/x-log-file" in cts

    def test_allowed_content_types_contains_docx(self):
        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in allowed_content_types()
        )

    def test_allowed_content_types_contains_doc(self):
        assert "application/msword" in allowed_content_types()

    def test_allowed_content_types_excludes_octet_stream(self):
        # application/octet-stream is added by the upload router as a pass-through,
        # not by individual adapters.
        assert "application/octet-stream" not in allowed_content_types()

    def test_adapter_file_type_attribute_matches_registry_key(self):
        for adapter in all_adapters():
            assert get_adapter(adapter.file_type) is adapter


# ── B. PDF adapter ────────────────────────────────────────────────────────────

class TestPDFAdapter:
    def setup_method(self):
        self.adapter = get_adapter("pdf")

    def test_viewer_mode_is_image(self):
        assert self.adapter.viewer_mode == "image"

    def test_supports_toc(self):
        assert self.adapter.supports_toc()

    def test_supports_toc_sidecar(self):
        assert self.adapter.supports_toc_sidecar()

    def test_no_toc_fallback_to_text(self):
        assert not self.adapter.toc_fallback_to_text()

    def test_supports_thumbnails(self):
        assert self.adapter.supports_thumbnails()

    def test_does_not_support_search(self):
        assert not self.adapter.supports_search()

    def test_upload_mime_types(self):
        assert "application/pdf" in self.adapter.upload_mime_types()

    def test_content_type_for_storage(self):
        assert self.adapter.content_type_for_storage() == "application/pdf"

    def test_max_upload_bytes_positive(self):
        assert self.adapter.max_upload_bytes() > 0

    def test_size_exceeded_message_contains_mb(self):
        assert "MB" in self.adapter.size_exceeded_message()

    def test_validate_bytes_accepts_valid_pdf(self):
        # No exception should be raised
        self.adapter.validate_bytes(b"%PDF-1.4 content", "test.pdf")

    def test_validate_bytes_rejects_non_pdf(self):
        with pytest.raises(ValueError, match="valid PDF"):
            self.adapter.validate_bytes(b"not a pdf", "test.pdf")

    def test_validate_bytes_rejects_empty(self):
        with pytest.raises(ValueError):
            self.adapter.validate_bytes(b"", "empty.pdf")

    def test_extract_toc_returns_empty_without_pdf_bytes(self):
        result = self.adapter.extract_toc()
        assert result == []

    def test_extract_toc_returns_list_with_pdf_bytes(self):
        # Minimal valid PDF with no bookmarks → empty list (no error)
        minimal_pdf = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
            b"xref\n0 1\n0000000000 65535 f\n"
            b"trailer\n<< /Size 1 >>\nstartxref\n9\n%%EOF"
        )
        result = self.adapter.extract_toc(pdf_bytes=minimal_pdf)
        assert isinstance(result, list)


# ── C. TXT adapter ────────────────────────────────────────────────────────────

class TestTXTAdapter:
    def setup_method(self):
        self.adapter = get_adapter("txt")

    def test_viewer_mode_is_text(self):
        assert self.adapter.viewer_mode == "text"

    def test_supports_toc(self):
        assert self.adapter.supports_toc()

    def test_supports_search(self):
        assert self.adapter.supports_search()

    def test_does_not_support_toc_sidecar(self):
        assert not self.adapter.supports_toc_sidecar()

    def test_does_not_support_thumbnails(self):
        assert not self.adapter.supports_thumbnails()

    def test_upload_mime_types(self):
        assert "text/plain" in self.adapter.upload_mime_types()

    def test_content_type_for_storage(self):
        assert self.adapter.content_type_for_storage() == "text/plain"

    def test_max_upload_bytes_positive(self):
        assert self.adapter.max_upload_bytes() > 0

    def test_size_exceeded_message_mentions_text(self):
        assert "Text file" in self.adapter.size_exceeded_message()

    def test_validate_bytes_accepts_clean_text(self):
        self.adapter.validate_bytes(b"Hello, world!\n", "notes.txt")

    def test_validate_bytes_rejects_binary(self):
        with pytest.raises(ValueError):
            self.adapter.validate_bytes(b"hello\x00world", "notes.txt")

    def test_extract_toc_empty_without_content(self):
        assert self.adapter.extract_toc() == []

    def test_extract_toc_with_numbered_headings(self):
        text = "1. Introduction\nsome body text\n2. Methods\nmore body\n"
        result = self.adapter.extract_toc(text_content=text)
        assert isinstance(result, list)
        assert len(result) >= 2


# ── D. MD adapter ─────────────────────────────────────────────────────────────

class TestMDAdapter:
    def setup_method(self):
        self.adapter = get_adapter("md")

    def test_viewer_mode_is_text(self):
        assert self.adapter.viewer_mode == "text"

    def test_upload_mime_types(self):
        assert "text/markdown" in self.adapter.upload_mime_types()

    def test_content_type_for_storage(self):
        assert self.adapter.content_type_for_storage() == "text/markdown"

    def test_validate_bytes_accepts_markdown(self):
        self.adapter.validate_bytes(b"# Heading\n\nbody text\n", "doc.md")

    def test_validate_bytes_rejects_binary(self):
        with pytest.raises(ValueError):
            self.adapter.validate_bytes(b"PK\x03\x04\x00\x00", "doc.md")

    def test_extract_toc_with_md_headings(self):
        text = "# Chapter 1\n\nIntro text.\n\n## Section 1.1\n\nDetails.\n"
        result = self.adapter.extract_toc(text_content=text)
        assert isinstance(result, list)
        assert len(result) >= 2
        assert result[0]["title"] == "Chapter 1"


# ── E. LOG adapter ────────────────────────────────────────────────────────────

class TestLOGAdapter:
    def setup_method(self):
        self.adapter = get_adapter("log")

    def test_viewer_mode_is_text(self):
        assert self.adapter.viewer_mode == "text"

    def test_upload_mime_types_include_log_types(self):
        mimes = self.adapter.upload_mime_types()
        assert "text/x-log" in mimes
        assert "text/x-log-file" in mimes

    def test_content_type_for_storage_is_plain(self):
        # LOG files stored as text/plain
        assert self.adapter.content_type_for_storage() == "text/plain"

    def test_validate_bytes_accepts_log_text(self):
        self.adapter.validate_bytes(b"2026-01-01 INFO server started\n", "app.log")

    def test_validate_bytes_rejects_binary(self):
        with pytest.raises(ValueError):
            self.adapter.validate_bytes(b"\x00\x01\x02\x03", "app.log")

    def test_size_exceeded_message_mentions_text(self):
        assert "Text file" in self.adapter.size_exceeded_message()


# ── F. DOCX adapter ───────────────────────────────────────────────────────────

class TestDOCXAdapter:
    """Phase D2: DOCX adapter is now image-based (LibreOffice → PDF pipeline)."""

    def setup_method(self):
        self.adapter = get_adapter("docx")

    def test_viewer_mode_is_image(self):
        assert self.adapter.viewer_mode == "image"

    def test_supports_toc_sidecar(self):
        assert self.adapter.supports_toc_sidecar()

    def test_no_toc_fallback_to_text(self):
        # TOC comes from heading-style sidecar; no text fallback needed
        assert not self.adapter.toc_fallback_to_text()

    def test_supports_thumbnails(self):
        assert self.adapter.supports_thumbnails()

    def test_upload_mime_types(self):
        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in self.adapter.upload_mime_types()
        )

    def test_content_type_for_storage(self):
        assert "wordprocessingml" in self.adapter.content_type_for_storage()

    def test_max_upload_bytes_uses_large_limit(self):
        from app.config import settings
        assert self.adapter.max_upload_bytes() == settings.max_upload_bytes

    def test_size_exceeded_message_no_text_prefix(self):
        msg = self.adapter.size_exceeded_message()
        assert "Text file" not in msg
        assert "MB" in msg

    def test_validate_bytes_accepts_zip_header(self):
        self.adapter.validate_bytes(b"PK\x03\x04" + b"\x00" * 30, "doc.docx")

    def test_validate_bytes_rejects_non_zip(self):
        with pytest.raises(ValueError, match="ZIP header"):
            self.adapter.validate_bytes(b"not a docx", "doc.docx")

    def test_extract_toc_empty_without_content(self):
        assert self.adapter.extract_toc() == []

    def test_extract_toc_defensive_fallback_accepts_text(self):
        # The viewer uses the heading sidecar in production; this tests the
        # defensive extract_toc() method that handles direct callers.
        text = "# Chapter 1\n\nbody\n\n## Section 1.1\n\nmore\n"
        result = self.adapter.extract_toc(text_content=text)
        assert isinstance(result, list)
        titles = [e["title"] for e in result]
        assert "Chapter 1" in titles


# ── G. DOC adapter ────────────────────────────────────────────────────────────

class TestDOCAdapter:
    def setup_method(self):
        self.adapter = get_adapter("doc")

    def test_viewer_mode_is_text(self):
        assert self.adapter.viewer_mode == "text"

    def test_supports_toc_sidecar(self):
        assert self.adapter.supports_toc_sidecar()

    def test_toc_fallback_to_text(self):
        assert self.adapter.toc_fallback_to_text()

    def test_upload_mime_types(self):
        assert "application/msword" in self.adapter.upload_mime_types()

    def test_content_type_for_storage(self):
        assert self.adapter.content_type_for_storage() == "application/msword"

    def test_max_upload_bytes_uses_large_limit(self):
        from app.config import settings
        assert self.adapter.max_upload_bytes() == settings.max_upload_bytes

    def test_validate_bytes_accepts_ole2_header(self):
        ole2 = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" + b"\x00" * 10
        self.adapter.validate_bytes(ole2, "legacy.doc")

    def test_validate_bytes_rejects_non_ole2(self):
        with pytest.raises(ValueError, match="OLE2 header"):
            self.adapter.validate_bytes(b"not a doc", "legacy.doc")

    def test_validate_bytes_rejects_short_file(self):
        with pytest.raises(ValueError):
            self.adapter.validate_bytes(b"\xD0\xCF", "short.doc")

    def test_extract_toc_uses_plain_text_rules(self):
        # DOC is stored as plain text after antiword conversion
        text = "CHAPTER ONE\n\nsome text\n\nCHAPTER TWO\n\nmore text\n"
        result = self.adapter.extract_toc(text_content=text)
        assert isinstance(result, list)


# ── H. Viewer mode classification ────────────────────────────────────────────

class TestViewerModeClassification:
    """Verify that viewer_mode correctly separates image vs text formats.

    After Phase D2: PDF and DOCX are image mode; TXT/MD/LOG/DOC are text mode.
    """

    @pytest.mark.parametrize("ft", ["pdf", "docx"])
    def test_image_mode_formats(self, ft):
        assert get_adapter(ft).viewer_mode == "image"

    @pytest.mark.parametrize("ft", ["txt", "md", "log", "doc"])
    def test_text_mode_formats(self, ft):
        assert get_adapter(ft).viewer_mode == "text"

    def test_pdf_is_not_text_mode(self):
        assert get_adapter("pdf").viewer_mode != "text"

    def test_docx_is_not_text_mode(self):
        assert get_adapter("docx").viewer_mode != "text"


# ── I. Sidecar classification ─────────────────────────────────────────────────

class TestSidecarClassification:
    @pytest.mark.parametrize("ft", ["pdf", "docx", "doc"])
    def test_sidecar_supported_types(self, ft):
        assert get_adapter(ft).supports_toc_sidecar()

    @pytest.mark.parametrize("ft", ["txt", "md", "log"])
    def test_no_sidecar_for_plain_text(self, ft):
        assert not get_adapter(ft).supports_toc_sidecar()

    def test_pdf_does_not_fallback(self):
        assert not get_adapter("pdf").toc_fallback_to_text()

    def test_docx_does_not_fallback(self):
        # Phase D2: DOCX uses heading-style sidecar; no text fallback needed
        assert not get_adapter("docx").toc_fallback_to_text()

    def test_doc_fallback_to_text(self):
        # DOC (legacy text pipeline) still falls back to text extraction
        assert get_adapter("doc").toc_fallback_to_text()

    @pytest.mark.parametrize("ft", ["txt", "md", "log"])
    def test_plain_text_does_not_fallback(self, ft):
        assert not get_adapter(ft).toc_fallback_to_text()
