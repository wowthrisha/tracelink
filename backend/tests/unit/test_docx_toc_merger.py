"""
Unit tests for DOCX TOC page-number resolution (Phase D2.7).

Tests _normalize_title, _extract_bookmark_pages, and resolve_toc_page_numbers
in isolation — no DB, no storage, no HTTP.
"""
from unittest.mock import MagicMock, patch


from app.services.toc.docx_extractor import (
    _normalize_title,
    _extract_bookmark_pages,
    resolve_toc_page_numbers,
)
from app.services.toc.model import TocEntry


# ── Helpers ───────────────────────────────────────────────────────────────────

def _entry(title: str, level: int = 1, counter: int = 1) -> TocEntry:
    return TocEntry(
        id=f"toc_{counter:04d}",
        title=title,
        level=level,
        anchor=f"sec_{counter:04d}",
        source="heading_style",
        confidence=0.92,
    )


def _mock_reader(bookmark_specs: list) -> MagicMock:
    """
    Build a mock pypdf.PdfReader with the given bookmarks.

    bookmark_specs: [(title, page_0indexed), ...]
    """
    reader = MagicMock()

    destinations = []
    page_index = {}

    for title, page_0idx in bookmark_specs:
        dest = MagicMock()
        dest.title = title
        destinations.append(dest)
        page_index[id(dest)] = page_0idx

    reader.outline = destinations
    reader.get_destination_page_number.side_effect = lambda d: page_index.get(id(d), 0)
    return reader


def _mock_reader_nested(bookmark_specs: list) -> MagicMock:
    """
    Build a mock pypdf.PdfReader with nested bookmarks.

    bookmark_specs: [(title, page_0indexed, [children_specs]), ...]
    """
    reader = MagicMock()
    page_index = {}

    def _build(specs):
        result = []
        for spec in specs:
            title, page_0idx, children = spec[0], spec[1], spec[2] if len(spec) > 2 else []
            dest = MagicMock()
            dest.title = title
            page_index[id(dest)] = page_0idx
            result.append(dest)
            if children:
                result.append(_build(children))
        return result

    reader.outline = _build(bookmark_specs)
    reader.get_destination_page_number.side_effect = lambda d: page_index.get(id(d), 0)
    return reader


# ── A. _normalize_title ───────────────────────────────────────────────────────

class TestNormalizeTitle:
    def test_lowercases(self):
        assert _normalize_title("Chapter One") == "chapter one"

    def test_collapses_whitespace(self):
        assert _normalize_title("  Introduction  ") == "introduction"
        assert _normalize_title("Section  1.1") == "section 1.1"

    def test_tabs_and_newlines(self):
        assert _normalize_title("A\tB\nC") == "a b c"

    def test_already_normalized(self):
        assert _normalize_title("methods") == "methods"

    def test_empty_string(self):
        assert _normalize_title("") == ""

    def test_unicode_casefold(self):
        # casefold handles German ß → ss
        assert _normalize_title("STRAßE") == "strasse"


# ── B. _extract_bookmark_pages ────────────────────────────────────────────────

class TestExtractBookmarkPages:
    def test_returns_empty_when_no_bookmarks(self):
        mock_reader = MagicMock()
        mock_reader.outline = []
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = _extract_bookmark_pages(b"%PDF-1.4 fake")
        assert result == {}

    def test_single_bookmark(self):
        mock_reader = _mock_reader([("Introduction", 0)])
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = _extract_bookmark_pages(b"%PDF-1.4 fake")
        assert result == {"introduction": 1}   # 0-indexed → 1-indexed

    def test_multiple_bookmarks(self):
        mock_reader = _mock_reader([
            ("Chapter 1", 0),
            ("Section 1.1", 3),
            ("Chapter 2", 9),
        ])
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = _extract_bookmark_pages(b"%PDF-1.4 fake")
        assert result["chapter 1"] == 1
        assert result["section 1.1"] == 4
        assert result["chapter 2"] == 10

    def test_nested_bookmarks_flattened(self):
        mock_reader = _mock_reader_nested([
            ("Part I", 0, [("Chapter 1", 1), ("Chapter 2", 8)]),
            ("Part II", 15, [("Chapter 3", 16)]),
        ])
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = _extract_bookmark_pages(b"%PDF-1.4 fake")
        assert "part i" in result
        assert "chapter 1" in result
        assert "chapter 2" in result
        assert "part ii" in result
        assert "chapter 3" in result

    def test_first_occurrence_wins_for_duplicates(self):
        mock_reader = _mock_reader([
            ("Introduction", 0),
            ("Introduction", 10),  # duplicate — second occurrence ignored
        ])
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = _extract_bookmark_pages(b"%PDF-1.4 fake")
        assert result["introduction"] == 1  # first occurrence

    def test_empty_title_skipped(self):
        mock_reader = _mock_reader([("", 0), ("Methods", 2)])
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = _extract_bookmark_pages(b"%PDF-1.4 fake")
        assert "" not in result
        assert "methods" in result

    def test_pypdf_import_error_returns_empty(self):
        with patch("builtins.__import__", side_effect=ImportError("no pypdf")):
            result = _extract_bookmark_pages(b"%PDF-1.4 fake")
        assert result == {}

    def test_parse_exception_returns_empty(self):
        with patch("pypdf.PdfReader", side_effect=Exception("corrupt PDF")):
            result = _extract_bookmark_pages(b"garbage")
        assert result == {}

    def test_page_resolution_error_skips_entry(self):
        mock_reader = MagicMock()
        dest = MagicMock()
        dest.title = "Chapter 1"
        mock_reader.outline = [dest]
        mock_reader.get_destination_page_number.side_effect = Exception("no page")
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = _extract_bookmark_pages(b"%PDF-1.4 fake")
        # Entry skipped because page resolution failed
        assert result == {}


