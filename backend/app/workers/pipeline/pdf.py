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

# Maximum rasterized pages held in the sliding window at once.
# One window slot = one page being watermarked/uploaded (≈100–400 KB WEBP).
# Keeping this at 2× the upload concurrency keeps R2 upload slots fully
# saturated while bounding peak WEBP RAM to ~6 MB (16 × 400 KB) vs the
# old O(N) approach that accumulated all pages before any uploading started.
_TASK_WINDOW = _UPLOAD_CONCURRENCY * 2


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

    # V3.1 + V3.2: stream one page at a time through a bounded sliding window.
    # stream_rasterized_pages() yields pages as they are encoded (one at a time).
    # We immediately schedule an upload task for each page and drain the oldest
    # task when the window reaches _TASK_WINDOW, capping peak WEBP RAM to
    # _TASK_WINDOW pages (≈16 × 400 KB = 6 MB) instead of O(N pages).
    logger.info("Document %s: rasterizing PDF (streaming)", document_id)
    semaphore = asyncio.Semaphore(_UPLOAD_CONCURRENCY)
    pending: list = []
    db_pages: list = []

    async for page in rasterizer.stream_rasterized_pages(pdf_bytes, document_id):
        task = asyncio.create_task(
            _process_and_upload_page(storage, watermark, semaphore, page, document_id)
        )
        pending.append(task)
        if len(pending) >= _TASK_WINDOW:
            db_pages.append(await pending.pop(0))

    for task in pending:
        db_pages.append(await task)

    db_pages.sort(key=lambda p: p.page_number)
    page_count = len(db_pages)
    logger.info("Document %s: rasterized %d page(s)", document_id, page_count)

    for db_page in db_pages:
        db.add(db_page)
    doc.status = "ready"
    doc.page_count = page_count
    await db.commit()
    logger.info("Document %s: status → ready (%d pages)", document_id, page_count)

    # Extract PDF TOC from bookmarks (best-effort: never blocks processing)
    await extract_and_store_pdf_toc(document_id, pdf_bytes, storage)
    # Extract page text for full-document search (best-effort: never blocks processing)
    await extract_and_store_text_sidecar(document_id, pdf_bytes, storage)

    return {
        "document_id": document_id,
        "page_count": page_count,
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


async def extract_and_store_text_sidecar(
    document_id: str,
    pdf_bytes: bytes,
    storage,
) -> None:
    """
    Extract plain text from each PDF page and store as a search sidecar.
    Stored at text/{doc_id}.json as [{"page": N, "text": "..."}].
    Used by the /api/viewer/search endpoint for full-document search.
    """
    import json as _json
    try:
        from io import BytesIO as _BytesIO
        import pypdf as _pypdf
        reader = _pypdf.PdfReader(_BytesIO(pdf_bytes))
        pages = []
        for i, pdf_page in enumerate(reader.pages, start=1):
            text = (pdf_page.extract_text() or "").strip()
            pages.append({"page": i, "text": text})
        if not pages:
            return
        sidecar_key = f"text/{document_id}.json"
        payload = _json.dumps(pages, ensure_ascii=False)
        await storage.upload_file(
            payload.encode("utf-8"),
            sidecar_key,
            content_type="application/json",
        )
        logger.info(
            "Document %s: stored text sidecar (%d pages) at %s",
            document_id, len(pages), sidecar_key,
        )
    except Exception as exc:
        logger.warning("Document %s: text sidecar extraction failed (non-fatal): %s", document_id, exc)
