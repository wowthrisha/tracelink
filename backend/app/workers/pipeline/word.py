"""DOC (legacy binary .doc) document processing pipeline.

DOCX is handled by docx_pdf.py (LibreOffice → PDF → image pipeline).
This module covers only the legacy .doc format via antiword text extraction.
"""
import logging

logger = logging.getLogger(__name__)


async def _process_as_converted_text(
    db,
    doc,
    document_id: str,
    storage,
    converted_text: str,
    content_type: str,
) -> dict:
    """
    Shared finalisation step after text conversion:
    overwrites the storage key with the converted text, counts chunks, marks ready.
    """
    from app.services.text_processor import count_chunks
    from app.config import settings

    await storage.upload_file(
        converted_text.encode("utf-8"),
        doc.storage_key,
        content_type=content_type,
    )

    chunk_count = count_chunks(converted_text, settings.text_lines_per_chunk)
    doc.status = "ready"
    doc.page_count = chunk_count
    await db.commit()
    return {"document_id": document_id, "page_count": chunk_count, "status": "ready"}


async def process_doc_document(db, doc, document_id: str, storage) -> dict:
    """
    Process a legacy .doc document.

    Pipeline:
      1. Download original .doc bytes
      2. Convert to plain text using antiword subprocess
      3. Overwrite storage key with plain text
      4. Count chunks and mark document ready

    If antiword is unavailable or conversion fails: mark as error.
    """
    import asyncio
    from app.services.toc.docx_extractor import doc_to_text

    logger.info("Document %s: downloading .doc from %r", document_id, doc.storage_key)
    doc_bytes = await storage.download_bytes(doc.storage_key)
    logger.info("Document %s: downloaded %d bytes", document_id, len(doc_bytes))

    loop = asyncio.get_running_loop()
    plain_text = await loop.run_in_executor(None, doc_to_text, doc_bytes, document_id)

    if not plain_text.strip():
        raise ValueError(
            f"DOC conversion produced empty text for document {document_id}. "
            "Ensure antiword is installed (apt-get install antiword)."
        )

    result = await _process_as_converted_text(
        db, doc, document_id, storage, plain_text, "text/plain"
    )
    logger.info(
        "Document %s: status → ready (%d text chunks from DOC)", document_id, result["page_count"]
    )
    return result
