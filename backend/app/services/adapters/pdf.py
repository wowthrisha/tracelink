"""PDF document adapter."""
from __future__ import annotations

from typing import Optional

from app.services.adapters.base import DocumentAdapter


class PDFAdapter(DocumentAdapter):
    file_type = "pdf"
    viewer_mode = "image"

    def supports_toc(self) -> bool:
        return True

    def supports_toc_sidecar(self) -> bool:
        return True

    def toc_fallback_to_text(self) -> bool:
        return False  # no sidecar = no bookmarks

    def supports_thumbnails(self) -> bool:
        return True

    def upload_mime_types(self) -> frozenset:
        return frozenset({"application/pdf"})

    def content_type_for_storage(self) -> str:
        return "application/pdf"

    def max_upload_bytes(self) -> int:
        from app.config import settings
        return settings.max_upload_bytes

    def size_exceeded_message(self) -> str:
        from app.config import settings
        return f"File exceeds {settings.max_upload_mb}MB limit"

    def validate_bytes(self, file_bytes: bytes, filename: str) -> None:
        if file_bytes[:5] != b"%PDF-":
            raise ValueError("File must be a valid PDF")

    async def process(
        self, db, doc, document_id: str, storage, rasterizer=None, watermark=None
    ) -> dict:
        from app.workers.pipeline.pdf import process_pdf_document
        return await process_pdf_document(db, doc, document_id, storage, rasterizer, watermark)

    def extract_toc(
        self,
        *,
        text_content: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
        lines_per_chunk: int = 100,
    ) -> list:
        if pdf_bytes is None:
            return []
        from app.services.toc.pdf_extractor import extract_pdf_toc
        entries = extract_pdf_toc(pdf_bytes)
        return [e.to_dict() for e in entries]
