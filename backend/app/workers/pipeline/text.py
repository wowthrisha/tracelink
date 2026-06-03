"""Text document processing pipeline (.txt / .md / .log)."""
import logging

logger = logging.getLogger(__name__)


async def process_text_document(db, doc, document_id: str, storage) -> dict:
    """
    Process a text document (.txt, .md, .log).

    Downloads the raw bytes, decodes safely, counts line-based chunks,
    then marks the document ready.  No DocumentPage records are created —
    the viewer fetches raw text chunks directly from storage at serve time.
    """
    from app.services.text_processor import decode_text_safe, count_chunks
    from app.config import settings

    logger.info("Document %s: downloading text from storage key %r", document_id, doc.storage_key)
    raw_bytes = await storage.download_bytes(doc.storage_key)
    logger.info("Document %s: downloaded %d bytes", document_id, len(raw_bytes))

    text = decode_text_safe(raw_bytes)
    chunk_count = count_chunks(text, settings.text_lines_per_chunk)
    logger.info("Document %s: text decoded, %d chunk(s)", document_id, chunk_count)

    doc.status = "ready"
    doc.page_count = chunk_count
    await db.commit()
    logger.info("Document %s: status → ready (%d text chunks)", document_id, chunk_count)

    return {
        "document_id": document_id,
        "page_count": chunk_count,
        "status": "ready",
    }
