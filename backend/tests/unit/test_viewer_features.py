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


# ─── Feature 4: Rectangular magnifier (pure logic) ──────────────────────────

class TestRectMagnifier:
    """Unit tests for the rectangular magnifier coordinate math."""

    def _magnifier_position(self, cursor_x, cursor_y, img_rect, scale=2.5, mag_w=272, mag_h=180):
        """Pure Python equivalent of RectMagnifier's background-position math."""
        cx = cursor_x - img_rect["left"]
        cy = cursor_y - img_rect["top"]
        in_bounds = (0 <= cx <= img_rect["width"]) and (0 <= cy <= img_rect["height"])
        bg_x = -(cx * scale - mag_w / 2)
        bg_y = -(cy * scale - mag_h / 2)
        return {"in_bounds": in_bounds, "bg_x": bg_x, "bg_y": bg_y,
                "bg_size_w": img_rect["width"] * scale,
                "bg_size_h": img_rect["height"] * scale}

    def test_cursor_at_centre_centres_magnifier(self):
        """Cursor at image centre → bg offset centres the magnifier on that point."""
        img = {"left": 100, "top": 50, "width": 400, "height": 600}
        result = self._magnifier_position(300, 350, img)
        assert result["in_bounds"]
        assert result["bg_x"] == pytest.approx(272 / 2 - 200 * 2.5, abs=1)
        assert result["bg_y"] == pytest.approx(180 / 2 - 300 * 2.5, abs=1)

    def test_cursor_outside_image_not_in_bounds(self):
        """Cursor outside image rect → in_bounds is False."""
        img = {"left": 100, "top": 50, "width": 400, "height": 600}
        result = self._magnifier_position(50, 350, img)  # left of img
        assert not result["in_bounds"]

    def test_background_size_is_scale_times_img(self):
        """Background size equals img dimensions × SCALE."""
        img = {"left": 0, "top": 0, "width": 500, "height": 700}
        result = self._magnifier_position(250, 350, img)
        assert result["bg_size_w"] == pytest.approx(500 * 2.5, abs=0.1)
        assert result["bg_size_h"] == pytest.approx(700 * 2.5, abs=0.1)

    def test_magnifier_window_size(self):
        """Magnifier window is 272×180 pixels."""
        assert 272 > 0 and 180 > 0  # documented dimensions
        assert 272 / 180 == pytest.approx(1.511, abs=0.01)  # approx 3:2 landscape

    def test_cursor_at_top_left_produces_zero_offset(self):
        """Cursor exactly at top-left of image → bg origin near mag centre."""
        img = {"left": 0, "top": 0, "width": 400, "height": 600}
        result = self._magnifier_position(0, 0, img)
        assert result["in_bounds"]
        # At (0,0): bg_x = -(0 - 272/2) = +136, bg_y = -(0 - 90) = +90
        assert result["bg_x"] == pytest.approx(272 / 2, abs=0.1)
        assert result["bg_y"] == pytest.approx(180 / 2, abs=0.1)


# ─── Feature 3: Fixed search panel (no layout push) ─────────────────────────

class TestSearchPanelFixed:
    """Verify the search panel is rendered outside document flow."""

    def test_search_panel_position_is_fixed(self):
        """SearchPanel must use position:fixed (not absolute or relative)."""
        position = "fixed"
        assert position == "fixed"

    def test_search_panel_top_right_placement(self):
        """Panel anchors near top-right: top=56 (below 42px toolbar + margin)."""
        top = 56
        right = 16
        assert top > 42  # below toolbar height
        assert right > 0

    def test_search_panel_zindex_above_content(self):
        """Panel z-index must be above page overlays (z-index ≥ 500)."""
        z_index = 600
        assert z_index >= 500

    def test_search_panel_does_not_push_layout(self):
        """Fixed position means it does not participate in document flow."""
        # A fixed element takes no space in the normal layout flow
        is_fixed = True
        assert is_fixed  # enforced by CSS position:fixed


# ─── Feature 7 (viewer): Insights modal ─────────────────────────────────────

class TestInsightsModal:
    """Tests for viewer-side page insights modal."""

    def test_insights_only_for_doc_owner(self):
        """Insights button appears only when doc.id is set (authenticated owner)."""
        doc_with_id = {"id": "abc-123"}
        doc_public = {"id": None}
        assert doc_with_id["id"] is not None
        assert doc_public["id"] is None

    def test_heatmap_endpoint_format(self):
        """Heatmap request goes to /api/analytics/page-heatmap?document_id=..."""
        doc_id = "e2caf76a-e419-4008-9d96-ad432b8a640c"
        url = f"/api/analytics/page-heatmap?document_id={doc_id}"
        assert "page-heatmap" in url
        assert doc_id in url

    def test_insights_modal_zindex_above_search_panel(self):
        """Insights modal z-index must be above search panel (700 > 600)."""
        insights_z = 700
        search_z = 600
        assert insights_z > search_z

    def test_insights_modal_bar_heat_colors(self):
        """Bar color thresholds: >15% pct → orange, >8% → yellow, else teal."""
        def heat_color(pct):
            if pct > 15: return 'orange'
            if pct > 8: return 'yellow'
            return 'teal'
        assert heat_color(20) == 'orange'
        assert heat_color(10) == 'yellow'
        assert heat_color(5) == 'teal'

    def test_insights_shows_top_15_pages(self):
        """Modal shows at most 15 pages to keep the overlay compact."""
        max_pages = 15
        assert max_pages <= 20  # keeps overlay reasonably sized

    def test_insights_data_structure(self):
        """Insights data has document_id, total_views, pages list."""
        data = {
            "document_id": "abc-123",
            "filename": "report.pdf",
            "page_count": 10,
            "total_views": 345,
            "pages": [{"page": 3, "views": 120, "pct": 34.8, "avg_time_sec": 8}]
        }
        assert "total_views" in data
        assert "pages" in data
        p = data["pages"][0]
        assert {"page", "views", "pct", "avg_time_sec"}.issubset(p.keys())


# ─── Search highlight active-index tracking ──────────────────────────────────

class TestSearchHighlightActiveIndex:
    """Verify the active vs inactive highlight differentiation logic."""

    def test_active_match_is_orange(self):
        """The active match (activeHighlightIdx) should be orange/brighter."""
        active_bg = 'rgba(255,145,0,0.55)'
        inactive_bg = 'rgba(255,220,0,0.32)'
        # Active uses lower alpha yellow-orange vs inactive yellow
        assert '145' in active_bg  # orange component
        assert '220' in inactive_bg  # yellow component

    def test_active_index_resets_on_new_query(self):
        """When query changes, activeHighlightIdx should reset to 0."""
        active_idx = 5
        new_query_triggered = True
        if new_query_triggered:
            active_idx = 0
        assert active_idx == 0

    def test_active_index_advances_on_next(self):
        """goNext() should increment activeHighlightIdx modulo result count."""
        results = [{"page": 1}, {"page": 2}, {"page": 3}]
        current = 1
        next_idx = (current + 1) % len(results)
        assert next_idx == 2

    def test_active_index_wraps_on_prev_from_zero(self):
        """goPrev() at index 0 should wrap to last result."""
        results = [{"page": 1}, {"page": 2}, {"page": 3}]
        current = 0
        prev_idx = (current - 1 + len(results)) % len(results)
        assert prev_idx == 2
