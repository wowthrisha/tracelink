# Database Hardening Report — Sprint 5.3 Phase 1

**Date:** 2026-06-23  
**Sprint:** 5.3  
**Phase:** 1 — Database Hardening  
**Status:** COMPLETE

---

## Summary

Phase 1 audited all SQLAlchemy models and Alembic migration history against the query patterns used in analytics and access control to identify missing indexes. Three missing composite and single-column indexes were identified and added via migration 025.

---

## Findings

### PASS — Existing Indexes (Pre-Sprint 5.3)

| Index | Table | Columns | Status |
|-------|-------|---------|--------|
| ix_documents_user_id | documents | user_id | PASS |
| ix_share_links_token | share_links | token | PASS |
| ix_access_events_link_id | access_events | link_id | PASS |
| ix_share_links_document_id | share_links | document_id | PASS |

### FALSE POSITIVE — Sprint 5.2 W-09 DB Pool Size

**Sprint 5.2 Report Claim:** DB pool size not configured.  
**Actual State:** `database.py` already configures `pool_size=settings.db_pool_size` (default 10), `max_overflow=settings.db_max_overflow` (default 20) with `pool_pre_ping=True` and `pool_recycle=1800`. Setting was always present.  
**Resolution:** FALSE POSITIVE — no change required.

### VIOLATION — Missing group_id Index (NEW-01) — FIXED

**Evidence:** `SELECT ... WHERE documents.group_id = ?` in `get_document_analytics()` and `get_group_analytics()` had no supporting index. Full table scan on every analytics request.  
**Fix:** Added `ix_documents_group_id` on `documents(group_id)`.  
**Migration:** `025_performance_indexes.py`

### VIOLATION — Missing composite link status index (NEW-02) — FIXED

**Evidence:** `SELECT ... WHERE share_links.document_id IN (...) AND share_links.revoked_at IS NULL` patterns in analytics had no composite index.  
**Fix:** Added `ix_share_links_doc_revoked` on `share_links(document_id, revoked_at)`.  
**Migration:** `025_performance_indexes.py`

### VIOLATION — Missing composite access event index (NEW-03) — FIXED

**Evidence:** `SELECT ... WHERE access_events.link_id = ? AND access_events.event_type = ?` had no composite index — only single-column `link_id` index existed.  
**Fix:** Added `ix_access_events_link_event` on `access_events(link_id, event_type)`.  
**Migration:** `025_performance_indexes.py`

---

## Changes Made

### backend/alembic/versions/025_performance_indexes.py (CREATED)

```python
def upgrade() -> None:
    op.create_index("ix_access_events_link_event", "access_events", ["link_id", "event_type"])
    op.create_index("ix_share_links_doc_revoked", "share_links", ["document_id", "revoked_at"])
    op.create_index("ix_documents_group_id", "documents", ["group_id"])

def downgrade() -> None:
    op.drop_index("ix_documents_group_id", table_name="documents")
    op.drop_index("ix_share_links_doc_revoked", table_name="share_links")
    op.drop_index("ix_access_events_link_event", table_name="access_events")
```

### Model updates

- `backend/app/models/event.py` — added `Index("ix_access_events_link_event", "link_id", "event_type")`
- `backend/app/models/link.py` — added `Index("ix_share_links_doc_revoked", "document_id", "revoked_at")`
- `backend/app/models/document.py` — added `Index("ix_documents_group_id", "group_id")`

---

## Test Results

All integration tests pass after migration. No test regressions.

---

## Verdict

**PASS** — All known index gaps remediated. Database hardening complete for 100 beta user / 10,000 document scale.
