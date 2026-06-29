import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.link import ShareLink
from app.models.document import Document
from app.schemas.link import (
    LinkCreateRequest,
    LinkUpdateRequest,
    LinkResponse,
    LinkSummary,
    RevokeResponse,
)
from app.services.link_service import LinkService
from app.services.viewer_cache import invalidate_link
from app.utils.crypto import hash_password
from app.config import settings
from app.auth import get_current_user, require_scope

router = APIRouter(prefix="/api/links", tags=["links"])
link_svc = LinkService()


async def _get_base_url_for_doc(doc: Document, db) -> str:
    """Return the share-link base URL, preferring the org's verified custom domain."""
    if doc.org_id is not None:
        try:
            from app.models.org import Organization
            org_result = await db.get(Organization, doc.org_id)
            if org_result and org_result.custom_domain_verified and org_result.custom_domain:
                return f"https://{org_result.custom_domain}"
        except Exception:
            pass
    return settings.app_public_base_url


def _link_to_summary(link: ShareLink, base_url: str = "") -> LinkSummary:
    now = datetime.now(timezone.utc)
    expires = link.expires_at
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    is_active = (
        link.revoked_at is None
        and (expires is None or expires > now)
        and (link.max_views is None or link.view_count < link.max_views)
    )
    
    permissions = None
    if link.permissions:
        try:
            permissions = json.loads(link.permissions)
        except Exception:
            pass

    def _parse_json_list(val) -> list | None:
        if val is None:
            return None
        try:
            return json.loads(val) if isinstance(val, str) else val
        except Exception:
            return None

    url_base = base_url or settings.app_public_base_url
    return LinkSummary(
        id=link.id,
        token=link.token,
        share_url=f"{url_base}/v/{link.token}",
        label=link.label,
        expires_at=link.expires_at,
        max_views=link.max_views,
        max_concurrent_sessions=link.max_concurrent_sessions,
        view_count=link.view_count,
        revoked_at=link.revoked_at,
        created_at=link.created_at,
        is_active=is_active,
        has_password=link.password_hash is not None,
        permissions=permissions,
        allowed_emails=_parse_json_list(link.allowed_emails),
        allowed_domains=_parse_json_list(link.allowed_domains),
        ip_allowlist=_parse_json_list(link.ip_allowlist),
    )


@router.post("", status_code=201, response_model=LinkResponse)
async def create_link(
    request: Request,
    payload: LinkCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("links:write")),
):
    # Verify document exists and belongs to this user
    doc_result = await db.execute(
        select(Document).where(
            Document.id == payload.document_id,
            Document.user_id == uuid.UUID(user["user_id"]),
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    link = await link_svc.create_link(
        db=db,
        document_id=str(payload.document_id),
        label=payload.label,
        password=payload.password,
        allowed_emails=payload.allowed_emails,
        allowed_domains=payload.allowed_domains,
        ip_allowlist=payload.ip_allowlist,
        max_views=payload.max_views,
        max_concurrent_sessions=payload.max_concurrent_sessions,
        expires_at=payload.expires_at,
        permissions=payload.permissions,
        created_by=uuid.UUID(user["user_id"]),
    )

    try:
        from app.services.audit_service import log_audit_event as _log_audit
        await _log_audit(
            db,
            event_type="link.created",
            actor_user_id=user["user_id"],
            target_type="link",
            target_id=str(link.id),
            details={
                "document_id": str(link.document_id),
                "token_prefix": link.token[:8] + "...",
                "label": link.label,
            },
        )
    except Exception:
        pass

    base_url = await _get_base_url_for_doc(doc, db)
    return LinkResponse(
        id=link.id,
        token=link.token,
        share_url=f"{base_url}/v/{link.token}",
        label=link.label,
        expires_at=link.expires_at,
        max_views=link.max_views,
        view_count=link.view_count,
        created_at=link.created_at,
    )


@router.get("", response_model=dict)
async def list_links(
    request: Request,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("links:read")),
):
    # Verify document belongs to this user; reuse result for URL generation
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == uuid.UUID(user["user_id"]),
        )
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    result = await db.execute(
        select(ShareLink)
        .where(ShareLink.document_id == document_id)
        .order_by(ShareLink.created_at.desc())
    )
    links = result.scalars().all()
    base_url = await _get_base_url_for_doc(doc, db)
    return {"links": [_link_to_summary(l, base_url) for l in links]}


