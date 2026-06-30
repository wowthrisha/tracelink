# Phase 0 — Verified Findings

**Sprint:** 5.3 — Production Hardening  
**Date:** 2026-06-23  
**Method:** Direct re-inspection of each Sprint 5.2 finding against current source code.

---

## Verification Legend

- **VERIFIED** — Finding confirmed in current code. Fix required.
- **FALSE POSITIVE** — Not present in actual code.
- **ALREADY FIXED** — Was present; already resolved.
- **DEFERRED** — Real issue but out of scope or requires architectural decision.

---

## Sprint 5.2 Findings Re-Verification

### V-01 — Python-side Timestamp Aggregation
**Sprint 5.2 classification:** VIOLATION  
**Phase 0 verdict:** VERIFIED  
**Evidence:** `analytics_service.py:148-155`
```python
week_ts_rows = (await db.execute(week_q)).scalars().all()  # ALL timestamps into Python
date_counts: dict = {}
for ts in week_ts_rows:
    date_counts[ts.strftime("%Y-%m-%d")] = ...
```
**Action:** Replace with SQL `GROUP BY func.date(created_at)`. Phase 3.

---

### W-01 — scoped_link_ids Materialized Into Python List
**Sprint 5.2 classification:** WARNING  
**Phase 0 verdict:** VERIFIED  
**Evidence:** `analytics_service.py:73-83` — `doc_ids` and `scoped_link_ids` loaded as Python lists, passed to IN clauses.  
**Additional finding (new):** `total_documents` COUNT query at line 87-90 is redundant — `len(doc_ids)` gives the same result when `user_id is not None`.  
**Action:** Remove redundant COUNT query. Phase 3. Full CTE rewrite deferred (Tier 2 concern).

---

### W-02 — Missing `(link_id, event_type)` Composite Index
**Sprint 5.2 classification:** WARNING  
**Phase 0 verdict:** VERIFIED  
**Evidence:** `models/event.py:40-46` — only `(created_at)`, `(link_id)`, `(link_id, created_at)` indexes exist. No `(link_id, event_type)`.  
**Action:** Alembic migration 025. Phase 1.

---

### W-03 — Missing `(document_id, revoked_at)` Index on share_links
**Sprint 5.2 classification:** WARNING  
**Phase 0 verdict:** VERIFIED  
**Evidence:** `models/link.py:11-13` — only `document_id` index.  
**Action:** Same migration 025. Phase 1.

---

### W-04 — Document Model Missing user_id Index (from pre-compaction summary)
**Sprint 5.2 classification:** Listed as VIOLATION in session summary  
**Phase 0 verdict:** FALSE POSITIVE  
**Evidence:** `models/document.py:16` — `Index("ix_documents_user_id", "user_id")` IS present.  
**Action:** None. Sprint 5.2 reports correctly classified this as PASS.

---

### W-05 — Missing group_id Index on Documents Table (NEW FINDING)
**Sprint 5.2 classification:** Not reported  
**Phase 0 verdict:** NEW — VERIFIED  
**Evidence:** `models/document.py:13-25` — no `group_id` index in `__table_args__`. `get_group_analytics()` at `analytics_service.py:397-406` queries `Document.group_id.in_(group_ids)` without an index.  
**Action:** Add to migration 025. Phase 1.

---

### W-06 — Analytics Endpoints Not Rate-Limited
**Sprint 5.2 classification:** WARNING  
**Phase 0 verdict:** VERIFIED  
**Evidence:** `routers/analytics.py:19-82` — no `@limiter.limit()` decorator on any GET endpoint.  
**Action:** Add rate limits + `request: Request` parameter. Phase 2.

---

### W-07 — Gate Endpoint HTTP 200 for Missing Token
**Sprint 5.2 classification:** WARNING  
**Phase 0 verdict:** VERIFIED  
**Evidence:** `routers/viewer.py:153` — returns `{"status": "not_found", ...}` with HTTP 200 for missing token.  
**Frontend impact:** `api.js:314-317` — `if (!r.ok) throw` means a 404 would throw. Both `useViewerSession.js:90` and `:119` catch blocks handle this but show generic error messages instead of "Link Not Found".  
**Action:** Coordinated change — backend returns 404, frontend `getGateRequirements()` handles 404 and converts to `{status: 'not_found', ...}`. Phase 2.

