import asyncio
import uuid
import logging
from datetime import datetime, timedelta, timezone
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# A document stuck in "processing" for longer than this threshold is assumed to
# have been orphaned by a crashed worker and will be cleaned up and retried.
_STALE_PROCESSING_THRESHOLD = timedelta(minutes=15)


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
    from sqlalchemy import select, delete
    from app.config import settings
    from app.models.document import Document, DocumentPage
    from app.services.storage import get_storage_service
    from app.services.rasterizer import RasterizerService, RasterizerError
    from app.services.watermark import WatermarkService

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    storage = get_storage_service()
    rasterizer = RasterizerService()
    watermark = WatermarkService()

    try:
        async with async_session() as db:
            # 1. Fetch document
            result = await db.execute(
                select(Document).where(Document.id == uuid.UUID(document_id))
            )
            doc = result.scalar_one_or_none()
            if not doc:
                raise ValueError(f"Document {document_id} not found")

            decision = _should_process(doc.status, doc.updated_at)

            if decision == "skip":
                logger.info(f"Document {document_id} status={doc.status!r}, skipping")
                return {"document_id": document_id, "status": doc.status}

            if decision == "recover":
                # Crashed mid-processing: delete any partial pages then reprocess
                logger.warning(
                    f"Document {document_id} stuck in processing, "
                    "cleaning up partial pages and retrying"
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

            # 3. Download PDF
            pdf_bytes = await storage.download_bytes(doc.storage_key)

            # 4. Validate + rasterize
            pages = await rasterizer.rasterize_document(pdf_bytes, document_id)

            # 5. Upload pages and insert records
            for page in pages:
                # Apply forensic stamp
                stamped = watermark.apply_forensic_stamp(
                    page.image_bytes, document_id, page.page_number
                )
                page_key = f"pages/{document_id}/{page.page_number:04d}.webp"
                await storage.upload_file(stamped, page_key, content_type="image/webp")

                db_page = DocumentPage(
                    document_id=uuid.UUID(document_id),
                    page_number=page.page_number,
                    storage_key=page_key,
                    width_px=page.width_px,
                    height_px=page.height_px,
                )
                db.add(db_page)

            # 6. Update document status
            doc.status = "ready"
            doc.page_count = len(pages)
            await db.commit()

            return {
                "document_id": document_id,
                "page_count": len(pages),
                "status": "ready",
            }

    except Exception as exc:
        logger.error(f"process_document failed for {document_id}: {exc}")
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
            logger.error(f"Failed to update error status: {inner}")
        raise task.retry(exc=exc)
    finally:
        await engine.dispose()
