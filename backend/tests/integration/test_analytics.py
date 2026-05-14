import uuid
import pytest

from app.models.document import Document
from app.models.group import DocumentGroup
from app.models.link import ShareLink
from app.models.event import AccessEvent
from tests.conftest import TEST_USER_ID, TEST_USER_B_ID


class TestAnalyticsEndpoints:

    @pytest.mark.asyncio
    async def test_overview_returns_required_fields(self, client):
        r = await client.get("/api/analytics/overview")
        assert r.status_code == 200
        body = r.json()
        assert "total_documents" in body
        assert "total_views_today" in body
        assert "active_links" in body
        assert "blocked_attempts_today" in body
        assert "views_last_7_days" in body
        assert len(body["views_last_7_days"]) == 7

    @pytest.mark.asyncio
    async def test_log_event_returns_200(self, client, active_link):
        # Must establish a real viewer session first
        val = await client.post("/api/viewer/validate", json={"token": active_link.token})
        session_id = val.json()["session_id"]

        r = await client.post("/api/analytics/events", json={
            "token": active_link.token,
            "session_id": session_id,
            "event_type": "print_attempt",
            "page_number": 3,
        })
        assert r.status_code == 200
        assert r.json()["logged"] is True

    @pytest.mark.asyncio
    async def test_log_event_requires_valid_session(self, client, active_link):
        """Sending a fake/unknown session_id must be rejected with 403."""
        r = await client.post("/api/analytics/events", json={
            "token": active_link.token,
            "session_id": "fakesession000000",
            "event_type": "print_attempt",
        })
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_log_event_requires_session_id(self, client, active_link):
        """Empty session_id must be rejected with 400."""
        r = await client.post("/api/analytics/events", json={
            "token": active_link.token,
            "session_id": "",
            "event_type": "print_attempt",
        })
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_log_event_rejects_server_side_event_types(self, client, active_link):
        """Internal security events must not be loggable via the public endpoint."""
        val = await client.post("/api/viewer/validate", json={"token": active_link.token})
        session_id = val.json()["session_id"]

        for bad_event in ("opened", "access_denied", "revoked", "expired", "ip_blocked",
                          "session_limit_reached", "max_views_reached", "password_wrong"):
            r = await client.post("/api/analytics/events", json={
                "token": active_link.token,
                "session_id": session_id,
                "event_type": bad_event,
            })
            assert r.status_code == 400, f"Expected 400 for {bad_event!r}, got {r.status_code}"

    @pytest.mark.asyncio
    async def test_log_event_with_invalid_token_returns_404(self, client):
        r = await client.post("/api/analytics/events", json={
            "token": "x" * 64,
            "session_id": "a" * 16,
            "event_type": "print_attempt",
        })
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_blocked_attempts_counted_correctly(self, client, active_link):
        # Must establish a real session before logging events
        val = await client.post("/api/viewer/validate", json={"token": active_link.token})
        session_id = val.json()["session_id"]

        for event_type in ["print_attempt", "copy_attempt", "right_click_attempt"]:
            await client.post("/api/analytics/events", json={
                "token": active_link.token,
                "session_id": session_id,
                "event_type": event_type,
            })
        r = await client.get("/api/analytics/overview")
        assert r.json()["blocked_attempts_today"] >= 3

    @pytest.mark.asyncio
    async def test_document_analytics_returns_list(self, client, active_link):
        r = await client.get("/api/analytics/documents")
        assert r.status_code == 200
        assert "documents" in r.json()

    @pytest.mark.asyncio
    async def test_document_analytics_with_events(self, client, active_link):
        # Generate a view + blocked events with a real session
        val = await client.post("/api/viewer/validate", json={"token": active_link.token})
        session_id = val.json()["session_id"]

        for et in ["print_attempt", "copy_attempt", "right_click_attempt",
                   "download_attempt", "right_click_attempt", "print_attempt"]:
            await client.post("/api/analytics/events", json={
                "token": active_link.token,
                "session_id": session_id,
                "event_type": et,
            })
        await client.post("/api/analytics/events", json={
            "token": active_link.token,
            "session_id": session_id,
            "event_type": "completed",
        })
        r = await client.get("/api/analytics/documents")
        assert r.status_code == 200
        docs = r.json()["documents"]
        assert len(docs) >= 1
        doc = docs[0]
        assert doc["risk_score"] in ("LOW", "MED", "HIGH")
        assert doc["total_views"] >= 1
        assert doc["blocked_attempts"] >= 6

    @pytest.mark.asyncio
    async def test_get_events_returns_list(self, client, active_link):
        # Use validate to get a real session, then log a viewer event
        val = await client.post("/api/viewer/validate", json={"token": active_link.token})
        session_id = val.json()["session_id"]

        await client.post("/api/analytics/events", json={
            "token": active_link.token,
            "session_id": session_id,
            "event_type": "completed",
        })
        r = await client.get("/api/analytics/events",
                             params={"document_id": str(active_link.document_id)})
        assert r.status_code == 200
        assert "events" in r.json()
        assert r.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_events_without_document_id(self, client, active_link):
        val = await client.post("/api/viewer/validate", json={"token": active_link.token})
        session_id = val.json()["session_id"]

        await client.post("/api/analytics/events", json={
            "token": active_link.token,
            "session_id": session_id,
            "event_type": "completed",
        })
        r = await client.get("/api/analytics/events")
        assert r.status_code == 200
        assert "events" in r.json()

    @pytest.mark.asyncio
    async def test_document_analytics_no_links(self, client, sample_document_in_db):
        # Document with no links should still appear with zero stats
        r = await client.get("/api/analytics/documents")
        assert r.status_code == 200
        docs = r.json()["documents"]
        doc_entry = next((d for d in docs if d["id"] == str(sample_document_in_db.id)), None)
        assert doc_entry is not None
        assert doc_entry["total_views"] == 0
        assert doc_entry["risk_score"] == "LOW"


