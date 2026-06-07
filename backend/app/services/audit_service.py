import json
import logging
import uuid
from typing import Optional

from app.models.audit import AdminAuditLog

logger = logging.getLogger(__name__)


async def log_audit_event(
    db,
    actor_user_id: str,
    event_type: str,
    org_id: Optional[str] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    details: Optional[dict] = None,
    ip_hash: Optional[str] = None,
) -> None:
    """
    Write an immutable audit log entry.  Never raises — caller wraps in
    try/except to prevent audit failure from breaking the primary operation.
    """
    try:
        entry = AdminAuditLog(
            actor_user_id=uuid.UUID(actor_user_id),
            event_type=event_type,
            org_id=uuid.UUID(org_id) if org_id else None,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            details_json=json.dumps(details, default=str) if details else None,
            ip_hash=ip_hash,
        )
        db.add(entry)
        await db.flush()
    except Exception as exc:
        logger.error("audit_service: failed to log %s: %s", event_type, exc)
