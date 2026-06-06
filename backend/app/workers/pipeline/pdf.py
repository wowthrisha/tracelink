"""PDF document processing pipeline."""
import asyncio
import logging
import uuid

from app.models.document import DocumentPage

logger = logging.getLogger(__name__)

_THUMBNAIL_WIDTH_PX = 200

# Maximum concurrent R2 upload pairs (page image + thumbnail) per document.
# Each pair is 2 parallel PUT requests.  With 8 slots → 16 concurrent PUTs,
# well within R2's per-connection limits while saturating the worker's
# network uplink on typical Railway / Render environments.
_UPLOAD_CONCURRENCY = 8


def _make_thumbnail(image_bytes: bytes) -> bytes:
    """
    Resize a full-resolution page image to a narrow thumbnail for sidebar navigation.

    Thumbnails are stored at thumbs/{doc_id}/{page:04d}.webp alongside full-res pages.
    They are generated best-effort — a failure here must never block document processing.
    """
    import io as _io
    from PIL import Image

    img = Image.open(_io.BytesIO(image_bytes))
    ratio = _THUMBNAIL_WIDTH_PX / img.width
    new_h = max(1, int(img.height * ratio))
    thumb = img.resize((_THUMBNAIL_WIDTH_PX, new_h), Image.LANCZOS)
    buf = _io.BytesIO()
    thumb.save(buf, format="WEBP", quality=60)
    return buf.getvalue()


async def _process_and_upload_page(
    storage, watermark, semaphore: asyncio.Semaphore, page, document_id: str
) -> DocumentPage:
    """
    Stamp, thumbnail, and upload one page; return the DB row.

    The page image and thumbnail are uploaded concurrently (asyncio.gather)
    within a shared semaphore that caps how many pages are processed in
    parallel at any moment.  All upload I/O is bounded by _UPLOAD_CONCURRENCY
    to prevent thundering-herd against R2/S3 on large documents.
    """
    page_key = f"pages/{document_id}/{page.page_number:04d}.webp"
    thumb_key = f"thumbs/{document_id}/{page.page_number:04d}.webp"

    stamped = watermark.apply_forensic_stamp(page.image_bytes, document_id, page.page_number)

    thumb_bytes = None
    try:
        thumb_bytes = _make_thumbnail(stamped)
    except Exception as thumb_exc:
        logger.warning(
            "Document %s: thumbnail failed for page %d: %s",
            document_id, page.page_number, thumb_exc,
        )

    async with semaphore:
        upload_coros = [storage.upload_file(stamped, page_key, content_type="image/webp")]
        if thumb_bytes is not None:
            upload_coros.append(
                storage.upload_file(thumb_bytes, thumb_key, content_type="image/webp")
            )
        await asyncio.gather(*upload_coros)

    logger.debug("Document %s: uploaded page %d → %s", document_id, page.page_number, page_key)

    return DocumentPage(
        document_id=uuid.UUID(document_id),
        page_number=page.page_number,
        storage_key=page_key,
        width_px=page.width_px,
        height_px=page.height_px,
    )


async def process_pdf_document(
    db, doc, document_id: str, storage, rasterizer, watermark, *, pdf_bytes=None
) -> dict:
    """
    Process a PDF document — rasterizes, watermarks, uploads pages + thumbnails.

    The caller owns the DB session lifecycle.

    Parameters
    ----------
    pdf_bytes:
        Pre-loaded PDF bytes.  When supplied (e.g. from a DOCX→PDF conversion
        step) the storage download is skipped.  When None (the normal PDF
        upload path) the bytes are fetched from doc.storage_key.
    """
    if pdf_bytes is None:
        logger.info("Document %s: downloading from storage key %r", document_id, doc.storage_key)
        pdf_bytes = await storage.download_bytes(doc.storage_key)
    logger.info("Document %s: pdf_bytes %d bytes", document_id, len(pdf_bytes))

    # Rasterize — raises RasterizerError on bad/malicious PDF (permanent failure).
    # Streaming implementation: peak RAM = O(1 page) not O(N pages).
    logger.info("Document %s: rasterizing PDF", document_id)
    pages = await rasterizer.rasterize_document(pdf_bytes, document_id)
    logger.info("Document %s: rasterized %d page(s)", document_id, len(pages))

    # Upload pages + thumbnails with bounded concurrency.
    # asyncio.gather preserves result order so db_pages[i] matches pages[i].
    semaphore = asyncio.Semaphore(_UPLOAD_CONCURRENCY)
    db_pages = await asyncio.gather(*[
        _process_and_upload_page(storage, watermark, semaphore, page, document_id)
        for page in pages
    ])

    for db_page in db_pages:
        db.add(db_page)
    doc.status = "ready"
    doc.page_count = len(pages)
    await db.commit()
    logger.info("Document %s: status → ready (%d pages)", document_id, len(pages))

    # Extract PDF TOC from bookmarks (best-effort: never blocks processing)
    await extract_and_store_pdf_toc(document_id, pdf_bytes, storage)

    return {
        "document_id": document_id,
        "page_count": len(pages),
        "status": "ready",
    }


async def extract_and_store_pdf_toc(
    document_id: str,
    pdf_bytes: bytes,
    storage,
) -> None:
    """
    Extract PDF bookmarks and store as a TOC sidecar JSON file.

    Stored at toc/{doc_id}.json — the /toc endpoint checks this before
    falling back to an empty response.  All errors are non-fatal.
    """
    import json as _json
    try:
        from app.services.toc.pdf_extractor import extract_pdf_toc
        entries = extract_pdf_toc(pdf_bytes)
        if not entries:
            logger.debug("Document %s: no PDF bookmarks found — TOC sidecar skipped", document_id)
            return
        sidecar_key = f"toc/{document_id}.json"
        payload = _json.dumps([e.to_dict() for e in entries], ensure_ascii=False)
        await storage.upload_file(
            payload.encode("utf-8"),
            sidecar_key,
            content_type="application/json",
        )
        logger.info(
            "Document %s: stored PDF TOC sidecar (%d entries) at %s",
            document_id, len(entries), sidecar_key,
        )
    except Exception as exc:
        logger.warning("Document %s: PDF TOC extraction failed (non-fatal): %s", document_id, exc)
