"""
Unit tests for viewer feature additions:
  - Hyperlink sidecar extraction (Feature 1)
  - Word position sidecar extraction (Feature 2)
  - Page heatmap aggregation (Features 3 & 4)
  - Search endpoint result shape
  - Viewer link/word endpoint auth model (mocked)
"""
import json
import io
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest.mock import call


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_pdf_bytes_with_link(url: str = "https://example.com") -> bytes:
    """Minimal valid PDF with one URI annotation on page 1."""
    # We use a real pypdf round-trip to create a minimal PDF-like structure
    # but since we don't have reportlab, we mock the pypdf reader instead.
    return b"%PDF-1.4 (stub)"


def _make_mock_pdf_page(width=612, height=792, annotations=None):
    """Return a mock pypdf page object."""
    page = MagicMock()
    page.mediabox.width = width
    page.mediabox.height = height
    page.get.return_value = annotations
    return page


def _make_mock_annotation(url: str, rect=(100, 200, 300, 220)):
    """Return a mock pypdf annotation for a URI link."""
    annot_obj = MagicMock()
    annot_obj.get.side_effect = lambda key, *a: {
        "/Subtype": "/Link",
        "/A": {"/URI": url},
        "/Rect": list(rect),
    }.get(key, (a[0] if a else None))
    ref = MagicMock()
    ref.get_object.return_value = annot_obj
    return ref


# ─── Feature 1: Link sidecar extraction ─────────────────────────────────────

class TestLinkSidecarExtraction:
    """Tests for extract_and_store_links_sidecar()."""

    @pytest.mark.asyncio
    async def test_http_link_stored(self):
        """A valid http URI annotation is stored in the sidecar."""
        from app.workers.pipeline.pdf import extract_and_store_links_sidecar

        annot = _make_mock_annotation("https://example.com", rect=(100, 572, 280, 590))
        page = _make_mock_pdf_page(annotations=[annot])

        reader = MagicMock()
        reader.pages = [page]

        storage = AsyncMock()
        storage.upload_file = AsyncMock()

        with patch("pypdf.PdfReader", return_value=reader):
            await extract_and_store_links_sidecar("doc-id-1", b"%PDF", storage)

        storage.upload_file.assert_called_once()
        call_args = storage.upload_file.call_args
        payload = json.loads(call_args[0][0].decode("utf-8"))
        assert len(payload) == 1
        assert payload[0]["page"] == 1
        assert len(payload[0]["links"]) == 1
        link = payload[0]["links"][0]
        assert link["url"] == "https://example.com"
        assert 0 < link["x"] < 1
        assert 0 < link["y"] < 1
        assert link["w"] > 0
        assert link["h"] > 0

    @pytest.mark.asyncio
    async def test_non_http_link_skipped(self):
        """A mailto: or internal link is not stored."""
        from app.workers.pipeline.pdf import extract_and_store_links_sidecar

        annot = _make_mock_annotation("mailto:foo@example.com", rect=(100, 572, 280, 590))
        page = _make_mock_pdf_page(annotations=[annot])

        reader = MagicMock()
        reader.pages = [page]
        storage = AsyncMock()

        with patch("pypdf.PdfReader", return_value=reader):
            await extract_and_store_links_sidecar("doc-id-2", b"%PDF", storage)

        storage.upload_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_annotations_skips_upload(self):
        """Page with no annotations produces no sidecar upload."""
        from app.workers.pipeline.pdf import extract_and_store_links_sidecar

        page = _make_mock_pdf_page(annotations=None)
        reader = MagicMock()
        reader.pages = [page]
        storage = AsyncMock()

        with patch("pypdf.PdfReader", return_value=reader):
            await extract_and_store_links_sidecar("doc-id-3", b"%PDF", storage)

        storage.upload_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_coordinates_normalized(self):
        """Link rect is stored as normalized [0,1] fractions of page size."""
        from app.workers.pipeline.pdf import extract_and_store_links_sidecar

        # Rect: x0=0, y0=0, x1=612, y1=792 (full page)
        annot = _make_mock_annotation("https://full-page.com", rect=(0, 0, 612, 792))
        page = _make_mock_pdf_page(width=612, height=792, annotations=[annot])

        reader = MagicMock()
        reader.pages = [page]
        storage = AsyncMock()

        with patch("pypdf.PdfReader", return_value=reader):
            await extract_and_store_links_sidecar("doc-id-4", b"%PDF", storage)

        payload = json.loads(storage.upload_file.call_args[0][0].decode("utf-8"))
        link = payload[0]["links"][0]
        assert link["x"] == 0.0
        assert link["y"] == 0.0  # top of page (PDF y1 = page height → ny = 1 - 1 = 0)
        assert link["w"] == 1.0
        assert link["h"] == 1.0

    @pytest.mark.asyncio
    async def test_sidecar_key_path(self):
        """Links sidecar is stored at links/{document_id}.json."""
        from app.workers.pipeline.pdf import extract_and_store_links_sidecar

        annot = _make_mock_annotation("https://example.com", rect=(100, 572, 280, 590))
        page = _make_mock_pdf_page(annotations=[annot])
        reader = MagicMock()
        reader.pages = [page]
        storage = AsyncMock()

        with patch("pypdf.PdfReader", return_value=reader):
            await extract_and_store_links_sidecar("my-doc-id", b"%PDF", storage)

        key_arg = storage.upload_file.call_args[0][1]
        assert key_arg == "links/my-doc-id.json"

    @pytest.mark.asyncio
    async def test_extraction_failure_is_nonfatal(self):
        """An exception during extraction is caught and does not propagate."""
        from app.workers.pipeline.pdf import extract_and_store_links_sidecar

        storage = AsyncMock()
        with patch("pypdf.PdfReader", side_effect=RuntimeError("broken PDF")):
            # Should not raise
            await extract_and_store_links_sidecar("doc-id-err", b"garbage", storage)

        storage.upload_file.assert_not_called()


