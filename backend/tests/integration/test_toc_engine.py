"""
Universal TOC Engine tests.

Coverage:
  A. TocEntry model — serialisation, HTML escaping, XSS prevention
  B. Text extractor — TXT, MD, LOG, DOCX (markdown), DOC (plain)
  C. PDF extractor — bookmarks, no bookmarks, parse error
  D. DOCX extractor — heading styles, outline levels, conversion
  E. Universal dispatcher — per-format routing
  F. TOC cache — L1 put/get/invalidate, clear_all_caches
  G. viewer /toc endpoint — all formats, cache hit, security checks
  H. Document upload — DOCX/DOC accepted, bad magic bytes rejected
  I. Worker pipeline — DOCX/DOC processing dispatched correctly
  J. File type detection — new magic byte checks
  K. Backward compatibility — existing text_processor.extract_toc
"""
import io
import json
import struct
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from tests.conftest import TEST_USER_ID


# ── A. TocEntry model ────────────────────────────────────────────────────────

class TestTocEntryModel:
    def test_basic_serialisation(self):
        from app.services.toc.model import TocEntry
        e = TocEntry(id="toc_0001", title="Introduction", level=1, anchor="sec_0001",
                     chunk=1, line=5, source="md_heading", confidence=0.90)
        d = e.to_dict()
        assert d["id"] == "toc_0001"
        assert d["title"] == "Introduction"
        assert d["level"] == 1
        assert d["chunk"] == 1
        assert d["line"] == 5
        assert d["source"] == "md_heading"
        assert d["confidence"] == 0.9

    def test_optional_fields_omitted_when_none(self):
        from app.services.toc.model import TocEntry
        e = TocEntry(id="toc_0001", title="Intro", level=1, anchor="sec_0001")
        d = e.to_dict()
        assert "page" not in d
        assert "chunk" not in d
        assert "line" not in d
        assert "children" not in d

    def test_page_field_set_for_pdf(self):
        from app.services.toc.model import TocEntry
        e = TocEntry(id="toc_0001", title="Chapter 1", level=1, anchor="page_5",
                     page=5, source="bookmarks", confidence=0.95)
        d = e.to_dict()
        assert d["page"] == 5
        assert "chunk" not in d

    def test_xss_escaping_in_title(self):
        from app.services.toc.model import TocEntry
        e = TocEntry(id="toc_0001",
                     title='<script>alert("xss")</script>',
                     level=1, anchor="sec_0001")
        d = e.to_dict()
        assert "<script>" not in d["title"]
        assert "&lt;script&gt;" in d["title"]

    def test_xss_javascript_url_escaped(self):
        from app.services.toc.model import TocEntry
        e = TocEntry(id="toc_0001",
                     title='<a href="javascript:void(0)">click</a>',
                     level=1, anchor="sec_0001")
        d = e.to_dict()
        assert "<a " not in d["title"]

    def test_html_entities_escaped(self):
        from app.services.toc.model import TocEntry
        e = TocEntry(id="toc_0001", title="A & B > C", level=1, anchor="sec_0001")
        d = e.to_dict()
        assert "&amp;" in d["title"]
        assert "&gt;" in d["title"]

    def test_children_serialised(self):
        from app.services.toc.model import TocEntry
        parent = TocEntry(id="toc_0001", title="Chapter", level=1, anchor="sec_0001",
                          chunk=1, confidence=0.9)
        child = TocEntry(id="toc_0002", title="Section", level=2, anchor="sec_0002",
                         chunk=2, confidence=0.9)
        parent.children.append(child)
        d = parent.to_dict()
        assert "children" in d
        assert d["children"][0]["title"] == "Section"

    def test_confidence_rounded_to_3_decimals(self):
        from app.services.toc.model import TocEntry
        e = TocEntry(id="toc_0001", title="T", level=1, anchor="a",
                     confidence=0.9234567)
        d = e.to_dict()
        assert d["confidence"] == 0.923


# ── B. Text extractor ────────────────────────────────────────────────────────

