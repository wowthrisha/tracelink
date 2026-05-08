"""
LinkService unit tests — isolated SQLite DB, no HTTP layer.
Add securedoc/backend to sys.path before running:
  PYTHONPATH=../backend pytest services/test_link_service.py
"""
import sys
import os
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from app.database import Base
from app.models.document import Document, DocumentPage
from app.models.link import ShareLink
from app.models.event import AccessEvent  # noqa: ensure model registered
from app.services.link_service import LinkService

pytestmark = pytest.mark.service

TEST_DB = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(TEST_DB, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def document(db):
    doc = Document(
        id=uuid.uuid4(),
        filename="test.pdf",
        storage_key="originals/test.pdf",
        status="ready",
        page_count=3,
        file_size_bytes=1024,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@pytest.fixture
def svc():
    return LinkService()


class TestCreateLink:

    async def test_creates_link_with_token(self, svc, db, document):
        link = await svc.create_link(db, document_id=str(document.id))
        assert link.token is not None
        assert len(link.token) == 64

    async def test_token_url_safe_chars_only(self, svc, db, document):
        link = await svc.create_link(db, document_id=str(document.id))
        import re
        assert re.match(r'^[A-Za-z0-9\-_]+$', link.token)

    async def test_unique_tokens_per_link(self, svc, db, document):
        tokens = set()
        for _ in range(10):
            lnk = await svc.create_link(db, document_id=str(document.id))
            tokens.add(lnk.token)
        assert len(tokens) == 10

    async def test_password_stored_as_hash(self, svc, db, document):
        link = await svc.create_link(db, document_id=str(document.id), password="secret123")
        assert link.password_hash is not None
        assert link.password_hash != "secret123"
        assert link.password_hash.startswith("$2b$")

    async def test_no_password_means_no_hash(self, svc, db, document):
        link = await svc.create_link(db, document_id=str(document.id))
        assert link.password_hash is None

    async def test_max_views_stored(self, svc, db, document):
        link = await svc.create_link(db, document_id=str(document.id), max_views=5)
        assert link.max_views == 5

    async def test_expires_at_stored(self, svc, db, document):
        expires = datetime.now(timezone.utc) + timedelta(days=7)
        link = await svc.create_link(db, document_id=str(document.id), expires_at=expires)
        assert link.expires_at is not None

    async def test_allowed_emails_stored_as_json(self, svc, db, document):
        emails = ["alice@example.com", "bob@example.com"]
        link = await svc.create_link(
            db, document_id=str(document.id), allowed_emails=emails
        )
        import json
        stored = json.loads(link.allowed_emails)
        assert "alice@example.com" in stored
        assert "bob@example.com" in stored

    async def test_emails_normalized_to_lowercase(self, svc, db, document):
        link = await svc.create_link(
            db, document_id=str(document.id), allowed_emails=["Alice@Example.COM"]
        )
        import json
        stored = json.loads(link.allowed_emails)
        assert "alice@example.com" in stored


class TestValidateLink:

    async def test_valid_link_returns_result(self, svc, db, document):
        link = await svc.create_link(db, document_id=str(document.id))
        result = await svc.validate_link(db, token=link.token)
        assert result.is_valid is True
        assert result.link.id == link.id

    async def test_session_id_is_16_hex_chars(self, svc, db, document):
        link = await svc.create_link(db, document_id=str(document.id))
        result = await svc.validate_link(db, token=link.token)
        assert len(result.session_id) == 16
        int(result.session_id, 16)  # must be valid hex

    async def test_invalid_token_raises_404(self, svc, db):
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(db, token="x" * 64)
        assert exc.value.status_code == 404

    async def test_expired_link_raises_410(self, svc, db, document):
        link = await svc.create_link(
            db,
            document_id=str(document.id),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(db, token=link.token)
        assert exc.value.status_code == 410

    async def test_revoked_link_raises_410(self, svc, db, document):
        link = await svc.create_link(db, document_id=str(document.id))
        await svc.revoke_link(db, str(link.id))
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(db, token=link.token)
        assert exc.value.status_code == 410

    async def test_max_views_exceeded_raises_410(self, svc, db, document):
        link = await svc.create_link(
            db, document_id=str(document.id), max_views=1
        )
        # Exhaust the one view
        await svc.increment_view_count(db, str(link.id))
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(db, token=link.token)
        assert exc.value.status_code == 410

    async def test_wrong_password_raises_401(self, svc, db, document):
        link = await svc.create_link(
            db, document_id=str(document.id), password="correct"
        )
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(db, token=link.token, password="wrong")
        assert exc.value.status_code == 401

    async def test_correct_password_validates(self, svc, db, document):
        link = await svc.create_link(
            db, document_id=str(document.id), password="correct"
        )
        result = await svc.validate_link(db, token=link.token, password="correct")
        assert result.is_valid is True

    async def test_missing_password_raises_401(self, svc, db, document):
        link = await svc.create_link(
            db, document_id=str(document.id), password="required"
        )
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(db, token=link.token)
        assert exc.value.status_code == 401

    async def test_email_not_in_allowlist_raises_403(self, svc, db, document):
        link = await svc.create_link(
            db,
            document_id=str(document.id),
            allowed_emails=["allowed@example.com"],
        )
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(
                db, token=link.token, viewer_email="denied@example.com"
            )
        assert exc.value.status_code == 403

    async def test_email_in_allowlist_validates(self, svc, db, document):
        link = await svc.create_link(
            db,
            document_id=str(document.id),
            allowed_emails=["allowed@example.com"],
        )
        result = await svc.validate_link(
            db, token=link.token, viewer_email="allowed@example.com"
        )
        assert result.is_valid is True


class TestRevokeLink:

    async def test_revoke_sets_revoked_at(self, svc, db, document):
        link = await svc.create_link(db, document_id=str(document.id))
        assert link.revoked_at is None
        revoked = await svc.revoke_link(db, str(link.id))
        assert revoked.revoked_at is not None

    async def test_revoke_nonexistent_raises_404(self, svc, db):
        with pytest.raises(HTTPException) as exc:
            await svc.revoke_link(db, str(uuid.uuid4()))
        assert exc.value.status_code == 404


class TestIncrementViewCount:

    async def test_increments_atomically(self, svc, db, document):
        link = await svc.create_link(db, document_id=str(document.id))
        assert link.view_count == 0
        await svc.increment_view_count(db, str(link.id))
        await svc.increment_view_count(db, str(link.id))
        await db.refresh(link)
        assert link.view_count == 2
