import asyncio
import uuid
import logging
from datetime import datetime, timedelta, timezone
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# A document stuck in "processing" for longer than this threshold is assumed to
# have been orphaned by a crashed worker and will be cleaned up and retried.
_STALE_PROCESSING_THRESHOLD = timedelta(minutes=15)
_THUMBNAIL_WIDTH_PX = 200


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


def _should_process(status: str, updated_at: datetime) -> str:
    """
    Decide whether the worker should (re)process a document.

    Returns one of:
      "proceed"  — normal upload path, start fresh
      "skip"     — already finished (ready / error) or actively processing
      "recover"  — stuck in processing past the staleness threshold; caller
                   must clean up partial pages before re-processing
    """
    if status == "uploaded":
        return "proceed"
    if status == "processing":
        ts = updated_at if updated_at.tzinfo else updated_at.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - ts >= _STALE_PROCESSING_THRESHOLD:
            return "recover"
        return "skip"
    return "skip"  # "ready" or "error"


async def process_document_with_session(
    db,
    document_id: str,
    storage,
    rasterizer,
    watermark,
) -> dict:
    """
    Core document processing logic — testable without Celery or Redis.

    The caller owns the DB session lifecycle.  On success the session is
    committed; on error the exception propagates (caller decides retry policy).
    """
    from sqlalchemy import select, delete
    from app.models.document import Document, DocumentPage

    # 1. Fetch document
    result = await db.execute(
        select(Document).where(Document.id == uuid.UUID(document_id))
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    decision = _should_process(doc.status, doc.updated_at)

    if decision == "skip":
        logger.info("Document %s status=%r — skipping", document_id, doc.status)
        return {"document_id": document_id, "status": doc.status}

    if decision == "recover":
        logger.warning(
            "Document %s stuck in processing — deleting partial pages and retrying",
            document_id,
        )
        await db.execute(
            delete(DocumentPage).where(
                DocumentPage.document_id == uuid.UUID(document_id)
            )
        )
        await db.flush()

    # 2. Set processing
    doc.status = "processing"
    await db.commit()
    logger.info("Document %s: status → processing", document_id)

    # 3. Download PDF
    logger.info("Document %s: downloading from storage key %r", document_id, doc.storage_key)
    pdf_bytes = await storage.download_bytes(doc.storage_key)
    logger.info("Document %s: downloaded %d bytes", document_id, len(pdf_bytes))

    # 4. Rasterize (validates magic bytes internally; raises RasterizerError on bad PDF)
    logger.info("Document %s: rasterizing PDF", document_id)
    pages = await rasterizer.rasterize_document(pdf_bytes, document_id)
    logger.info("Document %s: rasterized %d page(s)", document_id, len(pages))

    # 5. Apply forensic stamp, upload each page + thumbnail, insert DB records
    for page in pages:
        stamped = watermark.apply_forensic_stamp(
            page.image_bytes, document_id, page.page_number
        )
        page_key = f"pages/{document_id}/{page.page_number:04d}.webp"
        await storage.upload_file(stamped, page_key, content_type="image/webp")
        logger.debug(
            "Document %s: uploaded page %d → %s", document_id, page.page_number, page_key
        )

        # Thumbnail — best-effort: failure must not block document processing
        try:
            thumb_bytes = _make_thumbnail(stamped)
            thumb_key = f"thumbs/{document_id}/{page.page_number:04d}.webp"
            await storage.upload_file(thumb_bytes, thumb_key, content_type="image/webp")
            logger.debug(
                "Document %s: uploaded thumbnail %d → %s",
                document_id, page.page_number, thumb_key,
            )
        except Exception as thumb_exc:
            logger.warning(
                "Document %s: thumbnail generation failed for page %d: %s",
                document_id, page.page_number, thumb_exc,
            )

        db_page = DocumentPage(
            document_id=uuid.UUID(document_id),
            page_number=page.page_number,
            storage_key=page_key,
            width_px=page.width_px,
            height_px=page.height_px,
        )
        db.add(db_page)

    # 6. Mark ready
    doc.status = "ready"
    doc.page_count = len(pages)
    await db.commit()
    logger.info("Document %s: status → ready (%d pages)", document_id, len(pages))

    return {
        "document_id": document_id,
        "page_count": len(pages),
        "status": "ready",
    }


def _run_async(coro):
    """Run an async coroutine from sync Celery task context."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="securedoc.process_document",
)
def process_document(self, document_id: str) -> dict:
    """
    1. Fetch document record from DB. Verify status == 'uploaded'.
    2. Set status = 'processing'.
    3. Download original PDF bytes from storage.
    4. Validate PDF magic bytes. If invalid → set status='error', raise.
    5. Call RasterizerService.rasterize_document().
    6. For each page: upload image, insert DocumentPage record.
    7. Update Document: status='ready', page_count=N.
    """
    return _run_async(_process_document_async(self, document_id))


async def _process_document_async(task, document_id: str) -> dict:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.config import settings
    from app.models.document import Document
    from app.services.storage import get_storage_service
    from app.services.rasterizer import RasterizerService
    from app.services.watermark import WatermarkService

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    storage = get_storage_service()
    rasterizer = RasterizerService()
    watermark = WatermarkService()

    try:
        async with async_session() as db:
            return await process_document_with_session(
                db, document_id, storage, rasterizer, watermark
            )

    except Exception as exc:
        logger.error("process_document failed for %s: %s", document_id, exc)
        # Use a fresh engine for error reporting — the original session may be broken
        try:
            from sqlalchemy.ext.asyncio import create_async_engine as _make_engine
            from sqlalchemy.orm import sessionmaker as _sm
            from sqlalchemy import select as _sel
            from app.config import settings as _cfg
            err_engine = _make_engine(_cfg.database_url, echo=False)
            err_session = _sm(err_engine, class_=AsyncSession, expire_on_commit=False)
            async with err_session() as db2:
                res = await db2.execute(
                    _sel(Document).where(Document.id == uuid.UUID(document_id))
                )
                err_doc = res.scalar_one_or_none()
                if err_doc:
                    err_doc.status = "error"
                    err_doc.error_message = str(exc)[:2000]
                    await db2.commit()
            await err_engine.dispose()
        except Exception as inner:
            logger.error("Failed to update error status: %s", inner)
        raise task.retry(exc=exc)
    finally:
        await engine.dispose()