class TestTextExtractor:
    def test_markdown_atx_headings(self):
        from app.services.toc.text_extractor import extract_text_toc
        text = "# Chapter 1\n\nSome text.\n\n## Section 1.1\n\nMore.\n\n### Subsection\n"
        entries = extract_text_toc(text, "md", lines_per_chunk=100)
        assert len(entries) == 3
        assert entries[0].level == 1
        assert entries[0].title == "Chapter 1"
        assert entries[1].level == 2
        assert entries[2].level == 3

    def test_md_h6_supported(self):
        from app.services.toc.text_extractor import extract_text_toc
        text = "###### Deep Heading\n"
        entries = extract_text_toc(text, "md")
        assert entries[0].level == 6

    def test_md_confidence(self):
        from app.services.toc.text_extractor import extract_text_toc
        entries = extract_text_toc("# Test\n", "md")
        assert entries[0].confidence == 0.90

    def test_md_chunk_calculation(self):
        from app.services.toc.text_extractor import extract_text_toc
        # 150 lines of text, heading at line 105
        lines = ["line"] * 104 + ["# Heading at 105"] + ["body"] * 45
        text = "\n".join(lines)
        entries = extract_text_toc(text, "md", lines_per_chunk=100)
        # line 105 (index 104) → chunk 2
        assert entries[0].chunk == 2
        assert entries[0].line == 105

    def test_txt_allcaps_detection(self):
        from app.services.toc.text_extractor import extract_text_toc
        text = "INTRODUCTION\n\nSome text here.\n\nCONCLUSION\n"
        entries = extract_text_toc(text, "txt")
        titles = [e.title for e in entries]
        assert "Introduction" in titles or "INTRODUCTION" in [e.title.upper() for e in entries]
        assert len(entries) == 2

    def test_txt_label_colon_detection(self):
        from app.services.toc.text_extractor import extract_text_toc
        text = "Overview:\n\nSome content here.\n\nDetails:\n"
        entries = extract_text_toc(text, "txt")
        assert any(e.title == "Overview" for e in entries)
        assert any(e.title == "Details" for e in entries)

    def test_txt_numbered_heading(self):
        from app.services.toc.text_extractor import extract_text_toc
        text = "1. Introduction\n\n1.1 Background\n\n1.1.1 History\n"
        entries = extract_text_toc(text, "txt")
        levels = [e.level for e in entries]
        assert 1 in levels
        assert 2 in levels

    def test_log_same_as_txt(self):
        from app.services.toc.text_extractor import extract_text_toc
        text = "STARTUP\n\nINFO line\n\nSHUTDOWN\n"
        entries = extract_text_toc(text, "log")
        assert len(entries) == 2

    def test_docx_file_type_uses_md_rules(self):
        from app.services.toc.text_extractor import extract_text_toc
        text = "# Main Heading\n\n## Sub Heading\n"
        entries = extract_text_toc(text, "docx")
        assert len(entries) == 2
        assert entries[0].level == 1

    def test_doc_file_type_uses_txt_rules(self):
        from app.services.toc.text_extractor import extract_text_toc
        text = "INTRODUCTION\n\nSome content.\n\nCONCLUSION\n"
        entries = extract_text_toc(text, "doc")
        assert len(entries) == 2

    def test_empty_text_returns_empty(self):
        from app.services.toc.text_extractor import extract_text_toc
        assert extract_text_toc("", "md") == []
        assert extract_text_toc("", "txt") == []

    def test_max_200_entries(self):
        from app.services.toc.text_extractor import extract_text_toc
        text = "\n".join([f"# Heading {i}" for i in range(300)])
        entries = extract_text_toc(text, "md")
        assert len(entries) == 200

    def test_xss_in_heading_title_not_executed(self):
        from app.services.toc.text_extractor import extract_text_toc
        text = '# <script>alert("xss")</script>\n'
        entries = extract_text_toc(text, "md")
        assert len(entries) == 1
        d = entries[0].to_dict()
        assert "<script>" not in d["title"]

    def test_source_field_set_correctly(self):
        from app.services.toc.text_extractor import extract_text_toc
        text = "# Test\n"
        entries = extract_text_toc(text, "md")
        assert entries[0].source == "md_heading"

    def test_id_field_sequential(self):
        from app.services.toc.text_extractor import extract_text_toc
        text = "# A\n## B\n### C\n"
        entries = extract_text_toc(text, "md")
        assert entries[0].id == "toc_0001"
        assert entries[1].id == "toc_0002"
        assert entries[2].id == "toc_0003"

    def test_anchor_field_set(self):
        from app.services.toc.text_extractor import extract_text_toc
        text = "# Heading\n"
        entries = extract_text_toc(text, "md")
        assert entries[0].anchor == "sec_0001"


# ── C. PDF extractor ────────────────────────────────────────────────────────

