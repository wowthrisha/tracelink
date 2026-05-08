import asyncio
import io
from dataclasses import dataclass
from functools import partial
from typing import List
import pdf2image
from PIL import Image
from app.config import settings


class RasterizerError(Exception):
    """Raised when PDF rasterization fails."""
    def __init__(self, message: str, document_id: str = None):
        super().__init__(message)
        self.document_id = document_id


@dataclass
class RasterizedPage:
    page_number: int
    image_bytes: bytes
    width_px: int
    height_px: int


class RasterizerService:
    def _is_valid_pdf(self, pdf_bytes: bytes) -> bool:
        return len(pdf_bytes) >= 5 and pdf_bytes[:5] == b"%PDF-"

    async def rasterize_document(
        self,
        pdf_bytes: bytes,
        document_id: str,
        dpi: int = None,
        fmt: str = None,
        quality: int = None,
    ) -> List[RasterizedPage]:
        if not self._is_valid_pdf(pdf_bytes):
            raise RasterizerError("Not a valid PDF: missing %PDF- magic bytes", document_id=document_id)

        dpi = dpi or settings.page_tile_dpi
        fmt = fmt or settings.page_format
        quality = quality or settings.page_tile_quality

        loop = asyncio.get_event_loop()

        def _convert():
            return pdf2image.convert_from_bytes(
                pdf_bytes,
                dpi=dpi,
                fmt=fmt.lower(),
            )

        try:
            pil_pages = await loop.run_in_executor(None, _convert)
        except Exception as e:
            raise RasterizerError(f"PDF conversion failed: {e}", document_id=document_id) from e

        pages: List[RasterizedPage] = []
        for i, pil_img in enumerate(pil_pages, start=1):
            width_px, height_px = pil_img.size
            buf = io.BytesIO()
            pil_img.save(buf, format=fmt.upper(), quality=quality)
            image_bytes = buf.getvalue()
            pages.append(
                RasterizedPage(
                    page_number=i,
                    image_bytes=image_bytes,
                    width_px=width_px,
                    height_px=height_px,
                )
            )

        return pages
