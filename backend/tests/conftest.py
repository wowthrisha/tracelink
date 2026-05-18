import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.document import Document, DocumentPage
from app.models.link import ShareLink
from app.models.event import AccessEvent  # noqa: ensure event model loaded
from app.models.session import ViewerSession  # noqa: ensure session model loaded
from app.services.link_service import LinkService
from app.auth import get_current_user

TEST_DB_URL = "sqlite+aiosqlite:///./test_securedoc.db"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
TEST_USER_B_ID = "660f9500-f3ac-52e5-b827-557766551111"


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset slowapi's in-memory rate limit counters between tests.

    Without this, tests that share the FastAPI app instance accumulate hits
    against rate-limited endpoints (e.g. /api/viewer/validate at 20/min)
    and start failing with 429 after a few dozen tests within the same minute.
    """
    from app.middleware.rate_limit import limiter
    storage = getattr(limiter, "_storage", None)
    if storage is not None:
        try:
            storage.reset()
        except Exception:
            pass  # storage backend may not support reset — silently skip


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DB_URL, echo=False, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_db():
        yield db_session

    def override_get_current_user():
        return {"user_id": TEST_USER_ID, "email": "test@example.com", "role": "authenticated"}

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with patch("app.services.storage.StorageService.upload_file", new_callable=AsyncMock) as mock_upload, \
         patch("app.services.storage.StorageService.generate_presigned_url", new_callable=AsyncMock) as mock_presign, \
         patch("app.services.storage.StorageService.download_bytes", new_callable=AsyncMock) as mock_download, \
         patch("app.services.storage.StorageService.delete_file", new_callable=AsyncMock) as mock_delete, \
         patch("app.services.storage.StorageService.list_keys_with_prefix", new_callable=AsyncMock) as mock_list, \
         patch("app.workers.tasks.process_document.delay") as mock_celery:

        mock_upload.return_value = "mocked/key.pdf"
        mock_presign.return_value = "https://example.com/presigned"
        mock_download.return_value = _make_webp_bytes()
        mock_delete.return_value = None
        mock_list.return_value = []
        mock_celery.return_value = MagicMock(id="fake-task-id")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()


def _make_webp_bytes() -> bytes:
    """Create minimal valid WebP image bytes."""
    from PIL import Image
    import io
    img = Image.new("RGB", (100, 100), color=(200, 200, 200))
    buf = io.BytesIO()
    img.save(buf, format="WEBP")
    return buf.getvalue()


@pytest.fixture
def sample_pdf_bytes():
    return (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n"
        b"xref\n0 1\n0000000000 65535 f\n"
        b"trailer\n<< /Size 1 >>\nstartxref\n9\n%%EOF"
    )


@pytest.fixture
def invalid_bytes():
    return b"This is not a PDF at all"


@pytest.fixture
def sample_webp_bytes():
    return _make_webp_bytes()


@pytest_asyncio.fixture
async def sample_document(db_session):
    doc = Document(
        id=uuid.uuid4(),
        filename="test.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status="ready",
        page_count=3,
        file_size_bytes=1024,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest_asyncio.fixture
async def sample_document_in_db(client, db_session):
    doc = Document(
        id=uuid.uuid4(),
        filename="test.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status="ready",
        page_count=3,
        file_size_bytes=1024,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest_asyncio.fixture
async def ready_document(db_session):
    doc = Document(
        id=uuid.uuid4(),
        filename="ready.pdf",
        storage_key="originals/ready.pdf",
        status="ready",
        page_count=3,
        file_size_bytes=2048,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db_session.add(doc)
    await db_session.flush()

    for i in range(1, 4):
        page = DocumentPage(
            document_id=doc.id,
            page_number=i,
            storage_key=f"pages/{doc.id}/{i:04d}.webp",
            width_px=595,
            height_px=842,
        )
        db_session.add(page)

    await db_session.commit()
    await db_session.refresh(doc)
    return doc


@pytest_asyncio.fixture
async def active_link(db_session, ready_document):
    link_svc = LinkService()
    link = await link_svc.create_link(
        db_session,
        document_id=str(ready_document.id),
        label="Test link",
    )
    return link


@pytest_asyncio.fixture
async def sample_link(db_session, sample_document_in_db):
    link_svc = LinkService()
    link = await link_svc.create_link(
        db_session,
        document_id=str(sample_document_in_db.id),
        label="Sample link",
    )
    return link


@pytest_asyncio.fixture
async def password_link(db_session, ready_document):
    link_svc = LinkService()
    link = await link_svc.create_link(
        db_session,
        document_id=str(ready_document.id),
        password="correct_password",
    )
    return link


@pytest_asyncio.fixture
async def expired_link(db_session, ready_document):
    link_svc = LinkService()
    link = await link_svc.create_link(
        db_session,
        document_id=str(ready_document.id),
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    return link


@pytest_asyncio.fixture
async def revoked_link(db_session, ready_document):
    link_svc = LinkService()
    link = await link_svc.create_link(
        db_session,
        document_id=str(ready_document.id),
    )
    await link_svc.revoke_link(db_session, str(link.id))
    await db_session.refresh(link)
    return link


@pytest_asyncio.fixture
async def other_document(db_session):
    doc = Document(
        id=uuid.uuid4(),
        filename="other.pdf",
        storage_key=f"originals/{uuid.uuid4()}.pdf",
        status="ready",
        page_count=1,
        file_size_bytes=512,
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


# ── Phase 5: Text document fixtures ──────────────────────────────────────────

@pytest.fixture
def sample_txt_bytes() -> bytes:
    return b"Hello, SecureDoc!\nLine 2\nLine 3\n"


@pytest.fixture
def sample_md_bytes() -> bytes:
    return b"# Heading\n\nSome **bold** text.\n\n- item 1\n- item 2\n"


@pytest.fixture
def sample_log_bytes() -> bytes:
    return b"2026-01-01 INFO  Server started\n2026-01-01 DEBUG Request received\n"


@pytest_asyncio.fixture
async def ready_text_document(db_session):
    """A ready .txt document with 2 chunks (200 lines at 100/chunk)."""
    lines = "\n".join(f"line {i}" for i in range(1, 201))
    doc = Document(
        id=uuid.uuid4(),
        filename="notes.txt",
        storage_key=f"originals/{uuid.uuid4()}.txt",
        status="ready",
        file_type="txt",
        page_count=2,  # 200 lines / 100 per chunk = 2 chunks
        file_size_bytes=len(lines.encode()),
        user_id=uuid.UUID(TEST_USER_ID),
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    return doc, lines


@pytest_asyncio.fixture
async def active_text_link(db_session, ready_text_document):
    doc, _ = ready_text_document
    link_svc = LinkService()
    link = await link_svc.create_link(
        db_session,
        document_id=str(doc.id),
        label="Text test link",
    )
    return link, doc
