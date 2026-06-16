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
    export_reviewer_activity,
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

    @pytest.mark.asyncio
    async def test_thread_response_shape_sample(self, setup):
        """Documents the exact JSON shape the frontend timeline renders from."""
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
            body=AnnotationReplyCreate(comment_text="Thanks, fixed in v2"), db=db, current_user=current_user,
        )
        result = await get_annotation_thread(
            request=_make_starlette_request({"X-Session-ID": setup["session_id"]}),
            token=setup["link"].token, annotation_id=comment.id, db=db,
        )
        for key in ("id", "page_number", "annotation_type", "comment_text", "resolved_at",
                    "parent_id", "display_name", "author_role", "created_at", "updated_at"):
            assert key in result["root"]
            assert key in result["replies"][0]
        assert result["root"]["author_role"] == "viewer"
        assert result["root"]["parent_id"] is None
        assert result["replies"][0]["author_role"] == "uploader"
        assert result["replies"][0]["parent_id"] == str(comment.id)
        assert result["root"]["resolved_at"] is None  # Open until resolved

    @pytest.mark.asyncio
    async def test_viewer_reply_is_visible_in_thread(self, setup):
        """A viewer-authored reply (not just uploader) must show up with author_role 'viewer'."""
        db, comment = setup["db"], setup["comment"]
        viewer_reply = ViewerAnnotation(
            link_id=comment.link_id,
            session_id=setup["session_id"],
            viewer_email_masked=comment.viewer_email_masked,
            viewer_email=comment.viewer_email,
            viewer_profile_id=comment.viewer_profile_id,
            page_number=comment.page_number,
            annotation_type="comment",
            coords="{}",
            comment_text="Looks good now",
            parent_id=str(comment.id),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(viewer_reply)
        await db.commit()

        result = await get_annotation_thread(
            request=_make_starlette_request({"X-Session-ID": setup["session_id"]}),
            token=setup["link"].token, annotation_id=comment.id, db=db,
        )
        assert len(result["replies"]) == 1
        assert result["replies"][0]["author_role"] == "viewer"
        assert result["replies"][0]["comment_text"] == "Looks good now"

    @pytest.mark.asyncio
    async def test_replies_ordered_oldest_first(self, setup):
        """Conversation must read chronologically — oldest message first."""
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}

        first = await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
            body=AnnotationReplyCreate(comment_text="first"), db=db, current_user=current_user,
        )
        row = await db.get(ViewerAnnotation, uuid.UUID(first["id"]))
        row.created_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        await db.commit()

        await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
            body=AnnotationReplyCreate(comment_text="second"), db=db, current_user=current_user,
        )

        result = await get_annotation_thread(
            request=_make_starlette_request({"X-Session-ID": setup["session_id"]}),
            token=setup["link"].token, annotation_id=comment.id, db=db,
        )
        texts = [r["comment_text"] for r in result["replies"]]
        assert texts == ["first", "second"]


class TestEmptyStateLogic:
    """Frontend shows 'No replies yet' iff the combined timeline (root + replies) has exactly one message."""

    @pytest.mark.asyncio
    async def test_no_replies_means_single_message_timeline(self, setup):
        result = await get_annotation_thread(
            request=_make_starlette_request({"X-Session-ID": setup["session_id"]}),
            token=setup["link"].token, annotation_id=setup["comment"].id, db=setup["db"],
        )
        timeline_len = 1 + len(result["replies"])  # root + replies
        assert timeline_len == 1

    @pytest.mark.asyncio
    async def test_any_reply_means_timeline_longer_than_one(self, setup):
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
            body=AnnotationReplyCreate(comment_text="Thanks."), db=db, current_user=current_user,
        )
        result = await get_annotation_thread(
            request=_make_starlette_request({"X-Session-ID": setup["session_id"]}),
            token=setup["link"].token, annotation_id=comment.id, db=db,
        )
        timeline_len = 1 + len(result["replies"])
        assert timeline_len > 1


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
        assert lines[0] == (
            "Document,Page,Reviewer,Reviewer Email,Conversation,"
            "Status,First Comment,Last Activity"
        )

        body = "\n".join(lines[1:])
        # one row per THREAD — root and reply are flattened into one Conversation cell
        assert "Please clarify this clause" in body
        assert "uploader reply" in body
        assert "[Viewer]" in body
        assert "[Uploader]" in body
        assert "jane.smith@example.com" in body
        assert "report.pdf" in body
        assert "Open" in body

        # no internal IDs (document/thread/comment/parent) anywhere in the export
        assert str(comment.id) not in body
        assert str(doc.id) not in body
        # no hashed/raw session ids anywhere in the export
        assert comment.session_id not in body


