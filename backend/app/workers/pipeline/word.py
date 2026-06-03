"""Word document processing pipelines (.docx / .doc)."""
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
    Shared finalisation step for DOCX and DOC after text conversion:
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


async def process_docx_document(db, doc, document_id: str, storage) -> dict:
    """
    Process a DOCX document.

    Pipeline:
      1. Download original DOCX bytes
      2. Extract native TOC from heading styles (stored as JSON sidecar)
      3. Convert DOCX to markdown text using python-docx
      4. Overwrite storage key with converted text
      5. Count chunks and mark document ready
    """
    import json as _json
    from app.services.toc.docx_extractor import extract_docx_toc, docx_to_markdown

    logger.info("Document %s: downloading DOCX from %r", document_id, doc.storage_key)
    docx_bytes = await storage.download_bytes(doc.storage_key)
    logger.info("Document %s: downloaded %d bytes", document_id, len(docx_bytes))

    try:
        toc_entries = extract_docx_toc(docx_bytes)
        if toc_entries:
            sidecar_key = f"toc/{document_id}.json"
            payload = _json.dumps([e.to_dict() for e in toc_entries], ensure_ascii=False)
            await storage.upload_file(
                payload.encode("utf-8"), sidecar_key, content_type="application/json"
            )
            logger.info(
                "Document %s: stored DOCX TOC sidecar (%d entries)", document_id, len(toc_entries)
            )
    except Exception as exc:
        logger.warning("Document %s: DOCX TOC extraction failed (non-fatal): %s", document_id, exc)

    logger.info("Document %s: converting DOCX to markdown text", document_id)
    markdown_text = docx_to_markdown(docx_bytes)
    if not markdown_text.strip():
        raise ValueError(f"DOCX conversion produced empty text for document {document_id}")

    result = await _process_as_converted_text(
        db, doc, document_id, storage, markdown_text, "text/markdown"
    )
    logger.info(
        "Document %s: status → ready (%d text chunks from DOCX)", document_id, result["page_count"]
    )
    return result


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
