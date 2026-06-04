"""Plain-text document adapters: TXT, MD, LOG."""
from __future__ import annotations

from typing import Optional

from app.services.adapters.base import DocumentAdapter


class _TextBaseAdapter(DocumentAdapter):
    """Shared behaviour for plain-text document formats (TXT, MD, LOG)."""

    viewer_mode = "text"

    def supports_toc(self) -> bool:
        return True

    def supports_search(self) -> bool:
        return True

    def max_upload_bytes(self) -> int:
        from app.config import settings
        return settings.max_text_size_bytes

    def size_exceeded_message(self) -> str:
        from app.config import settings
        return f"Text file exceeds {settings.max_text_size_mb}MB limit"

    def validate_bytes(self, file_bytes: bytes, filename: str) -> None:
        from app.services.text_processor import _reject_if_binary
        _reject_if_binary(file_bytes, filename)

    async def process(
        self, db, doc, document_id: str, storage, rasterizer=None, watermark=None
    ) -> dict:
        from app.workers.pipeline.text import process_text_document
        return await process_text_document(db, doc, document_id, storage)

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


class TXTAdapter(_TextBaseAdapter):
    file_type = "txt"

    def upload_mime_types(self) -> frozenset:
        return frozenset({"text/plain"})

    def content_type_for_storage(self) -> str:
        return "text/plain"


class MDAdapter(_TextBaseAdapter):
    file_type = "md"

    def upload_mime_types(self) -> frozenset:
        return frozenset({"text/markdown"})

    def content_type_for_storage(self) -> str:
        return "text/markdown"


class LOGAdapter(_TextBaseAdapter):
    file_type = "log"

    def upload_mime_types(self) -> frozenset:
        return frozenset({"text/x-log", "text/x-log-file"})

    def content_type_for_storage(self) -> str:
        return "text/plain"
