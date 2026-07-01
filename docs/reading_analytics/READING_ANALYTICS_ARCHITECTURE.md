# Reading Analytics Architecture

## Overview

The Reading Intelligence Engine (RIE) is a production analytics system for SecureDoc that provides DocSend-style reading insights, Kindle-style reading progress, and Microsoft Clarity-style engagement scoring.

It tracks real viewer behavior — active time, page navigation, idle events, tab switches, revisits — and derives meaningful signals without any fabrication or hardcoding.

---

## System Components

```
Viewer Browser
├── useReadingAnalytics.js      Active-time tracker, EWMA speed, batch queue
├── ReadingStatusBar.jsx        Always-visible bottom bar (time, remaining, page)
└── InsightsModal.jsx           Owner analytics: heatmap, viewers, NL insights

Backend FastAPI
├── routers/reading.py          6 REST endpoints (viewer + owner auth)
├── services/reading_analytics_service.py   Score formulas, insights engine
└── models/reading_analytics.py             3 SQLAlchemy models

Database (PostgreSQL)
├── reading_sessions            Aggregate per-viewer session
├── page_reading_events         Per-page detail
└── document_complexity         Per-document complexity cache (WPM baseline)

Alembic Migration
└── 026_reading_analytics.py    Creates all tables, enum, indexes
```

---

## Data Flow

```
[Browser Timer (performance.now)]
    ↓ every 5s (fire-and-forget)
POST /api/reading/batch
    ↓ enforcer.is_active_session() auth
reading_analytics_service.ingest_batch()
    ├── upsert reading_session (aggregate totals)
    ├── upsert page_reading_events (per-page, max() accumulation)
    └── compute_document_complexity() (cached per doc)
```

**Key invariants:**
- `active_time_ms` never decreases (uses `max(existing, new)`)
- `completion_status` only upgrades (`unread → started → reading → completed / revisited`)
- Batch requests are idempotent — safe to retry on network failure

---

## Security Model

| Endpoint | Auth | Notes |
|---|---|---|
| `POST /api/reading/batch` | enforcer.is_active_session(token) | Viewer only |
| `GET /api/reading/session/{id}` | query param token | Viewer owns session |
| `GET /api/reading/document/{id}/summary` | require_scope("analytics:read") | Owner only |
| `GET /api/reading/document/{id}/heatmap` | require_scope("analytics:read") | Owner only |
| `GET /api/reading/document/{id}/insights` | require_scope("analytics:read") | Owner only |
| `GET /api/reading/document/{id}/viewers` | require_scope("analytics:read") | Owner only |

---

## Privacy

No webcam, microphone, or keylogging. Tracked signals:
- Time spent per page (active vs idle)
- Page navigation sequence
- Tab/window visibility changes (browser events)
- Scroll depth (scroll event position)
- Intentional interactions: copy/print attempts, annotations

All data is tied to `session_id` (a 32-char opaque random token), never to PII unless the uploader explicitly collects email via gate auth.

---

## Performance

- Batch writes: rate-limited 30/min, max 500 page_data items per request
- SQLAlchemy async with asyncpg — non-blocking
- Document complexity is computed once and cached in `document_complexity` table
- Insights queries use indexed foreign keys — O(log n) for typical document sizes
- Frontend batch queue: fire-and-forget fetch, never blocks rendering

---

## Scalability

The schema handles millions of events:
- `ix_rs_document_started`: fast lookup of all sessions for a document
- `ix_pre_document_page`: O(1) per-page lookups across sessions
- `ix_pre_reading_session`: cascade delete with FK, reading all pages for a session

At 10,000 sessions per document × 30 pages = 300,000 `page_reading_events` rows — well within PostgreSQL single-table performance bounds with the defined indexes.
