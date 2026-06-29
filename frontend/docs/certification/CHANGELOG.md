# CHANGELOG — Sprint 5.5 Engineering Investigation
**Date:** 2026-06-29  
**Sprint:** 5.5 Phase 2

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
