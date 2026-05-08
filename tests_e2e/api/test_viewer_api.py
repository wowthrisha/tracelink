"""
API contract tests for /api/viewer/validate and /api/viewer/page/*

API shapes:
  POST /api/viewer/validate → 200 {session_id, document_id, document_filename,
                                    page_count, watermark_text, link_id, permissions}
  GET  /api/viewer/page/{token}/{page}?session_id={sid} → 200 image/webp
"""
import io
import pytest
from PIL import Image

pytestmark = pytest.mark.api


class TestValidateLink:

    def test_validate_active_link_returns_200(self, api_client, active_link):
        r = api_client.post(
            "/api/viewer/validate",
            json={"token": active_link["token"]},
        )
        assert r.status_code == 200

    def test_validate_response_has_required_fields(self, api_client, active_link):
        r = api_client.post(
            "/api/viewer/validate",
            json={"token": active_link["token"]},
        )
        body = r.json()
        assert "session_id" in body
        assert "document_id" in body
        assert "page_count" in body
        assert "watermark_text" in body
        assert "permissions" in body

    def test_validate_permissions_all_false(self, api_client, active_link):
        r = api_client.post(
            "/api/viewer/validate",
            json={"token": active_link["token"]},
        )
        perms = r.json()["permissions"]
        assert perms["can_download"] is False
        assert perms["can_print"] is False
        assert perms["can_copy"] is False
        assert perms["can_right_click"] is False

    def test_validate_session_id_is_16_chars(self, api_client, active_link):
        r = api_client.post(
            "/api/viewer/validate",
            json={"token": active_link["token"]},
        )
        sid = r.json()["session_id"]
        assert len(sid) == 16

    def test_validate_invalid_token_returns_404(self, api_client):
        r = api_client.post(
            "/api/viewer/validate",
            json={"token": "x" * 64},
        )
        assert r.status_code == 404

    def test_validate_wrong_password_returns_401(self, api_client, password_link):
        r = api_client.post(
            "/api/viewer/validate",
            json={"token": password_link["token"], "password": "wrongpassword"},
        )
        assert r.status_code == 401

    def test_validate_correct_password_returns_200(self, api_client, password_link):
        r = api_client.post(
            "/api/viewer/validate",
            json={"token": password_link["token"], "password": "s3cr3t!"},
        )
        assert r.status_code == 200

    def test_validate_no_password_on_locked_link_returns_401(self, api_client, password_link):
        r = api_client.post(
            "/api/viewer/validate",
            json={"token": password_link["token"]},
        )
        assert r.status_code == 401

    def test_validate_response_no_bcrypt_hash(self, api_client, active_link):
        r = api_client.post(
            "/api/viewer/validate",
            json={"token": active_link["token"]},
        )
        assert "$2b$" not in r.text

    def test_validate_increments_view_count(self, api_client, create_link, ready_doc):
        link = create_link(label="view-count-test")
        token = link["token"]
        link_id = link["id"]

        # Get initial view count from list endpoint
        links_resp = api_client.get(f"/api/links?document_id={ready_doc['id']}").json()
        initial = next(
            (lnk["view_count"] for lnk in links_resp["links"] if lnk["id"] == link_id), 0
        )

        api_client.post("/api/viewer/validate", json={"token": token})
        api_client.post("/api/viewer/validate", json={"token": token})

        links_resp = api_client.get(f"/api/links?document_id={ready_doc['id']}").json()
        updated = next(
            lnk["view_count"] for lnk in links_resp["links"] if lnk["id"] == link_id
        )
        assert updated == initial + 2

    def test_validate_max_views_enforcement(self, api_client, max_views_link):
        token = max_views_link["token"]
        # First two succeed
        r1 = api_client.post("/api/viewer/validate", json={"token": token})
        r2 = api_client.post("/api/viewer/validate", json={"token": token})
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Third is blocked
        r3 = api_client.post("/api/viewer/validate", json={"token": token})
        assert r3.status_code == 410

    def test_validate_revoked_link_returns_410(self, api_client, create_link):
        link = create_link(label="to-revoke")
        api_client.delete(f"/api/links/{link['id']}")
        r = api_client.post(
            "/api/viewer/validate",
            json={"token": link["token"]},
        )
        assert r.status_code == 410


