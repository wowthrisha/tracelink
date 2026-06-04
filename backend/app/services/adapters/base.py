"""DocumentAdapter base class — the interface all format adapters must implement."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class DocumentAdapter(ABC):
    """
    Thin orchestration interface for a document format.

    Adapters delegate to existing pipeline functions — they do not reimplement
    them.  One adapter instance per format type is registered in the registry.
    """

    # Subclasses set these as class-level attributes.
    file_type: str   # canonical string: "pdf", "txt", "md", "log", "docx", "doc"
    viewer_mode: str  # "image" (rasterised pages) | "text" (plain/markdown chunks)

    # ── Capabilities (all False by default; subclasses override to opt in) ────

    def supports_toc(self) -> bool:
        return False

    def supports_toc_sidecar(self) -> bool:
        """Whether a toc/{doc_id}.json sidecar may exist for this format."""
        return False

    def toc_fallback_to_text(self) -> bool:
        """
        When a sidecar is absent, fall back to text-extraction (True) or
        return an empty TOC (False).
        PDF → False (no sidecar = no bookmarks).
        DOCX/DOC → True (fall back to heading heuristics).
        """
        return False

    def supports_search(self) -> bool:
        return False

    def supports_thumbnails(self) -> bool:
        return False

    # ── Upload ────────────────────────────────────────────────────────────────

    @abstractmethod
    def upload_mime_types(self) -> frozenset:
        """Primary MIME types accepted at upload time."""

    @abstractmethod
    def content_type_for_storage(self) -> str:
        """MIME type used when storing the original in object storage."""

    @abstractmethod
    def max_upload_bytes(self) -> int:
        """Maximum file size accepted at upload time."""

    @abstractmethod
    def size_exceeded_message(self) -> str:
        """Human-readable 413 error message when the upload is too large."""

    def validate_bytes(self, file_bytes: bytes, filename: str) -> None:
        """
        Format-specific byte-level validation (magic bytes, binary detection).
        Raises ValueError on failure.  No-op by default.
        """

    # ── Processing ────────────────────────────────────────────────────────────

    @abstractmethod
    async def process(
        self,
        db,
        doc,
        document_id: str,
        storage,
        rasterizer=None,
        watermark=None,
    ) -> dict:
        """
        Run the pipeline for this format.  Wraps an existing pipeline function.
        """

    # ── TOC ───────────────────────────────────────────────────────────────────

    def extract_toc(
        self,
        *,
        text_content: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
        lines_per_chunk: int = 100,
    ) -> list:
        """Return a list of serialisable TocEntry dicts.  Empty list by default."""
        return []
