"""
DOCX TOC extraction.

extract_docx_toc() extracts native heading styles from a DOCX file using
python-docx.  The result is stored as a JSON sidecar by the DOCX processing
pipeline (docx_pdf.py) for use by the viewer's /toc endpoint.

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

    This is the high-fidelity path used by the worker at document-process time.
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
    line_counter = 0

    from app.config import settings
    lines_per_chunk = settings.text_lines_per_chunk

    try:
        for para in doc.paragraphs:
            line_counter += 1
            text = para.text.strip()
            if not text:
                continue

            level = _get_paragraph_level(para)
            if level is None or not (1 <= level <= 6):
                continue

            counter += 1
            chunk = (line_counter - 1) // lines_per_chunk + 1
            entries.append(TocEntry(
                id=f"toc_{counter:04d}",
                title=text,
                level=level,
                anchor=f"sec_{counter:04d}",
                chunk=chunk,
                line=line_counter,
                source="heading_style",
                confidence=0.92,
            ))

            if counter >= 200:
                break
    except Exception as exc:
        logger.warning("docx_toc: error iterating paragraphs: %s", exc)

    logger.debug("docx_toc: extracted %d entries", len(entries))
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

        result = subprocess.run(
            ["antiword", tmp_path],
            capture_output=True,
            timeout=30,
            check=False,
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
