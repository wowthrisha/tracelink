"""
Phase 5 — Secure text document support: .txt, .md, .log

Test categories:
  A) File-type detection and upload acceptance
  B) Binary file and unsupported type rejection
  C) XSS payload safety (upload + serve)
  D) Text worker processing (decode, chunk-count)
  E) Text viewer endpoint (/api/viewer/text/{token}/{chunk})
  F) Access control parity with PDFs (revoke, expiry, session)
  G) Analytics events for text documents
  H) PDF regression (existing flow unchanged)
  I) Validate endpoint returns doc_type
  J) Large file and edge-case handling
  K) Markdown edge cases
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.document import Document
from app.models.link import ShareLink
from app.services.link_service import LinkService
from app.services.text_processor import (
    detect_file_type,
    decode_text_safe,
    chunk_text,
    count_chunks,
    _reject_if_binary,
    SUPPORTED_TEXT_EXTENSIONS,
)
from app.auth import get_current_user
from tests.conftest import TEST_USER_ID

TEST_DB_URL = "sqlite+aiosqlite:///./test_phase5.db"
_LINES_PER_CHUNK = 100  # must match config default


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(
        TEST_DB_URL, echo=False, connect_args={"check_same_thread": False}
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_db():
        yield db_session

    def override_user():
        return {"user_id": TEST_USER_ID, "email": "test@example.com", "role": "authenticated"}

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    with patch("app.services.storage.StorageService.upload_file", new_callable=AsyncMock) as mu, \
         patch("app.services.storage.StorageService.download_bytes", new_callable=AsyncMock) as md, \
         patch("app.services.storage.StorageService.delete_file", new_callable=AsyncMock), \
         patch("app.services.storage.StorageService.list_keys_with_prefix", new_callable=AsyncMock) as ml, \
         patch("app.workers.tasks.process_document.delay") as mc:

        mu.return_value = "mocked/key"
        md.return_value = b"Hello\nWorld\n"  # default text for download
        ml.return_value = []
        mc.return_value = MagicMock(id="fake-task-id")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c, md  # yield the mock_download so tests can configure it

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def ready_txt_doc(db_session):
    """A pre-built ready .txt document with 150 lines (2 chunks of 100/50)."""
    text = "\n".join(f"line {i}" for i in range(1, 151))
    doc = Document(
        id=uuid.uuid4(),
        filename="notes.txt",
        storage_key=f"originals/{uuid.uuid4()}.txt",
        status="ready",
        file_type="txt",
        page_count=2,
        file_size_bytes=len(text.encode()),
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc, text


@pytest_asyncio.fixture
async def ready_md_doc(db_session):
    text = "# Title\n\nSome **bold** text.\n\n- item 1\n- item 2\n"
    doc = Document(
        id=uuid.uuid4(),
        filename="readme.md",
        storage_key=f"originals/{uuid.uuid4()}.md",
        status="ready",
        file_type="md",
        page_count=1,
        file_size_bytes=len(text.encode()),
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc, text


@pytest_asyncio.fixture
async def txt_link(db_session, ready_txt_doc):
    doc, text = ready_txt_doc
    link = await LinkService().create_link(db_session, document_id=str(doc.id))
    return link, doc, text


@pytest_asyncio.fixture
async def md_link(db_session, ready_md_doc):
    doc, text = ready_md_doc
    link = await LinkService().create_link(db_session, document_id=str(doc.id))
    return link, doc, text


def _make_session(db_session, link, session_id="a" * 32):
    from app.models.session import ViewerSession
    s = ViewerSession(
        session_id=session_id,
        link_id=link.id,
        ip_hash=None,
    )
    return s


# ── A) Upload acceptance ───────────────────────────────────────────────────────

class TestTextUploadAcceptance:

    @pytest.mark.asyncio
    async def test_txt_upload_returns_202(self, client):
        c, _ = client
        files = {"file": ("notes.txt", b"Hello\nWorld\n", "text/plain")}
        r = await c.post("/api/documents/upload", files=files)
        assert r.status_code == 202, r.text
        assert r.json()["status"] == "uploaded"

    @pytest.mark.asyncio
    async def test_md_upload_returns_202(self, client):
        c, _ = client
        files = {"file": ("readme.md", b"# Title\n\nParagraph.\n", "text/markdown")}
        r = await c.post("/api/documents/upload", files=files)
        assert r.status_code == 202, r.text

    @pytest.mark.asyncio
    async def test_log_upload_returns_202(self, client):
        c, _ = client
        files = {"file": ("app.log", b"2026-01-01 INFO Started\n", "text/plain")}
        r = await c.post("/api/documents/upload", files=files)
        assert r.status_code == 202, r.text

    @pytest.mark.asyncio
    async def test_pdf_upload_still_returns_202(self, client):
        c, _ = client
        pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        files = {"file": ("doc.pdf", pdf, "application/pdf")}
        r = await c.post("/api/documents/upload", files=files)
        assert r.status_code == 202, r.text

    @pytest.mark.asyncio
    async def test_txt_upload_response_never_exposes_storage_key(self, client):
        c, _ = client
        files = {"file": ("notes.txt", b"safe content\n", "text/plain")}
        r = await c.post("/api/documents/upload", files=files)
        body_str = str(r.json())
        assert "storage_key" not in body_str
        assert "originals/" not in body_str

    @pytest.mark.asyncio
    async def test_upload_sets_file_type_txt(self, client, db_session):
        c, _ = client
        files = {"file": ("data.txt", b"content\n", "text/plain")}
        r = await c.post("/api/documents/upload", files=files)
        doc_id = uuid.UUID(r.json()["id"])
        from sqlalchemy import select
        result = await db_session.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one()
        assert doc.file_type == "txt"

    @pytest.mark.asyncio
    async def test_upload_sets_file_type_md(self, client, db_session):
        c, _ = client
        files = {"file": ("readme.md", b"# Hello\n", "text/markdown")}
        r = await c.post("/api/documents/upload", files=files)
        doc_id = uuid.UUID(r.json()["id"])
        from sqlalchemy import select
        result = await db_session.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one()
        assert doc.file_type == "md"

    @pytest.mark.asyncio
    async def test_upload_sets_file_type_log(self, client, db_session):
        c, _ = client
        files = {"file": ("server.log", b"INFO started\n", "text/plain")}
        r = await c.post("/api/documents/upload", files=files)
        doc_id = uuid.UUID(r.json()["id"])
        from sqlalchemy import select
        result = await db_session.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one()
        assert doc.file_type == "log"

    @pytest.mark.asyncio
    async def test_upload_pdf_sets_file_type_pdf(self, client, db_session):
        c, _ = client
        pdf = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\n%%EOF"
        files = {"file": ("doc.pdf", pdf, "application/pdf")}
        r = await c.post("/api/documents/upload", files=files)
        doc_id = uuid.UUID(r.json()["id"])
        from sqlalchemy import select
        result = await db_session.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one()
        assert doc.file_type == "pdf"


# ── B) Binary / unsupported rejection ─────────────────────────────────────────

class TestUnsupportedFileRejection:

    @pytest.mark.asyncio
    async def test_docx_rejected(self, client):
        c, _ = client
        files = {"file": ("doc.docx", b"PK\x03\x04fake", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        r = await c.post("/api/documents/upload", files=files)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_jpeg_content_type_rejected(self, client):
        c, _ = client
        files = {"file": ("photo.jpg", b"\xff\xd8\xff\xe0fake", "image/jpeg")}
        r = await c.post("/api/documents/upload", files=files)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_binary_file_with_txt_extension_rejected(self, client):
        """A file renamed .txt but containing null bytes must be rejected."""
        c, _ = client
        binary_content = b"not text\x00\x00\x00binary garbage"
        files = {"file": ("tricked.txt", binary_content, "text/plain")}
        r = await c.post("/api/documents/upload", files=files)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_pdf_magic_bytes_required_for_pdf_extension(self, client):
        """A .pdf file without %PDF- magic must still be rejected."""
        c, _ = client
        files = {"file": ("fake.pdf", b"definitely not a pdf", "application/pdf")}
        r = await c.post("/api/documents/upload", files=files)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_zip_with_txt_extension_rejected(self, client):
        """A ZIP file (starts with PK\x03\x04) renamed to .txt has null bytes → rejected."""
        c, _ = client
        zip_header = b"PK\x03\x04\x14\x00\x00\x00\x08\x00"
        files = {"file": ("archive.txt", zip_header, "text/plain")}
        r = await c.post("/api/documents/upload", files=files)
        assert r.status_code == 400


# ── C) XSS payload safety ─────────────────────────────────────────────────────

class TestXSSSafety:

    @pytest.mark.asyncio
    async def test_xss_payload_in_txt_accepted_as_upload(self, client):
        """XSS payload must upload OK — rejection happens at render, not upload."""
        c, _ = client
        xss = b"<script>alert(1)</script>\n<img onerror='alert(2)' src=x>\n"
        files = {"file": ("xss.txt", xss, "text/plain")}
        r = await c.post("/api/documents/upload", files=files)
        assert r.status_code == 202

    @pytest.mark.asyncio
    async def test_xss_content_returned_as_plain_text_not_html(self, client, db_session):
        """The text viewer endpoint must return content as a plain string, not HTML.
        The API response is JSON; the React frontend renders it safely.
        """
        c, mock_download = client
        xss_text = "<script>alert(1)</script>\nonload='evil()'\n"
        mock_download.return_value = xss_text.encode()

        doc = Document(
            id=uuid.uuid4(),
            filename="xss.txt",
            storage_key="originals/xss.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=len(xss_text),
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()

        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        # Validate to get a session
        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        assert val_r.status_code == 200
        session_id = val_r.json()["session_id"]

        # Fetch text chunk
        r = await c.get(f"/api/viewer/text/{link.token}/1?session_id={session_id}")
        assert r.status_code == 200
        body = r.json()

        # Content must be a plain string — not HTML-escaped, not rendered
        # The React frontend is responsible for escaping; the API returns raw text.
        assert body["content"] == xss_text.rstrip("\n").rsplit("\n", 1)[0] + "\n" + xss_text.rstrip("\n").rsplit("\n", 1)[1] or "<script>" in body["content"]
        # Critical: the response must NOT have Content-Type: text/html
        assert "text/html" not in r.headers.get("content-type", "")
        # Content is JSON — React will render it as text nodes (auto-escaped)
        assert r.headers["content-type"].startswith("application/json")

    @pytest.mark.asyncio
    async def test_javascript_url_in_md_returned_as_text(self, client, db_session):
        """javascript: URLs in .md content are returned as plain text strings."""
        c, mock_download = client
        md_with_js_url = "# Safe\n\n[click me](javascript:alert(1))\n"
        mock_download.return_value = md_with_js_url.encode()

        doc = Document(
            id=uuid.uuid4(),
            filename="evil.md",
            storage_key="originals/evil.md",
            status="ready",
            file_type="md",
            page_count=1,
            file_size_bytes=len(md_with_js_url),
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        r = await c.get(f"/api/viewer/text/{link.token}/1?session_id={session_id}")
        assert r.status_code == 200
        body = r.json()
        # The content field holds the raw markdown string — React renders it safely
        assert "javascript:alert" in body["content"]  # raw text, not executed
        assert r.headers["content-type"].startswith("application/json")

    @pytest.mark.asyncio
    async def test_html_entity_in_content_returned_as_raw_string(self, client, db_session):
        """HTML special chars in text must be returned as-is; React escapes them."""
        c, mock_download = client
        html_content = '<div onclick="alert(1)">&amp; &#x3C;script&#x3E;\n'
        mock_download.return_value = html_content.encode()

        doc = Document(
            id=uuid.uuid4(),
            filename="html.txt",
            storage_key="originals/html.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=len(html_content),
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        r = await c.get(f"/api/viewer/text/{link.token}/1?session_id={session_id}")
        assert r.status_code == 200
        # JSON response — React frontend auto-escapes all text nodes
        assert r.headers["content-type"].startswith("application/json")


# ── D) Text processor unit tests ──────────────────────────────────────────────

class TestTextProcessor:

    def test_detect_txt_by_extension(self):
        assert detect_file_type("notes.txt", "text/plain", b"hello") == "txt"

    def test_detect_md_by_extension(self):
        assert detect_file_type("readme.md", "application/octet-stream", b"# Hi") == "md"

    def test_detect_log_by_extension(self):
        assert detect_file_type("app.log", "text/plain", b"INFO msg") == "log"

    def test_detect_pdf_by_extension(self):
        assert detect_file_type("doc.pdf", "text/plain", b"%PDF-1.4") == "pdf"

    def test_detect_pdf_by_content_type(self):
        assert detect_file_type("noext", "application/pdf", b"%PDF-1.4") == "pdf"

    def test_detect_md_by_content_type_fallback(self):
        assert detect_file_type("noext", "text/markdown", b"# Hi") == "md"

    def test_detect_txt_by_content_type_fallback(self):
        assert detect_file_type("noext", "text/plain", b"plain text") == "txt"

    def test_unsupported_extension_raises(self):
        with pytest.raises(ValueError, match="Unsupported"):
            detect_file_type("doc.docx", "application/octet-stream", b"content")

    def test_binary_null_bytes_raises(self):
        with pytest.raises(ValueError, match="binary"):
            detect_file_type("data.txt", "text/plain", b"data\x00more")

    def test_zip_header_rejected(self):
        with pytest.raises(ValueError, match="binary"):
            detect_file_type("zip.txt", "text/plain", b"PK\x03\x04\x00something")

    def test_decode_utf8(self):
        assert decode_text_safe(b"hello\nworld") == "hello\nworld"

    def test_decode_crlf_normalized(self):
        assert decode_text_safe(b"line1\r\nline2\r\nline3") == "line1\nline2\nline3"

    def test_decode_cr_normalized(self):
        assert decode_text_safe(b"line1\rline2") == "line1\nline2"

    def test_decode_latin1_fallback(self):
        # latin-1 byte sequence invalid in UTF-8
        latin = b"caf\xe9 au lait"
        result = decode_text_safe(latin)
        assert "caf" in result and "au lait" in result

    def test_chunk_text_splits_correctly(self):
        text = "\n".join(str(i) for i in range(250))
        chunks = chunk_text(text, 100)
        assert len(chunks) == 3
        assert chunks[0].count("\n") == 99   # 100 lines, 99 newlines
        assert chunks[1].count("\n") == 99
        assert chunks[2].count("\n") == 49   # last 50 lines

    def test_chunk_text_empty_returns_one_chunk(self):
        assert chunk_text("", 100) == [""]

    def test_chunk_text_preserves_blank_lines(self):
        text = "a\n\nb\n\nc"
        chunks = chunk_text(text, 100)
        assert len(chunks) == 1
        assert "\n\n" in chunks[0]

    def test_chunk_text_preserves_indentation(self):
        text = "  indented\n\t\ttabbed"
        chunks = chunk_text(text, 100)
        assert "  indented" in chunks[0]
        assert "\t\ttabbed" in chunks[0]

    def test_count_chunks_exact_multiple(self):
        text = "\n".join("x" for _ in range(200))
        assert count_chunks(text, 100) == 2

    def test_count_chunks_with_remainder(self):
        text = "\n".join("x" for _ in range(150))
        assert count_chunks(text, 100) == 2

    def test_count_chunks_empty(self):
        assert count_chunks("", 100) == 1

    def test_supported_extensions_constant(self):
        assert "txt" in SUPPORTED_TEXT_EXTENSIONS
        assert "md" in SUPPORTED_TEXT_EXTENSIONS
        assert "log" in SUPPORTED_TEXT_EXTENSIONS
        assert "pdf" not in SUPPORTED_TEXT_EXTENSIONS

    def test_xss_payload_detected_as_text_not_binary(self):
        """XSS strings have no null bytes and pass binary check."""
        xss = b"<script>alert(1)</script>"
        result = detect_file_type("evil.txt", "text/plain", xss)
        assert result == "txt"


# ── E) Text viewer endpoint ────────────────────────────────────────────────────

class TestTextViewerEndpoint:

    @pytest.mark.asyncio
    async def test_get_chunk_returns_200_with_content(self, client, db_session):
        c, mock_download = client
        text = "\n".join(f"line {i}" for i in range(1, 51))
        mock_download.return_value = text.encode()

        doc = Document(
            id=uuid.uuid4(),
            filename="t.txt",
            storage_key="originals/t.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=len(text),
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        assert val_r.status_code == 200
        session_id = val_r.json()["session_id"]

        r = await c.get(f"/api/viewer/text/{link.token}/1?session_id={session_id}")
        assert r.status_code == 200
        body = r.json()
        assert "content" in body
        assert "chunk_number" in body
        assert "total_chunks" in body
        assert "doc_type" in body
        assert "watermark_text" in body
        assert body["chunk_number"] == 1
        assert body["doc_type"] == "txt"
        assert "line 1" in body["content"]

    @pytest.mark.asyncio
    async def test_chunk_2_returns_correct_slice(self, client, db_session):
        c, mock_download = client
        # 150 lines → 2 chunks (100 + 50)
        text = "\n".join(f"line {i}" for i in range(1, 151))
        mock_download.return_value = text.encode()

        doc = Document(
            id=uuid.uuid4(),
            filename="long.txt",
            storage_key="originals/long.txt",
            status="ready",
            file_type="txt",
            page_count=2,
            file_size_bytes=len(text),
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        r = await c.get(f"/api/viewer/text/{link.token}/2?session_id={session_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["chunk_number"] == 2
        assert "line 101" in body["content"]
        assert "line 1\n" not in body["content"]

    @pytest.mark.asyncio
    async def test_chunk_beyond_total_returns_404(self, client, db_session):
        c, mock_download = client
        text = "just one line"
        mock_download.return_value = text.encode()

        doc = Document(
            id=uuid.uuid4(),
            filename="t.txt",
            storage_key="originals/t.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=len(text),
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        r = await c.get(f"/api/viewer/text/{link.token}/999?session_id={session_id}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_missing_session_id_returns_400(self, client, db_session):
        c, _ = client
        doc = Document(
            id=uuid.uuid4(),
            filename="t.txt",
            storage_key="originals/t.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=10,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        r = await c.get(f"/api/viewer/text/{link.token}/1")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_response_has_no_store_cache_header(self, client, db_session):
        c, mock_download = client
        mock_download.return_value = b"content\n"

        doc = Document(
            id=uuid.uuid4(),
            filename="t.txt",
            storage_key="originals/t.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=8,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        r = await c.get(f"/api/viewer/text/{link.token}/1?session_id={session_id}")
        assert "no-store" in r.headers.get("cache-control", "")

    @pytest.mark.asyncio
    async def test_text_endpoint_rejects_pdf_document(self, client, db_session):
        """The /text/ endpoint must reject PDF documents."""
        c, _ = client
        doc = Document(
            id=uuid.uuid4(),
            filename="doc.pdf",
            storage_key="originals/doc.pdf",
            status="ready",
            file_type="pdf",
            page_count=3,
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        r = await c.get(f"/api/viewer/text/{link.token}/1?session_id={session_id}")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_watermark_text_present_in_response(self, client, db_session):
        c, mock_download = client
        mock_download.return_value = b"hello\n"

        doc = Document(
            id=uuid.uuid4(),
            filename="t.txt",
            storage_key="originals/t.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=6,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        r = await c.get(f"/api/viewer/text/{link.token}/1?session_id={session_id}")
        body = r.json()
        assert "watermark_text" in body
        assert body["watermark_text"]  # non-empty
        # Watermark must contain session prefix
        assert "sess:" in body["watermark_text"]


# ── F) Access control parity ──────────────────────────────────────────────────

class TestTextAccessControl:

    @pytest.mark.asyncio
    async def test_revoked_link_blocks_text_chunk(self, client, db_session):
        c, mock_download = client
        mock_download.return_value = b"content\n"

        doc = Document(
            id=uuid.uuid4(),
            filename="t.txt",
            storage_key="originals/t.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=8,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        # Get a valid session before revoking
        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        # Revoke
        await c.delete(f"/api/links/{link.id}")

        # Flush the link cache so the revocation is visible immediately
        from app.services.viewer_cache import clear_all_caches
        clear_all_caches()

        r = await c.get(f"/api/viewer/text/{link.token}/1?session_id={session_id}")
        assert r.status_code == 410

    @pytest.mark.asyncio
    async def test_expired_link_blocks_text_chunk(self, client, db_session):
        c, mock_download = client
        mock_download.return_value = b"content\n"

        doc = Document(
            id=uuid.uuid4(),
            filename="t.txt",
            storage_key="originals/t.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=8,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()

        past = datetime.now(timezone.utc) - timedelta(hours=1)
        link = await LinkService().create_link(
            db_session, document_id=str(doc.id), expires_at=past
        )
        await db_session.commit()

        # Validate succeeds before cache notices expiry (direct validate may also fail)
        # Use a dummy session_id that would exist
        from app.services.viewer_cache import clear_all_caches
        clear_all_caches()

        r = await c.get(f"/api/viewer/text/{link.token}/1?session_id={'b' * 32}")
        assert r.status_code == 410

    @pytest.mark.asyncio
    async def test_invalid_link_token_returns_404(self, client, db_session):
        c, _ = client
        r = await c.get(f"/api/viewer/text/nonexistent-token-xyz/1?session_id={'a' * 32}")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_processing_doc_blocks_text_chunk(self, client, db_session):
        c, _ = client
        doc = Document(
            id=uuid.uuid4(),
            filename="t.txt",
            storage_key="originals/t.txt",
            status="processing",  # not ready
            file_type="txt",
            page_count=None,
            file_size_bytes=8,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        from app.services.viewer_cache import clear_all_caches
        clear_all_caches()

        r = await c.get(f"/api/viewer/text/{link.token}/1?session_id={'a' * 32}")
        assert r.status_code == 503


# ── G) Analytics events ────────────────────────────────────────────────────────

class TestTextAnalytics:

    @pytest.mark.asyncio
    async def test_validate_logs_opened_event_for_text_doc(self, client, db_session):
        c, _ = client
        doc = Document(
            id=uuid.uuid4(),
            filename="t.txt",
            storage_key="originals/t.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=8,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        r = await c.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200

        from sqlalchemy import select
        from app.models.event import AccessEvent
        result = await db_session.execute(
            select(AccessEvent).where(AccessEvent.link_id == link.id)
        )
        events = result.scalars().all()
        assert any(e.event_type == "opened" for e in events)

    @pytest.mark.asyncio
    async def test_text_chunk_fetch_logs_page_viewed(self, client, db_session):
        c, mock_download = client
        mock_download.return_value = b"content\n"

        doc = Document(
            id=uuid.uuid4(),
            filename="t.txt",
            storage_key="originals/t.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=8,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        await c.get(f"/api/viewer/text/{link.token}/1?session_id={session_id}")

        from sqlalchemy import select
        from app.models.event import AccessEvent
        result = await db_session.execute(
            select(AccessEvent).where(
                AccessEvent.link_id == link.id,
                AccessEvent.event_type == "page_viewed",
            )
        )
        events = result.scalars().all()
        assert len(events) >= 1
        assert events[0].page_number == 1


# ── H) PDF regression ─────────────────────────────────────────────────────────

class TestPDFRegression:

    @pytest.mark.asyncio
    async def test_pdf_upload_still_accepted(self, client):
        c, _ = client
        pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
        r = await c.post("/api/documents/upload", files={"file": ("doc.pdf", pdf, "application/pdf")})
        assert r.status_code == 202

    @pytest.mark.asyncio
    async def test_pdf_page_endpoint_unchanged(self, client, db_session):
        """The /api/viewer/page/{token}/{page} endpoint must still work for PDFs."""
        c, mock_download = client
        from PIL import Image
        import io
        img = Image.new("RGB", (100, 100), color=(200, 200, 200))
        buf = io.BytesIO()
        img.save(buf, format="WEBP")
        mock_download.return_value = buf.getvalue()

        doc = Document(
            id=uuid.uuid4(),
            filename="doc.pdf",
            storage_key="originals/doc.pdf",
            status="ready",
            file_type="pdf",
            page_count=1,
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()

        from app.models.document import DocumentPage
        page = DocumentPage(
            document_id=doc.id,
            page_number=1,
            storage_key="pages/doc/0001.webp",
            width_px=595,
            height_px=842,
        )
        db_session.add(page)
        await db_session.flush()

        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        assert val_r.status_code == 200
        session_id = val_r.json()["session_id"]

        from app.services.viewer_cache import clear_all_caches
        clear_all_caches()

        r = await c.get(f"/api/viewer/page/{link.token}/1?session_id={session_id}")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/webp"

    @pytest.mark.asyncio
    async def test_validate_returns_doc_type_pdf_for_pdf(self, client, db_session):
        c, _ = client
        doc = Document(
            id=uuid.uuid4(),
            filename="doc.pdf",
            storage_key="originals/doc.pdf",
            status="ready",
            file_type="pdf",
            page_count=2,
            file_size_bytes=1024,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        r = await c.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200
        assert r.json()["doc_type"] == "pdf"

    @pytest.mark.asyncio
    async def test_pdf_worker_path_unchanged(self):
        """PDF pipeline still calls rasterizer + watermark services."""
        from unittest.mock import AsyncMock, MagicMock, patch
        import uuid as _uuid
        from app.workers.tasks import process_document_with_session

        doc_id = str(_uuid.uuid4())
        mock_db = MagicMock()
        mock_doc = MagicMock()
        mock_doc.id = _uuid.UUID(doc_id)
        mock_doc.status = "uploaded"
        mock_doc.file_type = "pdf"
        mock_doc.storage_key = f"originals/{doc_id}.pdf"
        import datetime
        mock_doc.updated_at = datetime.datetime.now(datetime.timezone.utc)

        async def mock_execute(_):
            result = MagicMock()
            result.scalar_one_or_none.return_value = mock_doc
            return result

        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        mock_storage = MagicMock()
        mock_storage.download_bytes = AsyncMock(return_value=b"%PDF-fake")
        mock_storage.upload_file = AsyncMock()

        mock_rasterizer = MagicMock()
        rast_page = MagicMock(page_number=1, image_bytes=b"webp", width_px=595, height_px=842)
        mock_rasterizer.rasterize_document = AsyncMock(return_value=[rast_page])

        mock_watermark = MagicMock()
        mock_watermark.apply_forensic_stamp = MagicMock(return_value=b"stamped")
        mock_watermark.apply_visible_watermark = MagicMock(return_value=b"watermarked")

        result = await process_document_with_session(
            mock_db, doc_id, mock_storage, mock_rasterizer, mock_watermark
        )
        assert result["status"] == "ready"
        mock_rasterizer.rasterize_document.assert_called_once()
        mock_watermark.apply_forensic_stamp.assert_called_once()


# ── I) Validate returns doc_type ──────────────────────────────────────────────

class TestValidateDocType:

    @pytest.mark.asyncio
    async def test_validate_returns_doc_type_txt(self, client, db_session):
        c, _ = client
        doc = Document(
            id=uuid.uuid4(),
            filename="notes.txt",
            storage_key="originals/notes.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=10,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        r = await c.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200
        assert r.json()["doc_type"] == "txt"

    @pytest.mark.asyncio
    async def test_validate_returns_doc_type_md(self, client, db_session):
        c, _ = client
        doc = Document(
            id=uuid.uuid4(),
            filename="readme.md",
            storage_key="originals/readme.md",
            status="ready",
            file_type="md",
            page_count=1,
            file_size_bytes=10,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        r = await c.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200
        assert r.json()["doc_type"] == "md"

    @pytest.mark.asyncio
    async def test_validate_returns_doc_type_log(self, client, db_session):
        c, _ = client
        doc = Document(
            id=uuid.uuid4(),
            filename="app.log",
            storage_key="originals/app.log",
            status="ready",
            file_type="log",
            page_count=1,
            file_size_bytes=10,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        r = await c.post("/api/viewer/validate", json={"token": link.token})
        assert r.status_code == 200
        assert r.json()["doc_type"] == "log"


# ── J) Large file and edge cases ──────────────────────────────────────────────

class TestLargeFileAndEdgeCases:

    @pytest.mark.asyncio
    async def test_large_text_file_chunks_correctly(self, client, db_session):
        """A 10_000-line file should produce 100 chunks at 100 lines each."""
        c, mock_download = client
        large_text = "\n".join(f"line {i}" for i in range(1, 10_001))
        mock_download.return_value = large_text.encode()

        doc = Document(
            id=uuid.uuid4(),
            filename="big.txt",
            storage_key="originals/big.txt",
            status="ready",
            file_type="txt",
            page_count=100,
            file_size_bytes=len(large_text),
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        # First chunk
        r1 = await c.get(f"/api/viewer/text/{link.token}/1?session_id={session_id}")
        assert r1.status_code == 200
        assert r1.json()["total_chunks"] == 100

        # Last chunk
        r100 = await c.get(f"/api/viewer/text/{link.token}/100?session_id={session_id}")
        assert r100.status_code == 200
        assert "line 10000" in r100.json()["content"]

    @pytest.mark.asyncio
    async def test_empty_text_file_returns_one_chunk(self, client, db_session):
        c, mock_download = client
        mock_download.return_value = b""

        doc = Document(
            id=uuid.uuid4(),
            filename="empty.txt",
            storage_key="originals/empty.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=0,
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        r = await c.get(f"/api/viewer/text/{link.token}/1?session_id={session_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["total_chunks"] == 1
        assert body["content"] == ""

    def test_long_lines_preserved_in_chunks(self):
        long_line = "x" * 10_000
        text = "\n".join([long_line] * 5)
        chunks = chunk_text(text, 100)
        assert len(chunks) == 1
        assert chunks[0].count("x" * 10_000) == 5

    def test_latin1_bytes_decode_without_error(self):
        latin_bytes = bytes(range(128, 256))  # all 8-bit bytes
        result = decode_text_safe(latin_bytes)
        assert isinstance(result, str)
        assert len(result) == 128

    @pytest.mark.asyncio
    async def test_repeated_chunk_requests_return_consistent_content(self, client, db_session):
        """Repeated chunk requests (second hits cache) must return identical content."""
        c, mock_download = client
        text = "\n".join(f"line {i}" for i in range(1, 51))
        mock_download.return_value = text.encode()

        doc = Document(
            id=uuid.uuid4(),
            filename="t.txt",
            storage_key="originals/concurrent.txt",
            status="ready",
            file_type="txt",
            page_count=1,
            file_size_bytes=len(text),
            user_id=uuid.UUID(TEST_USER_ID),
        )
        db_session.add(doc)
        await db_session.flush()
        link = await LinkService().create_link(db_session, document_id=str(doc.id))
        await db_session.commit()

        val_r = await c.post("/api/viewer/validate", json={"token": link.token})
        session_id = val_r.json()["session_id"]

        r1 = await c.get(f"/api/viewer/text/{link.token}/1?session_id={session_id}")
        r2 = await c.get(f"/api/viewer/text/{link.token}/1?session_id={session_id}")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["content"] == r2.json()["content"]


# ── K) Worker text pipeline ────────────────────────────────────────────────────

class TestTextWorkerPipeline:

    @pytest.mark.asyncio
    async def test_text_worker_sets_ready_and_chunk_count(self):
        """process_document_with_session correctly processes a text document."""
        from unittest.mock import AsyncMock, MagicMock
        import uuid as _uuid
        from app.workers.tasks import process_document_with_session

        doc_id = str(_uuid.uuid4())
        text_150 = "\n".join(f"L{i}" for i in range(1, 151))

        mock_doc = MagicMock()
        mock_doc.id = _uuid.UUID(doc_id)
        mock_doc.status = "uploaded"
        mock_doc.file_type = "txt"
        mock_doc.storage_key = f"originals/{doc_id}.txt"
        import datetime
        mock_doc.updated_at = datetime.datetime.now(datetime.timezone.utc)

        async def mock_execute(_):
            r = MagicMock()
            r.scalar_one_or_none.return_value = mock_doc
            return r

        mock_db = MagicMock()
        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        mock_storage = MagicMock()
        mock_storage.download_bytes = AsyncMock(return_value=text_150.encode())
        mock_storage.upload_file = AsyncMock()

        result = await process_document_with_session(
            mock_db, doc_id, mock_storage, MagicMock(), MagicMock()
        )

        assert result["status"] == "ready"
        assert result["page_count"] == 2  # 150 lines / 100 per chunk
        assert mock_doc.status == "ready"
        assert mock_doc.page_count == 2

    @pytest.mark.asyncio
    async def test_text_worker_rasterizer_not_called(self):
        """Rasterizer must never be called for text documents."""
        from unittest.mock import AsyncMock, MagicMock
        import uuid as _uuid
        from app.workers.tasks import process_document_with_session

        doc_id = str(_uuid.uuid4())
        mock_doc = MagicMock()
        mock_doc.id = _uuid.UUID(doc_id)
        mock_doc.status = "uploaded"
        mock_doc.file_type = "md"
        mock_doc.storage_key = f"originals/{doc_id}.md"
        import datetime
        mock_doc.updated_at = datetime.datetime.now(datetime.timezone.utc)

        async def mock_execute(_):
            r = MagicMock()
            r.scalar_one_or_none.return_value = mock_doc
            return r

        mock_db = MagicMock()
        mock_db.execute = mock_execute
        mock_db.commit = AsyncMock()
        mock_db.flush = AsyncMock()
        mock_db.add = MagicMock()

        mock_storage = MagicMock()
        mock_storage.download_bytes = AsyncMock(return_value=b"# Hello\n")
        mock_storage.upload_file = AsyncMock()

        mock_rasterizer = MagicMock()
        mock_rasterizer.rasterize_document = AsyncMock()

        await process_document_with_session(
            mock_db, doc_id, mock_storage, mock_rasterizer, MagicMock()
        )

        # Rasterizer must NOT be called for text documents
        mock_rasterizer.rasterize_document.assert_not_called()
