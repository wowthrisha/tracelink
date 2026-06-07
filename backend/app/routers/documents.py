import asyncio
import logging
import os
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

logger = logging.getLogger(__name__)

from app.database import get_db
from app.models.document import Document, DocumentPage
from app.models.group import DocumentGroup
from app.models.link import ShareLink
from app.models.event import AccessEvent
from app.schemas.document import (
    DocumentUploadResponse,
    DocumentSummary,
    DocumentDetail,
    DocumentPageMeta,
    DocumentStatusResponse,
)
from app.services.storage import get_storage_service
from app.config import settings
from app.middleware.rate_limit import limiter
from app.auth import get_current_user, require_scope
from app.models.billing import UserBilling, PLAN_PRO

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Content-types accepted at the upload boundary.
# Extension-based detection (in detect_file_type) is the primary signal.
# The set is derived from registered adapters; application/octet-stream is
# added as a browser pass-through for files with ambiguous content types.
from app.services.adapters import allowed_content_types as _adapter_content_types
ALLOWED_CONTENT_TYPES = _adapter_content_types() | {"application/octet-stream"}


async def _run_demo_processing(document_id: str) -> None:
    """
    Process a document entirely in-process (no Celery / Redis).
    Only used when USE_DEMO_STORAGE=1.  Runs as a background asyncio task so
    the upload response is returned immediately.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from app.config import settings
    from app.services.storage import get_storage_service
    from app.services.rasterizer import RasterizerService
    from app.services.watermark import WatermarkService
    from app.workers.tasks import process_document_with_session

    engine = create_async_engine(settings.database_url, echo=False)
    _sf = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with _sf() as db:
            await process_document_with_session(
                db,
                document_id,
                get_storage_service(),
                RasterizerService(),
                WatermarkService(),
            )
    except Exception as exc:
        logger.error("Demo-mode rendering failed for document %s: %s", document_id, exc)
    finally:
        await engine.dispose()


async def _check_upload_quota(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Raise 403 if the user has hit the document upload limit.

    Pro access is only granted when the subscription is in an active or trialing
    state.  A past_due or canceled subscription falls back to the free-plan limit.
    """
    from app.models.billing import STATUS_ACTIVE, STATUS_TRIALING
    limit = settings.free_plan_doc_limit
    if limit <= 0:
        return  # 0 means unlimited

    billing_result = await db.execute(
        select(UserBilling).where(UserBilling.user_id == user_id)
    )
    billing = billing_result.scalar_one_or_none()
    if (
        billing
        and billing.plan == PLAN_PRO
        and billing.subscription_status in (STATUS_ACTIVE, STATUS_TRIALING)
    ):
        return  # Active Pro users have no limit

    count_result = await db.execute(
        select(func.count()).select_from(Document).where(Document.user_id == user_id)
    )
    count = count_result.scalar() or 0
    if count >= limit:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Free plan allows up to {limit} documents. "
                "Upgrade to Pro to upload more."
            ),
        )


