"""
Phase 6 tests — production hardening, Cloudflare readiness, security headers,
proxy IP extraction, rate limiting, cache headers, token validation hardening.
"""
import os
import uuid

import pytest
from unittest.mock import AsyncMock, patch

from app.main import app
from app.database import get_db
from app.auth import get_current_user

# resolve frontend paths the same way test_phase2.py does
_BACKEND_APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../app"))
_FRONTEND_DIR = os.path.abspath(os.path.join(_BACKEND_APP, "../../frontend"))
_HTML_PATH = os.path.join(_FRONTEND_DIR, "SecureDoc.html")
_API_JS_PATH = os.path.join(_FRONTEND_DIR, "api.js")


# ══════════════════════════════════════════════════════════════════════════════
# A. Security Headers
# ══════════════════════════════════════════════════════════════════════════════

class TestSecurityHeaders:

    @pytest.mark.asyncio
    async def test_x_content_type_options_on_health(self, client):
        r = await client.get("/health")
        assert r.headers.get("X-Content-Type-Options") == "nosniff"

    @pytest.mark.asyncio
    async def test_x_frame_options_on_health(self, client):
        r = await client.get("/health")
        assert "X-Frame-Options" in r.headers

    @pytest.mark.asyncio
    async def test_referrer_policy_present(self, client):
        r = await client.get("/health")
        assert "Referrer-Policy" in r.headers

    @pytest.mark.asyncio
    async def test_permissions_policy_present(self, client):
        r = await client.get("/health")
        assert "Permissions-Policy" in r.headers

    @pytest.mark.asyncio
    async def test_csp_present_on_api(self, client):
        r = await client.get("/health")
        assert "Content-Security-Policy" in r.headers

    @pytest.mark.asyncio
    async def test_csp_has_script_src(self, client):
        r = await client.get("/health")
        assert "script-src" in r.headers["Content-Security-Policy"]

    @pytest.mark.asyncio
    async def test_csp_pins_react_by_hash_not_domain(self, client):
        """CSP must use SHA-384 hash pinning for React, not the broad unpkg.com domain."""
        r = await client.get("/health")
        csp = r.headers["Content-Security-Policy"]
        # The broad unpkg.com domain allowance was replaced with specific content hashes
        # to prevent CDN supply-chain compromise (Phase B1 fix)
        assert "https://unpkg.com" not in csp
        assert "sha384-" in csp

    @pytest.mark.asyncio
    async def test_csp_no_unsafe_eval(self, client):
        r = await client.get("/health")
        assert "unsafe-eval" not in r.headers["Content-Security-Policy"]

    @pytest.mark.asyncio
    async def test_csp_frame_ancestors_none(self, client):
        r = await client.get("/health")
        assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]

    @pytest.mark.asyncio
    async def test_csp_allows_supabase(self, client):
        r = await client.get("/health")
        csp = r.headers["Content-Security-Policy"]
        assert "supabase.co" in csp

    @pytest.mark.asyncio
    async def test_csp_allows_blob_for_images(self, client):
        r = await client.get("/health")
        csp = r.headers["Content-Security-Policy"]
        assert "blob:" in csp

    @pytest.mark.asyncio
    async def test_security_headers_on_documents_api(self, client):
        r = await client.get("/api/documents")
        assert "X-Content-Type-Options" in r.headers
        assert "Content-Security-Policy" in r.headers


# ══════════════════════════════════════════════════════════════════════════════
# B. Request ID
# ══════════════════════════════════════════════════════════════════════════════

class TestRequestID:

    @pytest.mark.asyncio
    async def test_request_id_generated_when_absent(self, client):
        r = await client.get("/health")
        assert "X-Request-ID" in r.headers
        # Must be parseable as UUID
        uuid.UUID(r.headers["X-Request-ID"])

    @pytest.mark.asyncio
    async def test_request_id_echoed_from_client(self, client):
        rid = str(uuid.uuid4())
        r = await client.get("/health", headers={"X-Request-ID": rid})
        assert r.headers["X-Request-ID"] == rid

    @pytest.mark.asyncio
    async def test_request_id_present_on_api_endpoint(self, client):
        r = await client.get("/api/documents")
        assert "X-Request-ID" in r.headers

    @pytest.mark.asyncio
    async def test_request_id_present_on_404(self, client):
        r = await client.get("/api/documents/" + str(uuid.uuid4()))
        assert "X-Request-ID" in r.headers

    @pytest.mark.asyncio
    async def test_different_requests_get_different_ids(self, client):
        r1 = await client.get("/health")
        r2 = await client.get("/health")
        assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]


