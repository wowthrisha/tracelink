"""
PDF TOC extraction from bookmark/outline structure.

Uses pypdf (pure Python, no system deps) to read the PDF outline.
Falls back gracefully when no outlines exist or pypdf is unavailable.

PDF outline objects returned by pypdf are either:
  - Destination objects (leaf entries with a title and page reference)
  - Lists (nested sections)

Confidence:
  bookmarks (from outline): 0.95
  (future) layout/heading detection: would be 0.75
"""
from __future__ import annotations

import io
import logging
from typing import List

from app.services.toc.model import TocEntry

logger = logging.getLogger(__name__)

_MAX_ENTRIES = 200


def extract_pdf_toc(pdf_bytes: bytes) -> List[TocEntry]:
    """
    Extract TOC from PDF bookmarks/outlines.

    Returns an empty list when:
    - No outline is embedded in the PDF
    - pypdf is not installed
    - Any parse error occurs
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning("pypdf not installed — PDF bookmark extraction unavailable")
        return []

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        outline = reader.outline
        if not outline:
            return []

        entries: List[TocEntry] = []
        counter = [0]

        _walk_outline(outline, reader, entries, counter, level=1)
        logger.debug("pdf_toc: extracted %d bookmark entries", len(entries))
        return entries

    except Exception as exc:
        logger.warning("pdf_toc: failed to extract outlines: %s", exc)
        return []


def _walk_outline(items, reader, entries: List[TocEntry], counter: list, level: int) -> None:
    """Recursively walk the PDF outline tree, producing flat TocEntry list."""
    for item in items:
        if len(entries) >= _MAX_ENTRIES:
            return

        if isinstance(item, list):
            # Nested section — walk one level deeper
            _walk_outline(item, reader, entries, counter, level + 1)
        else:
            # Leaf entry
            title = getattr(item, "title", "") or ""
            title = title.strip()
            if not title:
                continue

            page_num = _resolve_page(reader, item)
            counter[0] += 1
            idx = counter[0]

            entries.append(TocEntry(
                id=f"toc_{idx:04d}",
                title=title,
                level=min(level, 6),
                anchor=f"page_{page_num}" if page_num else f"sec_{idx:04d}",
                page=page_num,
                source="bookmarks",
                confidence=0.95,
            ))


def _resolve_page(reader, destination) -> int | None:
    """Safely resolve the page number for a PDF outline destination."""
    try:
        page_num = reader.get_destination_page_number(destination)
        if page_num is not None:
            return int(page_num) + 1  # convert 0-indexed to 1-indexed
    except Exception:
        pass
    return None
