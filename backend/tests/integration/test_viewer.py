import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock

from app.services.link_service import LinkService


class TestConcurrentSessions:
    """Verify that max_concurrent_sessions is enforced server-side."""

    @pytest.mark.asyncio
    async def test_max_1_browser_a_allowed_browser_b_denied(
        self, client, db_session, ready_document
    ):
        link = await LinkService().create_link(
            db_session,
            document_id=str(ready_document.id),
            max_concurrent_sessions=1,
        )
        r_a = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r_a.status_code == 200

        # Browser B — no session_id → new slot required → denied
        r_b = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r_b.status_code == 403
        assert "concurrent" in r_b.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_max_2_three_browsers(self, client, db_session, ready_document):
        link = await LinkService().create_link(
            db_session,
            document_id=str(ready_document.id),
            max_concurrent_sessions=2,
        )
        r_a = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r_a.status_code == 200
        r_b = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r_b.status_code == 200
        r_c = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r_c.status_code == 403
        assert "concurrent" in r_c.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_same_browser_refresh_reuses_session_does_not_consume_extra_slot(
        self, client, db_session, ready_document
    ):
        link = await LinkService().create_link(
            db_session,
            document_id=str(ready_document.id),
            max_concurrent_sessions=1,
        )
        # First load: no session_id
        r1 = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r1.status_code == 200
        session_id = r1.json()["session_id"]

        # Refresh (same session_id passed back) — must NOT consume an extra slot
        r2 = await client.post(
            "/api/viewer/validate",
            json={"token": link.token, "session_id": session_id},
        )
        assert r2.status_code == 200
        assert r2.json()["session_id"] == session_id  # same session returned

        # A genuinely new browser (no session_id) must still be denied at max=1
        r3 = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r3.status_code == 403

    @pytest.mark.asyncio
    async def test_forged_session_id_treated_as_new_session(
        self, client, db_session, ready_document
    ):
        """An attacker supplying a random session_id gets no special treatment."""
        link = await LinkService().create_link(
            db_session,
            document_id=str(ready_document.id),
            max_concurrent_sessions=1,
        )
        # Fill the one slot
        await client.post("/api/viewer/validate", json={"token": link.token})

        # Attacker sends a made-up session_id — should still be denied
        r = await client.post(
            "/api/viewer/validate",
            json={"token": link.token, "session_id": "deadbeefdeadbeef"},
        )
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_stale_sessions_purged_before_count_allows_new_viewer(
        self, client, db_session, ready_document
    ):
        from app.models.session import ViewerSession

        link = await LinkService().create_link(
            db_session,
            document_id=str(ready_document.id),
            max_concurrent_sessions=1,
        )
        # Manually insert a stale session (inactive >2 h)
        stale_time = datetime.now(timezone.utc) - timedelta(hours=3)
        db_session.add(
            ViewerSession(
                session_id="stalesesstale000",
                link_id=link.id,
                created_at=stale_time,
                last_seen_at=stale_time,
            )
        )
        await db_session.commit()

        # New browser — stale session purged, slot available
        r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_cross_link_session_id_not_reusable(
        self, client, db_session, ready_document
    ):
        """Session from link A must not give free pass on link B."""
        svc = LinkService()
        link_a = await svc.create_link(
            db_session,
            document_id=str(ready_document.id),
            max_concurrent_sessions=1,
        )
        link_b = await svc.create_link(
            db_session,
            document_id=str(ready_document.id),
            max_concurrent_sessions=1,
        )
        # Fill link_b's one slot
        r_fill = await client.post("/api/viewer/validate", json={"token": link_b.token})
        assert r_fill.status_code == 200

        # Obtain a valid session_id from link_a
        r_a = await client.post("/api/viewer/validate", json={"token": link_a.token})
        assert r_a.status_code == 200
        session_a = r_a.json()["session_id"]

        # Try to use link_a's session_id on link_b (should not bypass the limit)
        r_cross = await client.post(
            "/api/viewer/validate",
            json={"token": link_b.token, "session_id": session_a},
        )
        assert r_cross.status_code == 403

    @pytest.mark.asyncio
    async def test_no_limit_allows_unlimited_concurrent_viewers(
        self, client, db_session, ready_document
    ):
        link = await LinkService().create_link(
            db_session,
            document_id=str(ready_document.id),
            max_concurrent_sessions=None,
        )
        for _ in range(5):
            r = await client.post("/api/viewer/validate", json={"token": link.token})
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_page_load_refreshes_session_heartbeat(
        self, client, db_session, ready_document, active_link
    ):
        from app.models.session import ViewerSession

        r = await client.post("/api/viewer/validate", json={"token": active_link.token})
        assert r.status_code == 200
        session_id = r.json()["session_id"]

        await asyncio.sleep(0.05)

        r2 = await client.get(
            f"/api/viewer/page/{active_link.token}/1", headers={"X-Session-ID": session_id}
        )
        assert r2.status_code == 200

        session = await db_session.get(ViewerSession, session_id)
        assert session is not None
        assert session.last_seen_at is not None


