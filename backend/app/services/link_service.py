import json
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.link import ShareLink
from app.utils.crypto import hash_password, verify_password, hash_value, mask_email
from app.services.policy import enforcer

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    link: ShareLink
    is_valid: bool
    session_id: str


class LinkService:
    async def create_link(
        self,
        db: AsyncSession,
        document_id: str,
        label: Optional[str] = None,
        password: Optional[str] = None,
        allowed_emails: Optional[List[str]] = None,
        allowed_domains: Optional[List[str]] = None,
        ip_allowlist: Optional[List[str]] = None,
        max_views: Optional[int] = None,
        max_concurrent_sessions: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        permissions: Optional[dict] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> ShareLink:
        token = secrets.token_urlsafe(48)[:64]

        pw_hash = hash_password(password) if password else None
        emails_json = (
            json.dumps([e.lower().strip() for e in allowed_emails if e.strip()])
            if allowed_emails
            else None
        )
        # Domains are lowercased at storage time to ensure consistent case-insensitive matching
        domains_json = (
            json.dumps([d.strip().lower() for d in allowed_domains if d.strip()])
            if allowed_domains
            else None
        )
        ip_json = (
            json.dumps([ip.strip() for ip in ip_allowlist if ip.strip()])
            if ip_allowlist
            else None
        )
        permissions_json = json.dumps(permissions) if permissions else None

        link = ShareLink(
            document_id=uuid.UUID(document_id) if isinstance(document_id, str) else document_id,
            token=token,
            label=label,
            password_hash=pw_hash,
            allowed_emails=emails_json,
            allowed_domains=domains_json,
            ip_allowlist=ip_json,
            permissions=permissions_json,
            max_views=max_views,
            max_concurrent_sessions=max_concurrent_sessions,
            expires_at=expires_at,
            created_by=created_by,
        )
        db.add(link)
        await db.commit()
        await db.refresh(link)
        return link

    async def validate_link(
        self,
        db: AsyncSession,
        token: str,
        password: Optional[str] = None,
        viewer_email: Optional[str] = None,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        analytics_svc=None,
        existing_session_id: Optional[str] = None,
        commit: bool = True,
    ) -> ValidationResult:
        from app.services.analytics_service import AnalyticsService

        if analytics_svc is None:
            analytics_svc = AnalyticsService()

        # 1. Link exists
        result = await db.execute(select(ShareLink).where(ShareLink.token == token))
        link = result.scalar_one_or_none()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")

        now = datetime.now(timezone.utc)

        # 2. Not revoked
        if link.revoked_at is not None:
            await analytics_svc.log_event(db, link.id, "revoked", ip=ip, user_agent=user_agent)
            raise HTTPException(status_code=410, detail="Link revoked")

        # 3. Not expired
        if link.expires_at is not None:
            expires = link.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires < now:
                await analytics_svc.log_event(db, link.id, "expired", ip=ip, user_agent=user_agent)
                raise HTTPException(status_code=410, detail="Link expired")

        # 4. View count < max_views
        if link.max_views is not None and link.view_count >= link.max_views:
            await analytics_svc.log_event(
                db, link.id, "max_views_reached", ip=ip, user_agent=user_agent
            )
            raise HTTPException(status_code=410, detail="Max views reached")

        # 5. Password check
        if link.password_hash is not None:
            if not password or not verify_password(password, link.password_hash):
                await analytics_svc.log_event(
                    db, link.id, "password_wrong", ip=ip, user_agent=user_agent
                )
                raise HTTPException(
                    status_code=401,
                    detail="Wrong password" if password else "Password required",
                )

        # 6. Email allowlist check (exact match, case-insensitive)
        if link.allowed_emails:
            allowed = json.loads(link.allowed_emails)
            if not viewer_email or viewer_email.lower().strip() not in allowed:
                await analytics_svc.log_event(
                    db, link.id, "access_denied",
                    viewer_email=viewer_email, ip=ip, user_agent=user_agent,
                )
                raise HTTPException(status_code=403, detail="Access denied")

        # 7. Email-domain allowlist check (e.g. @acme.io)
        if link.allowed_domains:
            if not enforcer.email_domain_is_allowed(viewer_email, link.allowed_domains):
                await analytics_svc.log_event(
                    db, link.id, "access_denied",
                    viewer_email=viewer_email, ip=ip, user_agent=user_agent,
                )
                detail = (
                    "Email required to verify domain access"
                    if not viewer_email
                    else "Your email domain is not permitted"
                )
                raise HTTPException(status_code=403, detail=detail)

        # 8. IP allowlist check
        if link.ip_allowlist:
            if not enforcer.ip_is_allowed(ip, link.ip_allowlist):
                await analytics_svc.log_event(
                    db, link.id, "ip_blocked", ip=ip, user_agent=user_agent
                )
                raise HTTPException(status_code=403, detail="Access denied from this IP")

        # 9. Concurrent-session check
        #
        # Session identity: if the caller supplies an existing session_id (stored
        # by the browser in sessionStorage after a previous validate call), and that
        # session is still active for this link, we simply refresh it — no new slot
        # is consumed.  This allows the same browser tab to refresh the page without
        # eating into the concurrent-viewer budget.
        #
        # Different browsers / incognito windows have separate sessionStorage so they
        # always send no session_id on first load and receive a brand-new slot.

        is_session_reuse = False
        if existing_session_id:
            is_session_reuse = await enforcer.is_active_session(
                db, link.id, existing_session_id
            )
            if is_session_reuse:
                logger.info(
                    "[viewer] link=%s REUSE session=%s", link.id, existing_session_id
                )

        session_id = existing_session_id if is_session_reuse else self._generate_session_id()

        if link.max_concurrent_sessions is not None and not is_session_reuse:
            purged = await enforcer.purge_stale_sessions(db, link.id)
            if purged:
                logger.info("[viewer] link=%s purged %d stale session(s)", link.id, purged)

            active = await enforcer.active_session_count(db, link.id)
            logger.info(
                "[viewer] link=%s max_sessions=%d active_before=%d new_session=%s",
                link.id,
                link.max_concurrent_sessions,
                active,
                session_id,
            )

            if active >= link.max_concurrent_sessions:
                logger.warning(
                    "[viewer] link=%s DENY concurrent_limit_reached (active=%d max=%d)",
                    link.id,
                    active,
                    link.max_concurrent_sessions,
                )
                await analytics_svc.log_event(
                    db, link.id, "session_limit_reached", ip=ip, user_agent=user_agent
                )
                raise HTTPException(
                    status_code=403,
                    detail="Concurrent session limit reached. Try again later.",
                )

        # Create or refresh the session row
        ip_hash = hash_value(ip) if ip else None
        email_masked = mask_email(viewer_email) if viewer_email else None
        await enforcer.upsert_session(
            db, session_id, link.id,
            ip_hash=ip_hash,
            viewer_email_masked=email_masked,
        )
        if commit:
            await db.commit()

        return ValidationResult(link=link, is_valid=True, session_id=session_id)

    async def revoke_link(self, db: AsyncSession, link_id: str) -> ShareLink:
        result = await db.execute(
            select(ShareLink).where(ShareLink.id == uuid.UUID(link_id))
        )
        link = result.scalar_one_or_none()
        if not link:
            raise HTTPException(status_code=404, detail="Link not found")
        link.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(link)
        # Immediately evict from the viewer metadata cache so the next page
        # request does not serve a stale snapshot that still looks active.
        from app.services.viewer_cache import invalidate_link
        invalidate_link(link.token)
        return link

    async def increment_view_count(self, db: AsyncSession, link_id: str, commit: bool = True) -> None:
        await db.execute(
            update(ShareLink)
            .where(ShareLink.id == uuid.UUID(link_id))
            .values(view_count=ShareLink.view_count + 1)
        )
        if commit:
            await db.commit()

    def _generate_session_id(self) -> str:
        return secrets.token_hex(16)  # 32 hex chars = 128-bit entropy