class TestAnalyticsIsolation:
    """User A must never see User B's data in any analytics endpoint."""

    async def _setup_user_b_data(self, db_session):
        """Create doc + link + event owned by user B."""
        doc = Document(
            id=uuid.uuid4(),
            filename="user_b_secret.pdf",
            storage_key=f"originals/{uuid.uuid4()}.pdf",
            status="ready",
            page_count=1,
            file_size_bytes=512,
            user_id=uuid.UUID(TEST_USER_B_ID),
        )
        db_session.add(doc)
        await db_session.flush()

        import secrets
        link = ShareLink(
            id=uuid.uuid4(),
            document_id=doc.id,
            token=secrets.token_hex(32),
            view_count=0,
        )
        db_session.add(link)
        await db_session.flush()

        event = AccessEvent(
            id=uuid.uuid4(),
            link_id=link.id,
            event_type="opened",
        )
        db_session.add(event)
        await db_session.commit()
        return doc, link, event

    @pytest.mark.asyncio
    async def test_user_cannot_see_other_users_events(self, client, db_session):
        _, _, event_b = await self._setup_user_b_data(db_session)

        r = await client.get("/api/analytics/events")
        assert r.status_code == 200
        event_ids = [e["id"] for e in r.json()["events"]]
        assert str(event_b.id) not in event_ids

    @pytest.mark.asyncio
    async def test_user_cannot_see_other_users_document_in_analytics(
        self, client, db_session
    ):
        doc_b, _, _ = await self._setup_user_b_data(db_session)

        r = await client.get("/api/analytics/documents")
        assert r.status_code == 200
        doc_ids = [d["id"] for d in r.json()["documents"]]
        assert str(doc_b.id) not in doc_ids

    @pytest.mark.asyncio
    async def test_overview_excludes_other_users_documents(self, client, db_session):
        # DB is empty for user A; create one doc for user B
        await self._setup_user_b_data(db_session)

        r = await client.get("/api/analytics/overview")
        assert r.status_code == 200
        # User A has 0 documents — user B's doc must not be counted
        assert r.json()["total_documents"] == 0

    @pytest.mark.asyncio
    async def test_overview_excludes_other_users_views(self, client, db_session):
        # User B has a view event — user A's overview should show 0 views today
        await self._setup_user_b_data(db_session)

        r = await client.get("/api/analytics/overview")
        assert r.status_code == 200
        assert r.json()["total_views_today"] == 0

    @pytest.mark.asyncio
    async def test_events_filter_by_document_id_respects_ownership(
        self, client, db_session
    ):
        # User A must get empty events when querying by user B's document_id
        doc_b, _, _ = await self._setup_user_b_data(db_session)

        r = await client.get(f"/api/analytics/events?document_id={doc_b.id}")
        assert r.status_code == 200
        assert r.json()["events"] == []
        assert r.json()["total"] == 0

    # ── Group analytics isolation ───────────────────────────────────────────

    async def _make_group_b(self, db_session, name: str = "B Secret Group") -> DocumentGroup:
        grp = DocumentGroup(
            id=uuid.uuid4(),
            user_id=uuid.UUID(TEST_USER_B_ID),
            name=name,
            color="#ff0000",
        )
        db_session.add(grp)
        await db_session.commit()
        await db_session.refresh(grp)
        return grp

    @pytest.mark.asyncio
    async def test_group_analytics_excludes_other_users_groups(
        self, client, db_session
    ):
        """INVARIANT: /api/analytics/groups must never expose user B's groups to user A."""
        grp_b = await self._make_group_b(db_session)

        r = await client.get("/api/analytics/groups")
        assert r.status_code == 200
        group_ids = [g["group_id"] for g in r.json()["groups"]]
        assert str(grp_b.id) not in group_ids, (
            f"SECURITY VIOLATION: user B's group {grp_b.id} visible in user A's analytics"
        )

    @pytest.mark.asyncio
    async def test_group_analytics_shows_own_groups(
        self, client, db_session
    ):
        """User A's own groups appear; user B's do not."""
        grp_a = DocumentGroup(
            id=uuid.uuid4(),
            user_id=uuid.UUID(TEST_USER_ID),
            name="A Own Group",
            color="#00ff00",
        )
        db_session.add(grp_a)
        grp_b = await self._make_group_b(db_session, "B Only Group")
        await db_session.commit()

        r = await client.get("/api/analytics/groups")
        assert r.status_code == 200
        group_ids = [g["group_id"] for g in r.json()["groups"]]
        assert str(grp_a.id) in group_ids
        assert str(grp_b.id) not in group_ids

    @pytest.mark.asyncio
    async def test_overview_total_groups_excludes_other_users(
        self, client, db_session
    ):
        """INVARIANT: total_groups in overview counts only the current user's groups."""
        # Only user B has a group — user A's total_groups must be 0
        await self._make_group_b(db_session)

        r = await client.get("/api/analytics/overview")
        assert r.status_code == 200
        assert r.json()["total_groups"] == 0, (
            "SECURITY VIOLATION: total_groups counted another user's group"
        )
