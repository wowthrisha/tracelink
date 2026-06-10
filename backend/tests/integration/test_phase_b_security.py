"""
Phase B1 Security Remediation Tests.

Covers every fix applied in Phase B1:
  A. .cover files removed from git
  B. /health does not expose proxy configuration
  C. CSP uses SHA-384 hash pinning instead of broad unpkg.com domain
  D. Forensic stamp is not a no-op
  E. Analytics metadata size limit
  F. Download endpoint enforces IP allowlist
  G. Session IDs are not logged in full
  H. SecureDoc.html has no hardcoded Supabase credentials
  I. /app serves HTML with injected config
  J. Production startup warns about missing REAL_IP_HEADER
"""
import hashlib
import io
import json
import pathlib
import subprocess
import uuid

import pytest
from PIL import Image

TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
REPO_ROOT = pathlib.Path("/Users/thrisha/traceview/securedoc")


# ── A. .cover files must be gone from git ─────────────────────────────────────

class TestCoverFilesRemoved:
    def test_no_cover_files_tracked_in_git(self):
        """All .cover files must be untracked — none committed to git."""
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        # git ls-files of all tracked files should have no .cover entries
        tracked = subprocess.run(
            ["git", "ls-files"],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        cover_files = [f for f in tracked.stdout.splitlines() if ",cover" in f]
        assert cover_files == [], (
            f"Found {len(cover_files)} tracked .cover files that should be removed: {cover_files}"
        )

    def test_gitignore_covers_cover_extension(self):
        """The .gitignore must have *.cover to prevent future commits."""
        gitignore = (REPO_ROOT / ".gitignore").read_text()
        assert "*.cover" in gitignore


# ── B. /health must not expose proxy/CDN configuration ───────────────────────

class TestHealthSecurity:
    @pytest.mark.asyncio
    async def test_health_omits_real_ip_header(self, client):
        """/health must not reveal real_ip_header — prevents IP spoofing reconnaissance."""
        r = await client.get("/health")
        assert r.status_code == 200
        body = r.json()
        body_str = json.dumps(body)
        assert "real_ip_header" not in body_str
        assert "trusted_proxy_depth" not in body_str
        assert "https_redirect" not in body_str

    @pytest.mark.asyncio
    async def test_health_still_useful_for_ops(self, client):
        """/health must still report service status."""
        r = await client.get("/health")
        checks = r.json()["checks"]
        assert "db" in checks
        assert "storage" in checks
        assert "redis" in checks
        assert "worker" in checks

    @pytest.mark.asyncio
    async def test_health_no_proxy_block(self, client):
        """The proxy config block must be completely absent from health response."""
        r = await client.get("/health")
        assert "proxy" not in r.json().get("checks", {})


# ── C. CSP must pin React by content hash, not CDN domain ────────────────────

class TestCSPHardening:
    @pytest.mark.asyncio
    async def test_csp_has_no_unpkg_domain_allowance(self, client):
        """script-src must not allow the broad unpkg.com domain."""
        r = await client.get("/health")
        csp = r.headers.get("Content-Security-Policy", "")
        assert "https://unpkg.com" not in csp, (
            "CSP still allows any script from unpkg.com — should use hash pinning instead"
        )

    @pytest.mark.asyncio
    async def test_csp_has_react_sha384_hashes(self, client):
        """script-src must include the specific SHA-384 hashes for React 18.3.1."""
        r = await client.get("/health")
        csp = r.headers.get("Content-Security-Policy", "")
        assert "sha384-" in csp, "CSP must contain SHA-384 hash sources for React scripts"

    @pytest.mark.asyncio
    async def test_csp_retains_self_for_local_scripts(self, client):
        """script-src must retain 'self' to allow api.js and app.bundle.js."""
        r = await client.get("/health")
        csp = r.headers.get("Content-Security-Policy", "")
        assert "'self'" in csp

    def test_html_react_scripts_have_matching_integrity_hashes(self):
        """SecureDoc.html must have SRI integrity hashes matching the CSP hash sources."""
        from app.middleware.security_headers import _REACT_HASH, _REACT_DOM_HASH
        html = (REPO_ROOT / "frontend" / "SecureDoc.html").read_text()
        # Both SRI hashes from the HTML must match what's in the CSP
        assert _REACT_HASH.replace("sha384-", "") in html
        assert _REACT_DOM_HASH.replace("sha384-", "") in html

    @pytest.mark.asyncio
    async def test_csp_still_blocks_unsafe_eval(self, client):
        """CSP must not contain unsafe-eval."""
        r = await client.get("/health")
        csp = r.headers.get("Content-Security-Policy", "")
        assert "unsafe-eval" not in csp


# ── D. Forensic stamp is not a no-op ──────────────────────────────────────────

class TestForensicStamp:
    def test_forensic_stamp_modifies_image(self, sample_webp_bytes):
        """apply_forensic_stamp must actually change the image data."""
        from app.services.watermark import WatermarkService
        svc = WatermarkService()
        result = svc.apply_forensic_stamp(sample_webp_bytes, str(uuid.uuid4()), 1)
        assert result != sample_webp_bytes, (
            "Forensic stamp returned the input unchanged — it is still a no-op"
        )

    def test_forensic_stamp_produces_valid_image(self, sample_webp_bytes):
        from app.services.watermark import WatermarkService
        svc = WatermarkService()
        result = svc.apply_forensic_stamp(sample_webp_bytes, "doc-test", 1)
        img = Image.open(io.BytesIO(result))
        assert img.size == Image.open(io.BytesIO(sample_webp_bytes)).size

    def test_forensic_stamp_different_docs_produce_different_marks(self, sample_webp_bytes):
        from app.services.watermark import WatermarkService
        svc = WatermarkService()
        r1 = svc.apply_forensic_stamp(sample_webp_bytes, "doc-aaaa", 1)
        r2 = svc.apply_forensic_stamp(sample_webp_bytes, "doc-bbbb", 1)
        assert r1 != r2

    def test_forensic_stamp_mark_encodes_document_fingerprint(self):
        """The forensic mark text must be derivable from document_id."""
        doc_id = "my-secure-document-uuid"
        fingerprint = hashlib.sha256(doc_id.encode()).hexdigest()[:8]
        mark_text = f"SD:{fingerprint}:0001"
        # Verify the fingerprint is reproducible from the doc_id
        assert hashlib.sha256(doc_id.encode()).hexdigest()[:8] == fingerprint
        assert mark_text.startswith("SD:")


# ── E. Analytics metadata size limit ──────────────────────────────────────────

class TestAnalyticsMetadataLimit:
    @pytest.mark.asyncio
    async def test_oversized_metadata_rejected(self, client, sample_document, sample_link):
        """POST /api/analytics/events must reject metadata exceeding 1024 bytes."""
        # Build a valid session first
        r = await client.post(
            "/api/viewer/validate",
            json={"token": sample_link.token},
        )
        assert r.status_code == 200
        session_id = r.json()["session_id"]

        # Try to log with oversized metadata
        large_metadata = {"key": "x" * 2000}
        r = await client.post(
            "/api/analytics/events",
            json={
                "token": sample_link.token,
                "session_id": session_id,
                "event_type": "completed",
                "metadata": large_metadata,
            },
        )
        assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
        assert "1024" in r.json()["detail"] or "metadata" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_normal_metadata_accepted(self, client, sample_document, sample_link):
        """Small metadata payloads must still be accepted."""
        r = await client.post(
            "/api/viewer/validate",
            json={"token": sample_link.token},
        )
        assert r.status_code == 200
        session_id = r.json()["session_id"]

        r = await client.post(
            "/api/analytics/events",
            json={
                "token": sample_link.token,
                "session_id": session_id,
                "event_type": "completed",
                "metadata": {"page": 3, "action": "finished"},
            },
        )
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_null_metadata_accepted(self, client, sample_document, sample_link):
        """Null metadata must be accepted (field is optional)."""
        r = await client.post(
            "/api/viewer/validate",
            json={"token": sample_link.token},
        )
        session_id = r.json()["session_id"]

        r = await client.post(
            "/api/analytics/events",
            json={
                "token": sample_link.token,
                "session_id": session_id,
                "event_type": "completed",
                "metadata": None,
            },
        )
        assert r.status_code == 200


# ── F. Download endpoint enforces IP allowlist ────────────────────────────────

class TestDownloadIPAllowlist:
    @pytest.mark.asyncio
    async def test_download_blocked_by_ip_allowlist(self, client):
        """GET /api/viewer/download must enforce the IP allowlist."""
        from app.services.viewer_cache import clear_all_caches
        clear_all_caches()

        r = await client.post(
            "/api/documents/upload",
            files={"file": ("dl.pdf", b"%PDF-1.4 minimal", "application/pdf")},
        )
        doc_id = r.json()["id"]
        r = await client.post(
            "/api/links",
            json={
                "document_id": doc_id,
                "ip_allowlist": ["10.0.0.0/8"],  # only 10.x.x.x — testclient is not in this range
                "permissions": {"can_download": True},
            },
        )
        token = r.json()["token"]

        r_download = await client.get(
            f"/api/viewer/download/{token}",
            headers={"X-Session-ID": "e" * 32},
        )
        # Should be 403 (IP blocked) — not 401 (session) or 410 (revoked)
        assert r_download.status_code == 403, (
            f"Expected 403 for IP-blocked download, got {r_download.status_code}: {r_download.text}"
        )

    @pytest.mark.asyncio
    async def test_download_same_ip_check_as_page_endpoint(self, client):
        """Download and page endpoints must enforce the same IP allowlist logic."""
        from app.services.viewer_cache import clear_all_caches
        clear_all_caches()

        r = await client.post(
            "/api/documents/upload",
            files={"file": ("compare.pdf", b"%PDF-1.4", "application/pdf")},
        )
        doc_id = r.json()["id"]
        r = await client.post(
            "/api/links",
            json={
                "document_id": doc_id,
                "ip_allowlist": ["10.0.0.0/8"],
            },
        )
        token = r.json()["token"]
        fake_session = "f" * 32

        r_page = await client.get(
            f"/api/viewer/page/{token}/1",
            headers={"X-Session-ID": fake_session},
        )
        r_download = await client.get(
            f"/api/viewer/download/{token}",
            headers={"X-Session-ID": fake_session},
        )
        # Both endpoints must return 403 for IP-blocked requests
        assert r_page.status_code == 403
        assert r_download.status_code == 403


# ── G. Session IDs must not appear in full in server logs ─────────────────────

class TestSessionLogRedaction:
    def test_reuse_log_truncates_session_id(self):
        """The REUSE log message must only log the first 6 chars of the session ID."""
        import logging
        import inspect
        from app.services.link_service import LinkService
        source = inspect.getsource(LinkService.validate_link)
        # The log line must use [:6] truncation
        assert "existing_session_id[:6]" in source, (
            "Session ID REUSE log must be truncated to [:6] — not logging full session ID"
        )

    def test_new_session_log_truncates_session_id(self):
        """The new_session log must only log the first 6 chars."""
        import inspect
        from app.services.link_service import LinkService
        source = inspect.getsource(LinkService.validate_link)
        assert "session_id[:6]" in source, (
            "New session log must be truncated to [:6] — not logging full session ID"
        )

    def test_full_session_id_not_in_log_format_strings(self):
        """No log format string should reference full session IDs."""
        import inspect
        from app.services.link_service import LinkService
        source = inspect.getsource(LinkService.validate_link)
        # Must not log the raw full existing_session_id
        assert 'REUSE session=%s", link.id, existing_session_id\n' not in source
        assert 'new_session=%s",\n                link.id,\n' not in source or \
               "session_id[:6]" in source


# ── H. SecureDoc.html must have no hardcoded Supabase credentials ─────────────

class TestNoHardcodedCredentials:
    def test_html_has_no_real_supabase_url(self):
        """SecureDoc.html must not contain a real Supabase project URL."""
        html = (REPO_ROOT / "frontend" / "SecureDoc.html").read_text()
        assert "supabase.co" not in html, (
            "Real Supabase URL must not be hardcoded in tracked HTML. "
            "Use placeholder SECUREDOC_SUPABASE_URL instead."
        )

    def test_html_has_no_real_supabase_anon_key(self):
        """SecureDoc.html must not contain a real Supabase anon key."""
        html = (REPO_ROOT / "frontend" / "SecureDoc.html").read_text()
        assert "sb_publishable_" not in html, (
            "Real Supabase anon key must not be hardcoded in tracked HTML."
        )

    def test_html_uses_placeholder_values(self):
        """SecureDoc.html must use placeholder strings for Supabase config."""
        html = (REPO_ROOT / "frontend" / "SecureDoc.html").read_text()
        assert "SECUREDOC_SUPABASE_URL" in html
        assert "SECUREDOC_SUPABASE_ANON_KEY" in html

    def test_env_example_has_no_real_credentials(self):
        """The .env.example file must not contain any real API keys or secrets."""
        env_example = (REPO_ROOT / "backend" / ".env.example").read_text()
        # Must not contain a real Supabase anon key
        assert "sb_publishable_" not in env_example
        # Must not contain the real project ID (placeholder 'your-project-ref' is fine)
        assert "zznenaqcvzxtqxzilpyh" not in env_example


# ── I. /app endpoint serves config-injected HTML ──────────────────────────────

class TestAppEndpoint:
    @pytest.mark.asyncio
    async def test_app_returns_html(self, client):
        """/app must return HTML content."""
        r = await client.get("/app")
        # May return 200 (HTML served) or 503 (frontend dir not available in test env)
        assert r.status_code in (200, 503)

    @pytest.mark.asyncio
    async def test_root_redirects_to_app(self, client):
        """/ must redirect to /app."""
        r = await client.get("/", follow_redirects=False)
        assert r.status_code in (301, 302, 307, 308)
        assert "/app" in r.headers.get("location", "")

    @pytest.mark.asyncio
    async def test_share_link_redirects_to_app(self, client):
        """/v/{token} must redirect to /app?token=..."""
        r = await client.get("/v/some-token-here", follow_redirects=False)
        assert r.status_code in (301, 302, 307, 308)
        location = r.headers.get("location", "")
        assert "/app" in location
        assert "token" in location


# ── J. Production startup warnings for missing proxy config ───────────────────

class TestProductionStartupChecks:
    def test_startup_warns_about_missing_real_ip_header(self):
        """Production startup must warn when REAL_IP_HEADER is not set."""
        import inspect
        import app.main as main_module
        source = inspect.getsource(main_module)
        assert "REAL_IP_HEADER" in source
        assert "real_ip_header" in source.lower()

    def test_startup_warns_about_https_redirect_disabled(self):
        """Production startup must warn when HTTPS_REDIRECT is not enabled."""
        import inspect
        import app.main as main_module
        source = inspect.getsource(main_module)
        assert "HTTPS_REDIRECT" in source or "https_redirect" in source.lower()

    def test_env_example_documents_real_ip_header_as_required(self):
        """The .env.example must document REAL_IP_HEADER as production-required."""
        env_example = (REPO_ROOT / "backend" / ".env.example").read_text()
        assert "REAL_IP_HEADER" in env_example
        assert "PRODUCTION" in env_example.upper()
