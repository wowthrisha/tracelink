"""
E2E Security Invariants — verified against the live stack.

Hard security requirements that must NEVER regress:
1. Raw storage paths are never exposed in any API response
2. bcrypt hashes are never exposed
3. Page endpoint never redirects (always proxies)
4. IPs are stored as SHA-256 hashes only
5. All permissions default to false
6. Page endpoint requires session_id
7. Watermark is applied to every page
8. Security headers are present on page responses
"""
import io
import pytest
from PIL import Image
from conftest import make_minimal_pdf, upload_pdf

pytestmark = pytest.mark.e2e


class TestSecurityInvariants:

    # ── Invariant 1: No raw storage keys ────────────────────────────────────

    def test_upload_response_no_storage_key(self, api_client):
        body = upload_pdf(api_client, make_minimal_pdf())
        assert "storage_key" not in body

    def test_list_response_no_storage_key(self, api_client):
        r = api_client.get("/api/documents")
        for doc in r.json()["documents"]:
            assert "storage_key" not in doc

    def test_status_response_no_storage_key(self, api_client, ready_doc):
        r = api_client.get(f"/api/documents/{ready_doc['id']}/status")
        assert "storage_key" not in r.json()

    def test_link_list_response_no_storage_key(self, api_client, active_link, ready_doc):
        r = api_client.get(f"/api/links?document_id={ready_doc['id']}")
        for lnk in r.json()["links"]:
            assert "storage_key" not in lnk

    def test_validate_response_no_storage_key(self, api_client, active_link):
        r = api_client.post("/api/viewer/validate", json={"token": active_link["token"]})
        assert "storage_key" not in r.json()

    # ── Invariant 2: No bcrypt hash exposure ─────────────────────────────────

    def test_link_create_no_bcrypt_hash(self, api_client, ready_doc):
        r = api_client.post(
            "/api/links",
            json={"document_id": ready_doc["id"], "password": "test123"},
        )
        assert "$2b$" not in r.text
        assert "password_hash" not in r.json()

    def test_link_list_no_bcrypt_hash(self, api_client, password_link, ready_doc):
        r = api_client.get(f"/api/links?document_id={ready_doc['id']}")
        assert "$2b$" not in r.text

    def test_analytics_events_no_bcrypt_hash(self, api_client, active_link):
        api_client.post("/api/analytics/events", json={
            "token": active_link["token"],
            "session_id": "a" * 16,
            "event_type": "page_viewed",
        })
        r = api_client.get("/api/analytics/events")
        assert "$2b$" not in r.text

    # ── Invariant 3: Page endpoint must proxy, never redirect ────────────────

    def test_page_endpoint_no_redirect(self, api_client, active_link, ready_doc):
        if ready_doc.get("status") != "ready":
            pytest.skip("Document not ready")
        r = api_client.post("/api/viewer/validate", json={"token": active_link["token"]})
        sid = r.json()["session_id"]
        r = api_client.get(
            f"/api/viewer/page/{active_link['token']}/1",
            params={"session_id": sid},
            follow_redirects=False,
        )
        assert r.status_code not in (301, 302, 303, 307, 308), \
            f"Page endpoint redirected with status {r.status_code}"

    def test_page_endpoint_is_200_with_image(self, api_client, active_link, ready_doc):
        if ready_doc.get("status") != "ready":
            pytest.skip("Document not ready")
        r = api_client.post("/api/viewer/validate", json={"token": active_link["token"]})
        sid = r.json()["session_id"]
        r = api_client.get(
            f"/api/viewer/page/{active_link['token']}/1",
            params={"session_id": sid},
        )
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("image/webp")

    # ── Invariant 4: IPs are hashed ─────────────────────────────────────────

    def test_events_no_raw_ip(self, api_client, active_link):
        api_client.post("/api/analytics/events", json={
            "token": active_link["token"],
            "session_id": "b" * 16,
            "event_type": "page_viewed",
        })
        r = api_client.get("/api/analytics/events")
        events = r.json().get("events", [])
        for evt in events:
            # Raw 'ip' key must not exist; only ip_hash allowed
            assert "ip" not in evt
            if "ip_hash" in evt and evt["ip_hash"] is not None:
                # Must be a 64-char SHA-256 hex string
                assert len(evt["ip_hash"]) == 64
                int(evt["ip_hash"], 16)  # valid hex

    # ── Invariant 5: All permissions default to false ────────────────────────

    def test_permissions_all_false_by_default(self, api_client, active_link):
        r = api_client.post("/api/viewer/validate", json={"token": active_link["token"]})
        perms = r.json()["permissions"]
        assert perms["can_download"] is False
        assert perms["can_print"] is False
        assert perms["can_copy"] is False
        assert perms["can_right_click"] is False

    # ── Invariant 6: Session ID required for page endpoint ───────────────────

    def test_page_without_session_id_blocked(self, api_client, active_link):
        r = api_client.get(f"/api/viewer/page/{active_link['token']}/1")
        assert r.status_code == 400

    # ── Invariant 7: Watermark is applied to every page response ────────────

    def test_watermark_applied_to_page(self, api_client, active_link, ready_doc):
        if ready_doc.get("status") != "ready":
            pytest.skip("Document not ready")
        r = api_client.post("/api/viewer/validate", json={"token": active_link["token"]})
        sid = r.json()["session_id"]

        r = api_client.get(
            f"/api/viewer/page/{active_link['token']}/1",
            params={"session_id": sid},
        )
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        unique = set(img.getdata())
        assert len(unique) > 10

    # ── Invariant 8: Security headers ────────────────────────────────────────

    def test_page_endpoint_has_security_headers(self, api_client, active_link, ready_doc):
        if ready_doc.get("status") != "ready":
            pytest.skip("Document not ready")
        r = api_client.post("/api/viewer/validate", json={"token": active_link["token"]})
        sid = r.json()["session_id"]
        r = api_client.get(
            f"/api/viewer/page/{active_link['token']}/1",
            params={"session_id": sid},
        )
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert "no-store" in r.headers.get("cache-control", "")