# ─── Thread filtering (date range / page number / author role / search) ────

async def _csv_lines(response):
    content = b""
    async for chunk in response.body_iterator:
        content += chunk.encode() if isinstance(chunk, str) else chunk
    return content.decode().splitlines()


class TestThreadFiltering:

    @pytest.mark.asyncio
    async def test_page_number_filter_on_dashboard(self, setup):
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        other = ViewerAnnotation(
            link_id=comment.link_id, session_id=setup["session_id"],
            viewer_email_masked=comment.viewer_email_masked, viewer_email=comment.viewer_email,
            viewer_profile_id=comment.viewer_profile_id, page_number=5, annotation_type="comment",
            coords="{}", comment_text="On page five", created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(other)
        await db.commit()

        result = await list_document_feedback(
            request=_make_starlette_request(), doc_id=doc.id, page_number=2,
            db=db, current_user=current_user,
        )
        ids = {f["id"] for f in result["feedback"]}
        assert str(comment.id) in ids
        assert str(other.id) not in ids

        result5 = await list_document_feedback(
            request=_make_starlette_request(), doc_id=doc.id, page_number=5,
            db=db, current_user=current_user,
        )
        ids5 = {f["id"] for f in result5["feedback"]}
        assert str(other.id) in ids5
        assert str(comment.id) not in ids5

    @pytest.mark.asyncio
    async def test_date_range_filter_on_dashboard(self, setup):
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        far_future = (datetime.now(timezone.utc) + timedelta(days=365)).date().isoformat()

        future_only = await list_document_feedback(
            request=_make_starlette_request(), doc_id=doc.id, date_from=far_future,
            db=db, current_user=current_user,
        )
        assert all(f["id"] != str(comment.id) for f in future_only["feedback"])

        far_past = (datetime.now(timezone.utc) - timedelta(days=365)).date().isoformat()
        past_to_now = await list_document_feedback(
            request=_make_starlette_request(), doc_id=doc.id, date_from=far_past,
            db=db, current_user=current_user,
        )
        assert any(f["id"] == str(comment.id) for f in past_to_now["feedback"])

    @pytest.mark.asyncio
    async def test_author_role_filter_matches_any_message_in_thread(self, setup):
        """A thread with a viewer root + uploader reply must surface for BOTH
        author_role=viewer and author_role=uploader — filtering looks at every
        message in the thread, not only the root."""
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
            body=AnnotationReplyCreate(comment_text="uploader side"), db=db, current_user=current_user,
        )

        as_viewer = await list_document_feedback(
            request=_make_starlette_request(), doc_id=doc.id, author_role="viewer",
            db=db, current_user=current_user,
        )
        assert any(f["id"] == str(comment.id) for f in as_viewer["feedback"])

        as_uploader = await list_document_feedback(
            request=_make_starlette_request(), doc_id=doc.id, author_role="uploader",
            db=db, current_user=current_user,
        )
        assert any(f["id"] == str(comment.id) for f in as_uploader["feedback"])

    @pytest.mark.asyncio
    async def test_author_role_filter_excludes_thread_with_no_matching_message(self, setup):
        db, doc = setup["db"], setup["doc"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        # A thread whose root AND only message is uploader-authored, no viewer message at all.
        uploader_only = ViewerAnnotation(
            link_id=setup["comment"].link_id, session_id=f"uploader:{setup['owner_id']}",
            viewer_email_masked=None, viewer_email="owner@acme.com", viewer_profile_id=None,
            page_number=1, annotation_type="comment", coords="{}", comment_text="Uploader started this",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        )
        db.add(uploader_only)
        await db.commit()

        as_viewer = await list_document_feedback(
            request=_make_starlette_request(), doc_id=doc.id, author_role="viewer",
            db=db, current_user=current_user,
        )
        assert all(f["id"] != str(uploader_only.id) for f in as_viewer["feedback"])

    @pytest.mark.asyncio
    async def test_search_matches_reply_text_not_just_root(self, setup):
        """Searching for text that only appears in a reply must still surface
        the thread (the whole thread, including the non-matching root)."""
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
            body=AnnotationReplyCreate(comment_text="I will fix the typo"), db=db, current_user=current_user,
        )

        result = await list_document_feedback(
            request=_make_starlette_request(), doc_id=doc.id, search="typo",
            db=db, current_user=current_user,
        )
        top = next((f for f in result["feedback"] if f["id"] == str(comment.id)), None)
        assert top is not None
        assert "Please clarify this clause" not in str(comment.id)  # sanity: root text itself has no "typo"
        assert top["comment_text"] == "Please clarify this clause"

        no_match = await list_document_feedback(
            request=_make_starlette_request(), doc_id=doc.id, search="nonexistentword",
            db=db, current_user=current_user,
        )
        assert all(f["id"] != str(comment.id) for f in no_match["feedback"])

    @pytest.mark.asyncio
    async def test_export_page_filter_includes_whole_matching_thread_only(self, setup):
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
            body=AnnotationReplyCreate(comment_text="uploader reply"), db=db, current_user=current_user,
        )
        other = ViewerAnnotation(
            link_id=comment.link_id, session_id=setup["session_id"],
            viewer_email_masked=comment.viewer_email_masked, viewer_email=comment.viewer_email,
            viewer_profile_id=comment.viewer_profile_id, page_number=9, annotation_type="comment",
            coords="{}", comment_text="Different page thread", created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(other)
        await db.commit()

        response = await export_feedback(
            request=_make_starlette_request(), doc_id=_UUIDStr(doc.id), page_number=2,
            db=db, current_user=current_user,
        )
        lines = await _csv_lines(response)
        body = "\n".join(lines[1:])
        assert "Please clarify this clause" in body
        assert "uploader reply" in body  # whole thread exported, including the reply
        assert "Different page thread" not in body

    @pytest.mark.asyncio
    async def test_export_author_role_filter_includes_whole_thread(self, setup):
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
            body=AnnotationReplyCreate(comment_text="uploader reply"), db=db, current_user=current_user,
        )

        response = await export_feedback(
            request=_make_starlette_request(), doc_id=_UUIDStr(doc.id), author_role="uploader",
            db=db, current_user=current_user,
        )
        lines = await _csv_lines(response)
        body = "\n".join(lines[1:])
        # whole thread exported (root included) even though the filter matched only the reply
        assert "Please clarify this clause" in body
        assert "uploader reply" in body