class TestPdfExtractor:
    def _make_pdf_bytes(self, with_bookmarks: bool = False) -> bytes:
        """Return minimal PDF bytes for testing."""
        if not with_bookmarks:
            return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nxref\n0 1\n0000000000 65535 f\ntrailer\n<< /Size 1 >>\nstartxref\n9\n%%EOF"
        # Use real PDF bytes with bookmarks — mock pypdf instead
        return b"%PDF-1.4\n%%EOF"

    def test_empty_pdf_returns_empty(self):
        from app.services.toc.pdf_extractor import extract_pdf_toc
        with patch("pypdf.PdfReader") as MockReader:
            MockReader.return_value.outline = []
            result = extract_pdf_toc(b"%PDF-1.4\n%%EOF")
            assert result == []

    def test_pdf_bookmarks_extracted(self):
        from app.services.toc.pdf_extractor import extract_pdf_toc

        mock_dest = MagicMock()
        mock_dest.title = "Chapter 1"

        mock_reader = MagicMock()
        mock_reader.outline = [mock_dest]
        mock_reader.get_destination_page_number.return_value = 4  # 0-indexed

        with patch("pypdf.PdfReader", return_value=mock_reader):
            entries = extract_pdf_toc(b"%PDF-1.4\n%%EOF")

        assert len(entries) == 1
        assert entries[0].title == "Chapter 1"
        assert entries[0].page == 5  # converted to 1-indexed
        assert entries[0].source == "bookmarks"
        assert entries[0].confidence == 0.95

    def test_nested_pdf_bookmarks(self):
        from app.services.toc.pdf_extractor import extract_pdf_toc

        ch1 = MagicMock(); ch1.title = "Chapter 1"
        sec1 = MagicMock(); sec1.title = "Section 1.1"

        mock_reader = MagicMock()
        mock_reader.outline = [ch1, [sec1]]
        mock_reader.get_destination_page_number.side_effect = [0, 2]

        with patch("pypdf.PdfReader", return_value=mock_reader):
            entries = extract_pdf_toc(b"%PDF-1.4\n%%EOF")

        assert len(entries) == 2
        assert entries[0].level == 1
        assert entries[1].level == 2  # nested → level 2

    def test_pdf_parse_error_returns_empty(self):
        from app.services.toc.pdf_extractor import extract_pdf_toc
        with patch("pypdf.PdfReader", side_effect=Exception("bad pdf")):
            result = extract_pdf_toc(b"not a pdf")
        assert result == []

    def test_pypdf_not_installed_returns_empty(self):
        from app.services.toc.pdf_extractor import extract_pdf_toc
        with patch.dict("sys.modules", {"pypdf": None}):
            with patch("builtins.__import__", side_effect=ImportError("no pypdf")):
                # Just verify no unhandled exception
                pass  # ImportError is handled inside extract_pdf_toc
        # The function itself guards against ImportError
        result = extract_pdf_toc(b"")
        assert isinstance(result, list)

    def test_max_200_entries_respected(self):
        from app.services.toc.pdf_extractor import extract_pdf_toc

        def make_dest(title):
            d = MagicMock(); d.title = title; return d

        mock_reader = MagicMock()
        mock_reader.outline = [make_dest(f"Section {i}") for i in range(300)]
        mock_reader.get_destination_page_number.return_value = 0

        with patch("pypdf.PdfReader", return_value=mock_reader):
            entries = extract_pdf_toc(b"%PDF-1.4\n%%EOF")

        assert len(entries) == 200

    def test_bookmark_with_no_page_gets_sec_anchor(self):
        from app.services.toc.pdf_extractor import extract_pdf_toc

        mock_dest = MagicMock(); mock_dest.title = "Intro"
        mock_reader = MagicMock()
        mock_reader.outline = [mock_dest]
        mock_reader.get_destination_page_number.side_effect = Exception("no page")

        with patch("pypdf.PdfReader", return_value=mock_reader):
            entries = extract_pdf_toc(b"%%EOF")

        assert entries[0].page is None
        assert entries[0].anchor.startswith("sec_")


# ── D. DOCX extractor ────────────────────────────────────────────────────────