@router.post("/upload", status_code=202)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    filename: Optional[str] = Form(None),
    group_id: Optional[str] = Form(None),
    parent_document_id: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("documents:write")),
):
    user_uuid = uuid.UUID(user["user_id"])

    # Check free-plan document quota before accepting the upload
    await _check_upload_quota(db, user_uuid)

    from app.services.text_processor import detect_file_type
    from app.services.adapters import get_adapter as _get_adapter

    # Reject obviously unsupported content-types upfront (before reading bytes)
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Supported: .pdf, .docx, .doc, .txt, .md, .log",
        )

    file_bytes = await file.read()

    # Determine file type — extension-first, content-type fallback
    original_filename = filename or file.filename or "document"
    try:
        file_type = detect_file_type(original_filename, file.content_type or "", file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Size and format validation via adapter
    _adapter = _get_adapter(file_type)
    if len(file_bytes) > _adapter.max_upload_bytes():
        raise HTTPException(status_code=413, detail=_adapter.size_exceeded_message())
    try:
        _adapter.validate_bytes(file_bytes, original_filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    doc_id = uuid.uuid4()
    storage_key = f"originals/{doc_id}.{file_type}"
    # Provide sensible default extension in filename if none given
    if "." not in original_filename:
        original_filename = f"{original_filename}.{file_type}"

    # Validate group_id if provided (must belong to this user)
    resolved_group_id = None
    if group_id:
        try:
            gid = uuid.UUID(group_id)
            grp_result = await db.execute(
                select(DocumentGroup).where(
                    DocumentGroup.id == gid,
                    DocumentGroup.user_id == user_uuid,
                )
            )
            if not grp_result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="Group not found")
            resolved_group_id = gid
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid group_id format")

    storage = get_storage_service()
    try:
        await storage.upload_file(
            file_bytes, storage_key, content_type=_adapter.content_type_for_storage()
        )
    except Exception as exc:
        logger.error("Storage upload failed for key %s: %s", storage_key, exc)
        raise HTTPException(status_code=502, detail="Storage upload failed. Please try again.")

    # Version chain: validate and resolve parent_document_id
    resolved_parent_id = None
    doc_version = 1
    if parent_document_id:
        try:
            parent_uuid = uuid.UUID(parent_document_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid parent_document_id format")
        parent_result = await db.execute(
            select(Document).where(
                Document.id == parent_uuid,
                Document.user_id == user_uuid,
            )
        )
        parent_doc = parent_result.scalar_one_or_none()
        if not parent_doc:
            raise HTTPException(status_code=404, detail="Parent document not found")
        resolved_parent_id = parent_uuid
        doc_version = (parent_doc.version or 1) + 1

    doc = Document(
        id=doc_id,
        filename=original_filename,
        storage_key=storage_key,
        status="uploaded",
        file_type=file_type,
        file_size_bytes=len(file_bytes),
        group_id=resolved_group_id,
        user_id=user_uuid,
        version=doc_version,
        parent_document_id=resolved_parent_id,
    )
    db.add(doc)
    await db.commit()
    logger.info("Document %s uploaded by user %s (%s)", doc_id, user_uuid, original_filename)

    # Trigger processing: demo mode runs in-process; production queues a Celery task
    if os.getenv("USE_DEMO_STORAGE") == "1":
        logger.info("Demo mode: scheduling in-process rendering for document %s", doc_id)
        asyncio.create_task(_run_demo_processing(str(doc_id)))
    else:
        try:
            from app.workers.tasks import process_document
            process_document.delay(str(doc_id))
            logger.info("Queued Celery task securedoc.process_document for document %s", doc_id)
        except Exception as celery_exc:
            logger.error(
                "Failed to queue Celery task for document %s: %s — "
                "document will remain in 'uploaded' state until a worker picks it up",
                doc_id,
                celery_exc,
            )

    return DocumentUploadResponse(
        id=doc_id,
        filename=original_filename,
        status="uploaded",
        message="Processing started",
    )


@router.post("/{document_id}/reprocess", status_code=202)
async def reprocess_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("documents:write")),
):
    user_uuid = uuid.UUID(user["user_id"])
    try:
        doc_id = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    result = await db.execute(
        select(Document).where(Document.id == doc_id, Document.user_id == user_uuid)
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status == "ready":
        raise HTTPException(status_code=400, detail="Document is already processed")

    doc.status = "uploaded"
    doc.error_message = None
    await db.commit()

    if os.getenv("USE_DEMO_STORAGE") == "1":
        asyncio.create_task(_run_demo_processing(str(doc_id)))
    else:
        try:
            from app.workers.tasks import process_document
            process_document.delay(str(doc_id))
            logger.info("Requeued Celery task for document %s", doc_id)
        except Exception as celery_exc:
            logger.error("Failed to requeue document %s: %s", doc_id, celery_exc)

    return {"id": str(doc_id), "status": "uploaded", "message": "Reprocessing started"}


@router.get("", response_model=dict)
async def list_documents(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("documents:read")),
):
    from sqlalchemy import or_ as _or
    user_uuid = uuid.UUID(user["user_id"])

    # Find all orgs the user is a member of (for org-scoped document visibility)
    from app.models.org import OrgMembership as _OrgMembership
    org_result = await db.execute(
        select(_OrgMembership.org_id).where(_OrgMembership.user_id == user_uuid)
    )
    org_ids = [row.org_id for row in org_result.all()]

    # Return user-owned documents PLUS org documents the user has access to
    if org_ids:
        result = await db.execute(
            select(Document)
            .where(_or(
                Document.user_id == user_uuid,
                Document.org_id.in_(org_ids),
            ))
            .order_by(Document.created_at.desc())
        )
    else:
        result = await db.execute(
            select(Document)
            .where(Document.user_id == user_uuid)
            .order_by(Document.created_at.desc())
        )
    documents = result.scalars().all()

    if not documents:
        return {"documents": []}

    doc_ids = [doc.id for doc in documents]

    # Batch: link counts per document (1 query)
    link_counts_result = await db.execute(
        select(ShareLink.document_id, func.count(ShareLink.id).label("cnt"))
        .where(ShareLink.document_id.in_(doc_ids))
        .group_by(ShareLink.document_id)
    )
    link_counts: dict = {row.document_id: row.cnt for row in link_counts_result.all()}

    # Batch: view counts per document via JOIN (1 query)
    views_result = await db.execute(
        select(ShareLink.document_id, func.count(AccessEvent.id).label("cnt"))
        .join(
            AccessEvent,
            (AccessEvent.link_id == ShareLink.id) & (AccessEvent.event_type == "opened"),
        )
        .where(ShareLink.document_id.in_(doc_ids))
        .group_by(ShareLink.document_id)
    )
    view_counts: dict = {row.document_id: row.cnt for row in views_result.all()}

    # Batch: group info for all referenced groups (1 query)
    group_ids = {doc.group_id for doc in documents if doc.group_id}
    groups: dict = {}
    if group_ids:
        grp_result = await db.execute(
            select(DocumentGroup).where(DocumentGroup.id.in_(group_ids))
        )
        groups = {grp.id: grp for grp in grp_result.scalars().all()}

    summaries = []
    for doc in documents:
        grp = groups.get(doc.group_id) if doc.group_id else None
        summaries.append(
            DocumentSummary(
                id=doc.id,
                filename=doc.filename,
                status=doc.status,
                page_count=doc.page_count,
                file_size_bytes=doc.file_size_bytes,
                created_at=doc.created_at,
                share_link_count=link_counts.get(doc.id, 0),
                total_views=view_counts.get(doc.id, 0),
                group_id=doc.group_id,
                group_name=grp.name if grp else None,
                group_color=grp.color if grp else None,
            )
        )

    return {"documents": summaries}


