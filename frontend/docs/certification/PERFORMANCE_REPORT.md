# PERFORMANCE REPORT — Sprint 5.5 Engineering Investigation
**Date:** 2026-06-29  
**Sprint:** 5.5 Phase 2  
**Method:** Source code review of all backend routers and services for query patterns

---

## Summary

| Issue | Severity | Status |
|-------|----------|--------|
| N+1 query in list_orgs | MEDIUM | FIXED (FIX-002) |
| In-memory count in get_audit_log | LOW | FIXED (FIX-003) |
| No client-side caching | LOW | DOCUMENTED (by design) |
| Single bundle, no code splitting | LOW | DOCUMENTED (248 KB, acceptable) |

---

## Fixed Issues

### PERF-FIXED-001 — N+1 query in list_orgs

**File:** `backend/app/routers/orgs.py`  
**Before:** For N orgs: 1 JOIN query + N separate `SELECT COUNT(*)` queries = N+1 total  
**After:** 1 JOIN query + 1 `SELECT org_id, COUNT(id) GROUP BY org_id` query = 2 total  
**Impact:** Linear improvement proportional to number of orgs the user belongs to  
**Commit:** `3290a00`

### PERF-FIXED-002 — In-memory count in get_audit_log

**File:** `backend/app/routers/admin.py`  
**Before:** `len(count_result.all())` — fetched all matching IDs into Python memory  
**After:** `select(func.count()).select_from(query.subquery())` — single SQL COUNT scalar  
**Impact:** For large audit logs (thousands of events), this was loading all UUIDs into Python memory unnecessarily. Now uses a single scalar query.  
**Commit:** `3290a00`

---

## Existing Good Query Patterns

### list_documents — Batched queries (no N+1)
`backend/app/routers/documents.py:400-429`

Gets link counts, view counts, and group info for all documents in 3 separate batched queries:
1. `SELECT document_id, COUNT(share_link_id) GROUP BY document_id`
2. `SELECT document_id, COUNT(event_id) JOIN access_events ON type='opened' GROUP BY document_id`
3. `SELECT DocumentGroup WHERE id IN (group_ids set)`

No N+1 pattern.

### list_groups — Batched query
`backend/app/routers/groups.py:41-48`

Gets document counts per group in a single `GROUP BY` query. Already optimized.

### analytics overview — 4 scalar queries
`backend/app/services/analytics_service.py`

4 `SELECT COUNT()` queries for: total_views_today, active_links, blocked_attempts_today, expiring_soon. Each is a targeted indexed query against specific event_type + timestamp combinations.

---

## Performance Indexes Verified

Migration `025_performance_indexes.py` added in prior sprint:

| Index | Table | Columns | Query it serves |
|-------|-------|---------|-----------------|
| `ix_access_events_link_event` | access_events | (link_id, event_type) | Analytics aggregates filter by both |
| `ix_share_links_doc_revoked` | share_links | (document_id, revoked_at) | Active-link queries |
| `ix_documents_group_id` | documents | (group_id) | `get_group_analytics()` WHERE clause |

---

## Observations (By Design)

### PERF-OBS-001 — No client-side caching

The frontend fetches fresh data on every screen navigation. No React Query, SWR, or similar.

**Risk:** Low for beta. Medium at scale if server response times increase.  
**Recommendation:** Add stale-while-revalidate caching for document list and analytics in a future sprint.

### PERF-OBS-002 — Single bundle, no code splitting

Bundle: `frontend/dist/app.bundle.js` — 248.2 KB (esbuild IIFE)  
Build time: ~20ms

At 248 KB this is well within limits. No lazy loading.  
**Recommendation:** Consider route-based code splitting if bundle grows past 500 KB.

### PERF-OBS-003 — Viewer page watermarking is synchronous per page

Each page request: storage fetch → watermark → forensic stamp → response. No pre-computed watermarked pages.  
**By design:** Session-unique watermark angle requires runtime computation.  
**Mitigation:** L1 LRU cache + L2 Redis cache for raw page bytes avoids repeated storage fetches.