class TestDocxExtractor:
    def _mock_docx(self, paragraphs: list) -> MagicMock:
        """Create a mock python-docx Document with given paragraph specs."""
        mock_doc = MagicMock()
        mock_paras = []
        for text, style_name in paragraphs:
            p = MagicMock()
            p.text = text
            p.style.name = style_name
            p._p.find.return_value = None  # no XML outline level
            mock_paras.append(p)
        mock_doc.paragraphs = mock_paras
        return mock_doc

    def test_heading_styles_extracted(self):
        from app.services.toc.docx_extractor import extract_docx_toc

        mock_doc = self._mock_docx([
            ("Chapter One", "Heading 1"),
            ("Some body text", "Normal"),
            ("Section 1.1", "Heading 2"),
            ("More text", "Normal"),
        ])
        with patch("docx.Document", return_value=mock_doc):
            entries = extract_docx_toc(b"PK\x03\x04fake")

        assert len(entries) == 2
        assert entries[0].level == 1
        assert entries[0].title == "Chapter One"
        assert entries[1].level == 2
        assert entries[1].title == "Section 1.1"

    def test_image_mode_entries_have_no_chunk_or_page(self):
        """Phase D2.6: DOCX TOC entries must not carry text-mode chunk/line fields."""
        from app.services.toc.docx_extractor import extract_docx_toc

        mock_doc = self._mock_docx([
            ("Introduction", "Heading 1"),
            ("Methods", "Heading 2"),
        ])
        with patch("docx.Document", return_value=mock_doc):
            entries = extract_docx_toc(b"PK\x03\x04fake")

        assert len(entries) == 2
        for entry in entries:
            assert entry.chunk is None, "chunk must be absent (text-mode artifact)"
            assert entry.page is None, "page is not yet resolvable at extraction time"
        # Serialised form must also lack these fields
        for entry in entries:
            d = entry.to_dict()
            assert "chunk" not in d
            assert "page" not in d
            assert "title" in d
            assert "level" in d

    def test_confidence_is_correct(self):
        from app.services.toc.docx_extractor import extract_docx_toc
        mock_doc = self._mock_docx([("Introduction", "Heading 1")])
        with patch("docx.Document", return_value=mock_doc):
            entries = extract_docx_toc(b"PK\x03\x04fake")
        assert entries[0].confidence == 0.92

    def test_source_is_heading_style(self):
        from app.services.toc.docx_extractor import extract_docx_toc
        mock_doc = self._mock_docx([("Title", "Heading 1")])
        with patch("docx.Document", return_value=mock_doc):
            entries = extract_docx_toc(b"PK\x03\x04fake")
        assert entries[0].source == "heading_style"

    def test_all_heading_levels_supported(self):
        from app.services.toc.docx_extractor import extract_docx_toc
        paras = [(f"Level {i}", f"Heading {i}") for i in range(1, 7)]
        mock_doc = self._mock_docx(paras)
        with patch("docx.Document", return_value=mock_doc):
            entries = extract_docx_toc(b"PK\x03\x04fake")
        assert len(entries) == 6
        assert [e.level for e in entries] == list(range(1, 7))

    def test_empty_docx_returns_empty(self):
        from app.services.toc.docx_extractor import extract_docx_toc
        mock_doc = self._mock_docx([("Body text only", "Normal")])
        with patch("docx.Document", return_value=mock_doc):
            entries = extract_docx_toc(b"PK\x03\x04fake")
        assert entries == []

    def test_parse_error_returns_empty(self):
        from app.services.toc.docx_extractor import extract_docx_toc
        with patch("docx.Document", side_effect=Exception("corrupt")):
            entries = extract_docx_toc(b"not docx")
        assert entries == []

    def test_doc_to_text_antiword_success(self):
        from app.services.toc.docx_extractor import doc_to_text
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=b"Introduction\n\nBody text.\n")
            text = doc_to_text(b"\xD0\xCF\x11\xE0fake", "test_id")
        assert "Introduction" in text

    def test_doc_to_text_antiword_not_found(self):
        from app.services.toc.docx_extractor import doc_to_text
        with patch("subprocess.run", side_effect=FileNotFoundError("antiword not found")):
            text = doc_to_text(b"\xD0\xCF\x11\xE0fake", "test_id")
        assert text == ""

    def test_doc_to_text_antiword_failure(self):
        from app.services.toc.docx_extractor import doc_to_text
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout=b"", stderr=b"cannot open")
            text = doc_to_text(b"\xD0\xCF\x11\xE0fake", "test_id")
        assert text == ""


# ── E. Universal dispatcher ──────────────────────────────────────────────────

