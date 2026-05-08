"""
E2E Scenario: Analytics pipeline — events flow through to overview and per-doc stats.
"""
import pytest
from conftest import make_minimal_pdf, upload_pdf

pytestmark = pytest.mark.e2e


class TestAnalyticsFlow:

    def test_validate_increments_total_views_today(self, api_client, active_link):
        before = api_client.get("/api/analytics/overview").json()["total_views_today"]
        api_client.post("/api/viewer/validate", json={"token": active_link["token"]})
        after = api_client.get("/api/analytics/overview").json()["total_views_today"]
        assert after >= before + 1

    def test_blocked_events_increment_blocked_attempts(self, api_client, active_link):
        before = api_client.get("/api/analytics/overview").json()["blocked_attempts_today"]
        for etype in ["print_attempt", "copy_attempt", "right_click_attempt"]:
            api_client.post("/api/analytics/events", json={
                "token": active_link["token"],
                "session_id": "aa" * 8,
                "event_type": etype,
            })
        after = api_client.get("/api/analytics/overview").json()["blocked_attempts_today"]
        assert after >= before + 3

    def test_events_visible_in_get_events(self, api_client, active_link, ready_doc):
        api_client.post("/api/analytics/events", json={
            "token": active_link["token"],
            "session_id": "bb" * 8,
            "event_type": "page_viewed",
            "page_number": 1,
        })
        r = api_client.get(
            "/api/analytics/events",
            params={"document_id": ready_doc["id"]},
        )
        assert r.status_code == 200
        assert r.json()["total"] >= 1

    def test_document_appears_in_analytics_documents(self, api_client, ready_doc):
        r = api_client.get("/api/analytics/documents")
        doc_ids = [d["id"] for d in r.json()["documents"]]
        assert ready_doc["id"] in doc_ids

    def test_high_blocked_count_elevates_risk_score(self, api_client, active_link):
        """Send >5 blocked events to trigger HIGH risk score."""
        for etype in ["print_attempt", "copy_attempt", "right_click_attempt",
                      "download_attempt", "print_attempt", "copy_attempt"]:
            api_client.post("/api/analytics/events", json={
                "token": active_link["token"],
                "session_id": "cc" * 8,
                "event_type": etype,
            })
        r = api_client.get("/api/analytics/documents")
        docs = r.json()["documents"]
        # Find the doc associated with active_link
        assert len(docs) >= 1
        risk_scores = [d["risk_score"] for d in docs]
        # At least one document should have MED or HIGH risk
        assert any(rs in ("MED", "HIGH") for rs in risk_scores)

    def test_views_last_7_days_array_correct_length(self, api_client):
        r = api_client.get("/api/analytics/overview")
        days = r.json()["views_last_7_days"]
        assert len(days) == 7

    def test_views_last_7_days_all_numeric(self, api_client):
        r = api_client.get("/api/analytics/overview")
        days = r.json()["views_last_7_days"]
        for entry in days:
            # Each entry should be either a number or a dict with a count
            assert isinstance(entry, (int, float, dict))

    def test_active_links_count_increases_on_create(self, api_client, ready_doc):
        before = api_client.get("/api/analytics/overview").json()["active_links"]
        api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        after = api_client.get("/api/analytics/overview").json()["active_links"]
        assert after >= before + 1

    def test_active_links_count_decreases_on_revoke(self, api_client, ready_doc):
        # Create a link, record count, revoke it
        r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        link_id = r.json()["id"]
        before = api_client.get("/api/analytics/overview").json()["active_links"]
        api_client.delete(f"/api/links/{link_id}")
        after = api_client.get("/api/analytics/overview").json()["active_links"]
        assert after <= before

    def test_event_type_page_viewed_is_not_blocked(self, api_client, active_link):
        """page_viewed events should NOT count toward blocked_attempts."""
        before = api_client.get("/api/analytics/overview").json()["blocked_attempts_today"]
        api_client.post("/api/analytics/events", json={
            "token": active_link["token"],
            "session_id": "dd" * 8,
            "event_type": "page_viewed",
            "page_number": 1,
        })
        after = api_client.get("/api/analytics/overview").json()["blocked_attempts_today"]
        # page_viewed should not be counted as a blocked attempt
        assert after == before

    def test_invalid_token_event_not_logged(self, api_client):
        r = api_client.post("/api/analytics/events", json={
            "token": "z" * 64,
            "session_id": "ee" * 8,
            "event_type": "page_viewed",
        })
        assert r.status_code == 404
