"""
E2E Scenario: Full link lifecycle — create, restrict, enforce, revoke.
Uses the session-scoped ready_doc to avoid rate limit on uploads.
"""
import pytest
from datetime import datetime, timedelta, timezone
from conftest import make_minimal_pdf, upload_pdf

pytestmark = pytest.mark.e2e


class TestLinkLifecycle:

    def test_create_plain_link(self, api_client, ready_doc):
        r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        assert r.status_code == 201
        link = r.json()
        assert link["view_count"] == 0

    def test_validate_increments_view_count(self, api_client, ready_doc):
        r = api_client.post(
            "/api/links",
            json={"document_id": ready_doc["id"], "label": "view-counter"},
        )
        token = r.json()["token"]
        link_id = r.json()["id"]

        api_client.post("/api/viewer/validate", json={"token": token})
        api_client.post("/api/viewer/validate", json={"token": token})

        links_resp = api_client.get(
            f"/api/links?document_id={ready_doc['id']}"
        ).json()
        link = next(l for l in links_resp["links"] if l["id"] == link_id)
        assert link["view_count"] == 2

    def test_max_views_enforced(self, api_client, ready_doc):
        r = api_client.post(
            "/api/links",
            json={"document_id": ready_doc["id"], "max_views": 2, "label": "max-test"},
        )
        token = r.json()["token"]

        r1 = api_client.post("/api/viewer/validate", json={"token": token})
        r2 = api_client.post("/api/viewer/validate", json={"token": token})
        r3 = api_client.post("/api/viewer/validate", json={"token": token})

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r3.status_code == 410

    def test_password_protection_enforced(self, api_client, ready_doc):
        r = api_client.post(
            "/api/links",
            json={
                "document_id": ready_doc["id"],
                "password": "hunter2",
                "label": "pw-test",
            },
        )
        token = r.json()["token"]

        # No password → 401
        r_none = api_client.post("/api/viewer/validate", json={"token": token})
        assert r_none.status_code == 401

        # Wrong password → 401
        r_wrong = api_client.post(
            "/api/viewer/validate",
            json={"token": token, "password": "wrong"},
        )
        assert r_wrong.status_code == 401

        # Correct password → 200
        r_ok = api_client.post(
            "/api/viewer/validate",
            json={"token": token, "password": "hunter2"},
        )
        assert r_ok.status_code == 200

    def test_email_allowlist_enforced(self, api_client, ready_doc):
        r = api_client.post(
            "/api/links",
            json={
                "document_id": ready_doc["id"],
                "allowed_emails": ["allowed@example.com"],
                "label": "email-test",
            },
        )
        token = r.json()["token"]

        r_denied = api_client.post(
            "/api/viewer/validate",
            json={"token": token, "email": "denied@example.com"},
        )
        assert r_denied.status_code == 403

        r_allowed = api_client.post(
            "/api/viewer/validate",
            json={"token": token, "email": "allowed@example.com"},
        )
        assert r_allowed.status_code == 200

    def test_expired_link_returns_410(self, api_client, ready_doc):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        r = api_client.post(
            "/api/links",
            json={"document_id": ready_doc["id"], "expires_at": past, "label": "expired"},
        )
        token = r.json()["token"]
        r = api_client.post("/api/viewer/validate", json={"token": token})
        assert r.status_code == 410

    def test_revoke_blocks_access(self, api_client, ready_doc):
        r = api_client.post(
            "/api/links",
            json={"document_id": ready_doc["id"], "label": "to-revoke"},
        )
        link = r.json()

        # Validate succeeds before revoke
        r_before = api_client.post(
            "/api/viewer/validate", json={"token": link["token"]}
        )
        assert r_before.status_code == 200

        # Revoke
        api_client.delete(f"/api/links/{link['id']}")

        # Validate fails after revoke → 410
        r_after = api_client.post(
            "/api/viewer/validate", json={"token": link["token"]}
        )
        assert r_after.status_code == 410

    def test_revoked_link_page_returns_410(self, api_client, ready_doc):
        """Page endpoint must also respect revocation."""
        if ready_doc.get("status") != "ready":
            pytest.skip("Document not ready")

        r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        link = r.json()

        r_val = api_client.post("/api/viewer/validate", json={"token": link["token"]})
        sid = r_val.json()["session_id"]

        api_client.delete(f"/api/links/{link['id']}")

        r_page = api_client.get(
            f"/api/viewer/page/{link['token']}/1",
            params={"session_id": sid},
        )
        assert r_page.status_code == 410

    def test_link_label_update(self, api_client, ready_doc):
        r = api_client.post(
            "/api/links",
            json={"document_id": ready_doc["id"], "label": "original"},
        )
        link_id = r.json()["id"]

        r = api_client.patch(f"/api/links/{link_id}", json={"label": "updated"})
        assert r.status_code == 200
        assert r.json()["label"] == "updated"

    def test_password_hash_never_in_any_response(self, api_client, ready_doc):
        r = api_client.post(
            "/api/links",
            json={"document_id": ready_doc["id"], "password": "mypw"},
        )
        assert "$2b$" not in r.text

        link_id = r.json()["id"]
        r_patch = api_client.patch(f"/api/links/{link_id}", json={"label": "x"})
        assert "$2b$" not in r_patch.text

        r_list = api_client.get(f"/api/links?document_id={ready_doc['id']}")
        assert "$2b$" not in r_list.text