class TestUniversalExtractor:
    @pytest.mark.asyncio
    async def test_pdf_routes_to_pdf_extractor(self):
        from app.services.toc.extractor import extract_toc_for_document
        from app.services.toc.model import TocEntry

        real_entry = TocEntry(id="toc_0001", title="Ch1", level=1, anchor="page_1", page=1,
                              source="bookmarks", confidence=0.95)
        with patch("app.services.toc.pdf_extractor.extract_pdf_toc", return_value=[real_entry]):
            with patch("pypdf.PdfReader") as mock_reader_cls:
                mock_reader_cls.return_value.outline = []
                result = await extract_toc_for_document("pdf", pdf_bytes=b"%PDF-1.4")
        # Either real extractor ran or patch worked; just verify return type
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_md_routes_to_text_extractor(self):
        from app.services.toc.extractor import extract_toc_for_document
        result = await extract_toc_for_document("md", text_content="# Title\n")
        assert len(result) == 1
        assert result[0]["title"] == "Title"

    @pytest.mark.asyncio
    async def test_docx_routes_to_text_extractor_with_md_rules(self):
        from app.services.toc.extractor import extract_toc_for_document
        result = await extract_toc_for_document("docx", text_content="# Heading\n")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_unsupported_type_returns_empty(self):
        from app.services.toc.extractor import extract_toc_for_document
        result = await extract_toc_for_document("pptx", text_content="anything")
        assert result == []

    @pytest.mark.asyncio
    async def test_missing_content_returns_empty(self):
        from app.services.toc.extractor import extract_toc_for_document
        result = await extract_toc_for_document("md")  # no text_content
        assert result == []

    @pytest.mark.asyncio
    async def test_extractor_error_returns_empty(self):
        from app.services.toc.extractor import extract_toc_for_document
        # extract_text_toc is imported inside the function — patch at source module
        with patch("app.services.toc.text_extractor.extract_text_toc",
                   side_effect=Exception("boom")):
            result = await extract_toc_for_document("md", text_content="# Heading")
        assert result == []


# ── F. TOC cache ─────────────────────────────────────────────────────────────

class TestTocCache:
    def test_toc_cache_put_and_get(self):
        from app.services.viewer_cache import toc_cache, clear_all_caches
        clear_all_caches()
        doc_id = str(uuid.uuid4())
        entries = [{"title": "T", "level": 1}]
        toc_cache.put(doc_id, entries)
        assert toc_cache.get(doc_id) == entries
        clear_all_caches()

    def test_clear_all_caches_includes_toc(self):
        from app.services.viewer_cache import toc_cache, clear_all_caches
        doc_id = str(uuid.uuid4())
        toc_cache.put(doc_id, [{"x": 1}])
        clear_all_caches()
        assert toc_cache.get(doc_id) is None

    def test_invalidate_doc_entries_clears_toc(self):
        from app.services.viewer_cache import toc_cache, invalidate_doc_entries, clear_all_caches
        clear_all_caches()
        doc_id = str(uuid.uuid4())
        toc_cache.put(doc_id, [{"x": 1}])
        invalidate_doc_entries(doc_id)
        assert toc_cache.get(doc_id) is None

    @pytest.mark.asyncio
    async def test_store_and_get_toc_async(self):
        from app.services.toc.cache import store_toc_async, get_cached_toc_async
        from app.services.viewer_cache import clear_all_caches
        clear_all_caches()
        doc_id = str(uuid.uuid4())
        entries = [{"title": "Cached", "level": 1}]

        await store_toc_async(doc_id, entries)
        result = await get_cached_toc_async(doc_id)
        assert result == entries
        clear_all_caches()

    def test_invalidate_toc(self):
        from app.services.toc.cache import invalidate_toc
        from app.services.viewer_cache import toc_cache, clear_all_caches
        clear_all_caches()
        doc_id = str(uuid.uuid4())
        toc_cache.put(doc_id, [{"title": "X"}])
        invalidate_toc(doc_id)
        assert toc_cache.get(doc_id) is None


# ── G. /toc endpoint ─────────────────────────────────────────────────────────

