import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.models.document import Document, DocumentPage  # noqa
from app.models.event import AccessEvent  # noqa
from app.services.link_service import LinkService

TEST_DB_URL = "sqlite+aiosqlite:///./test_link_service.db"


@pytest.fixture
async def db_and_doc():
    engine = create_async_engine(TEST_DB_URL, echo=False, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        doc = Document(
            id=uuid.uuid4(),
            filename="test.pdf",
            storage_key="originals/test.pdf",
            status="ready",
            page_count=2,
            file_size_bytes=1024,
            user_id=uuid.uuid4(),
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)
        yield session, doc
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


class TestLinkService:

    @pytest.mark.asyncio
    async def test_create_link_generates_unique_token(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        link1 = await svc.create_link(db, document_id=str(doc.id))
        link2 = await svc.create_link(db, document_id=str(doc.id))
        assert link1.token != link2.token

    @pytest.mark.asyncio
    async def test_create_link_token_length_is_64(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        link = await svc.create_link(db, document_id=str(doc.id))
        assert len(link.token) == 64

    @pytest.mark.asyncio
    async def test_create_link_hashes_password(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        link = await svc.create_link(db, document_id=str(doc.id), password="mypassword")
        assert link.password_hash != "mypassword"
        assert link.password_hash.startswith("$2b$")

    @pytest.mark.asyncio
    async def test_validate_link_succeeds_with_correct_password(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        link = await svc.create_link(db, document_id=str(doc.id), password="correct_password")
        result = await svc.validate_link(db, token=link.token, password="correct_password")
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_validate_link_fails_with_wrong_password(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        link = await svc.create_link(db, document_id=str(doc.id), password="correct_password")
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(db, token=link.token, password="wrong_password")
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_validate_link_fails_when_expired(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        link = await svc.create_link(
            db,
            document_id=str(doc.id),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(db, token=link.token)
        assert exc.value.status_code == 410

    @pytest.mark.asyncio
    async def test_validate_link_fails_when_revoked(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        link = await svc.create_link(db, document_id=str(doc.id))
        await svc.revoke_link(db, str(link.id))
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(db, token=link.token)
        assert exc.value.status_code == 410

    @pytest.mark.asyncio
    async def test_validate_link_fails_when_max_views_exceeded(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        # max_views=2: two successful validates, third must fail.
        link = await svc.create_link(db, document_id=str(doc.id), max_views=2)
        await svc.validate_link(db, token=link.token)
        await svc.validate_link(db, token=link.token)
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(db, token=link.token)
        assert exc.value.status_code == 410

    @pytest.mark.asyncio
    async def test_validate_link_fails_for_disallowed_email(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        link = await svc.create_link(
            db,
            document_id=str(doc.id),
            allowed_emails=["allowed@example.com"],
        )
        with pytest.raises(HTTPException) as exc:
            await svc.validate_link(
                db, token=link.token, viewer_email="notallowed@example.com"
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_validate_link_email_check_is_case_insensitive(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        link = await svc.create_link(
            db,
            document_id=str(doc.id),
            allowed_emails=["user@example.com"],
        )
        result = await svc.validate_link(
            db, token=link.token, viewer_email="USER@EXAMPLE.COM"
        )
        assert result.is_valid is True

    @pytest.mark.asyncio
    async def test_revoke_sets_revoked_at(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        link = await svc.create_link(db, document_id=str(doc.id))
        assert link.revoked_at is None
        revoked = await svc.revoke_link(db, str(link.id))
        assert revoked.revoked_at is not None

    @pytest.mark.asyncio
    async def test_validate_increments_view_count_atomically(self, db_and_doc):
        """Each successful validate increments view_count by exactly 1."""
        db, doc = db_and_doc
        svc = LinkService()
        link = await svc.create_link(db, document_id=str(doc.id))
        assert link.view_count == 0
        await svc.validate_link(db, token=link.token)
        await svc.validate_link(db, token=link.token)
        await db.refresh(link)
        assert link.view_count == 2

    def test_generate_session_id_is_32_chars(self):
        svc = LinkService()
        sid = svc._generate_session_id()
        assert len(sid) == 32  # token_hex(16) = 32 hex chars = 128-bit entropy
        assert all(c in "0123456789abcdef" for c in sid)