async def _get_accessible_document(
    document_id: uuid.UUID, user: dict, db
) -> Document:
    """Return document if user owns it or is a member of the document's org."""
    from sqlalchemy import or_ as _or
    from app.models.org import OrgMembership as _OrgMembership
    user_uuid = uuid.UUID(user["user_id"])

    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.user_id == user_uuid:
        return doc

    # Check org membership for org-owned documents
    if doc.org_id:
        m_result = await db.execute(
            select(_OrgMembership).where(
                _OrgMembership.org_id == doc.org_id,
                _OrgMembership.user_id == user_uuid,
            )
        )
        if m_result.scalar_one_or_none():
            return doc

    raise HTTPException(status_code=404, detail="Document not found")


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_document_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("documents:read")),
):
    doc = await _get_accessible_document(document_id, user, db)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentStatusResponse(
        status=doc.status,
        page_count=doc.page_count,
        error_message=doc.error_message,
    )


@router.get("/{document_id}", response_model=dict)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("documents:read")),
):
    doc = await _get_accessible_document(document_id, user, db)

    # Link count + view count in a single JOIN query
    stats_result = await db.execute(
        select(
            func.count(ShareLink.id.distinct()).label("link_count"),
            func.count(AccessEvent.id).label("view_count"),
        )
        .select_from(ShareLink)
        .outerjoin(
            AccessEvent,
            (AccessEvent.link_id == ShareLink.id) & (AccessEvent.event_type == "opened"),
        )
        .where(ShareLink.document_id == doc.id)
    )
    stats_row = stats_result.one()
    share_link_count = stats_row.link_count or 0
    total_views = stats_row.view_count or 0

    pages_result = await db.execute(
        select(DocumentPage)
        .where(DocumentPage.document_id == doc.id)
        .order_by(DocumentPage.page_number)
    )
    pages = pages_result.scalars().all()

    # Fetch group info
    group_name = None
    group_color = None
    if doc.group_id:
        grp_result = await db.execute(
            select(DocumentGroup).where(DocumentGroup.id == doc.group_id)
        )
        grp = grp_result.scalar_one_or_none()
        if grp:
            group_name = grp.name
            group_color = grp.color

    detail = DocumentDetail(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        page_count=doc.page_count,
        file_size_bytes=doc.file_size_bytes,
        created_at=doc.created_at,
        share_link_count=share_link_count,
        total_views=total_views,
        group_id=doc.group_id,
        group_name=group_name,
        group_color=group_color,
        pages=[
            DocumentPageMeta(
                page_number=p.page_number,
                width_px=p.width_px,
                height_px=p.height_px,
            )
            for p in pages
        ],
    )
    return detail.model_dump()


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("documents:write")),
):
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == uuid.UUID(user["user_id"]),
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    storage = get_storage_service()

    # Invalidate all cache tiers for this document before removing from storage.
    # Metadata caches (link/doc/page snapshots) + text/chunk caches:
    from app.services.viewer_cache import invalidate_doc_entries
    invalidate_doc_entries(str(document_id), storage_key=doc.storage_key)
    # L1 + L2 byte caches (page images and thumbnails):
    from app.services.page_cache import clear_doc_bytes
    await clear_doc_bytes(str(document_id))
    logger.info("cache_invalidate doc_id=%s all_tiers=true", document_id)

    # Delete page images
    page_keys = await storage.list_keys_with_prefix(f"pages/{document_id}/")
    for key in page_keys:
        await storage.delete_file(key)

    # Delete thumbnails
    thumb_keys = await storage.list_keys_with_prefix(f"thumbs/{document_id}/")
    for key in thumb_keys:
        await storage.delete_file(key)

    # Delete original
    await storage.delete_file(doc.storage_key)

    doc_filename = doc.filename
    doc_id_str = str(document_id)
    await db.delete(doc)
    await db.commit()

    # Audit log: document.deleted
    try:
        from app.services.audit_service import log_audit_event as _log_audit
        await _log_audit(
            db,
            event_type="document.deleted",
            actor_user_id=user["user_id"],
            target_type="document",
            target_id=doc_id_str,
            details={"filename": doc_filename},
        )
    except Exception:
        pass


