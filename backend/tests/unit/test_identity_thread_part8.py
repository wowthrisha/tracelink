"""PART 8 tests — Identity Exposure and Reply Thread Visibility.

Covers:
- feedback serialization (display_name/viewer_email/viewer_profile_id exposure rules)
- uploader reply creation (JWT-only, no viewer session dependency)
- viewer thread retrieval (root + replies, depth-1)
- reply count aggregation
- CSV export contents (not just headers)
- expired viewer session with an active uploader reply still succeeding
"""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base
from app.models.document import Document, DocumentPage  # noqa
from app.models.event import AccessEvent  # noqa
from app.models.session import ViewerSession
from app.models.annotation import ViewerAnnotation
from app.services.link_service import LinkService
from app.services.viewer_cache import session_cache
from app.routers.annotations import (
    _serialize_annotation,
    _resolve_display_name,
    reply_to_feedback,
    get_annotation_thread,
    list_document_feedback,
    export_feedback,
    AnnotationReplyCreate,
)

TEST_DB_URL = "sqlite+aiosqlite:///./test_identity_thread_part8.db"


class _UUIDStr(str):
    """Behaves like a str (sliceable, for `doc_id[:8]` filename truncation) while
    still satisfying SQLAlchemy's sqlite UUID bind processor, which calls
    `.hex` on the bound value. Needed only because these router functions are
    invoked directly (bypassing FastAPI's str path-param coercion + the
    Postgres-native UUID column the routes assume in production)."""

    def __new__(cls, u):
        return str.__new__(cls, str(u))

    def __init__(self, u):
        self._uuid = u if isinstance(u, uuid.UUID) else uuid.UUID(str(u))

    @property
    def hex(self):
        return self._uuid.hex


def _make_starlette_request(headers=None):
    from starlette.requests import Request as StarletteRequest

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()],
    }
    return StarletteRequest(scope)


@pytest.fixture
async def setup():
    session_cache._data.clear()
    engine = create_async_engine(TEST_DB_URL, echo=False, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        owner_id = uuid.uuid4()
        doc = Document(
            id=uuid.uuid4(), filename="report.pdf", storage_key="originals/report.pdf",
            status="ready", page_count=5, file_size_bytes=2048, user_id=owner_id,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        svc = LinkService()
        link = await svc.create_link(db=session, document_id=str(doc.id), permissions={"can_annotate": True})
        result = await svc.validate_link(session, token=link.token, viewer_email="jane.smith@example.com")
        sess_row = await session.get(ViewerSession, result.session_id)

        comment = ViewerAnnotation(
            link_id=link.id,
            session_id=result.session_id,
            viewer_email_masked=sess_row.viewer_email_masked,
            viewer_email=sess_row.viewer_email,
            viewer_profile_id=sess_row.viewer_profile_id,
            page_number=2,
            annotation_type="comment",
            coords="{}",
            comment_text="Please clarify this clause",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(comment)
        await session.commit()
        await session.refresh(comment)

        yield {
            "db": session, "doc": doc, "owner_id": owner_id, "link": link,
            "session_id": result.session_id, "comment": comment,
        }
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ─── Feedback serialization ────────────────────────────────────────────────

class TestFeedbackSerialization:

    @pytest.mark.asyncio
    async def test_full_identity_exposes_email_and_profile_id(self, setup):
        c = setup["comment"]
        d = _serialize_annotation(c, profile_display_name="Jane Smith", full_identity=True)
        assert d["viewer_email"] == "jane.smith@example.com"
        assert d["viewer_profile_id"] == str(c.viewer_profile_id)
        assert d["display_name"] == "Jane Smith"
        assert d["author_role"] == "viewer"

    @pytest.mark.asyncio
    async def test_public_endpoint_never_exposes_plaintext_identity(self, setup):
        c = setup["comment"]
        d = _serialize_annotation(c, profile_display_name="Jane Smith")  # full_identity defaults False
        assert "viewer_email" not in d
        assert "viewer_profile_id" not in d
        assert d["display_name"] == "Jane Smith"  # display_name still shown to viewers

    def test_anonymous_viewer_fallback_when_no_email(self):
        assert _resolve_display_name(session_id="sess_abc123", viewer_email=None) == "Anonymous Viewer"

    def test_no_hashed_session_id_used_as_name(self, setup):
        c = setup["comment"]
        d = _serialize_annotation(c, profile_display_name="Jane Smith", full_identity=True)
        assert d["display_name"] != c.session_id
        assert "…" not in d["display_name"]


# ─── Uploader reply creation (JWT-only) ────────────────────────────────────

class TestUploaderReplyCreation:

    @pytest.mark.asyncio
    async def test_uploader_reply_persists_with_parent_and_role(self, setup):
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "Owner@Acme.com"}
        body = AnnotationReplyCreate(comment_text="Thanks, fixed in v2")
        request = _make_starlette_request()

        result = await reply_to_feedback(
            request=request, doc_id=doc.id, annotation_id=comment.id,
            body=body, db=db, current_user=current_user,
        )

        assert result["parent_id"] == str(comment.id)
        assert result["author_role"] == "uploader"
        assert result["viewer_email"] == "owner@acme.com"
        assert result["comment_text"] == "Thanks, fixed in v2"

        row = await db.get(ViewerAnnotation, uuid.UUID(result["id"]))
        assert row.session_id.startswith("uploader:")
        assert row.session_id == f"uploader:{setup['owner_id']}"

    @pytest.mark.asyncio
    async def test_uploader_reply_normalizes_to_thread_root(self, setup):
        """Replying to a reply must still attach to the original root, not nest."""
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        first = await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
            body=AnnotationReplyCreate(comment_text="first reply"), db=db, current_user=current_user,
        )
        second = await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=uuid.UUID(first["id"]),
            body=AnnotationReplyCreate(comment_text="reply to a reply"), db=db, current_user=current_user,
        )
        assert second["parent_id"] == str(comment.id)

    @pytest.mark.asyncio
    async def test_uploader_reply_rejects_non_owner(self, setup):
        from fastapi import HTTPException
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(uuid.uuid4()), "email": "intruder@evil.com"}
        with pytest.raises(HTTPException) as exc:
            await reply_to_feedback(
                request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
                body=AnnotationReplyCreate(comment_text="hi"), db=db, current_user=current_user,
            )
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_uploader_reply_succeeds_with_expired_viewer_session(self, setup):
        """PART 3 regression: uploader replies must not depend on viewer session state."""
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]

        # Expire the viewer's session (both cache and DB) — simulate a stale/expired session.
        session_cache.invalidate(setup["session_id"])
        sess_row = await db.get(ViewerSession, setup["session_id"])
        sess_row.last_seen_at = datetime.now(timezone.utc) - timedelta(days=2)
        await db.commit()

        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        result = await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
            body=AnnotationReplyCreate(comment_text="Reply despite expired viewer session"),
            db=db, current_user=current_user,
        )
        assert result["comment_text"] == "Reply despite expired viewer session"
        assert result["author_role"] == "uploader"


