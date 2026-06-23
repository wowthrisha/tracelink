# API Hardening Report — Sprint 5.3 Phase 2

**Date:** 2026-06-23  
**Sprint:** 5.3  
**Phase:** 2 — API Hardening  
**Status:** COMPLETE

---

## Summary

Phase 2 audited all API endpoints for rate limiting, input validation, pagination, and HTTP semantics. Four violations were identified and fixed.

---

## Findings

### FIX 1 — Analytics Rate Limiting (FIXED)

**Violation:** All 5 GET analytics endpoints (`/api/analytics/overview`, `/api/analytics/documents`, `/api/analytics/groups`, `/api/analytics/page-heatmap`, `/api/analytics/events`) lacked SlowAPI rate limiting.  
**Risk:** DoS via analytics polling; CPU exhaustion from unthrottled GROUP BY queries.  
**Fix:** Added `@limiter.limit("30/minute")` and `request: Request` to all 5 GET endpoints.  
**File:** `backend/app/routers/analytics.py`

### FIX 2 — group_id Silent Validation Failure (FIXED)

**Violation:** Malformed `group_id` UUID in `/api/analytics/documents` silently fell back to `group_uuid = None` (returning all documents). The caller could not distinguish a bad UUID from no filter.  
**Fix:** Changed `except ValueError: group_uuid = None` to `raise HTTPException(status_code=400, detail="Invalid group_id format")`.  
**File:** `backend/app/routers/analytics.py`

### FIX 3 — Gate Endpoint HTTP Semantics (FIXED)

**Violation:** `GET /api/viewer/gate/{token}` returned HTTP 200 with `{status: "not_found"}` for missing tokens. Correct REST semantics: missing resource = 404.  
**Fix:** Backend changed to `raise HTTPException(status_code=404)`. Frontend `api.js` converts 404 → `{status: 'not_found', requires_password: false, requires_email: false}` to preserve existing UI behavior.  
**Files:** `backend/app/routers/viewer.py`, `frontend/api.js`  
**Tests Updated:** `tests/integration/test_phase6.py`, `test_phase7.py`, `test_viewer.py`, `test_stability.py` — 4 files, all updated from 200 to 404 assertion.

### FIX 4 — Analytics Endpoint Pagination (FIXED)

**Violation:** `/api/analytics/documents` and `/api/analytics/groups` returned unbounded lists — at 10,000 documents this fetches and serializes the entire table.  
**Fix:**  
- Added `limit: int = Query(100, ge=1, le=500)` and `offset: int = Query(0, ge=0)` to both endpoints.  
- Service methods `get_document_analytics()` and `get_group_analytics()` updated to accept and apply limit/offset, return `(list, total)` tuple.  
- Response envelope: `{documents/groups, total, limit, offset}`.  
**Files:** `backend/app/routers/analytics.py`, `backend/app/services/analytics_service.py`

---

## API Contract Changes

The gate endpoint change (`200 → 404` for missing token) is coordinated — frontend was updated atomically in the same commit. No external API contract breaking change: the public-facing viewer gate was already documented as potentially returning 404 per HTTP standards.

The analytics pagination adds new optional query parameters with backward-compatible defaults (limit=100, offset=0). The response envelope now includes `total`, `limit`, `offset` keys — additive change, not breaking.

---

## Test Results

- 20 analytics tests: all pass
- 4 gate endpoint tests (across 4 files): all pass  
- Full suite: 1624 passed after all Phase 2 fixes

---

## Verdict

**PASS** — All API hardening fixes applied. Rate limits, input validation, HTTP semantics, and pagination are production-ready.
