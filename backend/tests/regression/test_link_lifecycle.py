"""Additional link lifecycle regression tests."""
import pytest
from sqlalchemy import select

from app.models.audit import AdminAuditLog


class TestLinkLifecycleAdditional:

    async def _assert_audit_event_truly_committed(self, db_session, event_type, target_id):
        """Verify an AdminAuditLog row was not just add()+flush()ed within the
        current session (which the shared test-session fixture would show as
        present regardless of whether a real commit happened) but genuinely
        committed — i.e. would still be there after a rollback of anything
        NOT covered by a commit. This is the exact distinction that let the
        link.created/link.updated/link.revoked bug (missing a trailing
        db.commit() after log_audit_event(), which only flushes) pass a naive
        "query it back on the same session" check while never actually
        persisting on a real per-request session lifecycle in production."""
        await db_session.rollback()
        result = await db_session.execute(
            select(AdminAuditLog).where(
                AdminAuditLog.event_type == event_type,
                AdminAuditLog.target_id == target_id,
            )
        )
        entry = result.scalar_one_or_none()
        assert entry is not None, (
            f"no AdminAuditLog row for {event_type} survived a rollback — "
            f"log_audit_event() flushes but never commits on its own, so the "
            f"caller must commit explicitly or this audit entry is silently "
            f"lost when the request-scoped session closes (confirmed live: "
            f"this exact event type was completely absent from production's "
            f"audit log despite the code path executing on every request)."
        )

    @pytest.mark.asyncio
    async def test_link_created_is_audit_logged(
        self, client, db_session, sample_document_in_db
    ):
        """POST /api/links must produce a link.created AdminAuditLog row —
        the audit log's own description promises 'configuration changes' are
        tracked, and creating a share link is exactly that."""
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
        })
        assert link_r.status_code == 201
        link_id = link_r.json()["id"]
        await self._assert_audit_event_truly_committed(db_session, "link.created", link_id)

    @pytest.mark.asyncio
    async def test_link_revoked_is_audit_logged(
        self, client, db_session, sample_document_in_db
    ):
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
        })
        link_id = link_r.json()["id"]
        revoke_r = await client.delete(f"/api/links/{link_id}")
        assert revoke_r.status_code == 200
        await self._assert_audit_event_truly_committed(db_session, "link.revoked", link_id)

    @pytest.mark.asyncio
    async def test_link_updated_is_audit_logged(
        self, client, db_session, sample_document_in_db
    ):
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
        })
        link_id = link_r.json()["id"]
        patch_r = await client.patch(f"/api/links/{link_id}", json={"label": "Renamed"})
        assert patch_r.status_code == 200
        await self._assert_audit_event_truly_committed(db_session, "link.updated", link_id)

    @pytest.mark.asyncio
    async def test_max_views_exactly_at_limit_still_succeeds(
        self, client, sample_document_in_db
    ):
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
            "max_views": 1,
        })
        token = link_r.json()["token"]
        r = await client.post("/api/viewer/validate", json={"token": token})
        assert r.status_code == 200
        r2 = await client.post("/api/viewer/validate", json={"token": token})
        assert r2.status_code == 410

    @pytest.mark.asyncio
    async def test_max_views_exhausted_link_is_inactive_in_list(
        self, client, sample_document_in_db
    ):
        """GET /api/links must show is_active=False when max_views is exhausted."""
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
            "max_views": 1,
        })
        link_id = link_r.json()["id"]
        token = link_r.json()["token"]
        # Use the one allowed view
        await client.post("/api/viewer/validate", json={"token": token})
        # List should now show is_active=False
        list_r = await client.get(f"/api/links?document_id={sample_document_in_db.id}")
        link_summary = next(link for link in list_r.json()["links"] if link["id"] == link_id)
        assert link_summary["is_active"] is False

    @pytest.mark.asyncio
    async def test_revoked_link_cannot_be_unrevoked_via_patch(
        self, client, sample_document_in_db
    ):
        link_r = await client.post("/api/links", json={
            "document_id": str(sample_document_in_db.id),
        })
        link_id = link_r.json()["id"]
        token = link_r.json()["token"]

        await client.delete(f"/api/links/{link_id}")

        # Try to patch revoked_at to None — should not re-enable link
        await client.patch(f"/api/links/{link_id}", json={"label": "patched"})
        # Link should still be revoked after patch
        v = await client.post("/api/viewer/validate", json={"token": token})
        assert v.status_code == 410