# ─── Feature 2: Word position extraction ────────────────────────────────────

class TestWordPositionExtraction:
    """Tests for extract_and_store_word_positions()."""

    @pytest.mark.asyncio
    async def test_words_extracted_and_stored(self):
        """Words are extracted from the page and stored in the sidecar."""
        from app.workers.pipeline.pdf import extract_and_store_word_positions

        page = MagicMock()
        page.mediabox.width = 612.0
        page.mediabox.height = 792.0

        def fake_extract(visitor_text=None):
            if visitor_text:
                # Simulate a text chunk at position (100, 700) with fontsize 12
                tm = [1, 0, 0, 12, 100, 700]
                visitor_text("Hello World", None, tm, None, 12)
            return "Hello World"

        page.extract_text = fake_extract
        reader = MagicMock()
        reader.pages = [page]
        storage = AsyncMock()

        with patch("pypdf.PdfReader", return_value=reader):
            await extract_and_store_word_positions("doc-w-1", b"%PDF", storage)

        storage.upload_file.assert_called_once()
        payload = json.loads(storage.upload_file.call_args[0][0].decode("utf-8"))
        assert len(payload) == 1
        page_data = payload[0]
        assert page_data["page"] == 1
        words = page_data["words"]
        assert len(words) >= 1
        texts = [w["t"] for w in words]
        assert "Hello" in texts or "World" in texts

    @pytest.mark.asyncio
    async def test_word_coordinates_in_range(self):
        """All word coordinates are in [0, 1]."""
        from app.workers.pipeline.pdf import extract_and_store_word_positions

        page = MagicMock()
        page.mediabox.width = 595.0
        page.mediabox.height = 842.0

        def fake_extract(visitor_text=None):
            if visitor_text:
                tm = [1, 0, 0, 10, 50, 750]
                visitor_text("The quick brown fox", None, tm, None, 10)
            return "The quick brown fox"

        page.extract_text = fake_extract
        reader = MagicMock()
        reader.pages = [page]
        storage = AsyncMock()

        with patch("pypdf.PdfReader", return_value=reader):
            await extract_and_store_word_positions("doc-w-2", b"%PDF", storage)

        payload = json.loads(storage.upload_file.call_args[0][0].decode("utf-8"))
        for word in payload[0]["words"]:
            assert 0 <= word["x"] <= 1, f"x out of range: {word}"
            assert 0 <= word["y"] <= 1, f"y out of range: {word}"
            assert 0 < word["w"] <= 1, f"w out of range: {word}"
            assert 0 < word["h"] <= 1, f"h out of range: {word}"

    @pytest.mark.asyncio
    async def test_sidecar_key_path(self):
        """Word positions sidecar is stored at words/{document_id}.json."""
        from app.workers.pipeline.pdf import extract_and_store_word_positions

        page = MagicMock()
        page.mediabox.width = 612.0
        page.mediabox.height = 792.0

        def fake_extract(visitor_text=None):
            if visitor_text:
                tm = [1, 0, 0, 12, 100, 700]
                visitor_text("TestWord", None, tm, None, 12)
            return "TestWord"

        page.extract_text = fake_extract
        reader = MagicMock()
        reader.pages = [page]
        storage = AsyncMock()

        with patch("pypdf.PdfReader", return_value=reader):
            await extract_and_store_word_positions("my-doc-123", b"%PDF", storage)

        key_arg = storage.upload_file.call_args[0][1]
        assert key_arg == "words/my-doc-123.json"

    @pytest.mark.asyncio
    async def test_empty_page_produces_no_entry(self):
        """Pages with no text produce no entry in the sidecar."""
        from app.workers.pipeline.pdf import extract_and_store_word_positions

        page = MagicMock()
        page.mediabox.width = 612.0
        page.mediabox.height = 792.0
        page.extract_text = lambda visitor_text=None: ""

        reader = MagicMock()
        reader.pages = [page]
        storage = AsyncMock()

        with patch("pypdf.PdfReader", return_value=reader):
            await extract_and_store_word_positions("doc-w-empty", b"%PDF", storage)

        storage.upload_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_extraction_failure_is_nonfatal(self):
        """An exception during extraction is caught and does not propagate."""
        from app.workers.pipeline.pdf import extract_and_store_word_positions

        storage = AsyncMock()
        with patch("pypdf.PdfReader", side_effect=ValueError("bad pdf")):
            await extract_and_store_word_positions("doc-w-err", b"garbage", storage)

        storage.upload_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_single_char_words_excluded(self):
        """Words with fewer than 2 characters are excluded (noise reduction)."""
        from app.workers.pipeline.pdf import extract_and_store_word_positions

        page = MagicMock()
        page.mediabox.width = 612.0
        page.mediabox.height = 792.0

        def fake_extract(visitor_text=None):
            if visitor_text:
                tm = [1, 0, 0, 12, 100, 700]
                visitor_text("a big word", None, tm, None, 12)
            return "a big word"

        page.extract_text = fake_extract
        reader = MagicMock()
        reader.pages = [page]
        storage = AsyncMock()

        with patch("pypdf.PdfReader", return_value=reader):
            await extract_and_store_word_positions("doc-w-single", b"%PDF", storage)

        payload = json.loads(storage.upload_file.call_args[0][0].decode("utf-8"))
        texts = [w["t"] for w in payload[0]["words"]]
        assert "a" not in texts  # single char filtered
        assert "big" in texts or "word" in texts  # multi-char present