# ── C. resolve_toc_page_numbers ──────────────────────────────────────────────

class TestResolveTocPageNumbers:
    def test_resolves_exact_title_match(self):
        entries = [_entry("Introduction", 1, 1)]
        mock_reader = _mock_reader([("Introduction", 0)])
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = resolve_toc_page_numbers(entries, b"%PDF-1.4 fake")
        assert result[0].page == 1

    def test_resolves_case_insensitive(self):
        entries = [_entry("introduction", 1, 1)]
        mock_reader = _mock_reader([("INTRODUCTION", 4)])
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = resolve_toc_page_numbers(entries, b"%PDF-1.4 fake")
        assert result[0].page == 5

    def test_resolves_whitespace_normalized(self):
        entries = [_entry("Section  1.1", 2, 1)]  # double space
        mock_reader = _mock_reader([("Section 1.1", 2)])  # single space
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = resolve_toc_page_numbers(entries, b"%PDF-1.4 fake")
        assert result[0].page == 3

    def test_unmatched_entry_retains_none_page(self):
        entries = [_entry("Appendix A", 1, 1)]
        mock_reader = _mock_reader([("Chapter 1", 0)])  # no "Appendix A"
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = resolve_toc_page_numbers(entries, b"%PDF-1.4 fake")
        assert result[0].page is None

    def test_multiple_entries_mixed_resolution(self):
        entries = [
            _entry("Overview", 1, 1),
            _entry("Deep Dive", 2, 2),
            _entry("Conclusion", 1, 3),
        ]
        mock_reader = _mock_reader([
            ("Overview", 0),
            # "Deep Dive" absent from bookmarks
            ("Conclusion", 11),
        ])
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = resolve_toc_page_numbers(entries, b"%PDF-1.4 fake")
        assert result[0].page == 1     # resolved
        assert result[1].page is None  # unmatched
        assert result[2].page == 12    # resolved

    def test_returns_entries_unchanged_when_no_bookmarks(self):
        entries = [_entry("Introduction", 1, 1), _entry("Methods", 1, 2)]
        mock_reader = MagicMock()
        mock_reader.outline = []
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = resolve_toc_page_numbers(entries, b"%PDF-1.4 fake")
        assert result[0].page is None
        assert result[1].page is None
        assert result is entries  # same list object returned

    def test_returns_entries_unchanged_on_pdf_error(self):
        entries = [_entry("Chapter 1", 1, 1)]
        with patch("pypdf.PdfReader", side_effect=Exception("corrupt")):
            result = resolve_toc_page_numbers(entries, b"garbage")
        assert result[0].page is None

    def test_empty_entries_list(self):
        result = resolve_toc_page_numbers([], b"%PDF-1.4 fake")
        assert result == []

    def test_mutates_in_place(self):
        entry = _entry("Intro", 1, 1)
        entries = [entry]
        mock_reader = _mock_reader([("Intro", 5)])
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = resolve_toc_page_numbers(entries, b"%PDF-1.4 fake")
        assert result is entries
        assert entry.page == 6

    def test_nested_headings_all_resolved(self):
        entries = [
            _entry("Part I", 1, 1),
            _entry("Chapter 1", 2, 2),
            _entry("Section 1.1", 3, 3),
            _entry("Chapter 2", 2, 4),
            _entry("Part II", 1, 5),
        ]
        mock_reader = _mock_reader_nested([
            ("Part I", 0, [
                ("Chapter 1", 1, [("Section 1.1", 3)]),
                ("Chapter 2", 8),
            ]),
            ("Part II", 15),
        ])
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = resolve_toc_page_numbers(entries, b"%PDF-1.4 fake")
        assert result[0].page == 1   # Part I
        assert result[1].page == 2   # Chapter 1
        assert result[2].page == 4   # Section 1.1
        assert result[3].page == 9   # Chapter 2
        assert result[4].page == 16  # Part II

    def test_serialised_dict_contains_page(self):
        entries = [_entry("Introduction", 1, 1)]
        mock_reader = _mock_reader([("Introduction", 2)])
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = resolve_toc_page_numbers(entries, b"%PDF-1.4 fake")
        d = result[0].to_dict()
        assert d["page"] == 3
        assert "chunk" not in d

    def test_serialised_dict_omits_page_when_unresolved(self):
        entries = [_entry("Mystery", 1, 1)]
        with patch("pypdf.PdfReader", return_value=MagicMock(outline=[])):
            result = resolve_toc_page_numbers(entries, b"%PDF-1.4 fake")
        d = result[0].to_dict()
        assert "page" not in d

    def test_large_document_100_headings(self):
        """Performance: 100 headings against 100 bookmarks should resolve fully."""
        entries = [_entry(f"Section {i}", 1, i) for i in range(1, 101)]
        specs = [(f"Section {i}", i - 1) for i in range(1, 101)]
        mock_reader = _mock_reader(specs)
        with patch("pypdf.PdfReader", return_value=mock_reader):
            result = resolve_toc_page_numbers(entries, b"%PDF-1.4 fake")
        resolved = [e for e in result if e.page is not None]
        assert len(resolved) == 100
        assert resolved[0].page == 1
        assert resolved[99].page == 100
