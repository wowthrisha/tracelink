"""
TOC extraction for plain-text document formats: TXT, MD, LOG.

Also handles the post-conversion text produced by the DOCX/DOC worker
(which stores content as markdown/plain-text after processing).

Handles:
  md         — ATX-style Markdown headings (# … ######)
  docx       — same as md (worker stores DOCX as markdown)
  txt / log  — ALL-CAPS titles, numbered headings, "Label:" patterns
  doc        — same as txt (worker stores DOC as plain text)

Returns a flat list of TocEntry objects (no nesting — caller may nest by level).
"""
from __future__ import annotations

import re
from typing import List

from app.services.toc.model import TocEntry

_MAX_TOC = 200
_MD_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
_NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+\S")  # "1. Title" or "1.2.3 Title"
_ROMAN = re.compile(r"^(X{0,3})(IX|IV|V?I{0,3})\.\s+\S", re.IGNORECASE)


def extract_text_toc(
    text: str,
    file_type: str,
    lines_per_chunk: int = 100,
) -> List[TocEntry]:
    """
    Extract TOC entries from decoded text.

    file_type controls which detection rules apply:
      "md", "docx"       → Markdown heading syntax (#, ##, …)
      "txt", "log", "doc" → plain-text heuristics
    """
    if not text:
        return []

    lines = text.split("\n")
    entries: List[TocEntry] = []
    counter = 0

    is_md_type = file_type in ("md", "docx")

    for i, raw_line in enumerate(lines):
        if len(entries) >= _MAX_TOC:
            break

        stripped = raw_line.strip()
        if not stripped or len(stripped) < 2:
            continue

        chunk = (i // lines_per_chunk) + 1
        line_num = i + 1
        entry = None

        if is_md_type:
            m = _MD_HEADING.match(stripped)
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()
                counter += 1
                entry = TocEntry(
                    id=f"toc_{counter:04d}",
                    title=title,
                    level=level,
                    anchor=f"sec_{counter:04d}",
                    chunk=chunk,
                    line=line_num,
                    source="md_heading",
                    confidence=0.90,
                )
        else:
            # Plain text / log heuristics — multiple signals, pick the best
            words = stripped.split()

            # 1. Numbered heading: "1.2.3 Some Title" (up to 4 levels)
            num_m = _NUMBERED.match(stripped)
            if num_m:
                depth = num_m.group(1).count(".") + 1
                level = min(depth, 4)
                title = stripped[len(num_m.group(0).split()[0]):].strip()
                if not title:
                    title = stripped
                counter += 1
                entry = TocEntry(
                    id=f"toc_{counter:04d}",
                    title=title,
                    level=level,
                    anchor=f"sec_{counter:04d}",
                    chunk=chunk,
                    line=line_num,
                    source="numbered_heading",
                    confidence=0.80,
                )

            # 2. ALL-CAPS title: ≤8 words, no leading digit, no punctuation at end
            elif (
                stripped.isupper()
                and not stripped[0].isdigit()
                and len(words) <= 8
                and not stripped.endswith(":")
            ):
                counter += 1
                entry = TocEntry(
                    id=f"toc_{counter:04d}",
                    title=stripped,  # preserve original casing
                    level=1,
                    anchor=f"sec_{counter:04d}",
                    chunk=chunk,
                    line=line_num,
                    source="heuristic_allcaps",
                    confidence=0.70,
                )

            # 3. "Label:" sub-heading: ≤5 words, ends with colon, no indent
            elif (
                stripped.endswith(":")
                and len(words) <= 5
                and "\t" not in raw_line
                and not raw_line.startswith(" ")
                and not raw_line.startswith("\t")
            ):
                counter += 1
                entry = TocEntry(
                    id=f"toc_{counter:04d}",
                    title=stripped[:-1],
                    level=2,
                    anchor=f"sec_{counter:04d}",
                    chunk=chunk,
                    line=line_num,
                    source="regex_label",
                    confidence=0.62,
                )

        if entry is not None:
            entries.append(entry)

    return entries
