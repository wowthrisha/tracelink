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
    # Extract hyperlink annotations for clickable overlay (best-effort)
    await extract_and_store_links_sidecar(document_id, pdf_bytes, storage)
    # Extract word bounding boxes for search highlighting (best-effort)
    await extract_and_store_word_positions(document_id, pdf_bytes, storage)

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


async def extract_and_store_links_sidecar(
    document_id: str,
    pdf_bytes: bytes,
    storage,
) -> None:
    """
    Extract hyperlinks from each PDF page and store as a links sidecar.

    Two extraction strategies are combined per page:
      1. PDF annotation-based (type=annotation): precise clickable regions with coordinates
      2. Text regex-based (type=text): any http/https URL found in page text

    Stored at links/{doc_id}.json as [{page, links: [{url, type, x?, y?, w?, h?, label?}]}].
    Annotation links include normalized [0,1] coordinates (top-left origin).
    Text links include a short `label` extracted from surrounding context.
    Always writes the sidecar (even when empty) so the frontend knows extraction ran.
    """
    import json as _json
    import re as _re
    _URL_RE = _re.compile(r"https?://[^\s\"'<>()\[\]{}]+[^\s\"'<>()\[\]{}.,;:!?]")
    try:
        from io import BytesIO as _BytesIO
        import pypdf as _pypdf

        reader = _pypdf.PdfReader(_BytesIO(pdf_bytes))
        pages_data = []

        for i, pdf_page in enumerate(reader.pages, start=1):
            width_pt = float(pdf_page.mediabox.width)
            height_pt = float(pdf_page.mediabox.height)
            if width_pt <= 0 or height_pt <= 0:
                continue

            links: list = []
            seen_urls: set = set()  # deduplicate within a page

            # ── Strategy 1: PDF annotation hyperlinks ─────────────────────────
            raw_annots = pdf_page.get("/Annots")
            if raw_annots is not None:
                # /Annots may be an IndirectObject pointing to an array — resolve it
                if hasattr(raw_annots, 'get_object'):
                    raw_annots = raw_annots.get_object()
            if raw_annots:
                for annot_ref in raw_annots:
                    try:
                        # Each annotation entry may be an IndirectObject — resolve
                        annot = annot_ref.get_object() if hasattr(annot_ref, 'get_object') else annot_ref
                        if annot.get("/Subtype") != "/Link":
                            continue
                        action = annot.get("/A")
                        if action is None:
                            continue
                        # Action dict may also be indirect
                        if hasattr(action, 'get_object'):
                            action = action.get_object()
                        uri = action.get("/URI")
                        if uri is None:
                            continue
                        # URI may be stored as bytes in some PDF generators
                        if isinstance(uri, bytes):
                            uri_str = uri.decode("utf-8", errors="replace").strip()
                        else:
                            uri_str = str(uri).strip()
                        if not uri_str.startswith(("http://", "https://")):
                            continue
                        rect = annot.get("/Rect")
                        if not rect or len(rect) < 4:
                            continue
                        x0, y0, x1, y1 = (float(v) for v in rect[:4])
                        if x1 <= x0 or y1 <= y0:
                            continue
                        nx = x0 / width_pt
                        ny = 1.0 - y1 / height_pt
                        nw = (x1 - x0) / width_pt
                        nh = (y1 - y0) / height_pt
                        if 0 <= nx <= 1 and 0 <= ny <= 1 and nw > 0 and nh > 0:
                            links.append({
                                "url": uri_str,
                                "type": "annotation",
                                "x": round(nx, 4), "y": round(ny, 4),
                                "w": round(nw, 4), "h": round(nh, 4),
                            })
                            seen_urls.add(uri_str)
                    except Exception:
                        continue

            # ── Strategy 2: URL regex on page text ────────────────────────────
            try:
                page_text = pdf_page.extract_text() or ""
                for m in _URL_RE.finditer(page_text):
                    url = m.group(0)
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    # Extract up to 40 chars before URL as label context
                    ctx_start = max(0, m.start() - 40)
                    ctx = page_text[ctx_start:m.start()].replace("\n", " ").strip()
                    label = ctx[-30:].lstrip() if ctx else url
                    links.append({"url": url, "type": "text", "label": label})
            except Exception:
                pass

            if links:
                pages_data.append({"page": i, "links": links})

        sidecar_key = f"links/{document_id}.json"
        # `extracted: true` lets the viewer skip re-extraction for docs with no links
        payload = _json.dumps({"pages": pages_data, "extracted": True}, ensure_ascii=False)
        await storage.upload_file(payload.encode("utf-8"), sidecar_key, content_type="application/json")
        logger.info("Document %s: stored links sidecar (%d pages)", document_id, len(pages_data))
    except Exception as exc:
        logger.warning("Document %s: link sidecar extraction failed (non-fatal): %s", document_id, exc)


async def extract_and_store_word_positions(
    document_id: str,
    pdf_bytes: bytes,
    storage,
) -> None:
    """
    Extract word-level bounding boxes from each PDF page for search highlighting.

    Stored at words/{doc_id}.json as [{page, words: [{t,x,y,w,h}]}] with
    coordinates normalized to [0,1] relative to page dimensions (top-left origin).
    Uses pypdf's visitor API; accuracy is approximate (±1 char width). Non-fatal.
    """
    import json as _json
    try:
        from io import BytesIO as _BytesIO
        import pypdf as _pypdf

        reader = _pypdf.PdfReader(_BytesIO(pdf_bytes))
        pages_data = []

        for i, pdf_page in enumerate(reader.pages, start=1):
            width_pt = float(pdf_page.mediabox.width)
            height_pt = float(pdf_page.mediabox.height)
            if width_pt <= 0 or height_pt <= 0:
                continue

            page_words: list = []

            def _visitor(text, cm, tm, fontdict, fontsize, _pw=width_pt, _ph=height_pt, _out=page_words):
                if not text:
                    return
                try:
                    x = float(tm[4])
                    y = float(tm[5])
                    h = abs(float(tm[3])) if tm[3] else float(fontsize or 10.0)
                    if h < 1:
                        h = 10.0
                    char_w = h * 0.52  # approximate average character width
                    cur_x = x
                    for part in text.split(" "):
                        if part:
                            word_w = len(part) * char_w
                            nx = cur_x / _pw
                            ny = 1.0 - (y + h) / _ph
                            nw = word_w / _pw
                            nh = h / _ph
                            if (0 <= nx <= 1 and 0 <= ny <= 1
                                    and nw > 0 and nh > 0 and len(part) >= 2):
                                _out.append({
                                    "t": part,
                                    "x": round(max(0.0, nx), 4),
                                    "y": round(max(0.0, ny), 4),
                                    "w": round(min(1.0 - nx, nw), 4),
                                    "h": round(min(1.0 - ny, nh), 4),
                                })
                            cur_x += word_w + char_w
                        else:
                            cur_x += char_w
                except Exception:
                    pass

            pdf_page.extract_text(visitor_text=_visitor)

            if page_words:
                pages_data.append({"page": i, "words": page_words})

        if not pages_data:
            return
        sidecar_key = f"words/{document_id}.json"
        payload = _json.dumps(pages_data, ensure_ascii=False)
        await storage.upload_file(payload.encode("utf-8"), sidecar_key, content_type="application/json")
        logger.info(
            "Document %s: stored word position sidecar (%d pages)",
            document_id, len(pages_data),
        )
    except Exception as exc:
        logger.warning("Document %s: word position extraction failed (non-fatal): %s", document_id, exc)
