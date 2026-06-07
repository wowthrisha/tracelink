"""
PPTX → PDF → image pipeline.

Converts a PPTX document to PDF via LibreOffice headless, then routes the
resulting PDF through the existing process_pdf_document() pipeline.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


async def process_pptx_as_pdf(db, doc, document_id: str, storage, rasterizer, watermark) -> dict:
    """PPTX processing pipeline.

    1. Download original PPTX bytes from storage.
    2. Convert PPTX → PDF via LibreOffice headless.
    3. Pass the PDF bytes to process_pdf_document() (existing pipeline).
    """
    from app.services.libreoffice_converter import LibreOfficeConverter, LibreOfficeError
    from app.workers.pipeline.pdf import process_pdf_document

    logger.info("Document %s: downloading PPTX from %r", document_id, doc.storage_key)
    pptx_bytes = await storage.download_bytes(doc.storage_key)
    logger.info("Document %s: downloaded %d bytes", document_id, len(pptx_bytes))

    converter = LibreOfficeConverter()
    loop = asyncio.get_running_loop()

    logger.info("Document %s: converting PPTX → PDF via LibreOffice", document_id)
    try:
        pdf_bytes = await asyncio.wait_for(
            loop.run_in_executor(None, converter.convert_to_pdf, pptx_bytes, ".pptx"),
            timeout=LibreOfficeConverter.CONVERSION_TIMEOUT_SEC + 10,
        )
    except (LibreOfficeError, asyncio.TimeoutError) as exc:
        raise ValueError(
            f"PPTX conversion failed for document {document_id}: {exc}"
        ) from exc

    logger.info(
        "Document %s: PPTX → PDF conversion complete (%d bytes)",
        document_id, len(pdf_bytes),
    )

    return await process_pdf_document(
        db, doc, document_id, storage, rasterizer, watermark,
        pdf_bytes=pdf_bytes,
    )
