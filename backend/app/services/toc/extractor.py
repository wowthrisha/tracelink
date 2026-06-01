"""
Universal TOC dispatcher.

Given a document's file_type and content (bytes or decoded text), routes to
the correct extractor and returns a normalised list of TocEntry dicts.

All callers use extract_toc_for_document(); format details stay inside
the individual extractors.
"""
from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# File types that this engine supports
TOC_SUPPORTED_TYPES: frozenset[str] = frozenset({
    "pdf", "docx", "doc", "txt", "md", "log",
})


async def extract_toc_for_document(
    file_type: str,
    *,
    text_content: Optional[str] = None,
    pdf_bytes: Optional[bytes] = None,
    lines_per_chunk: int = 100,
) -> List[dict]:
    """
    Extract TOC for a document and return a list of serialisable dicts.

    Routing:
      pdf           → pdf_extractor.extract_pdf_toc (needs pdf_bytes)
      docx/md       → text_extractor with md rules (needs text_content)
      doc/txt/log   → text_extractor with plain-text rules (needs text_content)

    Returns empty list when:
    - file_type not in TOC_SUPPORTED_TYPES
    - required content is not supplied
    - extraction raises any exception
    """
    if file_type not in TOC_SUPPORTED_TYPES:
        return []

    try:
        if file_type == "pdf":
            if pdf_bytes is None:
                return []
            from app.services.toc.pdf_extractor import extract_pdf_toc
            entries = extract_pdf_toc(pdf_bytes)
        else:
            if text_content is None:
                return []
            from app.services.toc.text_extractor import extract_text_toc
            entries = extract_text_toc(
                text_content, file_type, lines_per_chunk=lines_per_chunk
            )

        return [e.to_dict() for e in entries]

    except Exception as exc:
        logger.warning(
            "toc_extractor: unhandled error for file_type=%r: %s",
            file_type, exc,
        )
        return []
