"""
Universal TOC entry model.

Every extractor produces TocEntry objects regardless of source format.
The frontend consumes the serialised dict form and never depends on
which extractor produced it.

Confidence scoring reference:
  toc_field / bookmarks:    0.98   — explicit author-defined structure
  heading_style (DOCX):     0.92   — Word heading styles
  bookmarks (PDF):          0.95   — PDF outline bookmarks
  md_heading (# syntax):    0.90   — Markdown ATX headings
  numbered_heading:         0.80   — 1.1 / 1.1.1 section numbering
  heuristic_allcaps:        0.70   — ALL-CAPS title detection
  regex_label:              0.62   — "Chapter:", "Section:" etc.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class TocEntry:
    id: str             # "toc_0001"
    title: str          # heading text (HTML-escaped at serialisation)
    level: int          # 1 (highest) – 6 (deepest)
    anchor: str         # "page_12" | "sec_0003"

    # Navigation targets — at least one will be set for every usable entry
    page: Optional[int] = None    # PDF page number, 1-indexed
    chunk: Optional[int] = None   # text-doc chunk number, 1-indexed
    line: Optional[int] = None    # source line number, 1-indexed

    source: str = "unknown"       # which extractor / signal produced this entry
    confidence: float = 0.0       # 0.0-1.0

    children: List["TocEntry"] = field(default_factory=list)

    def to_dict(self) -> dict:
        import html
        d: dict = {
            "id": self.id,
            "title": html.escape(self.title, quote=False),
            "level": self.level,
            "anchor": self.anchor,
            "source": self.source,
            "confidence": round(self.confidence, 3),
        }
        # Only include navigation fields that are set — keeps response compact
        if self.page is not None:
            d["page"] = self.page
        if self.chunk is not None:
            d["chunk"] = self.chunk
        if self.line is not None:
            d["line"] = self.line
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d
