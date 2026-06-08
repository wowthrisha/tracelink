import asyncio
import io
import os
import shutil
import tempfile
from dataclasses import dataclass
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

    async def stream_rasterized_pages(
        self,
        pdf_bytes: bytes,
        document_id: str,
        dpi: int = None,
        fmt: str = None,
        quality: int = None,
    ):
        """
        Async generator that yields one RasterizedPage at a time.

        V3.1 — Streaming Rasterization:
        pdftoppm writes all pages to disk in a single subprocess call, then we
        encode pages one-at-a-time and yield each before encoding the next.
        Peak WEBP RAM is O(1 page) instead of O(N pages), so a 300-page PDF
        goes from ~30 MB of accumulated WEBP bytes down to ~100 KB at any
        moment in the pipeline.
        """
        if not self._is_valid_pdf(pdf_bytes):
            raise RasterizerError("Not a valid PDF: missing %PDF- magic bytes", document_id=document_id)

        dpi = dpi or settings.page_tile_dpi
        fmt = fmt or settings.page_format
        quality = quality or settings.page_tile_quality
        last_page = settings.max_pages_per_doc if settings.max_pages_per_doc > 0 else None
        timeout = settings.rasterizer_timeout_sec
        loop = asyncio.get_running_loop()

        tmp_dir = tempfile.mkdtemp(prefix="securedoc_raster_")
        try:
            try:
                page_paths = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda: pdf2image.convert_from_bytes(
                            pdf_bytes,
                            dpi=dpi,
                            output_folder=tmp_dir,
                            paths_only=True,
                            last_page=last_page,
                        ),
                    ),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                raise RasterizerError(
                    f"PDF conversion timed out after {timeout}s — file may be too large or malformed",
                    document_id=document_id,
                )
            except RasterizerError:
                raise
            except Exception as e:
                raise RasterizerError(f"PDF conversion failed: {e}", document_id=document_id) from e

            for i, path in enumerate(page_paths, start=1):
                pil_img = Image.open(path)
                try:
                    width_px, height_px = pil_img.size
                    buf = io.BytesIO()
                    pil_img.save(buf, format=fmt.upper(), quality=quality)
                    image_bytes = buf.getvalue()
                finally:
                    pil_img.close()
                try:
                    os.unlink(path)
                except OSError:
                    pass
                yield RasterizedPage(
                    page_number=i,
                    image_bytes=image_bytes,
                    width_px=width_px,
                    height_px=height_px,
                )
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    async def rasterize_document(
        self,
        pdf_bytes: bytes,
        document_id: str,
        dpi: int = None,
        fmt: str = None,
        quality: int = None,
    ) -> List[RasterizedPage]:
        """Collect all streamed pages into a list. Kept for backward compatibility."""
        pages: List[RasterizedPage] = []
        async for page in self.stream_rasterized_pages(
            pdf_bytes, document_id, dpi=dpi, fmt=fmt, quality=quality
        ):
            pages.append(page)
        return pages