class TestGateEndpoint:

    @pytest.mark.asyncio
    async def test_gate_active_link_no_restrictions(self, client, active_link):
        r = await client.get(f"/api/viewer/gate/{active_link.token}")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "active"
        assert body["requires_password"] is False
        assert body["requires_email"] is False

    @pytest.mark.asyncio
    async def test_gate_password_link(self, client, password_link):
        r = await client.get(f"/api/viewer/gate/{password_link.token}")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "active"
        assert body["requires_password"] is True
        assert body["requires_email"] is False

    @pytest.mark.asyncio
    async def test_gate_revoked_link(self, client, revoked_link):
        r = await client.get(f"/api/viewer/gate/{revoked_link.token}")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "revoked"
        assert body["requires_password"] is False

    @pytest.mark.asyncio
    async def test_gate_expired_link(self, client, expired_link):
        r = await client.get(f"/api/viewer/gate/{expired_link.token}")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "expired"

    @pytest.mark.asyncio
    async def test_gate_nonexistent_token(self, client):
        r = await client.get("/api/viewer/gate/deadbeefdeadbeef")
        assert r.status_code == 200
        assert r.json()["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_gate_email_restricted_link(self, client, db_session, ready_document):
        from app.services.link_service import LinkService
        link = await LinkService().create_link(
            db_session,
            document_id=str(ready_document.id),
            allowed_domains=["@psgtech.ac.in"],
        )
        r = await client.get(f"/api/viewer/gate/{link.token}")
        body = r.json()
        assert body["status"] == "active"
        assert body["requires_email"] is True
        assert body["requires_password"] is False

    @pytest.mark.asyncio
    async def test_gate_email_and_password_link(self, client, db_session, ready_document):
        from app.services.link_service import LinkService
        link = await LinkService().create_link(
            db_session,
            document_id=str(ready_document.id),
            password="s3cr3t",
            allowed_emails=["student@psgtech.ac.in"],
        )
        r = await client.get(f"/api/viewer/gate/{link.token}")
        body = r.json()
        assert body["status"] == "active"
        assert body["requires_password"] is True
        assert body["requires_email"] is True

    @pytest.mark.asyncio
    async def test_gate_never_exposes_password_hash(self, client, password_link):
        r = await client.get(f"/api/viewer/gate/{password_link.token}")
        body_str = str(r.json())
        assert "password_hash" not in body_str
        assert "$2b$" not in body_str

    @pytest.mark.asyncio
    async def test_gate_max_views_exhausted_returns_expired(
        self, client, db_session, ready_document
    ):
        """gate must return status=expired when max_views is reached, preventing the retry loop."""
        from app.services.link_service import LinkService
        svc = LinkService()
        link = await svc.create_link(
            db_session,
            document_id=str(ready_document.id),
            max_views=1,
        )
        # Use the validate endpoint to atomically increment view_count
        await svc.validate_link(db_session, token=link.token)
        r = await client.get(f"/api/viewer/gate/{link.token}")
        assert r.status_code == 200
        assert r.json()["status"] == "expired"


class TestViewerEndpoint:

    @pytest.mark.asyncio
    async def test_validate_link_returns_session_and_page_count(
        self, client, ready_document, active_link
    ):
        r = await client.post("/api/viewer/validate", json={"token": active_link.token})
        assert r.status_code == 200
        body = r.json()
        assert "session_id" in body
        assert len(body["session_id"]) == 32  # 128-bit entropy = 32 hex chars
        assert body["page_count"] == ready_document.page_count
        assert "watermark_text" in body

    @pytest.mark.asyncio
    async def test_validate_link_permissions_all_false(self, client, active_link):
        r = await client.post("/api/viewer/validate", json={"token": active_link.token})
        perms = r.json()["permissions"]
        assert perms["can_download"] is False
        assert perms["can_print"] is False
        assert perms["can_copy"] is False
        assert perms["can_right_click"] is False

    @pytest.mark.asyncio
    async def test_validate_link_increments_view_count(
        self, client, db_session, active_link
    ):
        initial_count = active_link.view_count
        await client.post("/api/viewer/validate", json={"token": active_link.token})
        await db_session.refresh(active_link)
        assert active_link.view_count == initial_count + 1

    @pytest.mark.asyncio
    async def test_validate_returns_401_for_wrong_password(self, client, password_link):
        r = await client.post(
            "/api/viewer/validate",
            json={"token": password_link.token, "password": "wrong"}
        )
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_validate_returns_410_for_expired_link(self, client, expired_link):
        r = await client.post("/api/viewer/validate", json={"token": expired_link.token})
        assert r.status_code == 410

    @pytest.mark.asyncio
    async def test_validate_returns_410_for_revoked_link(self, client, revoked_link):
        r = await client.post("/api/viewer/validate", json={"token": revoked_link.token})
        assert r.status_code == 410

    @pytest.mark.asyncio
    async def test_get_page_returns_image_bytes(self, client, ready_document, active_link):
        validate_r = await client.post(
            "/api/viewer/validate", json={"token": active_link.token}
        )
        session_id = validate_r.json()["session_id"]
        r = await client.get(
            f"/api/viewer/page/{active_link.token}/1", headers={"X-Session-ID": session_id}
        )
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/webp"

    @pytest.mark.asyncio
    async def test_get_page_returns_no_cache_headers(self, client, ready_document, active_link):
        validate_r = await client.post(
            "/api/viewer/validate", json={"token": active_link.token}
        )
        session_id = validate_r.json()["session_id"]
        r = await client.get(
            f"/api/viewer/page/{active_link.token}/1", headers={"X-Session-ID": session_id}
        )
        assert "no-store" in r.headers.get("cache-control", "")

    @pytest.mark.asyncio
    async def test_get_page_never_redirects_to_storage_url(
        self, client, ready_document, active_link
    ):
        validate_r = await client.post(
            "/api/viewer/validate", json={"token": active_link.token}
        )
        session_id = validate_r.json()["session_id"]
        r = await client.get(
            f"/api/viewer/page/{active_link.token}/1", headers={"X-Session-ID": session_id},
            follow_redirects=False,
        )
        assert r.status_code not in (301, 302, 307, 308)

    @pytest.mark.asyncio
    async def test_get_page_without_session_id_returns_400(self, client, active_link):
        r = await client.get(f"/api/viewer/page/{active_link.token}/1")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_get_page_for_out_of_range_page_returns_404(
        self, client, ready_document, active_link
    ):
        validate_r = await client.post(
            "/api/viewer/validate", json={"token": active_link.token}
        )
        session_id = validate_r.json()["session_id"]
        r = await client.get(
            f"/api/viewer/page/{active_link.token}/9999", headers={"X-Session-ID": session_id}
        )
        assert r.status_code == 404
