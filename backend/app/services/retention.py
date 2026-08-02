"""Document retention and storage lifecycle service.

Two main responsibilities:

1.  Storage deletion — delete_document_storage() removes every S3/R2 object
    for a document.  It is the single authoritative place that knows the full
    key namespace:

        originals/{doc_id}.{ext}           (original upload)
        pages/{doc_id}/{n:04d}.webp        (rasterised page images)
        thumbs/{doc_id}/{n:04d}.webp       (navigation thumbnails)
        toc/{doc_id}.json                  (TOC sidecar — PDF, DOCX, PPTX)
        text/{doc_id}.json                 (text-search sidecar — PDF)
        links/{doc_id}.json                (hyperlinks sidecar — PDF)

    It deletes via list+delete (prefix scan) for the /pages/ and /thumbs/
    prefixes, and attempts each sidecar key individually (delete_file silently
    ignores NoSuchKey).  Returns a summary dict for audit logging.

2.  Expiry resolution — compute_expires_at() converts a retention_policy
    string ('30_days' | '60_days' | '90_days' | 'never') to an absolute UTC
    datetime or None.  Called when a document is uploaded or its policy is
    updated.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models.document import RETENTION_DAYS

logger = logging.getLogger(__name__)

# Sidecars that may exist for any document; delete_file is a no-op on missing keys.
_SIDECAR_PREFIXES = ("toc", "text", "links", "words")


def compute_expires_at(
    created_at: datetime,
    retention_policy: str,
) -> Optional[datetime]:
    """Return the UTC expiry datetime for a document, or None for 'never'."""
    days = RETENTION_DAYS.get(retention_policy)
    if days is None:
        return None
    base = created_at if created_at.tzinfo else created_at.replace(tzinfo=timezone.utc)
    return base + timedelta(days=days)


async def delete_document_storage(
    doc_id: str,
    storage_key: str,
    storage,
) -> dict:
    """Delete all S3/R2 objects for a document.

    Deletes:
      - page images           pages/{doc_id}/*
      - thumbnails            thumbs/{doc_id}/*
      - original file         storage_key  (e.g. originals/{doc_id}.pdf)
      - TOC sidecar           toc/{doc_id}.json
      - text sidecar          text/{doc_id}.json
      - hyperlinks sidecar    links/{doc_id}.json
      - word positions sidecar words/{doc_id}.json

    Returns a summary dict for audit logging.

    Raises:
      Any StorageBackend exception propagates — callers decide whether to
      continue or abort.  NoSuchKey for individual files is swallowed by
      StorageService.delete_file() and therefore does not raise here.
    """
    deleted_pages = 0
    deleted_thumbs = 0
    deleted_sidecars = 0

    page_keys = await storage.list_keys_with_prefix(f"pages/{doc_id}/")
    for key in page_keys:
        await storage.delete_file(key)
        deleted_pages += 1

    thumb_keys = await storage.list_keys_with_prefix(f"thumbs/{doc_id}/")
    for key in thumb_keys:
        await storage.delete_file(key)
        deleted_thumbs += 1

    for prefix in _SIDECAR_PREFIXES:
        sidecar_key = f"{prefix}/{doc_id}.json"
        await storage.delete_file(sidecar_key)
        deleted_sidecars += 1

    await storage.delete_file(storage_key)

    summary = {
        "doc_id": doc_id,
        "original_key": storage_key,
        "deleted_pages": deleted_pages,
        "deleted_thumbs": deleted_thumbs,
        "deleted_sidecars": deleted_sidecars,
    }
    logger.info(
        "storage_delete doc_id=%s pages=%d thumbs=%d sidecars=%d original=%s",
        doc_id, deleted_pages, deleted_thumbs, deleted_sidecars, storage_key,
    )
    return summary


async def expire_and_delete_documents(
    db,
    storage,
    dry_run: bool = False,
) -> dict:
    """Find documents past their retention date, mark them expired, then delete.

    Two-phase within a single run:

    Phase 1 — Mark expired:
        Find docs with lifecycle_state IN ('active', 'archived') AND
        expires_at IS NOT NULL AND expires_at < NOW().
        Set lifecycle_state = 'expired'.

    Phase 2 — Delete storage + DB row:
        Find all docs with lifecycle_state = 'expired'.
        Delete storage files, then delete the DB row (cascades to all children).

    Cascade children (deleted automatically by PostgreSQL/SQLite):
        document_pages, share_links → access_events, viewer_sessions,
        viewer_annotations, viewer_bookmarks

    Args:
        dry_run: When True, identify what would be deleted but make no changes.

    Returns:
        {"marked_expired": N, "deleted": N, "errors": [...], "dry_run": bool}
    """
    from sqlalchemy import select
    from app.models.document import Document
    from app.services.viewer_cache import invalidate_doc_entries
    from app.services.page_cache import clear_doc_bytes

    now = datetime.now(timezone.utc)
    marked = 0
    deleted = 0
    errors = []

    # ── Phase 1: mark expired ─────────────────────────────────────────────────
    candidates = (
        await db.execute(
            select(Document).where(
                Document.lifecycle_state.in_(("active", "archived")),
                Document.expires_at.isnot(None),
                Document.expires_at < now,
            )
        )
    ).scalars().all()

    for doc in candidates:
        logger.info(
            "retention_expire doc_id=%s filename=%r expires_at=%s dry_run=%s",
            doc.id, doc.filename, doc.expires_at, dry_run,
        )
        if not dry_run:
            doc.lifecycle_state = "expired"
            marked += 1

    if not dry_run and marked:
        await db.commit()

    # ── Phase 2: delete expired ───────────────────────────────────────────────
    expired_docs = (
        await db.execute(
            select(Document).where(Document.lifecycle_state == "expired")
        )
    ).scalars().all()

    # Extract all data from ORM objects into plain dicts BEFORE the loop.
    # A rollback in one iteration expires ALL session objects; accessing their
    # attributes afterwards triggers lazy-loading in the wrong async context
    # and raises MissingGreenlet.
    expired_doc_data = [
        {
            "id": doc.id,
            "id_str": str(doc.id),
            "filename": doc.filename,
            "storage_key": doc.storage_key,
        }
        for doc in expired_docs
    ]

    for data in expired_doc_data:
        doc_id_str = data["id_str"]
        doc_filename = data["filename"]
        doc_storage_key = data["storage_key"]

        logger.info(
            "retention_delete doc_id=%s filename=%r dry_run=%s",
            doc_id_str, doc_filename, dry_run,
        )
        if dry_run:
            deleted += 1
            continue

        _db_write_started = False
        try:
            # Invalidate all caches before storage deletion (non-fatal)
            try:
                invalidate_doc_entries(doc_id_str, storage_key=doc_storage_key)
                await clear_doc_bytes(doc_id_str)
            except Exception as _cache_exc:
                logger.debug("cache invalidation failed for %s (non-fatal): %s", doc_id_str, _cache_exc)

            await delete_document_storage(doc_id_str, doc_storage_key, storage)

            # Re-fetch the ORM object so db.delete() triggers cascade (share_links etc.)
            # and mark that we've started a DB write for correct rollback handling.
            _db_write_started = True
            doc_obj = await db.get(Document, data["id"])
            if doc_obj:
                await db.delete(doc_obj)
            await db.commit()
            deleted += 1

        except Exception as exc:
            logger.error(
                "retention_delete_error doc_id=%s error=%s",
                doc_id_str, exc,
            )
            errors.append({"doc_id": doc_id_str, "error": str(exc)})
            if _db_write_started:
                # Only rollback if a DB write was started; rolling back a
                # write-free session can corrupt the aiosqlite connection state.
                try:
                    await db.rollback()
                except Exception:
                    pass

    return {
        "marked_expired": marked,
        "deleted": deleted,
        "errors": errors,
        "dry_run": dry_run,
    }
