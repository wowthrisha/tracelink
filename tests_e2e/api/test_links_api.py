"""
API contract tests for /api/links/*

API shapes:
  POST  /api/links            → 201 LinkResponse {id, token, share_url, label,
                                   expires_at, max_views, view_count, created_at}
  GET   /api/links?document_id → 200 {"links": [LinkSummary {id, token, label,
                                   expires_at, max_views, view_count, revoked_at,
                                   created_at, is_active, has_password}]}
  DELETE /api/links/{id}      → 200 RevokeResponse {id, revoked_at, message}
  PATCH  /api/links/{id}      → 200 LinkSummary
"""
import os
import pytest

pytestmark = pytest.mark.api

EXPECTED_PUBLIC_BASE = os.environ.get(
    "APP_PUBLIC_BASE_URL", "http://localhost:8000"
).rstrip("/")


class TestCreateLink:

    def test_create_returns_201(self, api_client, ready_doc):
        r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        assert r.status_code == 201

    def test_create_response_has_required_fields(self, api_client, ready_doc):
        r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        body = r.json()
        assert "id" in body
        assert "token" in body
        assert "share_url" in body
        assert "view_count" in body

    def test_token_is_64_chars(self, api_client, ready_doc):
        r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        assert len(r.json()["token"]) == 64

    def test_token_is_unique_per_link(self, api_client, ready_doc):
        tokens = set()
        for _ in range(5):
            r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
            tokens.add(r.json()["token"])
        assert len(tokens) == 5

    def test_password_hash_never_exposed_in_create(self, api_client, ready_doc):
        r = api_client.post(
            "/api/links",
            json={"document_id": ready_doc["id"], "password": "secret"},
        )
        body = r.json()
        assert "password_hash" not in body
        # bcrypt hash must not appear in raw text
        assert "$2b$" not in r.text

    def test_create_with_max_views(self, api_client, ready_doc):
        r = api_client.post(
            "/api/links",
            json={"document_id": ready_doc["id"], "max_views": 10},
        )
        assert r.status_code == 201
        assert r.json()["max_views"] == 10

    def test_create_with_label(self, api_client, ready_doc):
        r = api_client.post(
            "/api/links",
            json={"document_id": ready_doc["id"], "label": "My Share"},
        )
        assert r.json()["label"] == "My Share"

    def test_create_for_nonexistent_doc_returns_404(self, api_client):
        r = api_client.post(
            "/api/links",
            json={"document_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert r.status_code == 404

    def test_share_url_uses_public_base(self, api_client, ready_doc):
        """share_url must be rooted at APP_PUBLIC_BASE_URL, not localhost."""
        r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        share_url = r.json()["share_url"]
        assert share_url.startswith(EXPECTED_PUBLIC_BASE), (
            f"share_url '{share_url}' must start with '{EXPECTED_PUBLIC_BASE}'"
        )
        assert "localhost" not in share_url

    def test_share_url_is_v_token_path(self, api_client, ready_doc):
        """share_url must follow the pattern {base}/v/{64-char-token}."""
        r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        body = r.json()
        expected = f"{EXPECTED_PUBLIC_BASE}/v/{body['token']}"
        assert body["share_url"] == expected


class TestGetLinks:

    def test_get_links_returns_200(self, api_client, ready_doc):
        r = api_client.get(f"/api/links?document_id={ready_doc['id']}")
        assert r.status_code == 200

    def test_get_links_response_has_links_key(self, api_client, ready_doc):
        r = api_client.get(f"/api/links?document_id={ready_doc['id']}")
        body = r.json()
        assert "links" in body
        assert isinstance(body["links"], list)

    def test_get_links_no_password_hash(self, api_client, ready_doc, active_link):
        r = api_client.get(f"/api/links?document_id={ready_doc['id']}")
        for link in r.json()["links"]:
            assert "password_hash" not in link
            assert "$2b$" not in str(link)

    def test_get_links_has_has_password_field(self, api_client, ready_doc, active_link):
        r = api_client.get(f"/api/links?document_id={ready_doc['id']}")
        for link in r.json()["links"]:
            assert "has_password" in link

    def test_created_link_appears_in_list(self, api_client, ready_doc, active_link):
        r = api_client.get(f"/api/links?document_id={ready_doc['id']}")
        ids = [lnk["id"] for lnk in r.json()["links"]]
        assert active_link["id"] in ids


class TestRevokeLink:

    def test_revoke_returns_200(self, api_client, create_link):
        link = create_link()
        r = api_client.delete(f"/api/links/{link['id']}")
        assert r.status_code == 200

    def test_revoked_link_has_revoked_at(self, api_client, create_link):
        link = create_link()
        r = api_client.delete(f"/api/links/{link['id']}")
        body = r.json()
        assert body.get("revoked_at") is not None

    def test_revoke_nonexistent_returns_404(self, api_client):
        r = api_client.delete("/api/links/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


class TestUpdateLink:

    def test_patch_label_returns_200(self, api_client, create_link):
        link = create_link(label="original")
        r = api_client.patch(
            f"/api/links/{link['id']}",
            json={"label": "updated"},
        )
        assert r.status_code == 200
        assert r.json()["label"] == "updated"

    def test_patch_max_views(self, api_client, create_link):
        link = create_link()
        r = api_client.patch(
            f"/api/links/{link['id']}",
            json={"max_views": 99},
        )
        assert r.status_code == 200
        assert r.json()["max_views"] == 99

    def test_patch_no_password_hash_in_response(self, api_client, create_link):
        link = create_link()
        r = api_client.patch(f"/api/links/{link['id']}", json={"label": "safe"})
        assert "password_hash" not in r.json()
        assert "$2b$" not in r.text
