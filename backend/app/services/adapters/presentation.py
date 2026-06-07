"""Presentation document adapters: PPTX."""
from __future__ import annotations

from typing import Optional

from app.services.adapters.base import DocumentAdapter


class PPTXAdapter(DocumentAdapter):
    """PowerPoint presentation adapter — image pipeline via LibreOffice."""

    file_type = "pptx"
    viewer_mode = "image"

    def upload_mime_types(self) -> frozenset:
        return frozenset({
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        })

    def content_type_for_storage(self) -> str:
        return "application/vnd.openxmlformats-officedocument.presentationml.presentation"

    def supports_thumbnails(self) -> bool:
        return True

    def supports_toc(self) -> bool:
        return True

    def supports_toc_sidecar(self) -> bool:
        return True

    def toc_fallback_to_text(self) -> bool:
        return False

    def supports_search(self) -> bool:
        return False

    def max_upload_bytes(self) -> int:
        from app.config import settings
        return settings.max_upload_bytes

    def size_exceeded_message(self) -> str:
        from app.config import settings
        return f"File exceeds {settings.max_upload_mb}MB limit"

    def validate_bytes(self, file_bytes: bytes, filename: str) -> None:
        if not (len(file_bytes) >= 4 and file_bytes[:2] == b"PK"):
            raise ValueError(
                f"File {filename!r} does not appear to be a valid PPTX (missing ZIP header)."
            )

    def extract_toc(
        self,
        *,
        text_content: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
        lines_per_chunk: int = 100,
    ) -> list:
        return []

    async def process(
        self, db, doc, document_id: str, storage, rasterizer=None, watermark=None
    ) -> dict:
        from app.workers.pipeline.pptx_pdf import process_pptx_as_pdf
        return await process_pptx_as_pdf(
            db, doc, document_id, storage, rasterizer, watermark
        )
