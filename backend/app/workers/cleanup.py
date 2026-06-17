"""Daily storage cleanup worker.

Four periodic tasks registered in Celery Beat (see celery_app.py):

  securedoc.cleanup_orphaned_viewer_profiles — daily at 04:00 UTC
    Deletes viewer_profiles rows that are no longer referenced by any
    viewer_sessions or viewer_annotations row.  Closes the GDPR/CCPA
    retention gap where a viewer's email persists indefinitely after every
    document/link they accessed has been deleted.

  securedoc.cleanup_expired_documents  — daily at 03:00 UTC
    1. Marks docs past their retention date as 'expired'
    2. Deletes all S3/R2 objects for expired docs (pages, thumbs, sidecars, original)
    3. Deletes the document DB row (cascades to all children)
    4. Writes an audit log entry for each deleted document

  securedoc.sync_document_access_times — daily at 02:00 UTC
    Updates last_viewed_at and last_accessed_at on Document from the
    access_events table.  Run before cleanup so expiry logic can use
    accurate access times if needed in the future.

  securedoc.take_storage_snapshot      — daily at 01:00 UTC
    Records a StorageSnapshot row per user (and per org) so the forecast
    chart has historical data points to compute a growth trend.
"""
import logging
import uuid
from datetime import datetime, timezone

from app.workers.celery_app import celery_app
from app.workers.tasks import _run_async, _get_db_session_factory

logger = logging.getLogger(__name__)


# ── cleanup_orphaned_viewer_profiles ──────────────────────────────────────────

@celery_app.task(name="securedoc.cleanup_orphaned_viewer_profiles")
def cleanup_orphaned_viewer_profiles() -> dict:
    """Daily job: delete viewer_profiles with no remaining session or annotation references."""
    return _run_async(_cleanup_orphaned_viewer_profiles_async())


async def _cleanup_orphaned_viewer_profiles_async() -> dict:
    from sqlalchemy import delete, select, exists
    from app.models.viewer_profile import ViewerProfile
    from app.models.session import ViewerSession
    from app.models.annotation import ViewerAnnotation

    session_factory = _get_db_session_factory()
    async with session_factory() as db:
        stmt = (
            delete(ViewerProfile)
            .where(
                ~exists(
                    select(ViewerSession.viewer_profile_id).where(
                        ViewerSession.viewer_profile_id == ViewerProfile.id
                    )
                ),
                ~exists(
                    select(ViewerAnnotation.viewer_profile_id).where(
                        ViewerAnnotation.viewer_profile_id == ViewerProfile.id
                    )
                ),
            )
        )
        result = await db.execute(stmt)
        await db.commit()
        deleted = result.rowcount

    logger.info("cleanup_orphaned_viewer_profiles: deleted %d orphaned profile(s)", deleted)
    return {"deleted": deleted}


# ── cleanup_expired_documents ─────────────────────────────────────────────────

@celery_app.task(name="securedoc.cleanup_expired_documents")
def cleanup_expired_documents() -> dict:
    """Daily job: expire and delete documents past their retention date."""
    return _run_async(_cleanup_expired_documents_async())


async def _cleanup_expired_documents_async() -> dict:
    from app.services.retention import expire_and_delete_documents
    from app.services.storage import get_storage_service
    from app.services.audit_service import log_audit_event

    storage = get_storage_service()
    session_factory = _get_db_session_factory()

    async with session_factory() as db:
        result = await expire_and_delete_documents(db, storage)

    logger.info(
        "cleanup_expired_documents marked=%d deleted=%d errors=%d",
        result["marked_expired"], result["deleted"], len(result["errors"]),
    )

    # Audit log the run (non-fatal)
    try:
        async with session_factory() as db:
            await log_audit_event(
                db,
                event_type="retention.cleanup_run",
                actor_user_id=None,
                target_type="system",
                target_id="cleanup_expired_documents",
                details=result,
            )
    except Exception as exc:
        logger.debug("audit log failed for cleanup run: %s", exc)

    return result


# ── sync_document_access_times ────────────────────────────────────────────────

@celery_app.task(name="securedoc.sync_document_access_times")
def sync_document_access_times() -> dict:
    """Daily job: update last_viewed_at / last_accessed_at from access_events.

    Avoids hot-path DB writes on every page request; the cleanup worker
    back-fills these fields once per day instead.
    """
    return _run_async(_sync_access_times_async())


