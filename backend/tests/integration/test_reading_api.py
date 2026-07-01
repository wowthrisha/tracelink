"""Integration tests for the Reading Intelligence Engine API endpoints.

Tests cover:
  - POST /api/reading/batch (validation, auth, ingest)
  - GET  /api/reading/session/{session_id}
  - GET  /api/reading/document/{document_id}/summary
  - GET  /api/reading/document/{document_id}/heatmap
  - GET  /api/reading/document/{document_id}/insights
  - GET  /api/reading/document/{document_id}/viewers

Edge cases:
  - Tab switching, session resume, multi-session, invalid tokens
  - Oversized payloads, page-number out of range, active_time never decreases
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.reading_analytics import PageReadingEvent, ReadingSession
from tests.conftest import TEST_USER_ID


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_page_data(pages=(1,), active_ms=45_000, status="completed"):
    return [
        {
            "page_number": p,
            "active_time_ms": active_ms,
            "pause_duration_ms": 5_000,
            "revisit_count": 0,
            "scroll_percentage": 100.0,
            "zoom_level": 100,
            "fullscreen_used": False,
            "annotations_created": 0,
            "copy_attempts": 0,
            "print_attempts": 0,
            "tab_switch_count": 0,
            "visibility_changes": 0,
            "idle_events": 0,
            "completion_status": status,
        }
        for p in pages
    ]


def _session_meta(elapsed=60_000, active=45_000, page_count=5, current_page=1):
    return {
        "total_elapsed_ms": elapsed,
        "total_active_ms": active,
        "started_at": "2026-07-01T10:00:00Z",
        "page_count": page_count,
        "current_page": current_page,
        "initial_estimate_ms": 375_000,
    }


async def _batch(client, token, session_id, page_data=None, meta=None):
    return await client.post("/api/reading/batch", json={
        "token": token,
        "session_id": session_id,
        "page_data": page_data or _make_page_data(),
        "session_meta": meta or _session_meta(),
    })


# ── Batch validation tests (no auth needed — viewer endpoint) ─────────────────

@pytest.mark.asyncio
async def test_batch_missing_token(client):
    resp = await client.post("/api/reading/batch", json={"session_id": "abc123"})
    assert resp.status_code == 400
    assert "token" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_batch_missing_session_id(client):
    resp = await client.post("/api/reading/batch", json={"token": "abc"})
    assert resp.status_code == 400
    assert "session_id" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_batch_page_data_not_a_list(client):
    resp = await client.post("/api/reading/batch", json={
        "token": "abc",
        "session_id": "sess123",
        "page_data": "should_be_list",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_batch_page_data_too_large(client):
    resp = await client.post("/api/reading/batch", json={
        "token": "abc",
        "session_id": "sess123",
        "page_data": [{"page_number": i} for i in range(1, 502)],
    })
    assert resp.status_code == 400
    assert "500" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_batch_negative_elapsed_ms(client):
    resp = await client.post("/api/reading/batch", json={
        "token": "abc",
        "session_id": "sess123",
        "page_data": [],
        "session_meta": {"total_elapsed_ms": -1000},
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_batch_invalid_link_token(client):
    with patch("app.routers.reading.enforcer") as mock_enforcer:
        mock_enforcer.is_active_session = AsyncMock(return_value=False)
        resp = await client.post("/api/reading/batch", json={
            "token": "nonexistent-token-xyz",
            "session_id": "sess1234567890abcd",
            "page_data": [],
            "session_meta": {},
        })
    # Non-existent token → 404 before session check
    assert resp.status_code == 404


# ── Viewer session endpoint ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_viewer_session_missing_token(client):
    resp = await client.get("/api/reading/session/sess123")
    assert resp.status_code == 422  # required query param missing


@pytest.mark.asyncio
async def test_viewer_session_invalid_link(client):
    resp = await client.get("/api/reading/session/sess123?token=badtoken")
    assert resp.status_code == 404


# ── Document endpoints require auth ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_document_endpoints_require_auth():
    """Verify all document endpoints return 401 without auth."""
    from httpx import AsyncClient, ASGITransport
    from app.main import app
    doc_id = str(uuid.uuid4())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        for endpoint in ["summary", "heatmap", "insights", "viewers"]:
            resp = await c.get(f"/api/reading/document/{doc_id}/{endpoint}")
            assert resp.status_code == 401, f"{endpoint} should require auth"


@pytest.mark.asyncio
async def test_document_summary_invalid_uuid(client):
    resp = await client.get("/api/reading/document/not-a-uuid/summary")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_document_heatmap_invalid_uuid(client):
    resp = await client.get("/api/reading/document/not-a-uuid/heatmap")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_document_insights_invalid_uuid(client):
    resp = await client.get("/api/reading/document/not-a-uuid/insights")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_document_viewers_invalid_uuid(client):
    resp = await client.get("/api/reading/document/not-a-uuid/viewers")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_document_summary_not_found(client):
    resp = await client.get(f"/api/reading/document/{uuid.uuid4()}/summary")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_document_heatmap_not_found(client):
    resp = await client.get(f"/api/reading/document/{uuid.uuid4()}/heatmap")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_document_insights_not_found(client):
    resp = await client.get(f"/api/reading/document/{uuid.uuid4()}/insights")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_document_viewers_not_found(client):
    resp = await client.get(f"/api/reading/document/{uuid.uuid4()}/viewers")
    assert resp.status_code == 404


# ── Full flow: ingest + query ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_batch_ingest_and_viewer_session(client, db_session, sample_link):
    """Ingest a batch then query viewer session summary."""
    session_id = "readsess12345678901"[:32]
    link = sample_link

    with patch("app.routers.reading.enforcer") as mock_enforcer:
        mock_enforcer.is_active_session = AsyncMock(return_value=True)

        resp = await client.post("/api/reading/batch", json={
            "token": link.token,
            "session_id": session_id,
            "page_data": _make_page_data(pages=range(1, 6)),
            "session_meta": _session_meta(
                elapsed=300_000, active=225_000, page_count=5, current_page=5
            ),
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "total_active_ms" in data
    assert data["total_active_ms"] >= 0
    assert "completion_pct" in data
    assert "pages_completed" in data
    # sample_link document has 3 pages; pages 4-5 are dropped by page_count validation
    assert data["pages_completed"] >= 3

    # Query viewer session
    with patch("app.routers.reading.enforcer") as mock_enforcer:
        mock_enforcer.is_active_session = AsyncMock(return_value=True)
        resp2 = await client.get(
            f"/api/reading/session/{session_id}",
            params={"token": link.token},
        )

    assert resp2.status_code == 200
    session_data = resp2.json()
    assert "total_active_ms" in session_data
    assert "estimated_remaining_ms" in session_data
    assert "completion_pct" in session_data
    assert session_data["total_active_ms"] >= 0


@pytest.mark.asyncio
async def test_viewer_session_returns_zeros_with_no_data(client, sample_link):
    """Session endpoint returns zeros when no batch has been ingested yet."""
    session_id = "nosess12345678901234"[:32]

    with patch("app.routers.reading.enforcer") as mock_enforcer:
        mock_enforcer.is_active_session = AsyncMock(return_value=True)
        resp = await client.get(
            f"/api/reading/session/{session_id}",
            params={"token": sample_link.token},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["total_active_ms"] == 0
    assert data["completion_pct"] == 0.0


@pytest.mark.asyncio
async def test_batch_page_out_of_range_ignored(client, db_session, sample_link, sample_document):
    """Pages > document.page_count should be silently dropped."""
    session_id = "rangetest1234567890"[:32]
    link = sample_link

    with patch("app.routers.reading.enforcer") as mock_enforcer:
        mock_enforcer.is_active_session = AsyncMock(return_value=True)
        resp = await client.post("/api/reading/batch", json={
            "token": link.token,
            "session_id": session_id,
            "page_data": [
                {"page_number": 9999, "active_time_ms": 60_000, "completion_status": "completed"},
                {"page_number": 1, "active_time_ms": 60_000, "completion_status": "completed"},
            ],
            "session_meta": _session_meta(),
        })

    assert resp.status_code == 200
    data = resp.json()
    # page 9999 dropped, only page 1 accepted
    assert data["pages_completed"] == 1


@pytest.mark.asyncio
async def test_active_time_never_decreases(client, db_session, sample_link):
    """Second batch with lower active_time keeps the max from first batch."""
    session_id = "noregress12345678901"[:32]
    link = sample_link

    with patch("app.routers.reading.enforcer") as mock_enforcer:
        mock_enforcer.is_active_session = AsyncMock(return_value=True)

        # First batch: 45s
        await client.post("/api/reading/batch", json={
            "token": link.token,
            "session_id": session_id,
            "page_data": [{"page_number": 1, "active_time_ms": 45_000, "completion_status": "reading"}],
            "session_meta": _session_meta(active=45_000),
        })

        # Second batch: only 10s (frontend timer reset)
        r2 = await client.post("/api/reading/batch", json={
            "token": link.token,
            "session_id": session_id,
            "page_data": [{"page_number": 1, "active_time_ms": 10_000, "completion_status": "reading"}],
            "session_meta": _session_meta(active=10_000),
        })

    assert r2.status_code == 200
    rs_result = await db_session.execute(
        select(ReadingSession).where(ReadingSession.session_id == session_id)
    )
    rs = rs_result.scalar_one_or_none()
    assert rs is not None
    assert rs.total_active_ms >= 45_000, "active_time should never decrease"


@pytest.mark.asyncio
async def test_tab_switch_tracked(client, db_session, sample_link):
    """Tab switches accumulate in session."""
    session_id = "tabtest12345678901234"[:32]

    with patch("app.routers.reading.enforcer") as mock_enforcer:
        mock_enforcer.is_active_session = AsyncMock(return_value=True)
        resp = await client.post("/api/reading/batch", json={
            "token": sample_link.token,
            "session_id": session_id,
            "page_data": [{
                "page_number": 1, "active_time_ms": 30_000,
                "tab_switch_count": 5, "visibility_changes": 10,
                "completion_status": "completed",
            }],
            "session_meta": _session_meta(),
        })

    assert resp.status_code == 200
    rs_result = await db_session.execute(
        select(ReadingSession).where(ReadingSession.session_id == session_id)
    )
    rs = rs_result.scalar_one_or_none()
    assert rs is not None
    assert rs.tab_switch_count == 5


@pytest.mark.asyncio
async def test_multi_session_document_summary(client, db_session, sample_document_in_db, sample_link):
    """Uploader sees all sessions aggregated in summary."""
    doc = sample_document_in_db
    for i in range(3):
        sess = f"multisess{i:022d}"[:32]
        with patch("app.routers.reading.enforcer") as mock_enforcer:
            mock_enforcer.is_active_session = AsyncMock(return_value=True)
            resp = await client.post("/api/reading/batch", json={
                "token": sample_link.token,
                "session_id": sess,
                "page_data": _make_page_data(pages=range(1, 4)),  # 3 pages
                "session_meta": _session_meta(elapsed=180_000, active=135_000,
                                               page_count=3, current_page=3),
            })
            assert resp.status_code == 200

    resp = await client.get(f"/api/reading/document/{doc.id}/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_sessions"] == 3
    assert data["completion_rate_pct"] == 100.0
    assert "avg_engagement_score" in data
    assert "complexity" in data


@pytest.mark.asyncio
async def test_heatmap_response_structure(client, db_session, sample_document_in_db, sample_link):
    """Heatmap response includes all required per-page fields."""
    doc = sample_document_in_db
    session_id = "heatmaptest12345678"[:32]

    with patch("app.routers.reading.enforcer") as mock_enforcer:
        mock_enforcer.is_active_session = AsyncMock(return_value=True)
        await client.post("/api/reading/batch", json={
            "token": sample_link.token,
            "session_id": session_id,
            "page_data": _make_page_data(pages=range(1, 4)),  # 3 pages
            "session_meta": _session_meta(page_count=3, current_page=3),
        })

    resp = await client.get(f"/api/reading/document/{doc.id}/heatmap")
    assert resp.status_code == 200
    data = resp.json()
    assert "pages" in data
    assert len(data["pages"]) == doc.page_count

    page = data["pages"][0]
    for field in ["page", "views", "avg_time_ms", "median_time_ms", "revisit_pct",
                  "completion_pct", "predicted_difficulty", "engagement_score", "dropoff_pct"]:
        assert field in page, f"Missing heatmap field: {field}"


@pytest.mark.asyncio
async def test_viewers_response_structure(client, db_session, sample_document_in_db, sample_link):
    """Viewers endpoint returns all required per-viewer fields."""
    doc = sample_document_in_db
    session_id = "viewertest12345678901"[:32]

    with patch("app.routers.reading.enforcer") as mock_enforcer:
        mock_enforcer.is_active_session = AsyncMock(return_value=True)
        await client.post("/api/reading/batch", json={
            "token": sample_link.token,
            "session_id": session_id,
            "page_data": _make_page_data(pages=[1]),
            "session_meta": _session_meta(),
        })

    resp = await client.get(f"/api/reading/document/{doc.id}/viewers")
    assert resp.status_code == 200
    data = resp.json()
    assert "viewers" in data
    assert "total_viewers" in data
    assert data["total_viewers"] >= 1

    viewer = data["viewers"][0]
    for field in ["session_id", "completion_pct", "total_active_ms",
                  "pages_visited", "engagement_score"]:
        assert field in viewer, f"Missing viewer field: {field}"


@pytest.mark.asyncio
async def test_insights_response_structure(client, sample_document):
    """Insights endpoint returns valid structure (may be empty with little data)."""
    resp = await client.get(f"/api/reading/document/{sample_document.id}/insights")
    assert resp.status_code == 200
    data = resp.json()
    assert "insights" in data
    assert "total_sessions" in data
    assert "generated_at" in data
    assert isinstance(data["insights"], list)


@pytest.mark.asyncio
async def test_batch_completion_status_only_upgrades(client, db_session, sample_link):
    """Completion status can only be upgraded, never downgraded."""
    session_id = "statustest12345678901"[:32]

    with patch("app.routers.reading.enforcer") as mock_enforcer:
        mock_enforcer.is_active_session = AsyncMock(return_value=True)

        # First: completed
        await client.post("/api/reading/batch", json={
            "token": sample_link.token,
            "session_id": session_id,
            "page_data": [{"page_number": 1, "active_time_ms": 60_000, "completion_status": "completed"}],
            "session_meta": _session_meta(),
        })

        # Second: try to downgrade to "started"
        await client.post("/api/reading/batch", json={
            "token": sample_link.token,
            "session_id": session_id,
            "page_data": [{"page_number": 1, "active_time_ms": 10_000, "completion_status": "started"}],
            "session_meta": _session_meta(),
        })

    pre_result = await db_session.execute(
        select(PageReadingEvent).where(
            PageReadingEvent.session_id == session_id,
            PageReadingEvent.page_number == 1,
        )
    )
    pre = pre_result.scalar_one_or_none()
    assert pre is not None
    # Should remain "completed", not be downgraded to "started"
    assert pre.completion_status == "completed"
