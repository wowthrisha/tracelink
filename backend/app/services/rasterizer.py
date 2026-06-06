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

        loop = asyncio.get_running_loop()
        last_page = settings.max_pages_per_doc if settings.max_pages_per_doc > 0 else None
        timeout = settings.rasterizer_timeout_sec

        def _stream_convert() -> List[RasterizedPage]:
            """
            Stream-rasterize pages to disk then encode one at a time.

            Using output_folder + paths_only=True tells poppler to write each
            page as a PPM file (its native format).  We then open one file at a
            time, encode to WEBP, delete the temp file, and move on.

            Memory before: N PIL Images × ~8 MB = ~1.6 GB for a 200-page PDF.
            Memory after:  1 PIL Image × ~8 MB + accumulated WEBP bytes
                           (~100 KB each) = ~28 MB for a 200-page PDF.
            """
            tmp_dir = tempfile.mkdtemp(prefix="securedoc_raster_")
            try:
                page_paths = pdf2image.convert_from_bytes(
                    pdf_bytes,
                    dpi=dpi,
                    output_folder=tmp_dir,
                    paths_only=True,
                    last_page=last_page,
                )
                pages: List[RasterizedPage] = []
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
                    pages.append(
                        RasterizedPage(
                            page_number=i,
                            image_bytes=image_bytes,
                            width_px=width_px,
                            height_px=height_px,
                        )
                    )
                return pages
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        try:
            pages = await asyncio.wait_for(
                loop.run_in_executor(None, _stream_convert),
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

        return pages