# ─── Viewer thread retrieval ────────────────────────────────────────────────

class TestViewerThreadRetrieval:

    @pytest.mark.asyncio
    async def test_thread_returns_root_and_replies_in_order(self, setup):
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
            body=AnnotationReplyCreate(comment_text="Uploader reply #1"), db=db, current_user=current_user,
        )

        result = await get_annotation_thread(
            request=_make_starlette_request({"X-Session-ID": setup["session_id"]}),
            token=setup["link"].token, annotation_id=comment.id, db=db,
        )

        assert result["root"]["id"] == str(comment.id)
        assert result["root"]["comment_text"] == "Please clarify this clause"
        assert len(result["replies"]) == 1
        assert result["replies"][0]["comment_text"] == "Uploader reply #1"
        assert result["replies"][0]["author_role"] == "uploader"
        # public viewer-facing thread endpoint must never leak plaintext identity
        assert "viewer_email" not in result["root"]
        assert "viewer_email" not in result["replies"][0]

    @pytest.mark.asyncio
    async def test_thread_visible_with_no_dashboard_auth(self, setup):
        """Viewer-facing endpoint requires only the share-link session — no JWT."""
        db, comment = setup["db"], setup["comment"]
        result = await get_annotation_thread(
            request=_make_starlette_request({"X-Session-ID": setup["session_id"]}),
            token=setup["link"].token, annotation_id=comment.id, db=db,
        )
        assert result["root"]["id"] == str(comment.id)
        assert result["replies"] == []


# ─── Reply count aggregation ────────────────────────────────────────────────

class TestReplyCountAggregation:

    @pytest.mark.asyncio
    async def test_reply_count_reflects_actual_thread_size(self, setup):
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        for i in range(3):
            await reply_to_feedback(
                request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
                body=AnnotationReplyCreate(comment_text=f"reply {i}"), db=db, current_user=current_user,
            )

        result = await list_document_feedback(
            request=_make_starlette_request(), doc_id=doc.id,
            db=db, current_user=current_user,
        )
        top = next(f for f in result["feedback"] if f["id"] == str(comment.id))
        assert top["reply_count"] == 3
        assert len(top["replies"]) == 3

    @pytest.mark.asyncio
    async def test_zero_replies_reports_zero(self, setup):
        doc, comment = setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        result = await list_document_feedback(
            request=_make_starlette_request(), doc_id=doc.id,
            db=setup["db"], current_user=current_user,
        )
        top = next(f for f in result["feedback"] if f["id"] == str(comment.id))
        assert top["reply_count"] == 0


# ─── CSV export contents ────────────────────────────────────────────────────

class TestCsvExportContents:

    @pytest.mark.asyncio
    async def test_feedback_csv_rows_contain_real_identity_and_reply_count(self, setup):
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
            body=AnnotationReplyCreate(comment_text="uploader reply"), db=db, current_user=current_user,
        )

        response = await export_feedback(
            request=_make_starlette_request(), doc_id=_UUIDStr(doc.id), db=db, current_user=current_user,
        )
        content = b""
        async for chunk in response.body_iterator:
            content += chunk.encode() if isinstance(chunk, str) else chunk
        lines = content.decode().splitlines()
        assert lines[0] == "Reviewer Name,Reviewer Email,Document,Page,Comment,Replies,Status,Created At"

        data_rows = [l for l in lines[1:] if l.strip()]
        assert len(data_rows) == 1  # one row per thread root, replies not flattened
        row = data_rows[0]
        assert "jane.smith@example.com" in row
        assert "report.pdf" in row
        assert "Please clarify this clause" in row
        assert ",1," in row  # reply count of 1 in the Replies column
        assert "Open" in row
        # no hashed/raw session ids anywhere in the export
        assert comment.session_id not in row