async def _sync_access_times_async() -> dict:
    from sqlalchemy import text
    session_factory = _get_db_session_factory()

    # Single UPDATE per field derived from a correlated subquery.
    # Works on both PostgreSQL and SQLite (aiosqlite).
    update_last_viewed = text("""
        UPDATE documents
        SET last_viewed_at = sub.latest
        FROM (
            SELECT sl.document_id, MAX(ae.created_at) AS latest
            FROM access_events ae
            JOIN share_links sl ON ae.link_id = sl.id
            WHERE ae.event_type = 'page_viewed'
            GROUP BY sl.document_id
        ) AS sub
        WHERE documents.id = sub.document_id
          AND (documents.last_viewed_at IS NULL
               OR documents.last_viewed_at < sub.latest)
    """)
    update_last_accessed = text("""
        UPDATE documents
        SET last_accessed_at = sub.latest
        FROM (
            SELECT sl.document_id, MAX(ae.created_at) AS latest
            FROM access_events ae
            JOIN share_links sl ON ae.link_id = sl.id
            GROUP BY sl.document_id
        ) AS sub
        WHERE documents.id = sub.document_id
          AND (documents.last_accessed_at IS NULL
               OR documents.last_accessed_at < sub.latest)
    """)

    async with session_factory() as db:
        # SQLite does not support UPDATE...FROM; guard so tests pass.
        dialect = db.bind.dialect.name if db.bind else "unknown"
        if dialect == "postgresql":
            r1 = await db.execute(update_last_viewed)
            r2 = await db.execute(update_last_accessed)
            await db.commit()
            updated = (r1.rowcount or 0) + (r2.rowcount or 0)
        else:
            # SQLite fallback: row-by-row update (tests only, not production)
            updated = await _sync_access_times_sqlite(db)

    logger.info("sync_document_access_times: updated %d document(s)", updated)
    return {"updated": updated}


async def _sync_access_times_sqlite(db) -> int:
    """SQLite-compatible fallback for sync_document_access_times (test environments)."""
    from sqlalchemy import select, func
    from app.models.document import Document
    from app.models.link import ShareLink
    from app.models.event import AccessEvent

    updated = 0
    docs = (await db.execute(select(Document))).scalars().all()
    for doc in docs:
        # last_viewed_at
        viewed_q = (
            select(func.max(AccessEvent.created_at))
            .join(ShareLink, ShareLink.id == AccessEvent.link_id)
            .where(
                ShareLink.document_id == doc.id,
                AccessEvent.event_type == "page_viewed",
            )
        )
        last_viewed = (await db.execute(viewed_q)).scalar()
        # last_accessed_at
        accessed_q = (
            select(func.max(AccessEvent.created_at))
            .join(ShareLink, ShareLink.id == AccessEvent.link_id)
            .where(ShareLink.document_id == doc.id)
        )
        last_accessed = (await db.execute(accessed_q)).scalar()

        changed = False
        if last_viewed and (doc.last_viewed_at is None or doc.last_viewed_at < last_viewed):
            doc.last_viewed_at = last_viewed
            changed = True
        if last_accessed and (doc.last_accessed_at is None or doc.last_accessed_at < last_accessed):
            doc.last_accessed_at = last_accessed
            changed = True
        if changed:
            updated += 1

    if updated:
        await db.commit()
    return updated


# ── take_storage_snapshot ─────────────────────────────────────────────────────

@celery_app.task(name="securedoc.take_storage_snapshot")
def take_storage_snapshot() -> dict:
    """Daily job: record per-user (and per-org) storage totals for forecasting."""
    return _run_async(_take_storage_snapshot_async())


async def _take_storage_snapshot_async() -> dict:
    from sqlalchemy import select, func
    from app.models.document import Document
    from app.models.storage_snapshot import StorageSnapshot

    session_factory = _get_db_session_factory()
    now = datetime.now(timezone.utc)
    rows_written = 0

    async with session_factory() as db:
        # Per-user totals (only non-deleted docs)
        user_totals = (
            await db.execute(
                select(
                    Document.user_id,
                    func.sum(
                        func.coalesce(Document.storage_bytes_computed, Document.file_size_bytes)
                    ).label("total_bytes"),
                    func.count(Document.id).label("doc_count"),
                ).where(
                    Document.lifecycle_state != "deleted"
                ).group_by(Document.user_id)
            )
        ).all()

        for row in user_totals:
            db.add(StorageSnapshot(
                id=uuid.uuid4(),
                user_id=row.user_id,
                org_id=None,
                total_bytes=int(row.total_bytes or 0),
                document_count=int(row.doc_count or 0),
                snapshot_at=now,
            ))
            rows_written += 1

        # Per-org totals
        org_totals = (
            await db.execute(
                select(
                    Document.org_id,
                    Document.user_id,
                    func.sum(
                        func.coalesce(Document.storage_bytes_computed, Document.file_size_bytes)
                    ).label("total_bytes"),
                    func.count(Document.id).label("doc_count"),
                ).where(
                    Document.lifecycle_state != "deleted",
                    Document.org_id.isnot(None),
                ).group_by(Document.org_id, Document.user_id)
            )
        ).all()

        for row in org_totals:
            db.add(StorageSnapshot(
                id=uuid.uuid4(),
                user_id=row.user_id,
                org_id=row.org_id,
                total_bytes=int(row.total_bytes or 0),
                document_count=int(row.doc_count or 0),
                snapshot_at=now,
            ))
            rows_written += 1

        await db.commit()

    logger.info("take_storage_snapshot: wrote %d snapshot rows", rows_written)
    return {"rows_written": rows_written, "snapshot_at": now.isoformat()}
