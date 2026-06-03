import asyncio
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_STALE_PROCESSING_THRESHOLD = timedelta(minutes=15)

# ── Module-level async engine and event loop ────────────────────────────────
# Both are created once per worker *process* and reused across all tasks.
#
# WHY A PERSISTENT LOOP:
#   asyncpg connections are bound to the asyncio event loop on which they were
#   created.  Creating a new loop per task causes the pool to accumulate
#   connections bound to closed loops, triggering asyncpg's "another operation
#   is in progress" InterfaceError on the second task.
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
            pool_pre_ping=True,
            pool_recycle=1800,
        )
        _session_factory = async_sessionmaker(
            _engine, class_=AsyncSession, expire_on_commit=False
        )
        logger.info("Worker DB engine initialised")
    return _session_factory


def _run_async(coro):
    """Run an async coroutine from sync Celery task context using the persistent loop."""
    return _get_worker_loop().run_until_complete(coro)


def _should_process(status: str, updated_at: datetime) -> str:
    """
    Decide whether the worker should (re)process a document.

    Returns one of:
      "proceed"  — normal upload path, start fresh
      "skip"     — already finished (ready / error) or actively processing
      "recover"  — stuck in processing past the staleness threshold
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

    Dispatches to the appropriate pipeline based on doc.file_type.
    The caller owns the DB session lifecycle.
    """
    from sqlalchemy import select, delete
    from app.models.document import Document, DocumentPage
    from app.workers.pipeline.pdf import process_pdf_document
    from app.workers.pipeline.text import process_text_document
    from app.workers.pipeline.word import process_docx_document, process_doc_document

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
        from app.services.page_cache import clear_doc_bytes_redis
        from app.services.viewer_cache import invalidate_doc_entries
        await clear_doc_bytes_redis(document_id)
        invalidate_doc_entries(document_id)
        logger.info("cache_invalidate doc_id=%s source=worker type=reprocess", document_id)

    doc.status = "processing"
    await db.commit()
    logger.info("Document %s: status → processing", document_id)

    file_type = getattr(doc, "file_type", "pdf") or "pdf"
    if file_type in ("txt", "md", "log"):
        return await process_text_document(db, doc, document_id, storage)
    elif file_type == "docx":
        return await process_docx_document(db, doc, document_id, storage)
    elif file_type == "doc":
        return await process_doc_document(db, doc, document_id, storage)
    else:
        return await process_pdf_document(db, doc, document_id, storage, rasterizer, watermark)


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
        logger.error(
            "Document %s: permanent failure (%s): %s",
            document_id, type(exc).__name__, exc,
        )
        await _mark_document_error(document_id, str(exc))
        raise

    except Exception as exc:
        logger.error(
            "Document %s: transient failure (%s): %s — retrying",
            document_id, type(exc).__name__, exc,
        )
        await _mark_document_error(document_id, str(exc))
        raise task.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=10,
    name="securedoc.process_document",
)
def process_document(self, document_id: str) -> dict:
    """Celery task: fetch, validate, and process a document."""
    return _run_async(_process_document_async(self, document_id))


@celery_app.task(name="securedoc.purge_stale_sessions")
def purge_stale_sessions() -> dict:
    """
    Periodic cleanup: delete ViewerSession rows inactive for >2 hours.
    Run every 30 minutes via Celery Beat.
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


@celery_app.task(name="securedoc.requeue_orphaned_uploads")
def requeue_orphaned_uploads() -> dict:
    """
    Periodic safety-net: re-queue process_document for any document stuck
    in 'uploaded' status for longer than 10 minutes.
    Run every 5 minutes via Celery Beat.
    """
    return _run_async(_requeue_orphaned_uploads_async())


async def _requeue_orphaned_uploads_async() -> dict:
    from sqlalchemy import select
    from app.models.document import Document

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    session_factory = _get_db_session_factory()
    requeued = 0
    async with session_factory() as db:
        result = await db.execute(
            select(Document.id).where(
                Document.status == "uploaded",
                Document.updated_at < cutoff,
            )
        )
        orphan_ids = [str(row[0]) for row in result.all()]

    for doc_id in orphan_ids:
        try:
            process_document.delay(doc_id)
            logger.info("requeue_orphaned_uploads: re-queued doc_id=%s", doc_id)
            requeued += 1
        except Exception as exc:
            logger.error(
                "requeue_orphaned_uploads: failed to re-queue doc_id=%s: %s",
                doc_id, exc,
            )

    if requeued:
        logger.info("requeue_orphaned_uploads: re-queued %d orphaned upload(s)", requeued)
    return {"requeued": requeued}