# ══════════════════════════════════════════════════════════════════════════════
# C. Trusted Proxy — unit tests (no HTTP needed)
# ══════════════════════════════════════════════════════════════════════════════

class TestTrustedProxyUnit:

    def _make_middleware(self, **kwargs):
        from app.middleware.trusted_proxy import TrustedProxyMiddleware
        return TrustedProxyMiddleware(None, **kwargs)

    def _req(self, headers=None, host="1.2.3.4"):
        class FakeClient:
            pass
        class FakeRequest:
            pass
        r = FakeRequest()
        r.headers = headers or {}
        r.client = FakeClient()
        r.client.host = host
        return r

    def test_default_uses_client_host(self):
        m = self._make_middleware()
        assert m._resolve(self._req(host="10.0.0.1")) == "10.0.0.1"

    def test_real_ip_header_extracted(self):
        m = self._make_middleware(real_ip_header="CF-Connecting-IP")
        r = self._req(headers={"CF-Connecting-IP": "203.0.113.5"}, host="10.0.0.1")
        assert m._resolve(r) == "203.0.113.5"

    def test_real_ip_header_multi_value_takes_first(self):
        m = self._make_middleware(real_ip_header="CF-Connecting-IP")
        r = self._req(headers={"CF-Connecting-IP": "1.1.1.1, 2.2.2.2"}, host="10.0.0.1")
        assert m._resolve(r) == "1.1.1.1"

    def test_xff_depth_1_single_hop(self):
        m = self._make_middleware(trusted_proxy_depth=1)
        r = self._req(headers={"X-Forwarded-For": "203.0.113.1, 10.0.0.1"}, host="10.0.0.2")
        assert m._resolve(r) == "203.0.113.1"

    def test_xff_depth_1_no_spoof(self):
        m = self._make_middleware(trusted_proxy_depth=1)
        # Attacker prepends fake IPs; rightmost is always our proxy's addition
        r = self._req(headers={"X-Forwarded-For": "evil, fake, 203.0.113.1, 10.0.0.1"}, host="10.0.0.2")
        result = m._resolve(r)
        assert result != "evil"
        assert result != "fake"
        assert result == "203.0.113.1"

    def test_real_ip_absent_falls_back_to_client_host(self):
        m = self._make_middleware(real_ip_header="CF-Connecting-IP")
        r = self._req(headers={}, host="10.0.0.1")
        assert m._resolve(r) == "10.0.0.1"

    def test_no_client_returns_none(self):
        m = self._make_middleware()
        class FakeRequest:
            headers = {}
            client = None
        assert m._resolve(FakeRequest()) is None


# ══════════════════════════════════════════════════════════════════════════════
# D. Rate Limit Key Function
# ══════════════════════════════════════════════════════════════════════════════

class TestRateLimitKeyFunc:

    def test_uses_state_client_ip(self):
        from app.middleware.rate_limit import _get_real_client_ip
        class State:
            client_ip = "203.0.113.99"
        class Req:
            state = State()
            client = None
        assert _get_real_client_ip(Req()) == "203.0.113.99"

    def test_falls_back_to_client_host(self):
        from app.middleware.rate_limit import _get_real_client_ip
        class State:
            pass
        class Client:
            host = "5.5.5.5"
        class Req:
            state = State()
            client = Client()
        assert _get_real_client_ip(Req()) == "5.5.5.5"

    def test_no_client_returns_loopback(self):
        from app.middleware.rate_limit import _get_real_client_ip
        class State:
            pass
        class Req:
            state = State()
            client = None
        assert _get_real_client_ip(Req()) == "127.0.0.1"


# ══════════════════════════════════════════════════════════════════════════════
# E. Token Validation Hardening
# ══════════════════════════════════════════════════════════════════════════════

