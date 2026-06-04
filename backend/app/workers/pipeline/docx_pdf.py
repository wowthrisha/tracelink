"""
DOCX → PDF → image pipeline.

Converts a DOCX document to PDF via LibreOffice headless, then routes the
resulting PDF through the existing process_pdf_document() pipeline.

This is the single production entry point for DOCX processing after Phase D2.
DOC (legacy binary format) continues to use the antiword text pipeline.

TOC strategy
────────────
DOCX heading styles (extracted by python-docx) produce higher-quality TOC
entries than PDF bookmarks from a LibreOffice-converted file (which may have
none).  The sidecar is therefore written AFTER the PDF pipeline completes,
overwriting any bookmark-based sidecar the PDF pipeline might have stored.
"""
import asyncio
import json as _json
import logging

logger = logging.getLogger(__name__)


async def process_docx_as_pdf(db, doc, document_id: str, storage, rasterizer, watermark) -> dict:
    """
    DOCX processing pipeline.

    1. Download original DOCX bytes from storage.
    2. Convert DOCX → PDF via LibreOffice headless (run in thread-pool executor
       so the async event loop is not blocked during the subprocess call).
    3. Pass the PDF bytes directly to process_pdf_document() — no intermediate
       upload; the DOCX storage_key is left pointing to the original DOCX bytes.
    4. Write the DOCX heading TOC sidecar (overwrites any PDF bookmark sidecar
       produced in step 3, guaranteeing the highest-quality TOC).

    Conversion or rasterisation failures raise ValueError or RasterizerError,
    both of which are treated as permanent failures by the Celery task wrapper
    (no retry; document is marked as error).
    """
    from app.services.libreoffice_converter import (
        LibreOfficeConverter,
        LibreOfficeError,
    )
    from app.workers.pipeline.pdf import process_pdf_document
    from app.services.toc.docx_extractor import extract_docx_toc, resolve_toc_page_numbers

    # ── 1. Download ────────────────────────────────────────────────────────────
    logger.info("Document %s: downloading DOCX from %r", document_id, doc.storage_key)
    docx_bytes = await storage.download_bytes(doc.storage_key)
    logger.info("Document %s: downloaded %d bytes", document_id, len(docx_bytes))

    # ── 2. Convert DOCX → PDF ─────────────────────────────────────────────────
    converter = LibreOfficeConverter()
    loop = asyncio.get_running_loop()

    logger.info("Document %s: converting DOCX → PDF via LibreOffice", document_id)
    try:
        pdf_bytes = await asyncio.wait_for(
            loop.run_in_executor(None, converter.convert_to_pdf, docx_bytes, ".docx"),
            # Outer async timeout is slightly longer than the inner subprocess
            # timeout so the subprocess always gets a chance to clean up first.
            timeout=LibreOfficeConverter.CONVERSION_TIMEOUT_SEC + 10,
        )
    except (LibreOfficeError, asyncio.TimeoutError) as exc:
        # asyncio.TimeoutError is caught explicitly so it is treated as a
        # permanent document failure (ValueError → no Celery retry) rather
        # than a transient error that would trigger up to 3 unnecessary retries
        # of 70 s each before the task is finally abandoned.
        raise ValueError(
            f"DOCX conversion failed for document {document_id}: {exc}"
        ) from exc

    logger.info(
        "Document %s: DOCX → PDF conversion complete (%d bytes)",
        document_id, len(pdf_bytes),
    )

    # ── 3. Run existing PDF pipeline with converted bytes ─────────────────────
    # Passing pdf_bytes bypasses the storage download inside process_pdf_document.
    # The document record (doc.storage_key) still points to the original DOCX;
    # the generated page WebP files are stored at pages/{doc_id}/{page:04d}.webp
    # exactly as for native PDFs.
    result = await process_pdf_document(
        db, doc, document_id, storage, rasterizer, watermark,
        pdf_bytes=pdf_bytes,
    )

    # ── 4. Build TOC sidecar: DOCX headings + PDF page numbers ───────────────
    # Primary source: python-docx heading styles (title + level, high fidelity).
    # Page numbers: resolved from LibreOffice-generated PDF bookmarks via pypdf.
    # LibreOffice converts Word heading styles to PDF outline entries by default,
    # so most headings receive a page number.  Written after the PDF pipeline so
    # it always overrides any bookmark-only sidecar the PDF pipeline may have
    # stored.
    try:
        toc_entries = extract_docx_toc(docx_bytes)
        if toc_entries:
            toc_entries = resolve_toc_page_numbers(toc_entries, pdf_bytes)
            resolved = sum(1 for e in toc_entries if e.page is not None)
            sidecar_key = f"toc/{document_id}.json"
            payload = _json.dumps(
                [e.to_dict() for e in toc_entries], ensure_ascii=False
            )
            await storage.upload_file(
                payload.encode("utf-8"), sidecar_key, content_type="application/json"
            )
            logger.info(
                "Document %s: stored DOCX TOC sidecar (%d entries, %d with page numbers)",
                document_id, len(toc_entries), resolved,
            )
        else:
            logger.debug(
                "Document %s: no DOCX headings found — TOC sidecar skipped",
                document_id,
            )
    except Exception as exc:
        logger.warning(
            "Document %s: DOCX TOC extraction failed (non-fatal): %s",
            document_id, exc,
        )

    return result
