"""Word document adapters: DOCX, DOC."""
from __future__ import annotations

from typing import Optional

from app.services.adapters.base import DocumentAdapter


class _WordBaseAdapter(DocumentAdapter):
    """Shared behaviour for Word document formats (DOCX, DOC)."""

    viewer_mode = "text"

    def supports_toc(self) -> bool:
        return True

    def supports_toc_sidecar(self) -> bool:
        return True

    def toc_fallback_to_text(self) -> bool:
        return True

    def supports_search(self) -> bool:
        return True

    def max_upload_bytes(self) -> int:
        from app.config import settings
        return settings.max_upload_bytes

    def size_exceeded_message(self) -> str:
        from app.config import settings
        return f"File exceeds {settings.max_upload_mb}MB limit"

    def extract_toc(
        self,
        *,
        text_content: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
        lines_per_chunk: int = 100,
    ) -> list:
        if not text_content:
            return []
        from app.services.toc.text_extractor import extract_text_toc
        entries = extract_text_toc(text_content, self.file_type, lines_per_chunk=lines_per_chunk)
        return [e.to_dict() for e in entries]


class DOCXAdapter(_WordBaseAdapter):
    file_type = "docx"

    def upload_mime_types(self) -> frozenset:
        return frozenset({
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        })

    def content_type_for_storage(self) -> str:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    def validate_bytes(self, file_bytes: bytes, filename: str) -> None:
        if not (len(file_bytes) >= 4 and file_bytes[:2] == b"PK"):
            raise ValueError(
                f"File {filename!r} does not appear to be a valid DOCX (missing ZIP header)."
            )

    async def process(
        self, db, doc, document_id: str, storage, rasterizer=None, watermark=None
    ) -> dict:
        from app.workers.pipeline.word import process_docx_document
        return await process_docx_document(db, doc, document_id, storage)


class DOCAdapter(_WordBaseAdapter):
    file_type = "doc"

    def upload_mime_types(self) -> frozenset:
        return frozenset({"application/msword"})

    def content_type_for_storage(self) -> str:
        return "application/msword"

    def validate_bytes(self, file_bytes: bytes, filename: str) -> None:
        if not (
            len(file_bytes) >= 8
            and file_bytes[:8] == b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"
        ):
            raise ValueError(
                f"File {filename!r} does not appear to be a valid DOC (missing OLE2 header)."
            )

    async def process(
        self, db, doc, document_id: str, storage, rasterizer=None, watermark=None
    ) -> dict:
        from app.workers.pipeline.word import process_doc_document
        return await process_doc_document(db, doc, document_id, storage)