class TestTokenHardening:

    @pytest.mark.asyncio
    async def test_gate_unknown_token_returns_not_found(self, client):
        r = await client.get("/api/viewer/gate/totally-unknown-token-xyz")
        assert r.status_code == 200
        assert r.json()["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_gate_very_long_token_safe(self, client):
        long = "A" * 500
        r = await client.get(f"/api/viewer/gate/{long}")
        assert r.status_code in (200, 404, 400)

    @pytest.mark.asyncio
    async def test_validate_unknown_token_returns_error(self, client):
        r = await client.post("/api/viewer/validate", json={"token": "no-such-token"})
        assert r.status_code in (404, 410)

    @pytest.mark.asyncio
    async def test_validate_empty_token_returns_error(self, client):
        r = await client.post("/api/viewer/validate", json={"token": ""})
        assert r.status_code in (404, 410, 400, 422)

    @pytest.mark.asyncio
    async def test_session_id_is_32_hex_chars(self, client, active_link):
        r = await client.post("/api/viewer/validate", json={"token": active_link.token})
        assert r.status_code == 200
        sid = r.json()["session_id"]
        assert len(sid) == 32
        assert all(c in "0123456789abcdef" for c in sid)

    @pytest.mark.asyncio
    async def test_revoked_token_gate_shows_revoked(self, client, revoked_link):
        r = await client.get(f"/api/viewer/gate/{revoked_link.token}")
        assert r.json()["status"] == "revoked"

    @pytest.mark.asyncio
    async def test_revoked_token_validate_fails_immediately(self, client, revoked_link):
        r = await client.post("/api/viewer/validate", json={"token": revoked_link.token})
        assert r.status_code == 410

    @pytest.mark.asyncio
    async def test_expired_token_gate_shows_expired(self, client, expired_link):
        r = await client.get(f"/api/viewer/gate/{expired_link.token}")
        assert r.json()["status"] == "expired"

    @pytest.mark.asyncio
    async def test_token_not_in_any_response_body(self, client, active_link):
        r = await client.post("/api/viewer/validate", json={"token": active_link.token})
        # session_id is present but should not equal the link token
        body = str(r.json())
        assert active_link.token not in body


# ══════════════════════════════════════════════════════════════════════════════
# F. Cache Headers on Viewer Responses
# ══════════════════════════════════════════════════════════════════════════════

class TestViewerCacheHeaders:

    @pytest.mark.asyncio
    async def test_page_response_has_no_store(self, client, active_link):
        r = await client.post("/api/viewer/validate", json={"token": active_link.token})
        session_id = r.json()["session_id"]
        r2 = await client.get(
            f"/api/viewer/page/{active_link.token}/1?session_id={session_id}"
        )
        cc = r2.headers.get("Cache-Control", "")
        assert "no-store" in cc or "no-cache" in cc

    @pytest.mark.asyncio
    async def test_text_chunk_has_no_store(self, client, active_text_link):
        link, doc = active_text_link
        r = await client.post("/api/viewer/validate", json={"token": link.token})
        session_id = r.json()["session_id"]
        with patch(
            "app.services.storage.StorageService.download_bytes",
            new_callable=AsyncMock,
            return_value=b"line 1\nline 2\n",
        ):
            r2 = await client.get(
                f"/api/viewer/text/{link.token}/1?session_id={session_id}"
            )
        if r2.status_code == 200:
            cc = r2.headers.get("Cache-Control", "")
            assert "no-store" in cc or "no-cache" in cc


# ══════════════════════════════════════════════════════════════════════════════
# G. Cloudflare / Proxy Integration (end-to-end via HTTP client)
# ══════════════════════════════════════════════════════════════════════════════

class TestCloudflareIntegration:

    @pytest.mark.asyncio
    async def test_cf_connecting_ip_does_not_break_validate(self, client, active_link):
        r = await client.post(
            "/api/viewer/validate",
            json={"token": active_link.token},
            headers={"CF-Connecting-IP": "203.0.113.1"},
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_xff_does_not_break_validate(self, client, active_link):
        r = await client.post(
            "/api/viewer/validate",
            json={"token": active_link.token},
            headers={"X-Forwarded-For": "203.0.113.1, 10.0.0.1"},
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_x_forwarded_proto_accepted(self, client):
        r = await client.get("/health", headers={"X-Forwarded-Proto": "https"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_request_id_from_cloudflare_echoed(self, client):
        cf_ray = "7f3b2c1d-IAD"  # Cloudflare Ray ID format
        r = await client.get("/health", headers={"X-Request-ID": cf_ray})
        assert r.headers["X-Request-ID"] == cf_ray


# ══════════════════════════════════════════════════════════════════════════════
# H. Frontend CSP compliance — no inline scripts in HTML
# ══════════════════════════════════════════════════════════════════════════════

class TestFrontendCSPCompliance:

    def _read_html(self) -> str:
        with open(_HTML_PATH, encoding="utf-8") as f:
            return f.read()

    def _read_api_js(self) -> str:
        with open(_API_JS_PATH, encoding="utf-8") as f:
            return f.read()

    def test_html_file_exists(self):
        assert os.path.exists(_HTML_PATH)

    def test_no_inline_script_blocks_in_html(self):
        import re
        html = self._read_html()
        # Find all <script> tags; none should be inline (no src attribute)
        inline = re.findall(r"<script(?![^>]*\bsrc\s*=)[^>]*>[\s\S]*?</script>", html)
        assert len(inline) == 0, (
            f"Found {len(inline)} inline <script> block(s) in HTML — "
            "move them to api.js for CSP compliance. Found: {inline[:1]}"
        )

    def test_api_js_has_token_extraction_logic(self):
        api_js = self._read_api_js()
        assert "__PUBLIC_TOKEN" in api_js
        assert "__INITIAL_SCREEN" in api_js

    def test_html_loads_react_from_unpkg_with_sri(self):
        """React is still loaded from unpkg but must have SRI hash for CSP hash-pinning."""
        html = self._read_html()
        assert "https://unpkg.com/react@" in html
        # The CSP pins by content hash (not domain), so SRI hashes in HTML are mandatory
        assert 'integrity="sha384-' in html

    def test_html_react_scripts_have_integrity(self):
        html = self._read_html()
        assert 'integrity="sha384-' in html

    def test_html_loads_api_js(self):
        html = self._read_html()
        assert 'src="api.js"' in html or "src='api.js'" in html

    def test_html_loads_bundle(self):
        html = self._read_html()
        assert "dist/app.bundle.js" in html


# ══════════════════════════════════════════════════════════════════════════════
# I. Structured logging — path sanitization
# ══════════════════════════════════════════════════════════════════════════════

class TestPathSanitization:

    def test_token_redacted_in_path(self):
        from app.middleware.request_id import _sanitize_path
        path = "/api/viewer/page/eyJhbGciOiJIUzI1NiJ9abcde/1"
        result = _sanitize_path(path)
        assert "eyJhbGciOiJIUzI1NiJ9abcde" not in result
        assert "[token]" in result

    def test_short_segment_not_redacted(self):
        from app.middleware.request_id import _sanitize_path
        assert _sanitize_path("/api/documents") == "/api/documents"
        assert _sanitize_path("/health") == "/health"

    def test_uuid_segment_redacted(self):
        from app.middleware.request_id import _sanitize_path
        uid = "550e8400-e29b-41d4-a716-446655440000"
        result = _sanitize_path(f"/api/documents/{uid}")
        assert uid not in result


# ══════════════════════════════════════════════════════════════════════════════
# J. No regression — existing flows still work
# ══════════════════════════════════════════════════════════════════════════════

class TestNoRegression:

    @pytest.mark.asyncio
    async def test_pdf_upload_works(self, client, sample_pdf_bytes):
        files = {"file": ("test.pdf", sample_pdf_bytes, "application/pdf")}
        r = await client.post("/api/documents/upload", files=files)
        assert r.status_code == 202

    @pytest.mark.asyncio
    async def test_pdf_validate_works(self, client, active_link):
        r = await client.post("/api/viewer/validate", json={"token": active_link.token})
        assert r.status_code == 200
        assert "session_id" in r.json()

    @pytest.mark.asyncio
    async def test_gate_active_link_works(self, client, active_link):
        r = await client.get(f"/api/viewer/gate/{active_link.token}")
        assert r.status_code == 200
        assert r.json()["status"] == "active"

    @pytest.mark.asyncio
    async def test_revoked_link_fails_validate(self, client, revoked_link):
        r = await client.post("/api/viewer/validate", json={"token": revoked_link.token})
        assert r.status_code == 410

    @pytest.mark.asyncio
    async def test_expired_link_fails_validate(self, client, expired_link):
        r = await client.post("/api/viewer/validate", json={"token": expired_link.token})
        assert r.status_code == 410

    @pytest.mark.asyncio
    async def test_list_documents_works(self, client):
        r = await client.get("/api/documents")
        assert r.status_code == 200
        assert "documents" in r.json()

    @pytest.mark.asyncio
    async def test_page_endpoint_does_not_redirect(self, client, active_link):
        r = await client.post("/api/viewer/validate", json={"token": active_link.token})
        session_id = r.json()["session_id"]
        r2 = await client.get(
            f"/api/viewer/page/{active_link.token}/1?session_id={session_id}",
            follow_redirects=False,
        )
        assert r2.status_code not in (301, 302, 307, 308)

    @pytest.mark.asyncio
    async def test_health_endpoint_works(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