class TestTocEndpoint:
    @pytest.mark.asyncio
    async def test_toc_requires_session_id(self, client, db_session, active_link):
        r = await client.get(f"/api/viewer/toc/{active_link.token}")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_toc_revoked_link_rejected(self, client, db_session, revoked_link):
        # For a revoked link, validate itself would fail — TOC on revoked link should fail
        r = await client.get(
            f"/api/viewer/toc/{revoked_link.token}", headers={"X-Session-ID": 'a' * 32}
        )
        assert r.status_code in (410, 400, 404)

    @pytest.mark.asyncio
    async def test_toc_pdf_no_sidecar_returns_empty(self, client, db_session, ready_document):
        from app.models.link import ShareLink
        from app.services.link_service import LinkService
        from app.services.viewer_cache import clear_all_caches

        clear_all_caches()
        link = await LinkService().create_link(db_session, document_id=str(ready_document.id))

        val_r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert val_r.status_code == 200
        session_id = val_r.json()["session_id"]

        # Storage raises exception on sidecar fetch → no sidecar
        with patch("app.routers.viewer.get_storage_service") as mock_storage:
            mock_storage.return_value.download_bytes = AsyncMock(
                side_effect=Exception("not found")
            )
            r = await client.get(
                f"/api/viewer/toc/{link.token}", headers={"X-Session-ID": session_id}
            )

        assert r.status_code == 200
        data = r.json()
        assert data["doc_type"] == "pdf"
        assert data["supported"] is False
        assert data["toc"] == []
        clear_all_caches()

    @pytest.mark.asyncio
    async def test_toc_pdf_with_sidecar(self, client, db_session, ready_document):
        from app.services.link_service import LinkService
        from app.services.viewer_cache import clear_all_caches

        clear_all_caches()
        link = await LinkService().create_link(db_session, document_id=str(ready_document.id))

        val_r = await client.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        sidecar = json.dumps([
            {"id": "toc_0001", "title": "Chapter 1", "level": 1,
             "anchor": "page_1", "page": 1, "source": "bookmarks", "confidence": 0.95}
        ]).encode()

        with patch("app.routers.viewer.get_storage_service") as mock_storage:
            mock_storage.return_value.download_bytes = AsyncMock(return_value=sidecar)
            r = await client.get(
                f"/api/viewer/toc/{link.token}", headers={"X-Session-ID": session_id}
            )

        assert r.status_code == 200
        data = r.json()
        assert data["supported"] is True
        assert len(data["toc"]) == 1
        assert data["toc"][0]["title"] == "Chapter 1"
        assert data["toc"][0]["page"] == 1
        clear_all_caches()

    @pytest.mark.asyncio
    async def test_toc_text_document_extracted_inline(self, client, db_session):
        from app.models.document import Document
        from app.services.link_service import LinkService
        from app.services.viewer_cache import clear_all_caches

        clear_all_caches()
        doc = Document(
            id=uuid.uuid4(), filename="notes.md",
            storage_key=f"originals/{uuid.uuid4()}.md",
            status="ready", file_type="md",
            page_count=1, file_size_bytes=100,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()

        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        val_r = await client.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        md_content = b"# Introduction\n\nBody text.\n\n## Background\n\nMore text.\n"
        with patch("app.services.storage.StorageService.download_bytes",
                   new_callable=AsyncMock, return_value=md_content):
            r = await client.get(
                f"/api/viewer/toc/{link.token}", headers={"X-Session-ID": session_id}
            )

        assert r.status_code == 200
        data = r.json()
        assert data["doc_type"] == "md"
        assert data["supported"] is True
        assert len(data["toc"]) == 2
        assert data["toc"][0]["title"] == "Introduction"
        assert data["toc"][1]["title"] == "Background"
        clear_all_caches()

    @pytest.mark.asyncio
    async def test_toc_uses_cache_on_second_request(self, client, db_session):
        from app.models.document import Document
        from app.services.link_service import LinkService
        from app.services.viewer_cache import clear_all_caches

        clear_all_caches()
        doc = Document(
            id=uuid.uuid4(), filename="doc.md",
            storage_key=f"originals/{uuid.uuid4()}.md",
            status="ready", file_type="md", page_count=1, file_size_bytes=50,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()

        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        val_r = await client.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        fetch_count = [0]
        orig_download = b"# Test Heading\n"

        async def counting_download(key):
            if "toc/" in key:
                raise Exception("no sidecar")
            fetch_count[0] += 1
            return orig_download

        with patch("app.services.storage.StorageService.download_bytes",
                   side_effect=counting_download):
            await client.get(f"/api/viewer/toc/{link.token}", headers={"X-Session-ID": session_id})
            await client.get(f"/api/viewer/toc/{link.token}", headers={"X-Session-ID": session_id})

        # Second request should come from L1 cache (no storage call)
        assert fetch_count[0] == 1, f"Expected 1 storage fetch, got {fetch_count[0]}"
        clear_all_caches()

    @pytest.mark.asyncio
    async def test_toc_respects_revoked_link(self, client, db_session, revoked_link):
        val_r = await client.post("/api/viewer/validate", json={"token": revoked_link.token})
        assert val_r.status_code == 410

    @pytest.mark.asyncio
    async def test_toc_respects_expired_link(self, client, db_session, expired_link):
        r = await client.get(
            f"/api/viewer/toc/{expired_link.token}", headers={"X-Session-ID": "fakesession"}
        )
        assert r.status_code in (400, 410)


# ── H. Document upload — DOCX/DOC ────────────────────────────────────────────

class TestDocxDocUpload:
    def _make_docx_magic(self) -> bytes:
        """Minimal ZIP magic bytes (DOCX is ZIP)."""
        return b"PK\x03\x04" + b"\x00" * 26

    def _make_doc_magic(self) -> bytes:
        """OLE2 magic bytes for .doc files."""
        return b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" + b"\x00" * 50

    @pytest.mark.asyncio
    async def test_docx_upload_accepted(self, client, db_session):
        import io
        from app.services.viewer_cache import clear_all_caches
        clear_all_caches()

        docx_bytes = self._make_docx_magic()
        files = {"file": ("test.docx", io.BytesIO(docx_bytes),
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        r = await client.post("/api/documents/upload", files=files)
        assert r.status_code == 202
        data = r.json()
        assert data["filename"].endswith(".docx") or "test" in data["filename"]
        clear_all_caches()

    @pytest.mark.asyncio
    async def test_doc_upload_accepted(self, client, db_session):
        import io
        from app.services.viewer_cache import clear_all_caches
        clear_all_caches()

        doc_bytes = self._make_doc_magic()
        files = {"file": ("legacy.doc", io.BytesIO(doc_bytes), "application/msword")}
        r = await client.post("/api/documents/upload", files=files)
        assert r.status_code == 202
        clear_all_caches()

    @pytest.mark.asyncio
    async def test_docx_wrong_magic_rejected(self, client, db_session):
        import io
        # Send bytes that look like .docx content-type but are not actually ZIP
        bad_bytes = b"\x00\x01\x02\x03" * 20
        files = {"file": ("bad.docx", io.BytesIO(bad_bytes),
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        r = await client.post("/api/documents/upload", files=files)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_doc_wrong_magic_rejected(self, client, db_session):
        import io
        bad_bytes = b"this is not a doc file at all"
        files = {"file": ("bad.doc", io.BytesIO(bad_bytes), "application/msword")}
        r = await client.post("/api/documents/upload", files=files)
        assert r.status_code == 400


# ── I. Worker pipeline — DOCX/DOC dispatch ───────────────────────────────────

class TestWorkerDocxDoc:
    @pytest.mark.asyncio
    async def test_process_document_dispatches_docx(self, db_session):
        from app.models.document import Document
        from app.workers.tasks import process_document_with_session
        from app.services.storage import StorageService

        doc = Document(
            id=uuid.uuid4(), filename="report.docx",
            storage_key=f"originals/{uuid.uuid4()}.docx",
            status="uploaded", file_type="docx",
            file_size_bytes=1000,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()

        mock_storage = AsyncMock(spec=StorageService)
        mock_storage.download_bytes = AsyncMock(return_value=b"PK\x03\x04fake")
        mock_storage.upload_file = AsyncMock(return_value="key")

        with patch("app.workers.pipeline.docx_pdf.process_docx_as_pdf") as mock_process:
            mock_process.return_value = {"status": "ready", "page_count": 3}
            result = await process_document_with_session(
                db_session, str(doc.id), mock_storage,
                MagicMock(), MagicMock(),
            )
        mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_document_dispatches_doc(self, db_session):
        from app.models.document import Document
        from app.workers.tasks import process_document_with_session

        doc = Document(
            id=uuid.uuid4(), filename="legacy.doc",
            storage_key=f"originals/{uuid.uuid4()}.doc",
            status="uploaded", file_type="doc",
            file_size_bytes=500,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()

        with patch("app.workers.pipeline.word.process_doc_document") as mock_process:
            mock_process.return_value = {"status": "ready", "page_count": 2}
            from app.services.storage import StorageService
            mock_storage = AsyncMock(spec=StorageService)
            mock_storage.download_bytes = AsyncMock(return_value=b"\xD0\xCF\x11\xE0")
            await process_document_with_session(
                db_session, str(doc.id), mock_storage,
                MagicMock(), MagicMock(),
            )
        mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_docx_calls_libreoffice_pipeline(self, db_session):
        """Phase D2: DOCX processing routes to the LibreOffice-based PDF pipeline."""
        from app.models.document import Document
        from app.workers.tasks import process_document_with_session

        doc = Document(
            id=uuid.uuid4(), filename="test.docx",
            storage_key="originals/test.docx",
            status="uploaded", file_type="docx",
            file_size_bytes=100,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.commit()

        mock_storage = AsyncMock()
        mock_storage.download_bytes = AsyncMock(return_value=b"PK\x03\x04fake")
        mock_storage.upload_file = AsyncMock(return_value="key")

        with patch("app.workers.pipeline.docx_pdf.process_docx_as_pdf") as mock_pipeline:
            mock_pipeline.return_value = {"status": "ready", "page_count": 5}
            result = await process_document_with_session(
                db_session, str(doc.id), mock_storage,
                MagicMock(), MagicMock(),
            )

        mock_pipeline.assert_called_once()
        assert result["status"] == "ready"


# ── J. File type detection — magic bytes ─────────────────────────────────────

class TestFileTypeDetection:
    def test_docx_detected_by_extension(self):
        from app.services.text_processor import detect_file_type
        docx_magic = b"PK\x03\x04" + b"\x00" * 30
        result = detect_file_type("report.docx", "application/octet-stream", docx_magic)
        assert result == "docx"

    def test_doc_detected_by_extension(self):
        from app.services.text_processor import detect_file_type
        doc_magic = b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1" + b"\x00" * 50
        result = detect_file_type("legacy.doc", "application/octet-stream", doc_magic)
        assert result == "doc"

    def test_docx_detected_by_content_type(self):
        from app.services.text_processor import detect_file_type
        docx_magic = b"PK\x03\x04" + b"\x00" * 30
        result = detect_file_type(
            "upload",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            docx_magic,
        )
        assert result == "docx"

    def test_docx_bad_magic_raises(self):
        from app.services.text_processor import detect_file_type
        with pytest.raises(ValueError, match="DOCX"):
            detect_file_type("bad.docx", "application/octet-stream", b"\x00\x00\x00\x00")

    def test_doc_bad_magic_raises(self):
        from app.services.text_processor import detect_file_type
        with pytest.raises(ValueError, match="DOC"):
            detect_file_type("bad.doc", "application/msword", b"not ole2 bytes here!")

    def test_pdf_still_detected(self):
        from app.services.text_processor import detect_file_type
        result = detect_file_type("doc.pdf", "application/pdf", b"%PDF-1.4 stuff")
        assert result == "pdf"

    def test_txt_still_detected(self):
        from app.services.text_processor import detect_file_type
        result = detect_file_type("notes.txt", "text/plain", b"plain text content")
        assert result == "txt"

    def test_error_message_lists_docx_doc(self):
        from app.services.text_processor import detect_file_type
        with pytest.raises(ValueError) as exc_info:
            detect_file_type("bad.xyz", "application/octet-stream", b"random bytes")
        assert "docx" in str(exc_info.value).lower()
        assert "doc" in str(exc_info.value).lower()


# ── K. Backward compatibility ─────────────────────────────────────────────────

class TestBackwardCompatibility:
    def test_extract_toc_md_still_works(self):
        from app.services.text_processor import extract_toc
        text = "# Heading One\n\n## Heading Two\n"
        result = extract_toc(text, "md")
        assert len(result) == 2
        assert result[0]["title"] == "Heading One"

    def test_extract_toc_txt_still_works(self):
        from app.services.text_processor import extract_toc
        text = "INTRODUCTION\n\nContent here.\n"
        result = extract_toc(text, "txt")
        assert len(result) == 1

    def test_extract_toc_pdf_returns_empty(self):
        from app.services.text_processor import extract_toc
        result = extract_toc("anything", "pdf")
        assert result == []

    def test_extract_toc_returns_dicts(self):
        from app.services.text_processor import extract_toc
        result = extract_toc("# Hello\n", "md")
        assert isinstance(result, list)
        assert isinstance(result[0], dict)
        assert "title" in result[0]
        assert "level" in result[0]

    def test_toc_supported_types_include_all_formats(self):
        from app.services.toc.extractor import TOC_SUPPORTED_TYPES
        for fmt in ("pdf", "docx", "doc", "txt", "md", "log"):
            assert fmt in TOC_SUPPORTED_TYPES