@router.delete("/{link_id}", response_model=RevokeResponse)
async def revoke_link(
    link_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("links:write")),
):
    # Fetch link and verify its document belongs to this user
    link_result = await db.execute(select(ShareLink).where(ShareLink.id == link_id))
    link = link_result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    doc_result = await db.execute(
        select(Document).where(
            Document.id == link.document_id,
            Document.user_id == uuid.UUID(user["user_id"]),
        )
    )
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized")

    revoked = await link_svc.revoke_link(db, str(link_id))

    # Audit log: link.revoked
    try:
        from app.services.audit_service import log_audit_event as _log_audit
        await _log_audit(
            db,
            event_type="link.revoked",
            actor_user_id=user["user_id"],
            target_type="link",
            target_id=str(link_id),
            details={"document_id": str(revoked.document_id), "token": revoked.token[:8] + "..."},
        )
    except Exception:
        pass

    return RevokeResponse(
        id=revoked.id,
        revoked_at=revoked.revoked_at,
        message="Link revoked",
    )


@router.patch("/{link_id}", response_model=LinkSummary)
async def update_link(
    link_id: uuid.UUID,
    payload: LinkUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("links:write")),
):
    result = await db.execute(select(ShareLink).where(ShareLink.id == link_id))
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    doc_result = await db.execute(
        select(Document).where(
            Document.id == link.document_id,
            Document.user_id == uuid.UUID(user["user_id"]),
        )
    )
    doc_for_patch = doc_result.scalar_one_or_none()
    if not doc_for_patch:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Use model_fields_set so that explicitly-null values CLEAR the field,
    # while absent fields leave existing values untouched.
    if "label" in payload.model_fields_set:
        link.label = payload.label
    if "expires_at" in payload.model_fields_set:
        link.expires_at = payload.expires_at
    if "max_views" in payload.model_fields_set:
        link.max_views = payload.max_views
    if "max_concurrent_sessions" in payload.model_fields_set:
        link.max_concurrent_sessions = payload.max_concurrent_sessions
    if "allowed_emails" in payload.model_fields_set:
        link.allowed_emails = (
            json.dumps([e.lower().strip() for e in payload.allowed_emails if e.strip()])
            if payload.allowed_emails else None
        )
    if "allowed_domains" in payload.model_fields_set:
        link.allowed_domains = (
            json.dumps([d.strip().lower() for d in payload.allowed_domains if d.strip()])
            if payload.allowed_domains else None
        )
    if "ip_allowlist" in payload.model_fields_set:
        link.ip_allowlist = (
            json.dumps([ip.strip() for ip in payload.ip_allowlist if ip.strip()])
            if payload.ip_allowlist else None
        )
    if "permissions" in payload.model_fields_set and payload.permissions is not None:
        link.permissions = json.dumps(payload.permissions)
    if "password" in payload.model_fields_set:
        if payload.password is not None:
            link.password_hash = hash_password(payload.password)
        else:
            link.password_hash = None

    await db.commit()
    await db.refresh(link)
    # Policy changes (email list, IP allowlist, expiry, revoke) must be visible
    # on the next viewer request — evict link snapshot AND all session cache
    # entries for this link so any active viewer re-validates against the DB.
    invalidate_link(link.token, link_id=link.id)

    try:
        from app.services.audit_service import log_audit_event as _log_audit
        await _log_audit(
            db,
            event_type="link.updated",
            actor_user_id=user["user_id"],
            target_type="link",
            target_id=str(link_id),
            details={
                "document_id": str(link.document_id),
                "token_prefix": link.token[:8] + "...",
                "changed": sorted(payload.model_fields_set),
            },
        )
    except Exception:
        pass

    base_url = await _get_base_url_for_doc(doc_for_patch, db)
    return _link_to_summary(link, base_url)


@router.delete("/{link_id}/hard", response_model=dict)
async def delete_link_permanently(
    link_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_scope("links:write")),
):
    """Permanently remove a revoked link and all its analytics from the database."""
    result = await db.execute(select(ShareLink).where(ShareLink.id == link_id))
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    doc_result = await db.execute(
        select(Document).where(
            Document.id == link.document_id,
            Document.user_id == uuid.UUID(user["user_id"]),
        )
    )
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized")

    if link.revoked_at is None:
        raise HTTPException(status_code=400, detail="Revoke the link before deleting it permanently")

    token = link.token
    invalidate_link(token, link_id=link.id)

    try:
        from app.services.audit_service import log_audit_event as _log_audit
        await _log_audit(
            db,
            event_type="link.deleted",
            actor_user_id=user["user_id"],
            target_type="link",
            target_id=str(link_id),
            details={"document_id": str(link.document_id), "token_prefix": token[:8] + "..."},
        )
    except Exception:
        pass

    await db.delete(link)
    await db.commit()
    return {"id": str(link_id), "deleted": True}
