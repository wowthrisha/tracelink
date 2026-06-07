"""
XLSX → PDF → image pipeline.

Converts an XLSX document to PDF via LibreOffice headless, then routes the
resulting PDF through the existing process_pdf_document() pipeline.
"""
import asyncio
import logging

logger = logging.getLogger(__name__)


async def process_xlsx_as_pdf(db, doc, document_id: str, storage, rasterizer, watermark) -> dict:
    """XLSX processing pipeline.

    1. Download original XLSX bytes from storage.
    2. Convert XLSX → PDF via LibreOffice headless.
    3. Pass the PDF bytes to process_pdf_document() (existing pipeline).
    """
    from app.services.libreoffice_converter import LibreOfficeConverter, LibreOfficeError
    from app.workers.pipeline.pdf import process_pdf_document

    logger.info("Document %s: downloading XLSX from %r", document_id, doc.storage_key)
    xlsx_bytes = await storage.download_bytes(doc.storage_key)
    logger.info("Document %s: downloaded %d bytes", document_id, len(xlsx_bytes))

    converter = LibreOfficeConverter()
    loop = asyncio.get_running_loop()

    logger.info("Document %s: converting XLSX → PDF via LibreOffice", document_id)
    try:
        pdf_bytes = await asyncio.wait_for(
            loop.run_in_executor(None, converter.convert_to_pdf, xlsx_bytes, ".xlsx"),
            timeout=LibreOfficeConverter.CONVERSION_TIMEOUT_SEC + 10,
        )
    except (LibreOfficeError, asyncio.TimeoutError) as exc:
        raise ValueError(
            f"XLSX conversion failed for document {document_id}: {exc}"
        ) from exc

    logger.info(
        "Document %s: XLSX → PDF conversion complete (%d bytes)",
        document_id, len(pdf_bytes),
    )

    return await process_pdf_document(
        db, doc, document_id, storage, rasterizer, watermark,
        pdf_bytes=pdf_bytes,
    )
