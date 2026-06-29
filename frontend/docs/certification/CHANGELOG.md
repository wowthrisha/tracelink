# CHANGELOG — Sprint 6.0 Engineering Excellence
**Date:** 2026-06-29  
**Sprint:** 6.0 (supersedes Sprint 5.5)

---

## [Sprint 6.0 Engineering Excellence] — 2026-06-29

### Fixed

- **FIX-005** `backend/app/routers/documents.py` — Fix wrong import in `extract_sidecars` closure. `from app.storage import get_storage` raised `ModuleNotFoundError` on every call. Correct path: `from app.services.storage import get_storage_service`. This endpoint was fully broken. (Commit: `ef35524`)

- **FIX-006** `backend/app/routers/analytics.py` — Add `func` to module-level `from sqlalchemy import select, func`. Remove inner `from sqlalchemy import func as _func` that existed at line 153 inside `get_events()`. Module-level import is authoritative. (Commit: `ef35524`)

- **FIX-008** `backend/app/services/analytics_service.py` — Extract duplicate `_by_link()` helper to module level. It was defined identically inside both `get_document_analytics()` and `get_group_analytics()`. Now a single module-level function. (Commit: `ef35524`)

- **FIX-009** `backend/app/routers/orgs.py` — Replace deprecated `asyncio.get_event_loop()` with `asyncio.get_running_loop()` inside `verify_custom_domain` async function. `get_event_loop()` emits a DeprecationWarning in Python 3.10+ when called inside a running loop. (Commit: `ef35524`)

- **FIX-010** `backend/app/routers/links.py` — Eliminate redundant `Document` DB fetch in `list_links`. The document was fetched once for ownership check and again for `_get_base_url_for_doc()`. Now reuses the first result. (Commit: `ef35524`)

- **FIX-011** `backend/app/services/retention.py` — Add `"words"` to `_SIDECAR_PREFIXES`. The `words/{doc_id}.json` sidecar created by `extract_and_store_word_positions()` in the worker pipeline was never deleted on document removal or expiry. Storage leak closed. (Commit: `ef35524`)

### Refactored

- **Frontend** — Monolithic `frontend/src/app.jsx` (5525 lines) extracted into modular component hierarchy. `app.jsx` is now a single import from `./screens/AppShell.jsx`. Components, screens, hooks, contexts, constants, and utils are separate files. (Commit: `ef35524`)

- **`useViewerSession.js`** — `toast` notification function moved from caller-supplied parameter to `useToast()` context hook. Callers no longer need to pass their own toast instance. (Commit: `ef35524`)

### Tests Fixed

- **`tests_e2e/e2e/test_security_flow.py`** — Session ID now passed as `X-Session-ID` header (was incorrectly using query param `?session_id=`). Aligns with the API contract established in prior sprints. (Commit: `ef35524`)

---

## [Sprint 5.5 Phase 2] — 2026-06-29

### Fixed

- **FIX-001** `backend/app/routers/analytics.py` — Add missing `import logging` and `logger = logging.getLogger(__name__)`. Fixes `NameError: name 'logger' is not defined` in the `analytics.completed` webhook failure exception handler, which previously caused 500 errors to viewers when webhook dispatch failed. (Commit: `710ff78`)

- **FIX-002** `backend/app/routers/orgs.py` — Batch member count query in `list_orgs`. Replaced per-org `SELECT COUNT(*)` loop (N+1 queries) with single `SELECT org_id, COUNT(id) GROUP BY org_id` query. (Commit: `3290a00`)

- **FIX-003** `backend/app/routers/admin.py` — Replace in-memory ID count with SQL `COUNT()` in `get_audit_log`. Replaced `len(count_result.all())` (loads all matching IDs into Python memory) with `select(func.count()).select_from(query.subquery())`. (Commit: `3290a00`)

- **FIX-004** `backend/app/routers/webhooks.py` — Remove redundant `from datetime import datetime, timezone as _tz` inner import inside `update_webhook()` function. Module-level `datetime` and `timezone` already imported at line 4. (Commit: `3290a00`)

### Verified (Not Changed)

All Phase 1 audit findings (BUG-001 through BUG-007) were investigated with source code evidence and confirmed as not real bugs. No changes required.

### Investigated (No Changes)

The following areas were fully reviewed with no issues found:

- `api_keys.py` — CLEAN
- `auth.py` — CLEAN  
- `billing.py` — CLEAN
- `notifications.py` — CLEAN (SSE stream)
- `groups.py` — CLEAN
- `storage.py` — CLEAN
- `documents.py` — CLEAN
- `viewer.py` — CLEAN (page, thumb, download, search, TOC, word positions)
- `annotations.py` — CLEAN (input validation via Pydantic, session enforcement)
- `links.py` — VERIFIED (Sprint 5.4B)
- `audit_service.py` — CLEAN
- `webhook_service.py` — CLEAN
- `ssrf_guard.py` — CLEAN
- Security middleware — CLEAN (CSP, CORS, headers)
- All frontend screens — VERIFIED (StorageScreen, NotificationsScreen, AnalyticsScreen, BillingScreen, AccessScreen, UploadScreen, ViewerScreen)
- Database migrations 001–025 — CLEAN

---

## Previous Sprint Reference

### [Sprint 5.4B] — Link Management UX (prior sprint)

- Link Name field on Create tab
- "Create Share Link" button label
- Delete button for revoked links
- max_concurrent_sessions in LinkSummary and Edit modal
- PATCH uses `model_fields_set` (null-clear fields correctly)
- link.created audit event
- Hard delete endpoint (`DELETE /api/links/{id}/hard`, requires `revoked_at ≠ null`)

---

## Test Suite

1624 passing / 1 skipped across all Sprint 5.5 changes. Zero regressions.
