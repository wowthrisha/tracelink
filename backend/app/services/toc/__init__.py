"""
Universal TOC Engine — extracts, normalises, and caches Table of Contents
structures across all supported document formats (PDF, DOCX, DOC, TXT, MD, LOG).

All formats produce a list of TocEntry objects with a consistent schema.
Callers should never need to know which extractor produced the result.
"""
from app.services.toc.model import TocEntry
from app.services.toc.extractor import extract_toc_for_document, TOC_SUPPORTED_TYPES

__all__ = ["TocEntry", "extract_toc_for_document", "TOC_SUPPORTED_TYPES"]