class TestGetPage:

    def _get_session(self, api_client, token):
        r = api_client.post("/api/viewer/validate", json={"token": token})
        assert r.status_code == 200
        return r.json()["session_id"]

    def test_get_page_returns_200(self, api_client, active_link, ready_doc):
        if ready_doc.get("status") != "ready":
            pytest.skip("Document not ready (Celery not running)")
        sid = self._get_session(api_client, active_link["token"])
        r = api_client.get(
            f"/api/viewer/page/{active_link['token']}/1",
            params={"session_id": sid},
        )
        assert r.status_code == 200

    def test_get_page_content_type_is_webp(self, api_client, active_link, ready_doc):
        if ready_doc.get("status") != "ready":
            pytest.skip("Document not ready")
        sid = self._get_session(api_client, active_link["token"])
        r = api_client.get(
            f"/api/viewer/page/{active_link['token']}/1",
            params={"session_id": sid},
        )
        assert "image/webp" in r.headers["content-type"]

    def test_get_page_has_no_cache_header(self, api_client, active_link, ready_doc):
        if ready_doc.get("status") != "ready":
            pytest.skip("Document not ready")
        sid = self._get_session(api_client, active_link["token"])
        r = api_client.get(
            f"/api/viewer/page/{active_link['token']}/1",
            params={"session_id": sid},
        )
        cc = r.headers.get("cache-control", "")
        assert "no-store" in cc

    def test_get_page_never_redirects(self, api_client, active_link, ready_doc):
        """Backend must proxy image — 3xx redirects are a security violation."""
        if ready_doc.get("status") != "ready":
            pytest.skip("Document not ready")
        sid = self._get_session(api_client, active_link["token"])
        r = api_client.get(
            f"/api/viewer/page/{active_link['token']}/1",
            params={"session_id": sid},
            follow_redirects=False,
        )
        assert r.status_code == 200  # must be 200 not 3xx

    def test_get_page_is_valid_image(self, api_client, active_link, ready_doc):
        if ready_doc.get("status") != "ready":
            pytest.skip("Document not ready")
        sid = self._get_session(api_client, active_link["token"])
        r = api_client.get(
            f"/api/viewer/page/{active_link['token']}/1",
            params={"session_id": sid},
        )
        img = Image.open(io.BytesIO(r.content))
        assert img.width > 0
        assert img.height > 0

    def test_get_page_contains_watermark_pixels(self, api_client, active_link, ready_doc):
        """Watermark must visually alter the image — verify not all pixels identical."""
        if ready_doc.get("status") != "ready":
            pytest.skip("Document not ready")
        sid = self._get_session(api_client, active_link["token"])
        r = api_client.get(
            f"/api/viewer/page/{active_link['token']}/1",
            params={"session_id": sid},
        )
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        pixels = list(img.getdata())
        unique_pixels = set(pixels)
        assert len(unique_pixels) > 1

    def test_get_page_without_session_id_returns_400(self, api_client, active_link):
        r = api_client.get(f"/api/viewer/page/{active_link['token']}/1")
        assert r.status_code == 400

    def test_get_page_invalid_token_returns_404(self, api_client):
        r = api_client.get(
            f"/api/viewer/page/{'x' * 64}/1",
            params={"session_id": "abcdef1234567890"},
        )
        assert r.status_code == 404

    def test_get_page_revoked_link_returns_410(self, api_client, create_link, ready_doc):
        if ready_doc.get("status") != "ready":
            pytest.skip("Document not ready")
        link = create_link(label="to-revoke-page")
        sid = self._get_session(api_client, link["token"])
        api_client.delete(f"/api/links/{link['id']}")
        r = api_client.get(
            f"/api/viewer/page/{link['token']}/1",
            params={"session_id": sid},
        )
        assert r.status_code == 410
