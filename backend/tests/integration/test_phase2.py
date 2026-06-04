"""
Phase 2 production-hardening tests — frontend build.

Covers:
  A) Bundle existence and correctness — dist/app.bundle.js is present, non-trivial,
     and contains compiled React.createElement calls (no raw JSX syntax).
  B) No dev runtime in production HTML — SecureDoc.html must not reference
     Babel standalone or use text/babel script tags.
  C) No hardcoded URLs in bundle — no localhost, tunnel, or env-specific URLs
     must be baked into the compiled artifact.
  D) Static serving — backend correctly serves the HTML and the bundle via
     the /static/ mount.
"""
import os
import pytest

# Resolve the frontend directory the same way main.py does at runtime.
_BACKEND_APP = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../app"))
FRONTEND_DIR = os.path.abspath(os.path.join(_BACKEND_APP, "../../frontend"))
BUNDLE_PATH = os.path.join(FRONTEND_DIR, "dist", "app.bundle.js")
HTML_PATH = os.path.join(FRONTEND_DIR, "SecureDoc.html")


# ── helpers ────────────────────────────────────────────────────────────────────

def _read_bundle() -> str:
    with open(BUNDLE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _read_html() -> str:
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════════════════
# A. BUNDLE EXISTENCE AND CORRECTNESS
# ══════════════════════════════════════════════════════════════════════════════

class TestBundleCorrectness:
    """dist/app.bundle.js must exist and be a valid compiled JS artifact."""

    def test_bundle_file_exists(self):
        assert os.path.exists(BUNDLE_PATH), (
            f"dist/app.bundle.js not found at {BUNDLE_PATH}. "
            "Run `npm run build` in the frontend/ directory."
        )

    def test_bundle_is_not_empty(self):
        size = os.path.getsize(BUNDLE_PATH)
        assert size > 50_000, f"Bundle too small ({size} bytes) — build may have failed"

    def test_bundle_contains_react_createelement(self):
        """JSX must be compiled to React.createElement calls."""
        bundle = _read_bundle()
        count = bundle.count("React.createElement")
        assert count > 100, (
            f"Expected hundreds of React.createElement calls, got {count}. "
            "JSX may not have been compiled."
        )

    def test_bundle_contains_reactdom_mount(self):
        """App must mount via ReactDOM.createRoot."""
        bundle = _read_bundle()
        assert "ReactDOM.createRoot" in bundle

    def test_bundle_has_no_raw_jsx_syntax(self):
        """Compiled output must not contain raw <Component ... /> syntax."""
        bundle = _read_bundle()
        # Raw JSX would contain patterns like </div> or <App/> in JS context.
        # A compiled bundle only has string literals for CSS/HTML, not component tags.
        # Check the known root mount call is in compiled form, not JSX form.
        assert "<App />" not in bundle, "Raw JSX found in bundle — compilation may have been skipped"
        assert "<App/>" not in bundle

    def test_bundle_has_no_babel_references(self):
        """The compiled bundle must not contain any Babel references."""
        bundle = _read_bundle()
        assert "@babel" not in bundle
        assert "babel.min" not in bundle
        assert "text/babel" not in bundle

    def test_bundle_ends_with_reactdom_render(self):
        """The last statement must be the ReactDOM mount (app entry point)."""
        bundle = _read_bundle()
        # Strip trailing whitespace/newlines
        trimmed = bundle.strip()
        assert trimmed.endswith(
            'ReactDOM.createRoot(document.getElementById("root")).render(React.createElement(App,null));'
        ), "Bundle does not end with ReactDOM render — app entry point may be missing"


# ══════════════════════════════════════════════════════════════════════════════
# B. NO DEV RUNTIME IN PRODUCTION HTML
# ══════════════════════════════════════════════════════════════════════════════

class TestHtmlNoBabelRuntime:
    """SecureDoc.html must not ship Babel standalone or text/babel scripts."""

    def test_html_has_no_babel_standalone_script(self):
        html = _read_html()
        assert "@babel/standalone" not in html, (
            "Babel standalone CDN script still present in HTML. "
            "Remove it — JSX is now pre-compiled."
        )
        assert "babel.min.js" not in html

    def test_html_has_no_text_babel_scripts(self):
        html = _read_html()
        assert 'type="text/babel"' not in html, (
            'text/babel script tag found in HTML — all JSX must be pre-compiled'
        )

    def test_html_loads_compiled_bundle(self):
        html = _read_html()
        assert 'dist/app.bundle.js' in html, (
            "HTML must load the compiled bundle (dist/app.bundle.js)"
        )

    def test_html_still_loads_react_from_cdn(self):
        """React and ReactDOM must still be loaded before the app bundle."""
        html = _read_html()
        assert "react.production.min.js" in html
        assert "react-dom.production.min.js" in html

    def test_html_still_loads_api_js(self):
        html = _read_html()
        assert 'src="/static/api.js"' in html

    def test_html_has_root_div(self):
        html = _read_html()
        assert 'id="root"' in html

    def test_bundle_script_after_root_div(self):
        """The bundle <script> tag must come after #root so the DOM node exists."""
        html = _read_html()
        root_pos = html.index('id="root"')
        bundle_pos = html.index("dist/app.bundle.js")
        assert bundle_pos > root_pos, (
            "dist/app.bundle.js script tag must appear after the #root div"
        )


# ══════════════════════════════════════════════════════════════════════════════
# C. NO HARDCODED URLS IN BUNDLE
# ══════════════════════════════════════════════════════════════════════════════

class TestBundleUrlSafety:
    """The compiled bundle must not bake in environment-specific URLs."""

    def test_bundle_has_no_localhost_url(self):
        bundle = _read_bundle()
        assert "localhost" not in bundle, "localhost URL found in compiled bundle"

    def test_bundle_has_no_127_0_0_1(self):
        bundle = _read_bundle()
        assert "127.0.0.1" not in bundle

    def test_bundle_has_no_tunnel_url(self):
        """No Cloudflare tunnel or trycloudflare.com URLs must be baked in."""
        bundle = _read_bundle()
        assert "trycloudflare.com" not in bundle
        assert "ngrok" not in bundle

    def test_bundle_has_no_hardcoded_api_base(self):
        """API base detection must stay in api.js, not be hardcoded in the bundle."""
        bundle = _read_bundle()
        # The bundle must NOT contain a hardcoded http/https backend address
        # (API base auto-detection lives in api.js, which is loaded separately)
        assert "wowmyspace.com" not in bundle


# ══════════════════════════════════════════════════════════════════════════════
# D. STATIC SERVING
# ══════════════════════════════════════════════════════════════════════════════

class TestStaticServing:
    """Backend /static/ mount must serve both the HTML and the compiled bundle."""

    @pytest.mark.asyncio
    async def test_static_html_returns_200(self, client):
        r = await client.get("/static/SecureDoc.html")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_static_html_has_no_babel_standalone(self, client):
        r = await client.get("/static/SecureDoc.html")
        assert r.status_code == 200
        assert "@babel/standalone" not in r.text
        assert 'type="text/babel"' not in r.text

    @pytest.mark.asyncio
    async def test_static_bundle_returns_200(self, client):
        r = await client.get("/static/dist/app.bundle.js")
        assert r.status_code == 200
        content_type = r.headers.get("content-type", "")
        assert "javascript" in content_type or "text/plain" in content_type

    @pytest.mark.asyncio
    async def test_static_bundle_contains_react_createelement(self, client):
        r = await client.get("/static/dist/app.bundle.js")
        assert r.status_code == 200
        assert "React.createElement" in r.text

    @pytest.mark.asyncio
    async def test_static_api_js_still_served(self, client):
        """api.js must still be accessible — it loads before the bundle."""
        r = await client.get("/static/api.js")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_root_redirect_to_html(self, client):
        """/ must redirect to the app entry point."""
        r = await client.get("/", follow_redirects=False)
        assert r.status_code in (301, 302, 307, 308)
        location = r.headers.get("location", "")
        # / now redirects to /app (dynamic HTML endpoint with injected config)
        assert "/app" in location or "SecureDoc.html" in location