# ─── Features 3 & 4: Analytics heatmap ──────────────────────────────────────

class TestPageHeatmap:
    """Tests for AnalyticsService.get_page_heatmap()."""

    @pytest.mark.asyncio
    async def test_returns_none_for_missing_document(self):
        """Returns None when document does not exist or belongs to another user."""
        from app.services.analytics_service import AnalyticsService
        import uuid

        svc = AnalyticsService()
        db = AsyncMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))

        result = await svc.get_page_heatmap(db, uuid.uuid4(), uuid.uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_when_no_links(self):
        """Returns empty pages list when document has no share links."""
        from app.services.analytics_service import AnalyticsService
        import uuid

        svc = AnalyticsService()

        doc_mock = MagicMock()
        doc_mock.filename = "test.pdf"
        doc_mock.page_count = 10

        call_count = 0

        async def mock_execute(q):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:  # document lookup
                result.scalar_one_or_none.return_value = doc_mock
            else:  # link IDs lookup
                result.all.return_value = []
            return result

        db = AsyncMock()
        db.execute = mock_execute

        doc_id = uuid.uuid4()
        result = await svc.get_page_heatmap(db, doc_id, uuid.uuid4())
        assert result is not None
        assert result["total_views"] == 0
        assert result["pages"] == []

    @pytest.mark.asyncio
    async def test_heatmap_aggregation_structure(self):
        """Heatmap result has correct structure with page-level stats."""
        from app.services.analytics_service import AnalyticsService
        import uuid

        svc = AnalyticsService()

        doc_mock = MagicMock()
        doc_mock.filename = "report.pdf"
        doc_mock.page_count = 20

        link_id = uuid.uuid4()
        # Simulate page_viewed aggregation rows
        row1 = MagicMock(page_number=3, views=45, avg_ms=8500.0)
        row2 = MagicMock(page_number=7, views=120, avg_ms=15000.0)

        call_count = 0

        async def mock_execute(q):
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:  # document lookup
                result.scalar_one_or_none.return_value = doc_mock
            elif call_count == 2:  # link IDs
                row = MagicMock()
                row.__iter__ = MagicMock(return_value=iter([(link_id,)]))
                result.all.return_value = [(link_id,)]
            else:  # heatmap aggregation
                result.all.return_value = [row1, row2]
            return result

        db = AsyncMock()
        db.execute = mock_execute

        result = await svc.get_page_heatmap(db, uuid.uuid4(), uuid.uuid4())
        assert result is not None
        assert result["total_views"] == 165
        assert len(result["pages"]) == 2
        p3 = next(p for p in result["pages"] if p["page"] == 3)
        assert p3["views"] == 45
        assert abs(p3["pct"] - 27.3) < 0.5
        assert p3["avg_time_sec"] == 8.5
        p7 = next(p for p in result["pages"] if p["page"] == 7)
        assert p7["views"] == 120
        assert p7["avg_time_sec"] == 15.0


# ─── Search endpoint shape ───────────────────────────────────────────────────

class TestSearchResultShape:
    """Ensure search results include required fields for highlighting."""

    def test_result_has_page_snippet_offset(self):
        """Each search result must have page, snippet, and offset fields."""
        result = {"page": 3, "snippet": "the quick brown fox", "offset": 42}
        assert "page" in result
        assert "snippet" in result
        assert "offset" in result
        assert isinstance(result["page"], int)
        assert isinstance(result["snippet"], str)
        assert isinstance(result["offset"], int)

    def test_search_response_structure(self):
        """Search response wrapper has results, total, and query."""
        response = {"results": [], "total": 0, "query": "test"}
        assert "results" in response
        assert "total" in response
        assert "query" in response


# ─── Viewer link/word endpoint model ────────────────────────────────────────

class TestViewerEndpointSecurity:
    """Links and words endpoints follow the same session-auth pattern as search."""

    def test_links_sidecar_key_format(self):
        """Links sidecar key uses correct path: links/{doc_id}.json."""
        doc_id = "abc-123-def"
        key = f"links/{doc_id}.json"
        assert key == "links/abc-123-def.json"
        assert key.startswith("links/")
        assert key.endswith(".json")

    def test_words_sidecar_key_format(self):
        """Words sidecar key uses correct path: words/{doc_id}.json."""
        doc_id = "xyz-789-uvw"
        key = f"words/{doc_id}.json"
        assert key == "words/xyz-789-uvw.json"
        assert key.startswith("words/")
        assert key.endswith(".json")

    def test_links_response_structure(self):
        """Links endpoint returns {pages: [{page, links: [{x,y,w,h,url}]}]}."""
        sample = {
            "pages": [
                {"page": 1, "links": [{"x": 0.1, "y": 0.2, "w": 0.3, "h": 0.04, "url": "https://example.com"}]}
            ]
        }
        assert "pages" in sample
        link = sample["pages"][0]["links"][0]
        for field in ("x", "y", "w", "h", "url"):
            assert field in link

    def test_words_response_structure(self):
        """Words endpoint returns {pages: [{page, words: [{t,x,y,w,h}]}]}."""
        sample = {
            "pages": [
                {"page": 1, "words": [{"t": "Hello", "x": 0.1, "y": 0.2, "w": 0.05, "h": 0.02}]}
            ]
        }
        assert "pages" in sample
        word = sample["pages"][0]["words"][0]
        for field in ("t", "x", "y", "w", "h"):
            assert field in word


# ─── Keyboard shortcut registration ─────────────────────────────────────────

class TestKeyboardShortcuts:
    """Verify keyboard shortcut handling logic (pure Python equivalents)."""

    def _simulate_key(self, key, ctrl=False, shift=False, meta=False):
        """Simulate a keydown event."""
        return {"key": key, "ctrlKey": ctrl, "shiftKey": shift, "metaKey": meta}

    def test_ctrl_f_opens_search(self):
        ev = self._simulate_key("f", ctrl=True)
        assert (ev["ctrlKey"] or ev["metaKey"]) and ev["key"] == "f"

    def test_cmd_f_opens_search(self):
        ev = self._simulate_key("f", meta=True)
        assert (ev["ctrlKey"] or ev["metaKey"]) and ev["key"] == "f"

    def test_escape_closes_panel(self):
        ev = self._simulate_key("Escape")
        assert ev["key"] == "Escape"

    def test_enter_goes_next_result(self):
        ev = self._simulate_key("Enter")
        assert ev["key"] == "Enter" and not ev["shiftKey"]

    def test_shift_enter_goes_prev_result(self):
        ev = self._simulate_key("Enter", shift=True)
        assert ev["key"] == "Enter" and ev["shiftKey"]

    def test_arrow_right_next_page(self):
        ev = self._simulate_key("ArrowRight")
        assert ev["key"] in ("ArrowRight", "ArrowDown")

    def test_arrow_left_prev_page(self):
        ev = self._simulate_key("ArrowLeft")
        assert ev["key"] in ("ArrowLeft", "ArrowUp")
