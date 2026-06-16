import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.models.document import Document, DocumentPage  # noqa
from app.models.link import ShareLink
from app.models.event import AccessEvent  # noqa
from app.models.session import ViewerSession
from app.models.annotation import ViewerAnnotation
from app.models.viewer_profile import ViewerProfile
from app.services.link_service import LinkService
from app.services.viewer_profile import derive_display_name, get_or_create_viewer_profile

TEST_DB_URL = "sqlite+aiosqlite:///./test_viewer_identity.db"


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


class TestDeriveDisplayName:

    def test_dotted_local_part(self):
        assert derive_display_name("john.doe@x.com") == "John Doe"

    def test_underscore_and_hyphen(self):
        assert derive_display_name("jane_doe@x.com") == "Jane Doe"
        assert derive_display_name("jane-doe@x.com") == "Jane Doe"

    def test_no_separators(self):
        assert derive_display_name("jdoe@x.com") == "Jdoe"

    def test_digits_only_local_part_falls_back_to_raw(self):
        # all-digit tokens are dropped; nothing left to title-case meaningfully
        assert derive_display_name("12345@x.com") == "12345"

    def test_mixed_alpha_and_digit_tokens(self):
        assert derive_display_name("psg.student2024@psgtech.ac.in") == "Psg Student2024"


class TestGetOrCreateViewerProfile:

    @pytest.mark.asyncio
    async def test_creates_new_profile(self, db_and_doc):
        db, _doc = db_and_doc
        profile = await get_or_create_viewer_profile(db, "John.Doe@Example.com")
        await db.commit()
        assert profile is not None
        assert profile.email == "john.doe@example.com"  # normalized lowercase
        assert profile.display_name == "John Doe"
        assert profile.first_seen_at is not None
        assert profile.last_seen_at is not None

    @pytest.mark.asyncio
    async def test_reuses_existing_profile_for_same_email(self, db_and_doc):
        db, _doc = db_and_doc
        p1 = await get_or_create_viewer_profile(db, "john@example.com")
        await db.commit()
        p2 = await get_or_create_viewer_profile(db, "JOHN@EXAMPLE.COM")
        await db.commit()
        assert str(p1.id) == str(p2.id)
        rows = (await db.execute(__import__("sqlalchemy").select(ViewerProfile))).scalars().all()
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_falsy_email_returns_none(self, db_and_doc):
        db, _doc = db_and_doc
        assert await get_or_create_viewer_profile(db, None) is None
        assert await get_or_create_viewer_profile(db, "") is None
        assert await get_or_create_viewer_profile(db, "   ") is None


class TestValidateLinkPersistsIdentity:

    @pytest.mark.asyncio
    async def test_validate_with_email_stores_plaintext_and_profile(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        link = await svc.create_link(db, document_id=str(doc.id), allowed_emails=["john@example.com"])
        result = await svc.validate_link(db, token=link.token, viewer_email="John@Example.com")

        sess = await db.get(ViewerSession, result.session_id)
        assert sess.viewer_email == "john@example.com"  # normalized lowercase
        assert sess.viewer_email_masked == "J***@Example.com"  # mask_email preserves original case
        assert sess.viewer_profile_id is not None

        profile = await db.get(ViewerProfile, sess.viewer_profile_id)
        assert profile.email == "john@example.com"
        assert profile.display_name == "John"

    @pytest.mark.asyncio
    async def test_validate_without_email_leaves_identity_null(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        link = await svc.create_link(db, document_id=str(doc.id))
        result = await svc.validate_link(db, token=link.token)

        sess = await db.get(ViewerSession, result.session_id)
        assert sess.viewer_email is None
        assert sess.viewer_profile_id is None


class TestAnnotationCopiesIdentityFromSession:

    @pytest.mark.asyncio
    async def test_annotation_row_can_store_viewer_email_and_profile(self, db_and_doc):
        db, doc = db_and_doc
        svc = LinkService()
        link = await svc.create_link(db, document_id=str(doc.id), allowed_emails=["jane@example.com"])
        result = await svc.validate_link(db, token=link.token, viewer_email="jane@example.com")
        sess = await db.get(ViewerSession, result.session_id)

        annot = ViewerAnnotation(
            link_id=link.id,
            session_id=result.session_id,
            viewer_email_masked=sess.viewer_email_masked,
            viewer_email=sess.viewer_email,
            viewer_profile_id=sess.viewer_profile_id,
            page_number=1,
            annotation_type="comment",
            coords="{}",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(annot)
        await db.commit()
        await db.refresh(annot)

        assert annot.viewer_email == "jane@example.com"
        assert annot.viewer_profile_id == sess.viewer_profile_id

        profile = await db.get(ViewerProfile, annot.viewer_profile_id)
        assert profile.display_name == "Jane"
