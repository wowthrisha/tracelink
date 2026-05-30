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
from app.utils.crypto import hash_password
from app.config import settings
from app.auth import get_current_user

router = APIRouter(prefix="/api/links", tags=["links"])
link_svc = LinkService()


def _link_to_summary(link: ShareLink, request: Request) -> LinkSummary:
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

    return LinkSummary(
        id=link.id,
        token=link.token,
        share_url=f"{settings.app_public_base_url}/v/{link.token}",
        label=link.label,
        expires_at=link.expires_at,
        max_views=link.max_views,
        view_count=link.view_count,
        revoked_at=link.revoked_at,
        created_at=link.created_at,
        is_active=is_active,
        has_password=link.password_hash is not None,
        permissions=permissions,
    )


@router.post("", status_code=201, response_model=LinkResponse)
async def create_link(
    request: Request,
    payload: LinkCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
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

    return LinkResponse(
        id=link.id,
        token=link.token,
        share_url=f"{settings.app_public_base_url}/v/{link.token}",
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
    user: dict = Depends(get_current_user),
):
    # Verify document belongs to this user
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == uuid.UUID(user["user_id"]),
        )
    )
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    result = await db.execute(
        select(ShareLink)
        .where(ShareLink.document_id == document_id)
        .order_by(ShareLink.created_at.desc())
    )
    links = result.scalars().all()
    return {"links": [_link_to_summary(l, request) for l in links]}


@router.delete("/{link_id}", response_model=RevokeResponse)
async def revoke_link(
    link_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
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
    return RevokeResponse(
        id=revoked.id,
        revoked_at=revoked.revoked_at,
        message="Link revoked",
    )


@router.patch("/{link_id}", response_model=LinkSummary)
async def update_link(
    request: Request,
    link_id: uuid.UUID,
    payload: LinkUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
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
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized")

    if payload.label is not None:
        link.label = payload.label
    if payload.expires_at is not None:
        link.expires_at = payload.expires_at
    if payload.max_views is not None:
        link.max_views = payload.max_views
    if payload.allowed_emails is not None:
        link.allowed_emails = json.dumps([e.lower().strip() for e in payload.allowed_emails if e.strip()])
    if payload.allowed_domains is not None:
        link.allowed_domains = json.dumps([d.strip().lower() for d in payload.allowed_domains if d.strip()])
    if payload.ip_allowlist is not None:
        link.ip_allowlist = json.dumps([ip.strip() for ip in payload.ip_allowlist if ip.strip()]) if payload.ip_allowlist else None
    if payload.max_concurrent_sessions is not None:
        link.max_concurrent_sessions = payload.max_concurrent_sessions
    if payload.permissions is not None:
        link.permissions = json.dumps(payload.permissions)

    if "password" in payload.model_fields_set:
        if payload.password is not None:
            link.password_hash = hash_password(payload.password)
        else:
            link.password_hash = None

    await db.commit()
    await db.refresh(link)
    return _link_to_summary(link, request)