---

### W-08 — group_id UUID Validation Silent Failure
**Sprint 5.2 classification:** WARNING  
**Phase 0 verdict:** VERIFIED  
**Evidence:** `routers/analytics.py:32-38`
```python
try:
    group_uuid = uuid.UUID(group_id)
except ValueError:
    group_uuid = None  # ← silently returns ALL docs instead of 400
```
**Action:** Raise HTTP 400. Phase 2.

---

### W-09 — Default DB Connection Pool Size
**Sprint 5.2 classification:** WARNING  
**Phase 0 verdict:** VERIFIED  
**Evidence:** `database.py:1` — `create_async_engine(settings.database_url, echo=False)` with no pool parameters.  
**Action:** Add `pool_size` and `max_overflow` to engine creation, configurable via settings. Phase 1.

---

### W-10 — Policy Fields as JSON Text (Not JSONB)
**Sprint 5.2 classification:** WARNING  
**Phase 0 verdict:** DEFERRED  
**Reason:** Requires database migration changing column types from TEXT to JSONB. This is a schema migration with data transformation. Not addressable in a single-file fix. Deferred to Tier 2 planning.

---

### W-11 — Inconsistent Response Envelopes
**Sprint 5.2 classification:** WARNING  
**Phase 0 verdict:** DEFERRED  
**Reason:** Changing response shapes is an API contract change. Frontend must be updated simultaneously. Scope too large for this sprint.

---

### W-12 — Analytics Read Endpoints Return Unbounded Lists
**Sprint 5.2 classification:** WARNING  
**Phase 0 verdict:** VERIFIED (PARTIAL)  
**Evidence:** `GET /api/analytics/documents` and `/api/analytics/groups` have no pagination. `GET /api/analytics/events` correctly has `limit/offset`.  
**Action:** Add `limit` and `offset` query params to documents and groups endpoints. Phase 2.

---

### W-13 — Prometheus Metrics Without Alerting Rules
**Sprint 5.2 classification:** WARNING  
**Phase 0 verdict:** DEFERRED  
**Reason:** Alerting rules are infrastructure configuration (PagerDuty, Prometheus alert rules). Outside repository scope.

---

## Additional Findings from Phase 0 Re-inspection

### NEW-01 — Pre-existing Test Failure (test_phase2.py)
**Type:** Pre-existing  
**Evidence:** `tests/integration/test_phase2.py::TestBundleCorrectness::test_bundle_ends_with_reactdom_render` fails because the minified bundle uses `ti` (the mangled App component name) instead of `App`.  
**Action:** Fix test to check bundle contains `createRoot` + `render` without asserting the exact component name. Phase 6 (cleanup).

---

## Phase 0 Action Plan

| Phase | Finding | Action |
|---|---|---|
| Phase 1 | W-02 + W-03 + W-05 | Migration 025: add 3 missing indexes |
| Phase 1 | W-09 | Configurable DB pool settings |
| Phase 2 | W-06 | Rate limit analytics endpoints |
| Phase 2 | W-07 | Gate endpoint 404 (coordinated BE+FE) |
| Phase 2 | W-08 | Fix silent group_id UUID validation |
| Phase 2 | W-12 | Add pagination to document/group analytics |
| Phase 3 | V-01 | SQL GROUP BY for 7-day chart |
| Phase 3 | W-01 (partial) | Remove redundant COUNT query |
| Phase 4 | Frontend audit | Read all screens, fix verified issues |
| Phase 5 | Security audit | XSS, CSRF, open redirect checks |
| Phase 6 | NEW-01 | Fix pre-existing bundle test |
| DEFERRED | W-04, W-10, W-11, W-13 | Tier 2 or infrastructure concerns |

---

*Baseline test state: 1600 passed, 1 skipped, 1 pre-existing failure (test_phase2.py bundle assertion).*
