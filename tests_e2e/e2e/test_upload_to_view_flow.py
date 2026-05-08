"""
E2E Scenario: Upload → Process → Share → View

Full end-to-end flow without any mocks.
Requires: backend on :8000, Celery worker running (or demo stack).
"""
import io
import time
import pytest
import httpx
from PIL import Image
from conftest import make_minimal_pdf, upload_pdf, poll_until_ready

import os

pytestmark = pytest.mark.e2e

BASE = "http://localhost:8000"
EXPECTED_PUBLIC_BASE = os.environ.get(
    "APP_PUBLIC_BASE_URL", "http://localhost:8000"
).rstrip("/")


class TestUploadToViewFlow:

    def test_full_upload_create_link_validate_view(self, api_client, ready_doc, active_link):
        """
        Complete happy-path using the session-scoped ready_doc:
        1. Doc uploaded and (optionally) ready
        2. Share link created → 201, token 64 chars
        3. Validate link → 200, session_id 16 chars
        4. Fetch page 1 → 200, image/webp, watermark present
        """
        # Verify upload result
        assert ready_doc["id"]
        assert "storage_key" not in ready_doc

        # Verify link
        link = active_link
        assert len(link["token"]) == 64
        assert "password_hash" not in link

        # Validate
        r = api_client.post("/api/viewer/validate", json={"token": link["token"]})
        assert r.status_code == 200
        session = r.json()
        assert len(session["session_id"]) == 16
        assert session["permissions"]["can_download"] is False

        if ready_doc.get("status") != "ready":
            pytest.skip("Document not ready — Celery worker not running")

        # Fetch page
        r = api_client.get(
            f"/api/viewer/page/{link['token']}/1",
            params={"session_id": session["session_id"]},
        )
        assert r.status_code == 200
        assert "image/webp" in r.headers["content-type"]
        assert "no-store" in r.headers.get("cache-control", "")

        # Verify watermarked image
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        assert img.width > 0
        pixels = set(img.getdata())
        assert len(pixels) > 1

    def test_document_appears_in_list_after_upload(self, api_client, ready_doc):
        r = api_client.get("/api/documents")
        ids = [d["id"] for d in r.json()["documents"]]
        assert ready_doc["id"] in ids

    def test_delete_removes_from_list(self, api_client, minimal_pdf_bytes):
        """Upload a fresh doc and verify delete removes it from the list."""
        body = upload_pdf(api_client, minimal_pdf_bytes, "to_delete.pdf")
        doc_id = body["id"]

        api_client.delete(f"/api/documents/{doc_id}")

        r = api_client.get("/api/documents")
        ids = [d["id"] for d in r.json()["documents"]]
        assert doc_id not in ids

    def test_upload_increments_total_documents(self, api_client, minimal_pdf_bytes):
        before = api_client.get("/api/analytics/overview").json()["total_documents"]
        upload_pdf(api_client, minimal_pdf_bytes)
        after = api_client.get("/api/analytics/overview").json()["total_documents"]
        assert after == before + 1

    def test_storage_key_never_exposed_at_any_endpoint(self, api_client, ready_doc):
        doc_id = ready_doc["id"]
        for url in ["/api/documents", f"/api/documents/{doc_id}/status"]:
            r = api_client.get(url)
            assert "storage_key" not in r.text, f"storage_key exposed at {url}"

    def test_share_url_uses_public_domain(self, api_client, active_link):
        """Share link URL must use the configured public domain."""
        share_url = active_link["share_url"]
        assert share_url.startswith(EXPECTED_PUBLIC_BASE), (
            f"Expected '{EXPECTED_PUBLIC_BASE}', got '{share_url}'"
        )
        assert "localhost" not in share_url

    def test_viewer_redirect_works(self, api_client, active_link):
        """GET /v/{token} must redirect (3xx) to SecureDoc.html with the token."""
        token = active_link["token"]
        r = api_client.get(f"/v/{token}", follow_redirects=False)
        assert r.status_code in (301, 302, 307, 308)
        location = r.headers.get("location", "")
        assert "SecureDoc.html" in location
        assert token in location
