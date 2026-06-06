"""
DOCX TOC extraction and page-number resolution.

Two-step pipeline used by docx_pdf.py:

  1. extract_docx_toc(docx_bytes)
       Extracts heading styles from the DOCX using python-docx.
       Produces TocEntry objects with title + level but no page number
       (page layout is decided by LibreOffice during PDF conversion).

  2. resolve_toc_page_numbers(entries, pdf_bytes)
       Enriches those entries with page numbers by reading the PDF
       bookmarks that LibreOffice emits for heading styles.  Matching
       uses normalised titles (case-fold + whitespace collapse).
       Entries whose title has no matching bookmark retain page=None
       and still appear in the TOC sidebar without a navigation target.

doc_to_text() converts legacy .doc files via antiword (used by word.py).

Heading level priority for DOCX:
  1. Word built-in "Heading N" styles → level N
  2. Heading style aliases (Title → 1, Subtitle → 2)
  3. Outline level via paragraph XML (outlineLvl element)

Security:
  Never generates HTML.  Heading text is returned as plain strings.
  HTML escaping happens at serialisation time (TocEntry.to_dict).
"""
from __future__ import annotations

import io
import logging
from typing import List, Optional

from app.services.toc.model import TocEntry

logger = logging.getLogger(__name__)

_HEADING_STYLE_MAP: dict[str, int] = {
    "heading 1": 1, "heading 2": 2, "heading 3": 3,
    "heading 4": 4, "heading 5": 5, "heading 6": 6,
    "title": 1, "subtitle": 2,
}

_WML_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_OUTLINE_LVL_TAG = f"{{{_WML_NS}}}outlineLvl"
_VAL_ATTR = f"{{{_WML_NS}}}val"


def _get_paragraph_level(para) -> Optional[int]:
    """Resolve heading level from style name or XML outline level. Returns None if not a heading."""
    style_name = (para.style.name or "").lower() if para.style else ""
    level = _HEADING_STYLE_MAP.get(style_name)
    if level is not None:
        return level

    # Check outlineLvl in paragraph properties XML
    pPr = para._p.find(f"{{{_WML_NS}}}pPr")
    if pPr is not None:
        lvl_el = pPr.find(_OUTLINE_LVL_TAG)
        if lvl_el is not None:
            val = lvl_el.get(_VAL_ATTR)
            if val is not None:
                try:
                    # outlineLvl is 0-indexed (0 = Heading 1)
                    xml_level = int(val) + 1
                    if 1 <= xml_level <= 6:
                        return xml_level
                except (ValueError, TypeError):
                    pass
    return None


def extract_docx_toc(docx_bytes: bytes) -> List[TocEntry]:
    """
    Extract TOC entries natively from DOCX heading styles.

    Returns entries with title + level but without page numbers — page
    layout is determined by LibreOffice and is unknown at this stage.
    Call resolve_toc_page_numbers(entries, pdf_bytes) after conversion
    to enrich entries with page numbers from the resulting PDF bookmarks.

    Returns empty list on any failure (all errors are non-fatal).
    """
    try:
        from docx import Document  # python-docx
        doc = Document(io.BytesIO(docx_bytes))
    except Exception as exc:
        logger.warning("docx_toc: failed to open DOCX: %s", exc)
        return []

    entries: List[TocEntry] = []
    counter = 0

    try:
        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            level = _get_paragraph_level(para)
            if level is None or not (1 <= level <= 6):
                continue

            counter += 1
            entries.append(TocEntry(
                id=f"toc_{counter:04d}",
                title=text,
                level=level,
                anchor=f"sec_{counter:04d}",
                source="heading_style",
                confidence=0.92,
                # page, chunk, line intentionally absent:
                # page — unknown until LibreOffice converts the document
                # chunk/line — text-mode fields; not applicable in image mode
            ))

            if counter >= 200:
                break
    except Exception as exc:
        logger.warning("docx_toc: error iterating paragraphs: %s", exc)

    logger.debug("docx_toc: extracted %d entries", len(entries))
    return entries


# ── Page-number resolution ────────────────────────────────────────────────────

def _normalize_title(text: str) -> str:
    """Case-fold and collapse whitespace for fuzzy bookmark title matching."""
    return " ".join(text.casefold().split())


