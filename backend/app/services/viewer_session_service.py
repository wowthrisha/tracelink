"""Link validation, session creation, and validate endpoint response builder."""
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.document import Document, DocumentPage
from app.services.policy import enforcer as policy_enforcer

logger = logging.getLogger(__name__)


async def build_validate_response(
    db: AsyncSession,
    body: dict,
    ip: Optional[str],
    user_agent: Optional[str],
    link_svc,
    analytics_svc,
) -> dict:
    """Run the full validate-link flow and return the JSON response payload.

    Stages (all flushed in a single DB commit via log_event commit=True):
      1. Link validation + session upsert (commit=False)
      2. Analytics 'opened' event (commit=True — flushes everything)
      3. Concurrency detection (warning-only, never blocks)
      4. Document metadata + page dimensions fetch
      5. Permissions build
      6. Webhook + SSE notifications (fire-and-forget)
    """
    token = body.get("token", "")
    password = body.get("password")
    viewer_email = body.get("email")
    existing_session_id = body.get("session_id") or None

    validation = await link_svc.validate_link(
        db=db,
        token=token,
        password=password,
        viewer_email=viewer_email,
        analytics_svc=analytics_svc,
        ip=ip,
        user_agent=user_agent,
        existing_session_id=existing_session_id,
        commit=False,
    )

    link = validation.link
    session_id = validation.session_id

    await analytics_svc.log_event(
        db,
        link_id=link.id,
        event_type="opened",
        viewer_email=viewer_email,
        ip=ip,
        user_agent=user_agent,
        session_id=session_id,
        commit=True,
    )

    try:
        if settings.max_concurrent_sessions_per_link > 0:
            _count = await policy_enforcer.active_session_count(db, link.id)
            if _count > settings.max_concurrent_sessions_per_link:
                logger.warning(
                    "high_concurrent_sessions link_id=%s count=%d threshold=%d",
                    link.id, _count, settings.max_concurrent_sessions_per_link,
                )
    except Exception:
        pass  # concurrency check must never block the validate response

    doc_result = await db.execute(select(Document).where(Document.id == link.document_id))
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    pages_meta: list = []
    if doc.status == "ready":
        pages_result = await db.execute(
            select(DocumentPage)
            .where(DocumentPage.document_id == doc.id)
            .order_by(DocumentPage.page_number)
        )
        pages_meta = [
            {"page_number": p.page_number, "width_px": p.width_px, "height_px": p.height_px}
            for p in pages_result.scalars().all()
        ]

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    watermark_text = f"{viewer_email or 'anonymous'} · {now_str} · sess:{session_id[:6]}"

    permissions_dict = {
        "can_download": False,
        "can_print": False,
        "can_copy": False,
        "can_right_click": False,
        "watermark_enabled": True,
        "can_annotate": False,
        "enable_info": True,
    }
    if link.permissions:
        try:
            stored_perms = json.loads(link.permissions)
            for k, v in stored_perms.items():
                if k in permissions_dict:
                    permissions_dict[k] = bool(v)
        except Exception:
            pass

    _link_viewed_data = {
        "document_id": str(doc.id),
        "filename": doc.filename,
        "link_id": str(link.id),
        "link_label": link.label,
        "session_id_prefix": session_id[:8] if session_id else None,
    }
    try:
        from app.services.webhook_service import dispatch_webhook_event as _dispatch_wh
        await _dispatch_wh(db, user_id=str(doc.user_id), event_type="link.viewed", data=_link_viewed_data)
    except Exception as _wh_exc:
        logger.warning("link.viewed webhook trigger failed: %s", _wh_exc)

    try:
        from app.services.notification_service import publish_notification as _pub_notif
        await _pub_notif(str(doc.user_id), "link.viewed", _link_viewed_data)
    except Exception as _notif_exc:
        logger.debug("link.viewed SSE notification failed: %s", _notif_exc)

    return {
        "session_id": session_id,
        "document_id": str(doc.id),
        "document_filename": doc.filename,
        "page_count": doc.page_count or 0,
        "doc_status": doc.status,
        "doc_type": getattr(doc, "file_type", "pdf") or "pdf",
        "watermark_text": watermark_text if permissions_dict.get("watermark_enabled", True) else None,
        "link_id": str(link.id),
        "expires_at": link.expires_at.isoformat() if link.expires_at else None,
        "permissions": permissions_dict,
        "pages": pages_meta,
    }
