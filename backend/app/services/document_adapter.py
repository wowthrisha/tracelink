"""
Document Adapter Pattern — Phase 7

Abstracts document-type-specific operations behind a common interface,
eliminating scattered if/elif chains across routers and services.

Current adapters:
  PDFAdapter       — rasterized image pages (WebP)
  TextAdapter      — chunked plain text  (txt / md / log)

Future stubs (raise NotImplementedError — architecture only):
  DocxAdapterStub  — Microsoft Word
  PptxAdapterStub  — PowerPoint

Usage:
    adapter = DocumentAdapter.for_file_type(doc.file_type)
    if adapter.supports_thumbnails():
        ...
"""
from __future__ import annotations

import abc


class DocumentAdapter(abc.ABC):
    """Abstract interface for all document type adapters."""

    @property
    @abc.abstractmethod
    def file_type(self) -> str:
        """Canonical file_type string matching the Document.file_type column."""

    @abc.abstractmethod
    def supports_thumbnails(self) -> bool:
        """Return True if this format produces sidebar thumbnail images."""

    @abc.abstractmethod
    def content_mime_type(self) -> str:
        """MIME type for the primary served content."""

    @abc.abstractmethod
    def supports_search(self) -> bool:
        """Return True if full-text in-document search is possible."""

    @classmethod
    def for_file_type(cls, file_type: str) -> "DocumentAdapter":
        """Factory — return the registered adapter for a file_type.

        Raises ValueError for completely unknown types; returns a stub
        adapter (which raises NotImplementedError at call time) for future
        formats so callers can inspect capabilities without crashing.
        """
        _registry: dict[str, "DocumentAdapter"] = {
            "pdf":  PDFAdapter(),
            "txt":  TextAdapter(),
            "md":   TextAdapter(),
            "log":  TextAdapter(),
            "docx": DocxAdapterStub(),
            "pptx": PptxAdapterStub(),
        }
        adapter = _registry.get(file_type)
        if adapter is None:
            raise ValueError(f"Unsupported file_type: {file_type!r}")
        return adapter


class PDFAdapter(DocumentAdapter):
    """Handles rasterised PDF pages served as WebP images."""

    @property
    def file_type(self) -> str:
        return "pdf"

    def supports_thumbnails(self) -> bool:
        return True

    def content_mime_type(self) -> str:
        return "image/webp"

    def supports_search(self) -> bool:
        return False  # no server-side text extraction yet


class TextAdapter(DocumentAdapter):
    """Handles plain-text documents (txt / md / log) served as JSON chunks."""

    @property
    def file_type(self) -> str:
        return "txt"

    def supports_thumbnails(self) -> bool:
        return False

    def content_mime_type(self) -> str:
        return "application/json"

    def supports_search(self) -> bool:
        return True  # full-text search on loaded chunks


class DocxAdapterStub(DocumentAdapter):
    """
    Architecture stub for future Microsoft Word (.docx) support.

    When implemented this adapter will:
    - Rasterise pages via python-docx + reportlab or LibreOffice headless
    - Extract heading hierarchy for TOC generation
    - Map internal anchors to page/section references
    - Support full-text search via extracted paragraph text
    """

    @property
    def file_type(self) -> str:
        return "docx"

    def supports_thumbnails(self) -> bool:
        return True

    def content_mime_type(self) -> str:
        return "image/webp"

    def supports_search(self) -> bool:
        return True


class PptxAdapterStub(DocumentAdapter):
    """Architecture stub for future PowerPoint (.pptx) support."""

    @property
    def file_type(self) -> str:
        return "pptx"

    def supports_thumbnails(self) -> bool:
        return True

    def content_mime_type(self) -> str:
        return "image/webp"

    def supports_search(self) -> bool:
        return True