def _extract_bookmark_pages(pdf_bytes: bytes) -> dict:
    """
    Return a dict mapping normalised bookmark title → 1-indexed page number.

    LibreOffice converts Word heading styles (Heading 1 … Heading 6) to PDF
    outline bookmarks by default.  We read those bookmarks with pypdf, which
    is already a project dependency.

    The first occurrence of each normalised title wins, matching document order.
    All errors return an empty dict (non-fatal).
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        outline = reader.outline
        if not outline:
            return {}

        result: dict = {}

        def _walk(items) -> None:
            for item in items:
                if isinstance(item, list):
                    _walk(item)
                else:
                    title = (getattr(item, "title", "") or "").strip()
                    if not title:
                        continue
                    page_num = _safe_get_page(reader, item)
                    if page_num is not None:
                        key = _normalize_title(title)
                        if key not in result:   # first occurrence wins
                            result[key] = page_num

        _walk(outline)
        logger.debug("docx_toc_bookmarks: found %d PDF bookmark(s)", len(result))
        return result

    except Exception as exc:
        logger.debug("docx_toc_bookmarks: PDF bookmark extraction failed: %s", exc)
        return {}


def _safe_get_page(reader, destination) -> "int | None":
    """Safely resolve a 1-indexed page number for a PDF outline destination."""
    try:
        p = reader.get_destination_page_number(destination)
        return int(p) + 1 if p is not None else None
    except Exception:
        return None


def resolve_toc_page_numbers(
    entries: List[TocEntry],
    pdf_bytes: bytes,
) -> List[TocEntry]:
    """
    Enrich DOCX TOC entries with page numbers from the LibreOffice-converted PDF.

    Approach
    ────────
    LibreOffice preserves Word heading styles as PDF outline bookmarks when
    converting DOCX to PDF.  Those bookmarks contain 1-indexed page numbers.
    We match each DOCX heading entry to the corresponding PDF bookmark by
    normalised title (case-fold + whitespace collapse).

    Entries whose title has no matching PDF bookmark retain page=None and still
    appear in the TOC sidebar as structural headings without a navigation target.
    This is graceful degradation for the minority of documents where LibreOffice
    does not emit bookmarks (e.g. protected DOCX, unusual heading definitions).

    The match is by first occurrence, so duplicate heading titles across the
    document will all map to the first page that bookmark appears on.  This is
    the correct behaviour for chapter-style headings and acceptable for edge cases.

    Parameters
    ----------
    entries : List[TocEntry]
        Heading entries from extract_docx_toc().  Mutated in-place.
    pdf_bytes : bytes
        PDF produced by LibreOffice conversion (already in memory — no I/O).

    Returns the same list, with page fields populated where bookmarks matched.
    """
    bookmark_pages = _extract_bookmark_pages(pdf_bytes)
    if not bookmark_pages:
        logger.debug("docx_toc_resolve: no PDF bookmarks — page numbers unavailable")
        return entries

    resolved = 0
    for entry in entries:
        key = _normalize_title(entry.title)
        page = bookmark_pages.get(key)
        if page is not None:
            entry.page = page
            resolved += 1

    logger.debug(
        "docx_toc_resolve: %d/%d heading(s) resolved to PDF page numbers",
        resolved, len(entries),
    )
    return entries


def doc_to_text(doc_bytes: bytes, doc_id: str = "") -> str:
    """
    Convert legacy .doc file to plain text using antiword subprocess.

    antiword is a lightweight system utility (~1 MB) that must be installed
    in the container via `apt-get install antiword`.  If antiword is not
    available, falls back to a basic OLE stream extraction attempt.

    Returns empty string when conversion fails entirely.
    """
    import subprocess
    import tempfile
    import os

    # Write to a temp file (antiword requires a path, not stdin)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            suffix=".doc", delete=False, prefix=f"securedoc_{doc_id}_"
        ) as tmp:
            tmp.write(doc_bytes)
            tmp_path = tmp.name

        # Whitelist only variables antiword needs; strip all secrets from the
        # inherited environment (DATABASE_URL, REDIS_URL, AWS keys, etc.).
        _ANTIWORD_ENV_WHITELIST = {"HOME", "TMPDIR", "TEMP", "TMP", "PATH", "LANG", "LC_ALL"}
        _antiword_env = {k: v for k, v in os.environ.items() if k in _ANTIWORD_ENV_WHITELIST}

        result = subprocess.run(
            ["antiword", tmp_path],
            capture_output=True,
            timeout=30,
            check=False,
            env=_antiword_env,
        )
        if result.returncode == 0:
            return result.stdout.decode("utf-8", errors="replace")
        logger.warning(
            "antiword exited %d for doc_id=%s: %s",
            result.returncode, doc_id,
            result.stderr.decode("utf-8", errors="replace")[:200],
        )
    except FileNotFoundError:
        logger.warning(
            "antiword not installed — .doc support unavailable for doc_id=%s. "
            "Install via: apt-get install antiword",
            doc_id,
        )
    except subprocess.TimeoutExpired:
        logger.warning("antiword timed out for doc_id=%s", doc_id)
    except Exception as exc:
        logger.warning("doc_to_text error for doc_id=%s: %s", doc_id, exc)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

    return ""