@router.get("/{document_id}/versions")
async def get_document_versions(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("documents:read")),
):
    """Return the full version chain for a document, ordered oldest → newest.

    Uses a two-step recursive CTE to resolve the entire chain in a single DB
    round-trip (O(1) queries regardless of chain depth), replacing the former
    N+1 walk-to-root + collect-descendants loop.
    """
    from sqlalchemy import text as _text

    user_uuid = uuid.UUID(user["user_id"])

    # Confirm caller owns this document (ownership check on the entry point)
    ownership_result = await db.execute(
        select(Document.id).where(
            Document.id == document_id,
            Document.user_id == user_uuid,
        )
    )
    if not ownership_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    # Single recursive CTE query:
    #   Step 1 (ancestors): walk UP the chain from doc_id to find the root
    #   Step 2 (root_doc): pick the ancestor with no parent (= chain root)
    #   Step 3 (chain): collect ALL descendants from the root downward
    # PostgreSQL and SQLite both support WITH RECURSIVE.
    cte_query = _text("""
        WITH RECURSIVE ancestors AS (
            SELECT id, parent_document_id
            FROM documents
            WHERE id = :doc_id
            UNION ALL
            SELECT d.id, d.parent_document_id
            FROM documents d
            JOIN ancestors a ON d.id = a.parent_document_id
            WHERE a.parent_document_id IS NOT NULL
        ),
        root_doc AS (
            SELECT id FROM ancestors
            WHERE parent_document_id IS NULL
            LIMIT 1
        ),
        chain AS (
            SELECT d.id, d.parent_document_id, d.filename, d.version,
                   d.status, d.page_count, d.file_type, d.created_at
            FROM documents d
            JOIN root_doc ON d.id = root_doc.id
            UNION ALL
            SELECT d.id, d.parent_document_id, d.filename, d.version,
                   d.status, d.page_count, d.file_type, d.created_at
            FROM documents d
            JOIN chain c ON d.parent_document_id = c.id
        )
        SELECT id, filename, version, status, page_count, file_type, created_at
        FROM chain
        ORDER BY version
    """)

    result = await db.execute(cte_query, {"doc_id": str(document_id)})
    rows = result.fetchall()

    return {
        "versions": [
            {
                "id": str(row.id),
                "filename": row.filename,
                "version": row.version,
                "status": row.status,
                "page_count": row.page_count,
                "file_type": row.file_type or "pdf",
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }
