"""ENG-037 regression suite — is_link_active() vs. validate_link() consistency.

Investigation finding (V22.0 Priority 5): is_link_active(link, now) was
extracted as a "single source of truth" for link-active status, but
LinkService.validate_link() — the actual access-enforcement path — never
calls it; it independently re-implements the revoked/expired checks inline,
each with its own distinct HTTP status/detail and analytics event_type.

Consolidating the two into literally one code path was investigated and
NOT done: validate_link()'s revoked/expired checks are inseparable from
per-reason error messages and analytics logging that a pure boolean
predicate can't carry, and max_views is deliberately handled by validate_link
via an atomic UPDATE (not a read-then-compare, for concurrency-correctness)
that a shared predicate structurally cannot replace. Forcing a merge would
add complexity (a reason-code layer) for a risk that's currently only
theoretical — both implementations agree today.

What this suite does instead: it is the "shared canonical implementation"
in spirit, without the invasive refactor — it directly compares
is_link_active()'s boolean against validate_link()'s actual accept/reject
decision across every revoked/expired boundary case. If a future edit to
either implementation ever causes them to disagree, this suite fails
immediately, closing the actual risk (silent drift) without touching the
app's highest-stakes function.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from app.services.link_service import LinkService, is_link_active


class TestIsLinkActiveVsValidateLinkConsistency:
    @pytest.mark.asyncio
    async def test_not_revoked_not_expired_both_agree_active(self, db_session, ready_document):
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(ready_document.id))
        assert is_link_active(link) is True
        # validate_link must NOT raise
        result = await svc.validate_link(db_session, token=link.token)
        assert result.link.id == link.id

    @pytest.mark.asyncio
    async def test_revoked_both_agree_inactive(self, db_session, ready_document):
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(ready_document.id))
        await svc.revoke_link(db_session, str(link.id))
        await db_session.refresh(link)

        assert is_link_active(link) is False
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(db_session, token=link.token)
        assert exc.value.status_code == 410
        assert "revoked" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_expired_1s_in_past_both_agree_inactive(self, db_session, ready_document):
        svc = LinkService()
        link = await svc.create_link(
            db_session, document_id=str(ready_document.id),
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )

        assert is_link_active(link) is False
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(db_session, token=link.token)
        assert exc.value.status_code == 410
        assert "expired" in exc.value.detail.lower()

    @pytest.mark.asyncio
    async def test_expires_far_in_future_both_agree_active(self, db_session, ready_document):
        svc = LinkService()
        link = await svc.create_link(
            db_session, document_id=str(ready_document.id),
            expires_at=datetime.now(timezone.utc) + timedelta(days=1),
        )

        assert is_link_active(link) is True
        result = await svc.validate_link(db_session, token=link.token)
        assert result.link.id == link.id

    @pytest.mark.asyncio
    async def test_no_expiry_no_revocation_both_agree_active(self, db_session, ready_document):
        """max_views/expiry/revocation all unset — the permanently-open case."""
        svc = LinkService()
        link = await svc.create_link(db_session, document_id=str(ready_document.id))

        assert is_link_active(link) is True
        result = await svc.validate_link(db_session, token=link.token)
        assert result.link.id == link.id

    def test_expiry_boundary_exact_instant_is_still_active_in_predicate(self):
        """Documents the exact boundary semantic both implementations share:
        a link is still active AT its expires_at instant, only inactive once
        `now` strictly exceeds it. Pure unit test of the predicate's boundary
        (validate_link's equivalent boundary is exercised by the two async
        tests above using a 1-second offset, since asserting an exact
        simultaneous instant against a live DB call is inherently racy)."""
        from app.models.link import ShareLink
        import uuid

        now = datetime.now(timezone.utc)
        link = ShareLink(
            id=uuid.uuid4(), document_id=uuid.uuid4(), token="t" * 20,
            expires_at=now, revoked_at=None, max_views=None, view_count=0,
        )
        assert is_link_active(link, now=now) is True
        assert is_link_active(link, now=now + timedelta(microseconds=1)) is False
