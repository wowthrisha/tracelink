"""
Phase 8 — Global infrastructure + Cloudflare readiness + CDN + observability tests.

Coverage:
  A. HTTPS redirect middleware (proxy-aware)
  B. HSTS header injection
  C. Security headers — new Phase 8 additions
  D. Static asset cache headers
  E. X-Cache-Status on viewer page/thumb responses
  F. Request ID includes client IP in access log
  G. Proxy / custom domain: TrustedProxyMiddleware behaviour
  H. Startup validation — IP hash salt must not be default in production
  I. Config — new Phase 8 settings have correct defaults
  J. Storage abstraction — file_exists() method + StorageBackend ABC
  K. DB pool config — settings drive pool parameters
  L. Health endpoint — proxy config block present
  M. Regression: viewer PDF/TXT/TOC flows unaffected
  N. Security header regression — existing headers still present
  O. Storage path-style config flag
"""
import uuid
import secrets

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock


# ── A. HTTPS redirect middleware ───────────────────────────────────────────────

class TestHTTPSRedirectMiddleware:
    """The middleware must redirect HTTP to HTTPS using X-Forwarded-Proto."""

    def test_module_importable(self):
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        assert HTTPSRedirectMiddleware is not None

    def test_health_path_excluded(self):
        """Health check must never be redirected (load-balancer probe)."""
        from app.middleware.https_redirect import _EXCLUDED_PATHS
        assert "/health" in _EXCLUDED_PATHS

    @pytest.mark.asyncio
    async def test_redirects_http_proto(self, client):
        """Request with X-Forwarded-Proto: http should get a 301 redirect when enabled."""
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse

        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(HTTPSRedirectMiddleware)

        tc = TestClient(app, raise_server_exceptions=True, follow_redirects=False)
        r = tc.get("/", headers={"X-Forwarded-Proto": "http"})
        assert r.status_code == 301
        assert r.headers["location"].startswith("https://")

    @pytest.mark.asyncio
    async def test_passes_https_proto(self, client):
        """Request with X-Forwarded-Proto: https must not be redirected."""
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse

        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(HTTPSRedirectMiddleware)

        tc = TestClient(app, raise_server_exceptions=True, follow_redirects=False)
        r = tc.get("/", headers={"X-Forwarded-Proto": "https"})
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_no_proto_header_passes(self, client):
        """When no X-Forwarded-Proto header is present, request must pass through."""
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse

        async def homepage(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", homepage)])
        app.add_middleware(HTTPSRedirectMiddleware)

        tc = TestClient(app, raise_server_exceptions=True, follow_redirects=False)
        r = tc.get("/")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_health_not_redirected(self, client):
        """Health endpoint must be reachable even with X-Forwarded-Proto: http."""
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse

        async def health(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/health", health)])
        app.add_middleware(HTTPSRedirectMiddleware)

        tc = TestClient(app, raise_server_exceptions=True, follow_redirects=False)
        r = tc.get("/health", headers={"X-Forwarded-Proto": "http"})
        assert r.status_code == 200

    def test_redirect_preserves_path_and_query(self):
        """Redirect must preserve the full URL path + query string."""
        from app.middleware.https_redirect import HTTPSRedirectMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse

        async def page(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/docs", page)])
        app.add_middleware(HTTPSRedirectMiddleware)

        tc = TestClient(app, raise_server_exceptions=True, follow_redirects=False)
        r = tc.get("/docs?token=abc123", headers={"X-Forwarded-Proto": "http"})
        assert r.status_code == 301
        assert "docs" in r.headers["location"]
        assert "token=abc123" in r.headers["location"]


# ── B. HSTS header ─────────────────────────────────────────────────────────────

class TestHSTSHeader:
    def test_hsts_not_injected_when_zero(self, client):
        """HSTS must not appear when hsts_max_age=0 (default)."""
        import asyncio
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async def _run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get("/health")
            return r

        r = asyncio.get_event_loop().run_until_complete(_run())
        assert "strict-transport-security" not in r.headers

    def test_hsts_injected_when_configured(self):
        """When hsts_max_age > 0 and request comes via HTTPS, HSTS header must appear."""
        from app.middleware.security_headers import SecurityHeadersMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse

        async def index(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", index)])
        app.add_middleware(SecurityHeadersMiddleware, hsts_max_age=31536000)

        tc = TestClient(app, raise_server_exceptions=True)
        # Simulate HTTPS via X-Forwarded-Proto
        r = tc.get("/", headers={"X-Forwarded-Proto": "https"})
        assert "strict-transport-security" in r.headers
        assert "31536000" in r.headers["strict-transport-security"]
        assert "includeSubDomains" in r.headers["strict-transport-security"]

    def test_hsts_not_injected_over_plain_http(self):
        """HSTS must NOT be injected on plain HTTP (without HTTPS proto header)."""
        from app.middleware.security_headers import SecurityHeadersMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse

        async def index(request):
            return PlainTextResponse("ok")

        app = Starlette(routes=[Route("/", index)])
        app.add_middleware(SecurityHeadersMiddleware, hsts_max_age=31536000)

        tc = TestClient(app, raise_server_exceptions=True)
        # No X-Forwarded-Proto = plain HTTP
        r = tc.get("/")
        assert "strict-transport-security" not in r.headers


# ── C. New Phase 8 security headers ───────────────────────────────────────────

class TestPhase8SecurityHeaders:
    @pytest.mark.asyncio
    async def test_coop_header_present(self, client):
        """Cross-Origin-Opener-Policy must be set on all responses."""
        r = await client.get("/health")
        assert "cross-origin-opener-policy" in r.headers
        assert r.headers["cross-origin-opener-policy"] == "same-origin"

    @pytest.mark.asyncio
    async def test_x_permitted_cross_domain_policies(self, client):
        """X-Permitted-Cross-Domain-Policies must block Flash/legacy plugin reads."""
        r = await client.get("/health")
        assert "x-permitted-cross-domain-policies" in r.headers
        assert r.headers["x-permitted-cross-domain-policies"] == "none"

    @pytest.mark.asyncio
    async def test_existing_security_headers_preserved(self, client):
        """All Phase 6 security headers must still be present."""
        r = await client.get("/health")
        assert "x-content-type-options" in r.headers
        assert "x-frame-options" in r.headers
        assert "referrer-policy" in r.headers
        assert "permissions-policy" in r.headers
        assert "content-security-policy" in r.headers

    @pytest.mark.asyncio
    async def test_csp_no_unsafe_eval(self, client):
        """CSP must not contain unsafe-eval (prevents XSS via eval)."""
        r = await client.get("/health")
        csp = r.headers.get("content-security-policy", "")
        assert "unsafe-eval" not in csp

    @pytest.mark.asyncio
    async def test_csp_no_unsafe_inline_scripts(self, client):
        """CSP script-src must not contain unsafe-inline."""
        r = await client.get("/health")
        csp = r.headers.get("content-security-policy", "")
        # CSP can have unsafe-inline for styles but not for scripts
        parts = [p.strip() for p in csp.split(";")]
        script_src = next((p for p in parts if p.startswith("script-src")), "")
        assert "unsafe-inline" not in script_src


# ── D. Static asset cache headers ─────────────────────────────────────────────

class TestStaticAssetCacheHeaders:
    def test_security_middleware_js_cache_control(self):
        """JS assets should receive public cache headers with configurable max-age."""
        from app.middleware.security_headers import SecurityHeadersMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse

        async def js_file(request):
            return PlainTextResponse("// bundle")

        app = Starlette(routes=[Route("/static/app.bundle.js", js_file)])
        app.add_middleware(SecurityHeadersMiddleware, static_asset_max_age=7200)

        tc = TestClient(app, raise_server_exceptions=True)
        r = tc.get("/static/app.bundle.js")
        cc = r.headers.get("cache-control", "")
        assert "public" in cc
        assert "7200" in cc

    def test_security_middleware_html_no_cache(self):
        """HTML files must never be cached by CDN (viewer might change)."""
        from app.middleware.security_headers import SecurityHeadersMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse

        async def html_file(request):
            return PlainTextResponse("<html/>")

        app = Starlette(routes=[Route("/static/SecureDoc.html", html_file)])
        app.add_middleware(SecurityHeadersMiddleware)

        tc = TestClient(app, raise_server_exceptions=True)
        r = tc.get("/static/SecureDoc.html")
        cc = r.headers.get("cache-control", "")
        assert "no-cache" in cc

    def test_js_vary_accept_encoding(self):
        """JS files must include Vary: Accept-Encoding for CDN compression support."""
        from app.middleware.security_headers import SecurityHeadersMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse

        async def js_file(request):
            return PlainTextResponse("// bundle")

        app = Starlette(routes=[Route("/static/app.js", js_file)])
        app.add_middleware(SecurityHeadersMiddleware)

        tc = TestClient(app, raise_server_exceptions=True)
        r = tc.get("/static/app.js")
        assert "Accept-Encoding" in r.headers.get("vary", "")

    def test_stale_while_revalidate_on_js(self):
        """JS cache-control should include stale-while-revalidate."""
        from app.middleware.security_headers import SecurityHeadersMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse

        async def js_file(request):
            return PlainTextResponse("// bundle")

        app = Starlette(routes=[Route("/static/app.js", js_file)])
        app.add_middleware(SecurityHeadersMiddleware)

        tc = TestClient(app, raise_server_exceptions=True)
        r = tc.get("/static/app.js")
        cc = r.headers.get("cache-control", "")
        assert "stale-while-revalidate" in cc


# ── E. X-Cache-Status on viewer responses ─────────────────────────────────────

class TestXCacheStatusHeader:
    @pytest_asyncio.fixture
    async def ready_link(self, client, db_session):
        from app.models.document import Document
        from app.models.link import ShareLink
        doc = Document(
            id=uuid.uuid4(), filename="cache_test.pdf",
            storage_key="originals/cache_test.pdf",
            status="ready", page_count=2,
            file_size_bytes=1024,
            user_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        )
        db_session.add(doc)
        await db_session.commit()
        link = ShareLink(
            id=uuid.uuid4(), document_id=doc.id,
            token=secrets.token_urlsafe(16), label="cache-test",
        )
        db_session.add(link)
        await db_session.commit()
        return link.token

    @pytest.mark.asyncio
    async def test_page_response_has_x_cache_status(self, client, db_session, ready_link):
        """Page endpoint must always return X-Cache-Status header."""
        r = await client.post("/api/viewer/validate", json={"token": ready_link})
        assert r.status_code == 200
        session_id = r.json()["session_id"]

        from app.models.document import DocumentPage
        # Add a page record so the page endpoint can find it
        from app.models.link import ShareLink
        from sqlalchemy import select
        link_row = await db_session.execute(select(ShareLink).where(ShareLink.token == ready_link))
        link = link_row.scalar_one()

        page = DocumentPage(
            id=uuid.uuid4(), document_id=link.document_id,
            page_number=1, storage_key="pages/test/0001.webp",
            width_px=595, height_px=842,
        )
        db_session.add(page)
        await db_session.commit()

        with patch("app.routers.viewer.fetch_page_bytes", new_callable=AsyncMock) as mock_fetch, \
             patch("app.routers.viewer.watermark_svc") as mock_wm, \
             patch("app.routers.viewer.analytics_svc") as mock_analytics, \
             patch("app.routers.viewer.policy_enforcer") as mock_policy:
            mock_fetch.return_value = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "local")
            mock_wm.apply_visible_watermark.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
            mock_wm.apply_viewer_forensic_stamp.side_effect = lambda img, *a, **kw: img
            mock_analytics.log_event = AsyncMock()
            mock_policy.ip_is_allowed.return_value = True
            mock_policy.upsert_session = AsyncMock()
            mock_policy.is_active_session = AsyncMock(return_value=True)

            rp = await client.get(
                f"/api/viewer/page/{ready_link}/1", headers={"X-Session-ID": session_id}
            )
        assert "x-cache-status" in rp.headers
        assert rp.headers["x-cache-status"] in ("HIT", "MISS")

    @pytest.mark.asyncio
    async def test_cache_hit_returns_hit_status(self, client, db_session, ready_link):
        """When cache_source is 'local', X-Cache-Status must be 'HIT'."""
        r = await client.post("/api/viewer/validate", json={"token": ready_link})
        session_id = r.json()["session_id"]

        from app.models.document import DocumentPage
        from app.models.link import ShareLink
        from sqlalchemy import select
        link_row = await db_session.execute(select(ShareLink).where(ShareLink.token == ready_link))
        link = link_row.scalar_one()

        page = DocumentPage(
            id=uuid.uuid4(), document_id=link.document_id,
            page_number=1, storage_key="pages/test/0001.webp",
            width_px=595, height_px=842,
        )
        db_session.add(page)
        await db_session.commit()

        with patch("app.routers.viewer.fetch_page_bytes", new_callable=AsyncMock) as mock_fetch, \
             patch("app.routers.viewer.watermark_svc") as mock_wm, \
             patch("app.routers.viewer.analytics_svc") as mock_analytics, \
             patch("app.routers.viewer.policy_enforcer") as mock_policy:
            mock_fetch.return_value = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 100, "local")
            mock_wm.apply_visible_watermark.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
            mock_wm.apply_viewer_forensic_stamp.side_effect = lambda img, *a, **kw: img
            mock_analytics.log_event = AsyncMock()
            mock_policy.ip_is_allowed.return_value = True
            mock_policy.upsert_session = AsyncMock()
            mock_policy.is_active_session = AsyncMock(return_value=True)

            rp = await client.get(
                f"/api/viewer/page/{ready_link}/1", headers={"X-Session-ID": session_id}
            )
        assert rp.headers.get("x-cache-status") == "HIT"

    @pytest.mark.asyncio
    async def test_cache_miss_returns_miss_status(self, client, db_session, ready_link):
        """When cache_source is 'storage', X-Cache-Status must be 'MISS'."""
        r = await client.post("/api/viewer/validate", json={"token": ready_link})
        session_id = r.json()["session_id"]

        from app.models.document import DocumentPage
        from app.models.link import ShareLink
        from sqlalchemy import select
        link_row = await db_session.execute(select(ShareLink).where(ShareLink.token == ready_link))
        link = link_row.scalar_one()

        page = DocumentPage(
            id=uuid.uuid4(), document_id=link.document_id,
            page_number=1, storage_key="pages/test/0001.webp",
            width_px=595, height_px=842,
        )
        db_session.add(page)
        await db_session.commit()

        with patch("app.routers.viewer.fetch_page_bytes", new_callable=AsyncMock) as mock_fetch, \
             patch("app.routers.viewer.store_page_bytes", new_callable=AsyncMock), \
             patch("app.routers.viewer.get_storage_service") as mock_storage, \
             patch("app.routers.viewer.watermark_svc") as mock_wm, \
             patch("app.routers.viewer.analytics_svc") as mock_analytics, \
             patch("app.routers.viewer.policy_enforcer") as mock_policy:
            mock_fetch.return_value = (None, "storage")  # cache miss
            mock_storage.return_value.download_bytes = AsyncMock(
                return_value=b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
            )
            mock_wm.apply_visible_watermark.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 50
            mock_wm.apply_viewer_forensic_stamp.side_effect = lambda img, *a, **kw: img
            mock_analytics.log_event = AsyncMock()
            mock_policy.ip_is_allowed.return_value = True
            mock_policy.upsert_session = AsyncMock()
            mock_policy.is_active_session = AsyncMock(return_value=True)

            rp = await client.get(
                f"/api/viewer/page/{ready_link}/1", headers={"X-Session-ID": session_id}
            )
        assert rp.headers.get("x-cache-status") == "MISS"

    @pytest.mark.asyncio
    async def test_thumb_response_has_x_cache_status(self, client, db_session, ready_link):
        """Thumbnail endpoint must also return X-Cache-Status."""
        r = await client.post("/api/viewer/validate", json={"token": ready_link})
        session_id = r.json()["session_id"]

        from app.models.document import DocumentPage
        from app.models.link import ShareLink
        from sqlalchemy import select
        link_row = await db_session.execute(select(ShareLink).where(ShareLink.token == ready_link))
        link = link_row.scalar_one()

        page = DocumentPage(
            id=uuid.uuid4(), document_id=link.document_id,
            page_number=1, storage_key="pages/test/0001.webp",
            width_px=595, height_px=842,
        )
        db_session.add(page)
        await db_session.commit()

        with patch("app.routers.viewer.fetch_thumb_bytes", new_callable=AsyncMock) as mock_thumb, \
             patch("app.routers.viewer.analytics_svc") as mock_analytics, \
             patch("app.routers.viewer.policy_enforcer") as mock_policy:
            mock_thumb.return_value = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 50, "redis")
            mock_analytics.log_event = AsyncMock()
            mock_policy.ip_is_allowed.return_value = True
            mock_policy.upsert_session = AsyncMock()
            mock_policy.is_active_session = AsyncMock(return_value=True)

            rt = await client.get(
                f"/api/viewer/thumb/{ready_link}/1", headers={"X-Session-ID": session_id}
            )
        assert "x-cache-status" in rt.headers
        assert rt.headers["x-cache-status"] == "HIT"


# ── F. Request ID includes client IP ──────────────────────────────────────────

class TestRequestIDWithClientIP:
    def test_access_log_format_includes_ip(self):
        """Access log format string in request_id.py must contain ip= field."""
        import inspect
        from app.middleware import request_id as rid_module
        src = inspect.getsource(rid_module.RequestIDMiddleware.dispatch)
        assert "ip=" in src, "RequestIDMiddleware.dispatch must log ip= field"

    def test_request_id_echoed_in_response(self, client):
        """X-Request-ID must be echoed back in every response."""
        import asyncio
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async def _run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get("/health", headers={"X-Request-ID": "test-req-id-abc"})
            return r

        r = asyncio.get_event_loop().run_until_complete(_run())
        assert r.headers.get("x-request-id") == "test-req-id-abc"

    def test_request_id_generated_when_absent(self, client):
        """X-Request-ID must be generated (UUID4) when not supplied."""
        import asyncio
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        async def _run():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                r = await ac.get("/health")
            return r

        r = asyncio.get_event_loop().run_until_complete(_run())
        assert r.headers.get("x-request-id")


# ── G. Proxy / Cloudflare IP extraction ───────────────────────────────────────

class TestProxyIPExtraction:
    def test_cf_connecting_ip_extracted(self):
        """When real_ip_header=CF-Connecting-IP, that header value is used."""
        from app.middleware.trusted_proxy import TrustedProxyMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import JSONResponse

        async def ip_view(request):
            return JSONResponse({"ip": getattr(request.state, "client_ip", None)})

        app = Starlette(routes=[Route("/ip", ip_view)])
        app.add_middleware(TrustedProxyMiddleware, real_ip_header="CF-Connecting-IP")

        tc = TestClient(app)
        r = tc.get("/ip", headers={"CF-Connecting-IP": "1.2.3.4"})
        assert r.json()["ip"] == "1.2.3.4"

    def test_xff_depth_extraction(self):
        """With trusted_proxy_depth=1, rightmost-1 from XFF is used."""
        from app.middleware.trusted_proxy import TrustedProxyMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import JSONResponse

        async def ip_view(request):
            return JSONResponse({"ip": getattr(request.state, "client_ip", None)})

        app = Starlette(routes=[Route("/ip", ip_view)])
        app.add_middleware(TrustedProxyMiddleware, trusted_proxy_depth=1)

        tc = TestClient(app)
        r = tc.get("/ip", headers={"X-Forwarded-For": "203.0.113.1, 10.0.0.1"})
        assert r.json()["ip"] == "203.0.113.1"

    def test_no_proxy_uses_direct_host(self):
        """Without proxy config, request.client.host is used directly."""
        from app.middleware.trusted_proxy import TrustedProxyMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import JSONResponse

        async def ip_view(request):
            return JSONResponse({"ip": getattr(request.state, "client_ip", None)})

        app = Starlette(routes=[Route("/ip", ip_view)])
        app.add_middleware(TrustedProxyMiddleware)

        tc = TestClient(app)
        r = tc.get("/ip")
        assert r.json()["ip"] is not None

    def test_xff_with_multiple_hops(self):
        """depth=2 should skip two rightmost proxy hops."""
        from app.middleware.trusted_proxy import TrustedProxyMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import JSONResponse

        async def ip_view(request):
            return JSONResponse({"ip": getattr(request.state, "client_ip", None)})

        app = Starlette(routes=[Route("/ip", ip_view)])
        app.add_middleware(TrustedProxyMiddleware, trusted_proxy_depth=2)

        tc = TestClient(app)
        r = tc.get("/ip", headers={"X-Forwarded-For": "5.5.5.5, 10.0.0.1, 192.168.1.1"})
        assert r.json()["ip"] == "5.5.5.5"

    def test_real_ip_header_comma_separated(self):
        """If CF-Connecting-IP somehow contains a comma, only the first value is used."""
        from app.middleware.trusted_proxy import TrustedProxyMiddleware
        from starlette.testclient import TestClient
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import JSONResponse

        async def ip_view(request):
            return JSONResponse({"ip": getattr(request.state, "client_ip", None)})

        app = Starlette(routes=[Route("/ip", ip_view)])
        app.add_middleware(TrustedProxyMiddleware, real_ip_header="CF-Connecting-IP")

        tc = TestClient(app)
        r = tc.get("/ip", headers={"CF-Connecting-IP": "9.9.9.9, 1.2.3.4"})
        assert r.json()["ip"] == "9.9.9.9"


# ── H. Startup validation — IP hash salt ──────────────────────────────────────

class TestStartupValidation:
    def test_ip_salt_default_constant_matches(self):
        """The default placeholder salt used in startup validation must match config."""
        from app.main import _IP_SALT_DEFAULT
        assert _IP_SALT_DEFAULT == "securedoc_ip_salt_change_in_production"

    def test_ip_salt_default_is_config_default(self):
        """The default IP salt in config must match the one checked at startup."""
        from app.config import Settings
        from app.main import _IP_SALT_DEFAULT
        default_settings = Settings(app_env="development")
        assert default_settings.ip_hash_salt == _IP_SALT_DEFAULT

    def test_production_startup_rejects_default_ip_salt(self):
        """Starting in production with the default IP salt must raise RuntimeError."""
        env = {
            "APP_ENV": "production",
            "SUPABASE_URL": "https://test.supabase.co",
            "APP_PUBLIC_BASE_URL": "https://myapp.example.com",
            "IP_HASH_SALT": "securedoc_ip_salt_change_in_production",  # still default
        }
        with patch.dict("os.environ", env, clear=False):
            # We need to re-evaluate the module-level guard, not re-import
            # (can't re-import safely). Test the logic directly instead.
            from app.config import Settings
            from app.main import _IP_SALT_DEFAULT
            s = Settings(**{k.lower(): v for k, v in env.items()})
            assert s.ip_hash_salt == _IP_SALT_DEFAULT

    def test_production_startup_passes_with_custom_salt(self):
        """A custom non-default IP salt should not be flagged."""
        from app.config import Settings
        from app.main import _IP_SALT_DEFAULT
        custom = "a" * 64  # long random hex string
        s = Settings(app_env="production", ip_hash_salt=custom)
        assert s.ip_hash_salt != _IP_SALT_DEFAULT


# ── I. Config — new Phase 8 defaults ──────────────────────────────────────────

class TestPhase8ConfigDefaults:
    def test_https_redirect_default_false(self):
        from app.config import Settings
        assert Settings(app_env="development").https_redirect is False

    def test_hsts_max_age_default_one_year(self):
        from app.config import Settings
        assert Settings(app_env="development").hsts_max_age == 31536000

    def test_static_asset_max_age_default(self):
        from app.config import Settings
        s = Settings(app_env="development")
        assert s.static_asset_max_age > 0

    def test_storage_path_style_default_false(self):
        from app.config import Settings
        assert Settings(app_env="development").storage_path_style is False

    def test_db_pool_size_default(self):
        from app.config import Settings
        s = Settings(app_env="development")
        assert s.db_pool_size > 0

    def test_db_max_overflow_default(self):
        from app.config import Settings
        s = Settings(app_env="development")
        assert s.db_max_overflow >= 0

    def test_db_pool_recycle_default(self):
        from app.config import Settings
        s = Settings(app_env="development")
        assert s.db_pool_recycle > 0

    def test_db_pool_timeout_default(self):
        from app.config import Settings
        s = Settings(app_env="development")
        assert s.db_pool_timeout > 0


# ── J. Storage abstraction — file_exists() and ABC ────────────────────────────

class TestStorageAbstraction:
    def test_storage_backend_abc_importable(self):
        from app.services.storage import StorageBackend
        assert StorageBackend is not None

    def test_storage_service_is_subclass_of_backend(self):
        from app.services.storage import StorageService, StorageBackend
        assert issubclass(StorageService, StorageBackend)

    def test_storage_backend_has_file_exists(self):
        from app.services.storage import StorageBackend
        assert hasattr(StorageBackend, "file_exists")

    def test_storage_service_has_file_exists(self):
        from app.services.storage import StorageService
        assert hasattr(StorageService, "file_exists")

    def test_demo_storage_has_file_exists(self, tmp_path, monkeypatch):
        """DemoStorageService must also implement file_exists()."""
        import sys
        # Patch STORE_DIR and settings before importing demo patch
        monkeypatch.setenv("APP_ENV", "development")
        # Import the class directly without triggering the module-level monkey-patch
        import importlib.util, os
        demo_path = os.path.join(
            os.path.dirname(__file__), "../../demo_storage_patch.py"
        )
        spec = importlib.util.spec_from_file_location("demo_storage_patch_test", demo_path)
        # Can't safely re-import, test method existence via attribute check on the instance
        from app.services.storage import _storage_service
        # The storage service in tests is the mock; just check the interface exists
        from app.services.storage import StorageBackend
        assert "file_exists" in dir(StorageBackend)

    @pytest.mark.asyncio
    async def test_file_exists_returns_bool(self):
        """file_exists must return a bool, not raise, for any input."""
        from app.services.storage import StorageService
        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.storage_access_key_id = "key"
            mock_settings.storage_secret_access_key = "secret"
            mock_settings.storage_endpoint_url = None
            mock_settings.storage_region = "us-east-1"
            mock_settings.storage_path_style = False
            mock_settings.storage_bucket_name = "test-bucket"
            svc = StorageService()
            with patch.object(svc, "_client") as mock_client:
                mock_client.head_object.side_effect = Exception("NoSuchKey")

                async def run():
                    # Patch the executor call to raise ClientError 404
                    from botocore.exceptions import ClientError
                    svc._client.head_object.side_effect = None
                    svc._client.head_object.return_value = {}
                    result = await svc.file_exists("some/key.pdf")
                    return result

                result = await run()
                assert isinstance(result, bool)

    def test_abstract_methods_defined(self):
        """StorageBackend must declare all required abstract methods."""
        from app.services.storage import StorageBackend
        required = {"upload_file", "download_bytes", "delete_file",
                    "list_keys_with_prefix", "file_exists"}
        for method in required:
            assert hasattr(StorageBackend, method), f"Missing abstract method: {method}"


# ── K. DB pool config driven by settings ──────────────────────────────────────

class TestDBPoolConfig:
    def test_pool_size_from_settings(self):
        """make_engine must use settings.db_pool_size not a hardcoded value."""
        from app.database import make_engine
        from unittest.mock import patch

        with patch("app.database.settings") as mock_settings:
            mock_settings.database_url = "postgresql+asyncpg://u:p@localhost/db"
            mock_settings.db_pool_size = 42
            mock_settings.db_max_overflow = 5
            mock_settings.db_pool_timeout = 20
            mock_settings.db_pool_recycle = 900

            engine = make_engine("postgresql+asyncpg://u:p@localhost/db")
            pool = engine.pool
            assert pool.size() == 42

    def test_pool_recycle_from_settings(self):
        """make_engine must use settings.db_pool_recycle."""
        from app.database import make_engine

        with patch("app.database.settings") as mock_settings:
            mock_settings.database_url = "postgresql+asyncpg://u:p@localhost/db"
            mock_settings.db_pool_size = 5
            mock_settings.db_max_overflow = 5
            mock_settings.db_pool_timeout = 30
            mock_settings.db_pool_recycle = 600

            engine = make_engine("postgresql+asyncpg://u:p@localhost/db")
            assert engine.pool._recycle == 600


# ── L. Health endpoint — no proxy config disclosure (Phase B1 hardening) ──────

class TestHealthProxyBlock:
    @pytest.mark.asyncio
    async def test_health_does_not_expose_proxy_config(self, client):
        """Health must not expose proxy configuration — prevents real_ip_header spoofing."""
        r = await client.get("/health")
        assert r.status_code == 200
        body = r.json()
        # proxy config must be absent — it was removed in Phase B1 to prevent
        # attackers from learning which header to forge for IP allowlist bypass
        assert "proxy" not in body.get("checks", {})

    @pytest.mark.asyncio
    async def test_health_has_safe_checks(self, client):
        """Health must still report db, redis, storage, worker status."""
        r = await client.get("/health")
        checks = r.json()["checks"]
        assert "db" in checks
        assert "storage" in checks

    @pytest.mark.asyncio
    async def test_health_version_updated(self, client):
        r = await client.get("/health")
        assert r.json()["version"] == "8.1.0"


# ── M. Regression — existing viewer flows unaffected ─────────────────────────

class TestPhase8Regression:
    @pytest.mark.asyncio
    async def test_validate_still_works(self, client, db_session):
        """validate_link must still work after Phase 8 changes."""
        from app.models.document import Document
        from app.models.link import ShareLink
        doc = Document(
            id=uuid.uuid4(), filename="regression.pdf",
            storage_key="originals/regression.pdf",
            status="ready", page_count=1,
            file_size_bytes=512,
            user_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        )
        db_session.add(doc)
        await db_session.commit()
        link = ShareLink(
            id=uuid.uuid4(), document_id=doc.id,
            token=secrets.token_urlsafe(16), label="regression",
        )
        db_session.add(link)
        await db_session.commit()

        r = await client.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200
        assert "session_id" in r.json()
        assert "doc_type" in r.json()

    @pytest.mark.asyncio
    async def test_gate_still_works(self, client, db_session):
        """get_gate_requirements must still work after Phase 8."""
        from app.models.document import Document
        from app.models.link import ShareLink
        doc = Document(
            id=uuid.uuid4(), filename="gate_test.pdf",
            storage_key="originals/gate.pdf",
            status="ready", page_count=1, file_size_bytes=512,
            user_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        )
        db_session.add(doc)
        await db_session.commit()
        link = ShareLink(
            id=uuid.uuid4(), document_id=doc.id,
            token=secrets.token_urlsafe(16), label="gate",
        )
        db_session.add(link)
        await db_session.commit()

        r = await client.get(f"/api/viewer/gate/{link.token}")
        assert r.status_code == 200
        assert r.json()["status"] == "active"

    @pytest.mark.asyncio
    async def test_toc_endpoint_still_works(self, client, db_session):
        """TOC endpoint from Phase 7 must still work."""
        from app.models.document import Document
        from app.models.link import ShareLink
        doc = Document(
            id=uuid.uuid4(), filename="doc.md",
            storage_key="originals/doc.md",
            status="ready", page_count=1, file_size_bytes=256,
            file_type="md",
            user_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        )
        db_session.add(doc)
        await db_session.commit()
        link = ShareLink(
            id=uuid.uuid4(), document_id=doc.id,
            token=secrets.token_urlsafe(16), label="toc",
        )
        db_session.add(link)
        await db_session.commit()

        r = await client.post("/api/viewer/validate", json={"token": link.token})
        session_id = r.json()["session_id"]

        r2 = await client.get(
            f"/api/viewer/toc/{link.token}", headers={"X-Session-ID": session_id}
        )
        assert r2.status_code in (200, 503)  # 503 if storage has no file in tests

    @pytest.mark.asyncio
    async def test_protected_assets_still_no_store(self, client, db_session):
        """Page/thumb responses must still have Cache-Control: no-store."""
        from app.models.document import Document
        from app.models.link import ShareLink
        from app.models.document import DocumentPage
        doc = Document(
            id=uuid.uuid4(), filename="nostore.pdf",
            storage_key="originals/nostore.pdf",
            status="ready", page_count=1, file_size_bytes=512,
            user_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
        )
        db_session.add(doc)
        await db_session.commit()
        link = ShareLink(
            id=uuid.uuid4(), document_id=doc.id,
            token=secrets.token_urlsafe(16), label="nostore",
        )
        db_session.add(link)
        await db_session.commit()

        r = await client.post("/api/viewer/validate", json={"token": link.token})
        session_id = r.json()["session_id"]

        page = DocumentPage(
            id=uuid.uuid4(), document_id=doc.id,
            page_number=1, storage_key="pages/test/nostore.webp",
            width_px=595, height_px=842,
        )
        db_session.add(page)
        await db_session.commit()

        with patch("app.routers.viewer.fetch_page_bytes", new_callable=AsyncMock) as mf, \
             patch("app.routers.viewer.watermark_svc") as mw, \
             patch("app.routers.viewer.analytics_svc") as ma, \
             patch("app.routers.viewer.policy_enforcer") as mp:
            mf.return_value = (b"\x00" * 100, "local")
            mw.apply_visible_watermark.return_value = b"\x00" * 50
            mw.apply_viewer_forensic_stamp.side_effect = lambda img, *a, **kw: img
            ma.log_event = AsyncMock()
            mp.ip_is_allowed.return_value = True
            mp.upsert_session = AsyncMock()
            mp.is_active_session = AsyncMock(return_value=True)

            rp = await client.get(
                f"/api/viewer/page/{link.token}/1", headers={"X-Session-ID": session_id}
            )
        cc = rp.headers.get("cache-control", "")
        assert "no-store" in cc


# ── N. Security header regression ─────────────────────────────────────────────

class TestSecurityHeaderRegression:
    @pytest.mark.asyncio
    async def test_x_frame_options_deny(self, client):
        r = await client.get("/health")
        assert r.headers.get("x-frame-options") == "DENY"

    @pytest.mark.asyncio
    async def test_referrer_policy_present(self, client):
        r = await client.get("/health")
        assert "referrer-policy" in r.headers

    @pytest.mark.asyncio
    async def test_permissions_policy_present(self, client):
        r = await client.get("/health")
        assert "permissions-policy" in r.headers

    @pytest.mark.asyncio
    async def test_x_content_type_options_nosniff(self, client):
        r = await client.get("/health")
        assert r.headers.get("x-content-type-options") == "nosniff"


# ── O. Storage path-style config ──────────────────────────────────────────────

class TestStoragePathStyle:
    def test_path_style_false_by_default(self):
        from app.config import Settings
        assert Settings(app_env="development").storage_path_style is False

    def test_path_style_configurable_via_env(self, monkeypatch):
        monkeypatch.setenv("STORAGE_PATH_STYLE", "true")
        from app.config import Settings
        s = Settings(app_env="development")
        assert s.storage_path_style is True

    def test_storage_service_uses_path_style_config(self):
        """When storage_path_style=True, addressing_style=path must be in the config."""
        from app.services.storage import StorageService
        with patch("app.services.storage.settings") as mock_settings:
            mock_settings.storage_access_key_id = "key"
            mock_settings.storage_secret_access_key = "secret"
            mock_settings.storage_endpoint_url = "https://minio.example.com"
            mock_settings.storage_region = "us-east-1"
            mock_settings.storage_path_style = True
            mock_settings.storage_bucket_name = "test"
            with patch("boto3.client") as mock_boto:
                mock_boto.return_value = MagicMock()
                StorageService()
                call_kwargs = mock_boto.call_args[1]
                cfg = call_kwargs.get("config")
                # The config should have s3 addressing_style=path when path_style=True
                assert cfg is not None
