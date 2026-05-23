"""
Shared fixtures for the E2E test suite.
Tests run against the live stack.
No mocks — real HTTP calls only.

Set E2E_BASE_URL to target a different host, e.g.:
  E2E_BASE_URL=https://secure.wowmyspace.com pytest api/
  E2E_AUTH_TOKEN=<supabase_jwt> pytest api/
"""
import io
import os
import time
import pytest
import httpx
from PIL import Image


BASE_URL = os.environ.get("E2E_BASE_URL", "http://localhost:8000").rstrip("/")
_AUTH_TOKEN = os.environ.get("E2E_AUTH_TOKEN", "")


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_minimal_pdf() -> bytes:
    """Minimal valid single-page PDF that passes the magic-bytes check."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R "
        b"/MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\n"
        b"startxref\n190\n%%EOF"
    )


def make_minimal_webp(width: int = 100, height: int = 100) -> bytes:
    img = Image.new("RGB", (width, height), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()


def upload_pdf(client: httpx.Client, pdf_bytes: bytes, filename: str = "test.pdf") -> dict:
    """Upload a PDF and return the response body (status 202).
    Skips the current test on rate-limit (429) or missing auth (401).
    Response shape: {id, filename, status, message}
    """
    r = client.post(
        "/api/documents/upload",
        files={"file": (filename, pdf_bytes, "application/pdf")},
        data={"filename": filename},
    )
    if r.status_code == 429:
        pytest.skip("Upload rate-limited — rerun after 1 minute")
    if r.status_code == 401:
        pytest.skip(
            "Auth required — add a valid Supabase JWT to the api_client fixture. "
            "See README: 'Running E2E tests with authentication'."
        )
    assert r.status_code == 202, f"Upload failed: {r.status_code} {r.text}"
    return r.json()


def poll_until_ready(client: httpx.Client, doc_id: str, timeout: int = 60) -> dict:
    """Poll /api/documents/{id}/status until ready.
    Returns merged dict: {id: doc_id, status, page_count, error_message}
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/api/documents/{doc_id}/status")
        assert r.status_code == 200
        body = r.json()
        status = body.get("status")
        if status == "ready":
            return {"id": doc_id, **body}
        if status == "error":
            raise RuntimeError(f"Document processing failed: {body}")
        time.sleep(1)
    raise TimeoutError(f"Document {doc_id} not ready within {timeout}s")


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def minimal_pdf_bytes() -> bytes:
    return make_minimal_pdf()


def _build_headers() -> dict:
    if _AUTH_TOKEN:
        return {"Authorization": f"Bearer {_AUTH_TOKEN}"}
    return {}


@pytest.fixture(scope="session")
def api_client() -> httpx.Client:
    """Synchronous httpx client against live stack."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0, headers=_build_headers()) as client:
        yield client


@pytest.fixture(scope="session")
async def async_client():
    """Async httpx client against live stack."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, headers=_build_headers()) as client:
        yield client


@pytest.fixture(scope="session")
def ready_doc(api_client, minimal_pdf_bytes):
    """Upload + poll until ready. Session-scoped so all tests share one doc."""
    body = upload_pdf(api_client, minimal_pdf_bytes)
    doc_id = body["id"]
    try:
        return poll_until_ready(api_client, doc_id, timeout=60)
    except TimeoutError:
        # Celery not running — return current status + id so id-based tests still run
        r = api_client.get(f"/api/documents/{doc_id}/status")
        return {"id": doc_id, **r.json()}


@pytest.fixture()
def create_link(api_client, ready_doc):
    """Factory: creates a link for the ready doc and returns LinkResponse body."""
    def _create(**kwargs):
        payload = {"document_id": ready_doc["id"], **kwargs}
        r = api_client.post("/api/links", json=payload)
        assert r.status_code == 201, f"Create link failed: {r.status_code} {r.text}"
        return r.json()
    return _create


@pytest.fixture()
def active_link(create_link):
    """A plain unrestricted share link for the ready doc."""
    return create_link(label="e2e-active")


@pytest.fixture()
def password_link(create_link):
    return create_link(label="e2e-password", password="s3cr3t!")


@pytest.fixture()
def max_views_link(create_link):
    return create_link(label="e2e-maxviews", max_views=2)
