import asyncio
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# A document stuck in "processing" for longer than this threshold is assumed to
# have been orphaned by a crashed worker and will be cleaned up and retried.
_STALE_PROCESSING_THRESHOLD = timedelta(minutes=15)
_THUMBNAIL_WIDTH_PX = 200

# ── Module-level async engine and event loop ────────────────────────────────
# Both are created once per worker *process* and reused across all tasks.
#
# WHY A PERSISTENT LOOP:
#   asyncpg connections are bound to the asyncio event loop on which they were
#   created.  The original code called asyncio.new_event_loop() per task and
#   then closed it, but the module-level _engine kept its connection pool alive.
#   On the second task (new loop) asyncpg tried to use connections from the
#   first (closed) loop → "cannot perform operation: another operation is in
#   progress".  A persistent per-process loop ensures connections are always
#   used on the loop they were created on.
_engine = None
_session_factory = None
_worker_loop: Optional[asyncio.AbstractEventLoop] = None


def _get_worker_loop() -> asyncio.AbstractEventLoop:
    """Return (and lazily create) the persistent async event loop for this worker process."""
    global _worker_loop
    if _worker_loop is None or _worker_loop.is_closed():
        _worker_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_worker_loop)
        logger.info("Worker async event loop created (pid=%d)", __import__("os").getpid())
    return _worker_loop


def _get_db_session_factory():
    """Return the module-level async session factory, initialising it on first call."""
    global _engine, _session_factory
    if _session_factory is None:
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
        from app.config import settings
        from app.database import _normalize_db_url
        _engine = create_async_engine(
            _normalize_db_url(settings.database_url),
            echo=False,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,    # validate connections before checkout
            pool_recycle=1800,     # discard stale connections every 30 min
        )
        _session_factory = async_sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info("Worker DB engine initialised")
    return _session_factory


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
        # Invalidate L2 (Redis) byte cache so API replicas don't serve stale bytes
        # after reprocess.  L1 (in-process on the API server) cannot be cleared from
        # the worker but will repopulate from fresh storage after its next eviction.
        from app.services.page_cache import clear_doc_bytes_redis
        from app.services.viewer_cache import invalidate_doc_entries
        await clear_doc_bytes_redis(document_id)
        invalidate_doc_entries(document_id)
        logger.info("cache_invalidate doc_id=%s source=worker type=reprocess", document_id)

    # 2. Set processing
    doc.status = "processing"
    await db.commit()
    logger.info("Document %s: status → processing", document_id)

    # 3. Download PDF
    logger.info("Document %s: downloading from storage key %r", document_id, doc.storage_key)
    pdf_bytes = await storage.download_bytes(doc.storage_key)
    logger.info("Document %s: downloaded %d bytes", document_id, len(pdf_bytes))

    # 4. Rasterize — raises RasterizerError on bad/malicious PDF (permanent failure)
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
    """Run an async coroutine from sync Celery task context.

    Uses a persistent per-process event loop so asyncpg connection-pool
    connections are always executed on the loop they were created on.
    Creating a new loop per task (the previous approach) caused the pool to
    accumulate connections bound to closed loops, triggering asyncpg's
    "another operation is in progress" InterfaceError on the second task.
    """
    return _get_worker_loop().run_until_complete(coro)


@celery_app.task(name="securedoc.purge_stale_sessions")
def purge_stale_sessions() -> dict:
    """
    Periodic cleanup task: delete ViewerSession rows inactive for >2 hours.

    Run this every 30 minutes via Celery Beat to prevent unbounded table growth.
    Safe to run while the app is serving traffic — uses a DELETE WHERE clause
    with an indexed timestamp column.
    """
    return _run_async(_purge_stale_sessions_async())


async def _purge_stale_sessions_async() -> dict:
    from sqlalchemy import delete
    from app.models.session import ViewerSession

    cutoff = datetime.now(timezone.utc) - timedelta(hours=2)
    session_factory = _get_db_session_factory()
    async with session_factory() as db:
        result = await db.execute(
            delete(ViewerSession).where(ViewerSession.last_seen_at < cutoff)
        )
        await db.commit()
        deleted = result.rowcount
        logger.info("purge_stale_sessions: removed %d stale session(s)", deleted)
    return {"deleted": deleted}


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
    5. Call RasterizerService.rasterize_document() with timeout protection.
    6. For each page: upload image, insert DocumentPage record.
    7. Update Document: status='ready', page_count=N.
    """
    return _run_async(_process_document_async(self, document_id))


async def _mark_document_error(document_id: str, message: str) -> None:
    """Set a document's status to 'error' using the module-level engine."""
    from sqlalchemy import select
    from app.models.document import Document

    session_factory = _get_db_session_factory()
    try:
        async with session_factory() as db:
            result = await db.execute(
                select(Document).where(Document.id == uuid.UUID(document_id))
            )
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = "error"
                doc.error_message = message[:2000]
                await db.commit()
    except Exception as inner:
        logger.error("Failed to update error status for %s: %s", document_id, inner)


async def _process_document_async(task, document_id: str) -> dict:
    from app.services.storage import get_storage_service
    from app.services.rasterizer import RasterizerService, RasterizerError
    from app.services.watermark import WatermarkService

    session_factory = _get_db_session_factory()
    storage = get_storage_service()
    rasterizer = RasterizerService()
    watermark = WatermarkService()

    try:
        async with session_factory() as db:
            return await process_document_with_session(
                db, document_id, storage, rasterizer, watermark
            )

    except (RasterizerError, ValueError) as exc:
        # Permanent failures — bad PDF, document not found, conversion timeout.
        # Retrying won't help; mark error and stop.
        logger.error(
            "Document %s: permanent failure (%s): %s",
            document_id, type(exc).__name__, exc,
        )
        await _mark_document_error(document_id, str(exc))
        # Raise WITHOUT retry so Celery marks task as FAILURE immediately
        raise

    except Exception as exc:
        # Transient failure — storage blip, DB connection error, etc.
        # Mark error status then retry (Celery will re-queue).
        logger.error(
            "Document %s: transient failure (%s): %s — retrying",
            document_id, type(exc).__name__, exc,
        )
        await _mark_document_error(document_id, str(exc))
        raise task.retry(exc=exc)
