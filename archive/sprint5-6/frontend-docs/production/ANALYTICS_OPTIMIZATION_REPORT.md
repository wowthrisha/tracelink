# Analytics Optimization Report — Sprint 5.3 Phase 3

**Date:** 2026-06-23  
**Sprint:** 5.3  
**Phase:** 3 — Analytics Scalability  
**Status:** COMPLETE

---

## Summary

Phase 3 identified and fixed the Python-side timestamp aggregation in `get_overview()` — the only remaining O(n-events) memory operation in the analytics service. All other aggregations were already SQL-based (GROUP BY in `get_document_analytics()` and `get_group_analytics()`).

---

## Finding — Python-Side Timestamp Loop (FIXED)

### Root Cause

`get_overview()` in `analytics_service.py` computed the 7-day view chart by:
1. Fetching ALL `access_events.created_at` timestamps for the last 7 days matching `event_type = 'opened'`
2. Iterating over every timestamp in Python to build a date → count dict

```python
# Before (VIOLATION):
week_q = select(AccessEvent.created_at).where(
    AccessEvent.event_type == "opened",
    AccessEvent.created_at >= week_start,
)
week_ts_rows = (await db.execute(week_q)).scalars().all()
date_counts: dict = {}
for ts in week_ts_rows:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    date_counts[ts.strftime("%Y-%m-%d")] = date_counts.get(..., 0) + 1
```

At 100,000 events/week, this loads the entire set into Python memory and iterates it.

### Fix

Replaced with a single SQL `GROUP BY DATE(created_at)` query that returns 7 aggregate rows maximum:

```python
# After (PASS):
week_q = (
    select(
        func.date(AccessEvent.created_at).label("day"),
        func.count().label("cnt"),
    )
    .where(
        AccessEvent.event_type == "opened",
        AccessEvent.created_at >= week_start,
    )
    .group_by(func.date(AccessEvent.created_at))
)
if scoped_link_ids:
    week_q = week_q.where(AccessEvent.link_id.in_(scoped_link_ids))
date_counts = {str(row.day): row.cnt for row in (await db.execute(week_q)).all()}
```

**Compatibility note:** `func.date()` returns a string in SQLite (tests) and a `datetime.date` object in PostgreSQL (production). `str()` normalises both to `"YYYY-MM-DD"` format.

---

## Remaining Scalability Notes

### N+1 Queries — PASS

Both `get_document_analytics()` and `get_group_analytics()` use batch queries (6 GROUP BY aggregates per call). No N+1 patterns remain.

### Pagination — PASS (Phase 2)

Both analytics list endpoints are now paginated (limit/offset). See API_HARDENING_REPORT.md.

### Count vs len(doc_ids) — DEFER

`get_overview()` issues a `SELECT COUNT(*) FROM documents WHERE user_id = ?` separately even though `doc_ids` was already fetched above it. Replacing with `len(doc_ids)` would save one query per request. Deferred — the savings are one fast index-only COUNT per overview load, acceptable at beta scale.

---

## Test Results

- 20 analytics tests: all pass after the GROUP BY DATE change
- Verified SQLite (test DB) and SQLAlchemy both handle `func.date()` correctly

---

## Verdict

**PASS** — Analytics service no longer has O(n-events) memory operations. Production-safe at 100,000 event scale.
