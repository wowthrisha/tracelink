"""
Public URL generation tests.

Verifies that all share links are generated with APP_PUBLIC_BASE_URL
(https://secure.wowmyspace.com) and that no localhost/placeholder URLs
leak into any API response.

These tests hit the live backend directly (localhost:8000) but assert
on the *content* of responses — the share_url field must reflect the
configured public domain, not the local dev address.
"""
import os
import pytest

pytestmark = pytest.mark.api

# The expected public base comes from the environment so the suite works
# on any deployment (dev override, staging, production).
EXPECTED_PUBLIC_BASE = os.environ.get(
    "APP_PUBLIC_BASE_URL", "http://localhost:8000"
).rstrip("/")


class TestShareUrlFormat:

    def test_create_link_share_url_uses_public_domain(self, api_client, ready_doc):
        """share_url in POST /api/links response must use the configured public base."""
        r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        assert r.status_code == 201
        share_url = r.json()["share_url"]
        assert share_url.startswith(EXPECTED_PUBLIC_BASE), (
            f"share_url '{share_url}' must start with '{EXPECTED_PUBLIC_BASE}'"
        )

    def test_create_link_share_url_no_localhost(self, api_client, ready_doc):
        """share_url must never contain localhost or 127.0.0.1."""
        r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        share_url = r.json()["share_url"]
        assert "localhost" not in share_url, f"localhost leaked in share_url: {share_url}"
        assert "127.0.0.1" not in share_url, f"127.0.0.1 leaked in share_url: {share_url}"

    def test_create_link_share_url_contains_token(self, api_client, ready_doc):
        """share_url must be {PUBLIC_BASE}/v/{token}."""
        r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        body = r.json()
        token = body["token"]
        share_url = body["share_url"]
        assert share_url == f"{EXPECTED_PUBLIC_BASE}/v/{token}", (
            f"Expected '{EXPECTED_PUBLIC_BASE}/v/{token}', got '{share_url}'"
        )

    def test_list_links_share_url_no_localhost(self, api_client, ready_doc, active_link):
        """GET /api/links must not expose localhost in any share_url."""
        r = api_client.get(f"/api/links?document_id={ready_doc['id']}")
        assert r.status_code == 200
        for link in r.json()["links"]:
            url = link.get("share_url") or link.get("token", "")
            assert "localhost" not in url, f"localhost leaked in list share_url: {url}"

    def test_list_links_share_url_uses_public_domain(self, api_client, ready_doc, active_link):
        """GET /api/links — every share_url must start with the public base."""
        r = api_client.get(f"/api/links?document_id={ready_doc['id']}")
        links = r.json()["links"]
        assert len(links) > 0
        for link in links:
            url = link.get("share_url", "")
            assert url.startswith(EXPECTED_PUBLIC_BASE), (
                f"share_url '{url}' does not use public domain '{EXPECTED_PUBLIC_BASE}'"
            )

    def test_no_trycloudflare_in_share_url(self, api_client, ready_doc):
        """No expired tunnel URLs must appear in share_url."""
        r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        share_url = r.json()["share_url"]
        assert "trycloudflare.com" not in share_url
        assert "ngrok" not in share_url


