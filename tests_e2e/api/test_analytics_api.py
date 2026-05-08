"""
API contract tests for /api/analytics/*
"""
import pytest

pytestmark = pytest.mark.api


class TestOverview:

    def test_overview_returns_200(self, api_client):
        r = api_client.get("/api/analytics/overview")
        assert r.status_code == 200

    def test_overview_required_fields(self, api_client):
        body = api_client.get("/api/analytics/overview").json()
        assert "total_documents" in body
        assert "total_views_today" in body
        assert "active_links" in body
        assert "blocked_attempts_today" in body
        assert "views_last_7_days" in body

    def test_overview_views_last_7_days_has_7_entries(self, api_client):
        body = api_client.get("/api/analytics/overview").json()
        assert len(body["views_last_7_days"]) == 7

    def test_overview_numeric_fields_non_negative(self, api_client):
        body = api_client.get("/api/analytics/overview").json()
        assert body["total_documents"] >= 0
        assert body["total_views_today"] >= 0
        assert body["active_links"] >= 0
        assert body["blocked_attempts_today"] >= 0


class TestLogEvent:

    def test_log_event_returns_200(self, api_client, active_link):
        r = api_client.post("/api/analytics/events", json={
            "token": active_link["token"],
            "session_id": "a" * 16,
            "event_type": "print_attempt",
            "page_number": 1,
        })
        assert r.status_code == 200
        assert r.json()["logged"] is True

    def test_log_event_invalid_token_returns_404(self, api_client):
        r = api_client.post("/api/analytics/events", json={
            "token": "x" * 64,
            "session_id": "a" * 16,
            "event_type": "page_viewed",
        })
        assert r.status_code == 404

    def test_blocked_attempts_counted(self, api_client, active_link):
        before = api_client.get("/api/analytics/overview").json()["blocked_attempts_today"]
        for etype in ["print_attempt", "copy_attempt", "right_click_attempt"]:
            api_client.post("/api/analytics/events", json={
                "token": active_link["token"],
                "session_id": "b" * 16,
                "event_type": etype,
            })
        after = api_client.get("/api/analytics/overview").json()["blocked_attempts_today"]
        assert after >= before + 3

    def test_ip_not_exposed_in_events(self, api_client, active_link):
        api_client.post("/api/analytics/events", json={
            "token": active_link["token"],
            "session_id": "c" * 16,
            "event_type": "page_viewed",
        })
        r = api_client.get("/api/analytics/events")
        for evt in r.json().get("events", []):
            assert "ip" not in evt
            # raw IP should not appear (only SHA-256 hash if at all)
            if "ip_hash" in evt:
                val = evt["ip_hash"]
                assert val is None or (isinstance(val, str) and len(val) == 64)


class TestDocumentAnalytics:

    def test_document_analytics_returns_200(self, api_client):
        r = api_client.get("/api/analytics/documents")
        assert r.status_code == 200

    def test_document_analytics_has_documents_key(self, api_client):
        body = api_client.get("/api/analytics/documents").json()
        assert "documents" in body

    def test_document_analytics_risk_score_valid(self, api_client, active_link):
        # Generate some blocked events to get a meaningful risk score
        for etype in ["print_attempt", "copy_attempt", "right_click_attempt"] * 3:
            api_client.post("/api/analytics/events", json={
                "token": active_link["token"],
                "session_id": "d" * 16,
                "event_type": etype,
            })
        body = api_client.get("/api/analytics/documents").json()
        for doc in body["documents"]:
            assert doc["risk_score"] in ("LOW", "MED", "HIGH")

    def test_document_analytics_has_total_views(self, api_client):
        body = api_client.get("/api/analytics/documents").json()
        for doc in body["documents"]:
            assert "total_views" in doc
            assert doc["total_views"] >= 0


class TestGetEvents:

    def test_get_events_returns_200(self, api_client):
        r = api_client.get("/api/analytics/events")
        assert r.status_code == 200

    def test_get_events_has_events_and_total(self, api_client):
        body = api_client.get("/api/analytics/events").json()
        assert "events" in body
        assert "total" in body

    def test_get_events_filtered_by_document(self, api_client, active_link, ready_doc):
        api_client.post("/api/analytics/events", json={
            "token": active_link["token"],
            "session_id": "e" * 16,
            "event_type": "page_viewed",
            "page_number": 1,
        })
        r = api_client.get(
            "/api/analytics/events",
            params={"document_id": ready_doc["id"]},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
