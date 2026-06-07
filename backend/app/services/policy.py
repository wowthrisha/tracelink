"""
Centralised access-control validation engine.

All policy checks (IP allowlist, email-domain allowlist, concurrent sessions)
live here so both the validate endpoint and the page-delivery endpoint share
the same rules without duplicating logic.
"""
import ipaddress
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# A session not seen within this window is considered stale / disconnected.
SESSION_ACTIVE_MINUTES = 120

# Minimum interval between session heartbeat DB writes.  Writing on every page
# request creates ~100 writes/sec under load; throttling to 30-second intervals
# reduces that by 30× while keeping session expiry accurate within one period.
SESSION_HEARTBEAT_INTERVAL_SEC = 30


class PolicyEnforcer:

    # ── IP allowlist ──────────────────────────────────────────────────────────

    def ip_is_allowed(
        self, ip: Optional[str], allowlist_json: Optional[str]
    ) -> bool:
        """
        Return True when the request IP is permitted.

        Allowlist entries may be:
          - exact IPv4/IPv6 addresses: "192.168.1.1"
          - CIDR ranges:              "10.0.0.0/24", "2001:db8::/32"

        If the allowlist column is NULL / empty → open access (no restriction).
        If the allowlist JSON is malformed → fail CLOSED (deny) to prevent
        a data corruption bug from bypassing the allowlist silently.
        """
        if not allowlist_json:
            return True
        try:
            entries = [e.strip() for e in json.loads(allowlist_json) if e.strip()]
        except Exception:
            logger.error("ip_allowlist JSON parse failed — denying access (fail-closed)")
            return False  # malformed JSON → fail closed
        if not entries:
            return True
        if not ip:
            return False  # allowlist set but request has no IP → deny
        try:
            client = ipaddress.ip_address(ip)
        except ValueError:
            return False
        for entry in entries:
            try:
                if "/" in entry:
                    if client in ipaddress.ip_network(entry, strict=False):
                        return True
                else:
                    if client == ipaddress.ip_address(entry):
                        return True
            except ValueError:
                continue
        return False

    # ── Email-domain allowlist ────────────────────────────────────────────────

    def email_domain_is_allowed(
        self,
        viewer_email: Optional[str],
        allowed_domains_json: Optional[str],
    ) -> bool:
        """
        Return True when the viewer's email domain matches the allowlist.

        Stored format: JSON list of domains, optionally prefixed with '@'.
        Examples: ["acme.io", "@partner.com"]

        If no domains are configured → open access.
        If domains are configured and no email is supplied → deny.
        If the stored JSON is malformed → fail CLOSED (deny).
        """
        if not allowed_domains_json:
            return True
        try:
            allowed = json.loads(allowed_domains_json)
        except Exception:
            logger.error("allowed_domains JSON parse failed — denying access (fail-closed)")
            return False  # malformed JSON → fail closed
        if not allowed:
            return True
        if not viewer_email or "@" not in viewer_email:
            return False
        email_domain = viewer_email.rsplit("@", 1)[1].lower().strip()
        for domain in allowed:
            d = domain.strip().lower().lstrip("@")
            if d and email_domain == d:
                return True
        return False

    # ── Concurrent-session tracking ───────────────────────────────────────────

    async def active_session_count(self, db: AsyncSession, link_id) -> int:
        """Count sessions that have been seen within SESSION_ACTIVE_MINUTES."""
        from app.models.session import ViewerSession

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=SESSION_ACTIVE_MINUTES)
        q = (
            select(func.count())
            .select_from(ViewerSession)
            .where(
                ViewerSession.link_id == link_id,
                ViewerSession.last_seen_at >= cutoff,
            )
        )
        return (await db.execute(q)).scalar() or 0

    async def is_active_session(
        self, db: AsyncSession, link_id, session_id: str
    ) -> bool:
        """Return True if session_id is an active (non-stale) session for this link.

        Checks the process-local session cache first (5 s TTL) to avoid a DB
        read on every page request.  On cache miss, falls back to DB and
        populates the cache for subsequent requests.

        Cross-link session replay is validated on both cache hits and DB reads.
        """
        from app.services.viewer_cache import session_cache

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=SESSION_ACTIVE_MINUTES)

        # ── L1: process-local session cache ──────────────────────────────────
        cached = session_cache.get(session_id)
        if cached is not None:
            cached_link_id, last_seen_at, _email = cached
            if str(cached_link_id) != str(link_id):
                return False  # cross-link replay
            last_seen = last_seen_at
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            return last_seen >= cutoff

        # ── DB fallback ───────────────────────────────────────────────────────
        from app.models.session import ViewerSession

        row = await db.get(ViewerSession, session_id)
        if row is None or str(row.link_id) != str(link_id):
            return False
        last_seen = row.last_seen_at
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        is_active = last_seen >= cutoff
        if is_active:
            # Populate cache so subsequent requests in this TTL window skip DB.
            session_cache.put(
                session_id,
                (row.link_id, last_seen, row.viewer_email_masked),
            )
        return is_active

    async def purge_stale_sessions(self, db: AsyncSession, link_id) -> int:
        """Delete sessions inactive past the timeout. Returns number of rows deleted."""
        from app.models.session import ViewerSession

        cutoff = datetime.now(timezone.utc) - timedelta(minutes=SESSION_ACTIVE_MINUTES)
        result = await db.execute(
            delete(ViewerSession).where(
                ViewerSession.link_id == link_id,
                ViewerSession.last_seen_at < cutoff,
            )
        )
        return result.rowcount or 0
        # caller must commit

    async def upsert_session(
        self,
        db: AsyncSession,
        session_id: str,
        link_id,
        ip_hash: Optional[str] = None,
        viewer_email_masked: Optional[str] = None,
    ) -> Optional[str]:
        """Create or refresh a viewer session record.

        Returns the stored viewer_email_masked so callers (page endpoint) can
        embed the viewer's identity in the forensic watermark without an extra
        DB query.

        For existing sessions, the heartbeat write is throttled to at most once
        per SESSION_HEARTBEAT_INTERVAL_SEC to reduce DB write amplification when
        a viewer rapidly pages through a document.

        Also updates the process-local session cache so subsequent is_active_session
        calls in the same TTL window skip the DB entirely.
        """
        from app.models.session import ViewerSession
        from app.services.viewer_cache import session_cache

        now = datetime.now(timezone.utc)

        # ── Check session cache first to avoid an extra DB round-trip ─────────
        cached = session_cache.get(session_id)
        if cached is not None:
            cached_link_id, cached_last_seen, cached_email = cached
            if str(cached_link_id) != str(link_id):
                logger.warning(
                    "session_link_mismatch session=%s... expected_link=%s actual_link=%s",
                    session_id[:6], link_id, cached_link_id,
                )
                return None
            # Update cache timestamp and fall through to DB heartbeat logic.
            resolved_email = cached_email

            # Only write to DB if heartbeat interval has elapsed (throttle writes).
            last_seen = cached_last_seen
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            elapsed = (now - last_seen).total_seconds()
            if elapsed >= SESSION_HEARTBEAT_INTERVAL_SEC:
                # Refresh DB row and cache.
                existing = await db.get(ViewerSession, session_id)
                if existing:
                    existing.last_seen_at = now
                    session_cache.put(session_id, (link_id, now, cached_email))
            # else: within heartbeat interval — update cache timestamp only.
            return resolved_email

        # ── Cache miss: full DB path ──────────────────────────────────────────
        existing = await db.get(ViewerSession, session_id)
        if existing:
            if str(existing.link_id) != str(link_id):
                logger.warning(
                    "session_link_mismatch session=%s... expected_link=%s actual_link=%s",
                    session_id[:6], link_id, existing.link_id,
                )
                return None
            last_seen = existing.last_seen_at
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            elapsed = (now - last_seen).total_seconds()
            if elapsed >= SESSION_HEARTBEAT_INTERVAL_SEC:
                existing.last_seen_at = now
                session_cache.put(session_id, (existing.link_id, now, existing.viewer_email_masked))
            else:
                session_cache.put(session_id, (existing.link_id, last_seen, existing.viewer_email_masked))
            return existing.viewer_email_masked
        else:
            db.add(
                ViewerSession(
                    session_id=session_id,
                    link_id=link_id,
                    ip_hash=ip_hash,
                    viewer_email_masked=viewer_email_masked,
                    created_at=now,
                    last_seen_at=now,
                )
            )
            # Populate cache for the new session immediately.
            session_cache.put(session_id, (link_id, now, viewer_email_masked))
            return viewer_email_masked
        # caller must commit


enforcer = PolicyEnforcer()