# ─── Reviewer activity export ───────────────────────────────────────────────

class TestReviewerActivityExport:

    @pytest.mark.asyncio
    async def test_aggregates_comment_and_reply_counts_per_reviewer(self, setup):
        db, doc, comment = setup["db"], setup["doc"], setup["comment"]
        current_user = {"user_id": str(setup["owner_id"]), "email": "owner@acme.com"}
        viewer_reply = ViewerAnnotation(
            link_id=comment.link_id, session_id=setup["session_id"],
            viewer_email_masked=comment.viewer_email_masked, viewer_email=comment.viewer_email,
            viewer_profile_id=comment.viewer_profile_id, page_number=comment.page_number,
            annotation_type="comment", coords="{}", comment_text="Looks good now",
            parent_id=str(comment.id), created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        )
        db.add(viewer_reply)
        await db.commit()
        await reply_to_feedback(
            request=_make_starlette_request(), doc_id=doc.id, annotation_id=comment.id,
            body=AnnotationReplyCreate(comment_text="uploader reply"), db=db, current_user=current_user,
        )

        response = await export_reviewer_activity(
            request=_make_starlette_request(), doc_id=_UUIDStr(doc.id), db=db, current_user=current_user,
        )
        lines = await _csv_lines(response)
        assert lines[0] == "Reviewer Name,Reviewer Email,Document,Comment Count,Reply Count,Last Activity"
        data_rows = [l for l in lines[1:] if l.strip()]
        assert len(data_rows) == 1  # one row for the single reviewer (jane.smith)
        row = data_rows[0]
        assert "jane.smith@example.com" in row
        assert row.split(",")[3] == "1"  # comment_count
        assert row.split(",")[4] == "1"  # reply_count
        # uploader's own reply must never appear as a reviewer row
        assert "owner@acme.com" not in "\n".join(lines)