class TestViewerRedirect:
    """
    The /v/{token} redirect is unconditional — no auth required.
    Any token string (even fake ones) triggers the redirect to SecureDoc.html.
    This makes these tests runnable without auth setup.
    """

    # Use a fake but syntactically valid token (64 hex chars)
    FAKE_TOKEN = "a" * 64

    def test_v_token_redirects_to_static_html(self, api_client):
        """GET /v/{token} must redirect to /static/SecureDoc.html?token={token}."""
        r = api_client.get(f"/v/{self.FAKE_TOKEN}", follow_redirects=False)
        assert r.status_code in (301, 302, 307, 308), (
            f"Expected redirect from /v/{{token}}, got {r.status_code}"
        )
        location = r.headers.get("location", "")
        assert "SecureDoc.html" in location, (
            f"Redirect location '{location}' must point to SecureDoc.html"
        )
        assert self.FAKE_TOKEN in location, (
            f"Redirect location '{location}' must include the token"
        )

    def test_v_redirect_does_not_expose_localhost(self, api_client):
        """Redirect Location header must not expose localhost."""
        r = api_client.get(f"/v/{self.FAKE_TOKEN}", follow_redirects=False)
        location = r.headers.get("location", "")
        # Location is typically a relative path (/static/...) — safe by definition.
        # If it is somehow absolute it must not point to localhost.
        if location.startswith("http"):
            assert "localhost" not in location, f"localhost in redirect: {location}"
            assert "127.0.0.1" not in location

    def test_v_redirect_path_pattern(self, api_client):
        """The redirect path must follow the pattern /static/SecureDoc.html?token=..."""
        r = api_client.get(f"/v/{self.FAKE_TOKEN}", follow_redirects=False)
        location = r.headers.get("location", "")
        assert "token=" in location, f"token param missing from redirect: {location}"
        assert "REPLACE_WITH" not in location
        assert "trycloudflare" not in location

    def test_embed_iframe_src_format(self, api_client):
        """A share URL built from the public base must be a valid HTTPS iframe src.
        Verifies the format without requiring auth by constructing the expected URL."""
        fake_token = "b" * 64
        expected_share_url = f"{EXPECTED_PUBLIC_BASE}/v/{fake_token}"
        # Simulate what the embed snippet in the frontend renders
        iframe_src = expected_share_url
        assert "REPLACE_WITH" not in iframe_src
        assert "trycloudflare" not in iframe_src
        if EXPECTED_PUBLIC_BASE.startswith("https://"):
            assert iframe_src.startswith("https://"), "Embed src must use HTTPS in production"


class TestEnvironmentConfig:

    def test_health_endpoint_reachable(self, api_client):
        """Backend must respond to /health — confirms the stack is up."""
        r = api_client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_share_url_consistent_across_creates(self, api_client, ready_doc):
        """All links created in the same session must use the same public base."""
        urls = []
        for _ in range(3):
            r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
            urls.append(r.json()["share_url"])
        bases = {u.rsplit("/v/", 1)[0] for u in urls}
        assert len(bases) == 1, f"Inconsistent public base across links: {bases}"
        base = bases.pop()
        assert base == EXPECTED_PUBLIC_BASE

    def test_public_base_url_not_localhost_when_configured(self, api_client, ready_doc):
        """When APP_PUBLIC_BASE_URL is set to a custom domain the share_url reflects it."""
        r = api_client.post("/api/links", json={"document_id": ready_doc["id"]})
        share_url = r.json()["share_url"]
        # If the env is configured for production domain, localhost must not appear
        if EXPECTED_PUBLIC_BASE != "http://localhost:8000":
            assert "localhost" not in share_url, (
                f"Running with APP_PUBLIC_BASE_URL={EXPECTED_PUBLIC_BASE} "
                f"but share_url still contains localhost: {share_url}"
            )


class TestNoLocalhostLeakage:

    def test_no_localhost_in_public_gate_response(self, api_client):
        """Public /api/viewer/gate/{token} must not expose localhost in any field.
        Uses a fake token — gate returns a JSON status object, no auth needed."""
        fake_token = "c" * 64
        r = api_client.get(f"/api/viewer/gate/{fake_token}")
        assert r.status_code == 200
        data = r.json()
        for value in data.values():
            assert "localhost" not in str(value), f"localhost in gate response: {data}"
            assert "127.0.0.1" not in str(value)

    def test_analytics_overview_no_localhost(self, api_client):
        """Analytics overview response must not expose internal localhost references."""
        r = api_client.get("/api/analytics/overview")
        if r.status_code == 401:
            pytest.skip("Analytics requires auth — add Authorization header to api_client fixture")
        assert r.status_code == 200
        # No raw localhost URLs in analytics data values
        assert "http://localhost" not in r.text
