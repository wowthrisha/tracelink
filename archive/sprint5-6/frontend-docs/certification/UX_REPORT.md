# UX REPORT — Sprint 5.5 Engineering Investigation
**Date:** 2026-06-29  
**Sprint:** 5.5 Phase 2  
**Method:** Source code review of all 13 frontend screens + component tree

---

## Summary

| Screen | UX Status | Issues |
|--------|-----------|--------|
| Upload Dashboard | PASS | Clean; stats show 0 for new accounts (expected) |
| Access Control — Create | PASS | Link Name, all permissions, correct button labels |
| Access Control — Links | PASS | Edit/Revoke/Delete/Copy/Rename all present |
| Access Control — Edit Modal | PASS | All 9 fields including max_concurrent_sessions |
| Access Control — View History | PASS | Tab renders |
| Access Control — Feedback | PASS | Filters, reviewer dropdown, reply UX |
| Access Control — Annotations | PASS | Visual annotation export |
| Analytics | PASS | Chart + KPI cards; 0 on new accounts (expected) |
| Storage | PASS | Forecast, per-document breakdown, retention controls |
| API Keys | PASS | Create/revoke key flows |
| Webhooks | PASS | Create/test/toggle/delete flows; status reads `is_active` correctly |
| Audit Log | PASS | Event list with pagination |
| Organizations | PASS | Member management, role enforcement |
| Notifications | PASS | 30s auto-refresh, unread badge, mark-read |
| Billing | PASS | Plan display, upgrade/portal links |
| Viewer | PASS | Null-doc → DocumentPicker; with doc → full viewer |

---

## Verified Sprint 5.4B UX Features

All Sprint 5.4B features confirmed in source code:

| Feature | File | Evidence |
|---------|------|---------|
| Link Name field | `AccessScreen.jsx:124` | `if (label_txt) payload.label = label_txt` |
| "Create Share Link" button | `AccessScreen.jsx` | Verified in JSX render |
| Delete button for revoked links | `AccessScreen.jsx` | Renders delete action when `l.revoked_at` is set |
| max_concurrent_sessions in edit | `AccessScreen.jsx:127` | `if (maxConcurrentSessions) payload.max_concurrent_sessions = parseInt(...)` |
| max_concurrent_sessions in modal | `AccessScreen.jsx:51` | `useState('')` for `maxConcurrentSessions` |

---

## Loading State Review

All screens clear loading state correctly — no permanent loading screens possible:

| Screen | Loading Guard | Clear mechanism |
|--------|--------------|-----------------|
| StorageScreen | `if (loading) return <div>Loading…</div>` | `.finally(() => setLoading(false))` |
| NotificationsScreen | `loading && ...` conditional | `finally { if (!silent) setLoading(false) }` |
| AnalyticsScreen | `analyticsLoading` flag | `.finally(() => setAnalyticsLoading(false))` |
| UploadScreen | `docsLoading` flag | `finally { setDocsLoading(false) }` |
| AccessScreen | `linksLoading` flag | `finally { setLinksLoading(false) }` |
| All screens | Various | All use `.finally()` to ensure clearing |

**No screen can be permanently stuck in a loading state.**

---

## Error State Review

| Screen | Error display | Method |
|--------|--------------|--------|
| All screens | Toast notification | `toast(_errMsg(e, 'message'), 'error')` |
| ViewerScreen | Error boundary | `ViewerErrorBoundary` wraps entire viewer |
| BillingScreen | Inline error | `setError(...)` shows message below buttons |

---

## UX Observations (Not Bugs)

| ID | Observation | Priority |
|----|-------------|----------|
| UX-OBS-001 | Stats show 0 on new accounts | P3 — cosmetic; expected behavior. Could add "No data yet" copy. |
| UX-OBS-002 | Viewer shows DocumentPicker when no doc selected | CORRECT BEHAVIOR — not a bug |
| UX-OBS-003 | No loading timeout or error recovery state on Storage/Notifications | P3 — if API takes >10s, user sees loading with no feedback. `.finally()` ensures eventual resolution. |
| UX-OBS-004 | Notifications uses polling (30s) not SSE | DOCUMENTED — SSE stream exists at `/api/notifications/stream` but NotificationsScreen uses REST poll. Intentional choice (SSE adds complexity). |
| UX-OBS-005 | Link name placeholder truncated at fixed width | COSMETIC — display constraint, not data issue |
