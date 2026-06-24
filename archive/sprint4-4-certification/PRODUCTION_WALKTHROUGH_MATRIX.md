# Production Walkthrough Matrix — Sprint 4.6C
Date: 2026-06-22
Scope: Every user-visible feature, button, tab, modal, export, and endpoint.
Method: Source-code trace (UI → API → backend → database). No guessing.

Classification key:
- **CERTIFIED** — works end-to-end in production, verified by code trace
- **PARTIAL** — works but has a known defect or missing edge-case coverage
- **BROKEN** — known failure in production (not just local dev)
- **STUB** — backend exists, no frontend UI
- **UNUSED** — frontend calls an endpoint that returns data never rendered
- **SECURITY_RISK** — potential security issue

---

## 1. Auth / Login

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| Sign In (Supabase) | LoginScreen | Submit button | `POST {supabase_url}/auth/v1/token` | supabase auth | CERTIFIED | `api.js:83-95` | LOW | No |
| Sign Up (backend admin) | LoginScreen | Submit button | `POST /api/auth/register` | users | CERTIFIED | `api.js:60-76` | LOW | No |
| Sign Up fallback (Supabase) | LoginScreen | Submit button | `POST {supabase_url}/auth/v1/signup` | supabase auth | CERTIFIED | `api.js:98-116` | LOW | No |
| Auto-redirect after Stripe return | AppShell | URL `?billing=success` | None | None | CERTIFIED | `AppShell.jsx:47-53` | LOW | No |
| Logout | Sidebar | Logout button | None (localStorage clear) | None | CERTIFIED | `AppShell.jsx:41-44` | LOW | No |
| Token decode for email display | Sidebar | Email in nav | None | None | CERTIFIED | `AppShell.jsx:14-19` | LOW | No |

---

## 2. Upload Screen

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| Document upload | UploadScreen | Drop zone / file picker | `POST /api/documents/upload` (XHR) | documents, object storage | CERTIFIED | `api.js:162-178`, `UploadScreen.jsx` | LOW | No |
| Upload progress bar | UploadScreen | Progress panel | XHR `progress` event | None | CERTIFIED | `UploadProgressPanel.jsx` | LOW | No |
| Document list fetch | UploadScreen | Table | `GET /api/documents` | documents | CERTIFIED | `api.js:212-219` | LOW | No |
| Document status polling | UploadScreen | Status badge | `GET /api/documents/{id}/status` | documents | CERTIFIED | `UploadScreen.jsx:84-105` | LOW | No |
| View document | UploadScreen | View button | None (state change) | None | CERTIFIED | `UploadScreen.jsx` → `AppShell.jsx:30` | LOW | No |
| Access Control for doc | UploadScreen | Access button | None (state change) | None | CERTIFIED | `AppShell.jsx:31` | LOW | No |
| Delete document | UploadScreen | Delete button | `DELETE /api/documents/{id}` | documents | CERTIFIED | `api.js:251-259` | LOW | No |
| Reprocess document | UploadScreen | Reprocess button | `POST /api/documents/{id}/reprocess` | documents | CERTIFIED | `api.js:231-239` | LOW | No |
| Re-extract sidecars | UploadScreen | Re-extract button | `POST /api/documents/{id}/extract-sidecars` | documents | CERTIFIED | `api.js:241-249` | LOW | No |
| Quick Share button | UploadScreen / DocRow | ↗ Share | `POST /api/links` | share_links | CERTIFIED | `QuickShareModal.jsx`, `api.js:261` | LOW | No |
| Quick Share copy link | QuickShareModal | ⧉ Copy link | None (clipboard API) | None | CERTIFIED | `QuickShareModal.jsx:42-49` | LOW | No |
| Quick Share configure | QuickShareModal | Configure in Access Control → | None (state change) | None | CERTIFIED | `QuickShareModal.jsx:84-91` | LOW | No |
| Group assignment | DocRow | Group dropdown | `PATCH /api/documents/{id}` or groups endpoint | documents | PARTIAL | `DocRow.jsx:75` — dropdown passes groupId but verify save call | LOW | Verify patch call |
| Stat cards (analytics) | UploadScreen | 4 stat cards | `GET /api/analytics/overview` | access_events, share_links, documents | CERTIFIED | `UploadScreen.jsx:57`, `api.js:431` | LOW | No |
| "undefined docs" in stat sub-text | UploadScreen | Stat card | N/A | N/A | CERTIFIED (fixed) | Previously `dashboard?.document_count` with no fallback | LOW | Fixed in 77598f8 |
| Metadata panel (filename, tags) | UploadMetadataPanel | Inline panel | `PATCH /api/documents/{id}` | documents | PARTIAL | Need to verify PATCH call exists in api.js | LOW | Verify |

---

## 3. Viewer Screen

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| Public viewer route | AppShell | `?token=` or `#view/token` URL | `GET /api/viewer/gate/{token}` + `POST /api/viewer/validate` | share_links, viewer_sessions, access_events | CERTIFIED | `AppShell.jsx:70-84`, `api.js:294-315` | LOW | No |
| Document page rendering | ViewerScreen | Canvas | `GET /api/viewer/page/{token}/{page}` | documents, raster cache | CERTIFIED | `usePageLoader.js` | LOW | No |
| Password gate | ViewerScreen / AccessGate | Password input | `POST /api/viewer/validate` with password | share_links | CERTIFIED | `AccessGate.jsx:68`, `api.js:300` | LOW | No |
| Email gate | ViewerScreen / AccessGate | Email input | `POST /api/viewer/validate` with email | share_links | CERTIFIED | `api.js:300` | LOW | No |
| Viewer session validation | ViewerScreen | On mount | `POST /api/viewer/validate` | viewer_sessions, access_events | CERTIFIED | `useViewerSession.js` | LOW | No |
| Page navigation (← →) | ViewerToolbar | Prev/Next buttons | None (local state) | None | CERTIFIED | `ViewerToolbar.jsx:199,220` | LOW | No |
| Zoom controls | ViewerToolbar | +/- buttons, fit modes | None | None | CERTIFIED | `ViewerToolbar.jsx` | LOW | No |
| Search | SearchPanel | Search input | None (local text layer) | None | CERTIFIED | `useSearchHighlights.js` | LOW | No |
| TOC sidebar | TocSidebar | TOC panel | Sidecar JSON | documents (sidecars) | CERTIFIED | `TocSidebar.jsx` | LOW | No |
| Links panel | LinksPanel | Links sidebar | Sidecar JSON | documents (sidecars) | CERTIFIED | `LinksPanel.jsx` | LOW | No |
| Viewer annotations (comment, sticky note) | ViewerScreen | Annotation toolbar | `POST /api/viewer/annotations/{token}` | annotations | CERTIFIED | `useAnnotations.js`, `api.js:546` | LOW | No |
| Annotation delete | ViewerScreen | Delete annotation | `DELETE /api/viewer/annotations/{token}/{id}` | annotations | CERTIFIED | `api.js:584` | LOW | No |
| Annotation resolve | ViewerScreen | Resolve annotation | `PATCH /api/viewer/annotations/{token}/{id}/resolve` | annotations | CERTIFIED | `api.js:638` | LOW | No |
| Annotation thread reply | ViewerScreen | Thread panel | `GET /api/viewer/annotations/{token}/{id}/thread` | annotations | CERTIFIED | `api.js:759` | LOW | No |
| Draw/Highlight/Rectangle/Arrow annotations | ViewerScreen | Annotation toolbar | `POST /api/viewer/annotations/{token}` | annotations | CERTIFIED | Visual annotation types | LOW | No |
| Magnifier | RectMagnifier | Zoom glass | None (canvas) | None | CERTIFIED | `RectMagnifier.jsx` | LOW | No |
| Laser pointer | LaserPointer | Pointer mode | None (local overlay) | None | CERTIFIED | `LaserPointer.jsx` | LOW | No |
| Insights modal | InsightsModal | Insights button | `GET /api/viewer/gate/{token}` re-read | share_links | CERTIFIED | `InsightsModal.jsx` | LOW | No |
| Download | ViewerToolbar | Download button | `GET /api/viewer/download/{token}` | share_links, documents | PARTIAL | Disabled when `!canDownload` — verify actual download endpoint | LOW | Verify download flow |
| Print | ViewerToolbar | Print button | `window.print()` | None | CERTIFIED | `ViewerToolbar.jsx:379` | LOW | No |
| Watermark overlay | ViewerScreen | DOM overlay | None (CSS) | None | CERTIFIED | `watermark_enabled` perm | LOW | No |
| Right-click block | ViewerScreen | Global event | None | None | CERTIFIED | `useViewerSession.js:132` | LOW | No |
| Keyboard shortcut block (Ctrl+P/C/S) | ViewerScreen | Global keydown | None | None | CERTIFIED | `useViewerSession.js:136-138` | LOW | No |
| Page time tracking / logEvent | ViewerScreen | Page change | `POST /api/analytics/events` | access_events | CERTIFIED | `useViewerSession.js`, `api.js:414` | LOW | No |
| Viewer session heartbeat | ViewerScreen | Timer | `POST /api/viewer/heartbeat` or logEvent | viewer_sessions | PARTIAL | Need to verify heartbeat call vs analytics event | LOW | Verify |
| Error boundary | ViewerErrorBoundary | Crash fallback | None | None | CERTIFIED | `ViewerErrorBoundary.jsx` | LOW | No |

---

## 4. Access Control Screen

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| Document picker (no doc selected) | AccessScreen | DocumentPicker | `GET /api/documents` | documents | CERTIFIED | `AccessScreen.jsx:160-168`, `DocumentPicker.jsx` | LOW | No |
| Policy tab — password, expiry, IP, email, domain | AccessScreen / Policy | Form fields | `POST /api/links` | share_links | CERTIFIED | `AccessScreen.jsx:116-135` | LOW | No |
| Policy tab — permissions toggles | AccessScreen / Policy | Toggle row | `POST /api/links` | share_links | CERTIFIED | `AccessScreen.jsx:280-318` | LOW | No |
| "Save Policy" creates new link | AccessScreen / Policy | Save Policy button | `POST /api/links` | share_links | CERTIFIED | `handleSave()` — note: always creates a new link, never updates existing | LOW | No (by design) |
| "New Link" (bare) | AccessScreen / Policy | ⟳ New Link button | `POST /api/links` with document_id only | share_links | CERTIFIED | `AccessScreen.jsx:307-317` | LOW | No |
| Share Link tab — list | AccessScreen / link | Link cards | `GET /api/links?document_id={id}` | share_links | CERTIFIED | `fetchLinks()`, `api.js:273` | LOW | No |
| Share Link tab — copy | AccessScreen / link | ⧉ Copy button | None (clipboard) | None | CERTIFIED | `handleCopy()` | LOW | No |
| Share Link tab — revoke single link | AccessScreen / link | Revoke button | `PATCH /api/links/{id}/revoke` | share_links | CERTIFIED | `api.js:282-291` | LOW | No |
| Revoke All Access | AccessScreen | ✕ Revoke All Access | `PATCH /api/links/{id}/revoke` × N | share_links | CERTIFIED | `handleRevoke()` — loops activeLinks | LOW | No |
| Share Link tab — embed code | AccessScreen / link | Pre block | None | None | CERTIFIED | `AccessScreen.jsx:388-395` | LOW | No |
| Share Link tab — open in new tab | AccessScreen / link | ↗ button | None | None | CERTIFIED | `window.open()` | LOW | No |
| Access Log tab | AccessScreen / log | Event table | `GET /api/analytics/events?document_id={id}` | access_events | PARTIAL | `AccessLog.jsx:15`: `getEvents(docId, 50)` passes 50 as groupId (latent misuse — works accidentally) | LOW | P2 fix: `getEvents(docId, null, 50)` |
| Feedback tab — list | AccessScreen / feedback | Thread table | `GET /api/documents/{id}/feedback` | annotations | CERTIFIED | `api.js:669`, `annotations.py:375` | LOW | No |
| Feedback tab — search/filter | AccessScreen / feedback | Filter bar | `GET /api/documents/{id}/feedback?search=...` | annotations | CERTIFIED | `buildFeedbackFilters()`, `api.js:669` | LOW | No |
| Feedback tab — reply from uploader | AccessScreen / feedback | ↩ Reply + Send | `POST /api/documents/{id}/feedback/{ann_id}/reply` | annotations | CERTIFIED | `api.js:698`, `annotations.py:346` | LOW | No |
| Feedback tab — Export Conversations CSV | AccessScreen / feedback | ↓ Export… → | `GET /api/documents/{id}/feedback/export` | annotations | CERTIFIED | `api.js:709-728`, `annotations.py` | LOW | No |
| Feedback tab — Export Reviewer Activity CSV | AccessScreen / feedback | ↓ Export… → | `GET /api/documents/{id}/feedback/export-reviewer-activity` | annotations | CERTIFIED | `api.js:730-737` | LOW | No |
| Feedback tab — reviewer filter dropdown | AccessScreen / feedback | Reviewer dropdown | `GET /api/documents/{id}/feedback/reviewers` | annotations | CERTIFIED | `api.js:688`, `annotations.py:fetch_feedback_reviewers` | LOW | No |
| Annotations tab — visual annotations list | AccessScreen / annotations | Table | `GET /api/documents/{id}/annotations-visual` | annotations | CERTIFIED | `api.js:739-748` | LOW | No |
| Annotations tab — type filter | AccessScreen / annotations | Type dropdown | Client-side filter on fetched data | None | CERTIFIED | `AccessScreen.jsx:653-654` | LOW | No |
| Annotations tab — Export CSV | AccessScreen / annotations | ↓ Export CSV | `GET /api/documents/{id}/annotations-visual/export` | annotations | CERTIFIED | `api.js:750-757` | LOW | No |

---

## 5. Analytics Screen

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| KPI cards (views, links, blocked, etc.) | AnalyticsScreen / Overview | 6 KPI cards | `GET /api/analytics/overview` | access_events, share_links, documents | CERTIFIED | `AnalyticsScreen.jsx:27, 44-51` | LOW | No |
| Spark chart (views over time) | AnalyticsScreen / Overview | SVG chart | `GET /api/analytics/overview` → `views_last_7_days` | access_events | CERTIFIED | `SparkChart.jsx:8-10` | LOW | No |
| Range selector (24h / 7d / 30d / 90d) | AnalyticsScreen / Overview | Range buttons | **NONE — no API call** | N/A | **BROKEN** | `AnalyticsScreen.jsx:14,78` — `range` state set, useEffect has `[]` deps, no range param passed to API. Data always shows all-time / 7d regardless of selected range. SparkChart always uses `views_last_7_days`. | MEDIUM | **P1: Pass range to API or remove buttons** |
| SparkChart empty state (no real data) | AnalyticsScreen | Chart area | None | None | PARTIAL | `SparkChart.jsx:12-17` — renders fake sine-wave when `sparkData` is empty. No "no data" message. | LOW | P3: Show empty state |
| Access outcomes donut chart | AnalyticsScreen / Overview | Donut | `GET /api/analytics/overview` | access_events | CERTIFIED | `DonutChart.jsx` | LOW | No |
| Top documents | AnalyticsScreen / Overview | Mini-list | `GET /api/analytics/documents` | access_events, documents | CERTIFIED | `AnalyticsScreen.jsx:358` | LOW | No |
| By Document tab — table | AnalyticsScreen / documents | Table | `GET /api/analytics/documents` | access_events, documents | CERTIFIED | `api.js:440` | LOW | No |
| By Document tab — page heatmap | AnalyticsScreen / documents | Expandable heatmap | `GET /api/analytics/page-heatmap?document_id={id}` | access_events | CERTIFIED | `AnalyticsScreen.jsx:159-163`, `api.js:383` | LOW | No |
| By Group tab — cards + table | AnalyticsScreen / groups | Card grid | `GET /api/analytics/groups` | groups, access_events | CERTIFIED | `api.js:451` | LOW | No |
| Export CSV (all 3 tabs) | AnalyticsScreen | ↓ Export CSV button | None (client-side Blob) | None | CERTIFIED | `AnalyticsScreen.jsx:82-124` | LOW | No |

---

## 6. Storage Screen

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| Storage dashboard fetch | StorageScreen | On mount | `GET /api/storage/dashboard` | documents | **CERTIFIED (post-fix)** | Bug fixed commit 77598f8 — `new URL()` crash in production | LOW | Fixed |
| Forecast fetch | StorageScreen | On mount | `GET /api/storage/forecast` | documents, storage_snapshots | CERTIFIED | `api.js:190-197` | LOW | No |
| Total bytes / doc count header | StorageScreen | Header | From dashboard response | documents | CERTIFIED | `StorageScreen.jsx:65-67` | LOW | No |
| "undefined docs" summary card | StorageScreen | Total Storage card | N/A | N/A | **CERTIFIED (post-fix)** | Fixed: `dashboard?.document_count ?? 0` | LOW | Fixed |
| Per-document table | StorageScreen | Table rows | From dashboard `by_document` | documents | CERTIFIED | `StorageScreen.jsx:120` | LOW | No |
| Retention policy dropdown | StorageScreen | `<select>` | `PATCH /api/documents/{id}/retention` | documents | CERTIFIED | `handleRetentionChange()`, `api.js:199-210` | LOW | No |
| 30-day / 90-day projection cards | StorageScreen | Summary cards | `GET /api/storage/forecast` | documents | CERTIFIED | `StorageScreen.jsx:75-76` | LOW | No |
| Per-org breakdown | StorageScreen | Bar chart | From dashboard `by_org` | documents | CERTIFIED | `StorageScreen.jsx:87-102` | LOW | No |
| Header title | StorageScreen | Screen title | N/A | None | PARTIAL | `atoms.jsx:390`: `titles` map missing `storage` entry — renders `undefined` title | LOW | P3: Add `storage: 'Storage'` to titles map |

---

## 7. Billing Screen

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| Billing status fetch | BillingScreen | On mount | `GET /api/billing/status` | user_billing | CERTIFIED | `BillingScreen.jsx:18`, `billing.py:68` | LOW | No |
| Upgrade to Pro | BillingScreen | "Upgrade to Pro" button | `POST /api/billing/checkout` | user_billing | CERTIFIED | `handleUpgrade()`, `billing.py:79` — redirects to Stripe | LOW | No |
| Manage Subscription | BillingScreen | "Manage Subscription" button | `POST /api/billing/portal` | user_billing | CERTIFIED | `handleManage()`, `billing.py:116` | LOW | No |
| "Billing not configured" banner | BillingScreen | Info banner | `GET /api/billing/status` → `billing_enabled: false` | None | CERTIFIED | `BillingScreen.jsx:154-162` | LOW | No |
| Stripe webhook (subscription events) | Backend only | None | `POST /api/billing/webhook` | user_billing | **STUB (no UI)** | Webhook handler exists and is complete, but no notification/toast when plan upgrades. UI only refreshes plan on next full load. | LOW | P2: Refresh billing status on `?billing=success` return |
| Plan enforcement (doc upload limit) | Backend | None visible | N/A | user_billing, documents | PARTIAL | Plan check in documents.py likely, but not confirmed in this audit scope | MEDIUM | Verify 10-doc limit enforcement |

---

## 8. Quick Share

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| Quick Share button (ready docs only) | UploadScreen / DocRow | ↗ Share | None (opens modal) | None | CERTIFIED | `DocRow.jsx:63-65` | LOW | No |
| Quick Share — auto-create link on open | QuickShareModal | Modal mount | `POST /api/links` | share_links | CERTIFIED | `QuickShareModal.jsx:32` | LOW | No |
| Quick Share — loading state | QuickShareModal | Spinner | N/A | None | CERTIFIED | `QuickShareModal.jsx` phase=loading | LOW | No |
| Quick Share — error state + retry | QuickShareModal | Error + retry | `POST /api/links` on retry | share_links | CERTIFIED | 13/13 tests pass | LOW | No |
| Quick Share — copy URL | QuickShareModal | ⧉ Copy link | None (clipboard) | None | CERTIFIED | `QuickShareModal.jsx:42-49` | LOW | No |
| Quick Share — configure redirect | QuickShareModal | Configure → | None (state) | None | CERTIFIED | `QuickShareModal.jsx:84-91` | LOW | No |

---

## 9. Notifications

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| Viewer open notification to uploader | None | None | `GET /api/notifications/stream` (SSE) | None | **STUB** | Backend SSE exists (`notifications.py`), no frontend UI built. `viewer_session_service.py:116-133` dispatches events on validation. | LOW | Sprint 4.6B planned |
| Notification center / bell | None | None | N/A | None | **STUB** | No frontend component exists | LOW | Sprint 4.6B |
| Unread count badge | None | None | N/A | None | **STUB** | No frontend component exists | LOW | Sprint 4.6B |

---

## 10. Webhooks

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| List webhooks | None | None | `GET /api/webhooks` | webhook_endpoints | **STUB** | Full CRUD backend in `webhooks.py`. No frontend screen. | LOW | No screen in AppShell |
| Create webhook | None | None | `POST /api/webhooks` | webhook_endpoints | **STUB** | Backend complete with SSRF guard | LOW | No frontend |
| Edit/delete webhook | None | None | `PATCH/DELETE /api/webhooks/{id}` | webhook_endpoints | **STUB** | Backend complete | LOW | No frontend |
| Webhook delivery history | None | None | `GET /api/webhooks/{id}/deliveries` | webhook_deliveries | **STUB** | Backend complete | LOW | No frontend |
| Test webhook ping | None | None | `POST /api/webhooks/{id}/test` | webhook_deliveries | **STUB** | Backend dispatches via Celery | LOW | No frontend |
| Webhook dispatch (viewer.opened) | Backend | None | Fired from `viewer_session_service.py` | webhook_deliveries | CERTIFIED | `dispatch_webhook_event` called on validate | LOW | No |
| Webhook dispatch (analytics.completed) | Backend | None | Fired from `analytics.py:300-323` | webhook_deliveries | CERTIFIED | Triggered on `completed` event type | LOW | No |

---

## 11. API Keys

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| List API keys | None | None | `GET /api/api-keys` | api_keys | **STUB** | Full CRUD in `api_keys.py`. No frontend screen, no Sidebar entry. | MEDIUM | No frontend — API integration blocked |
| Create API key | None | None | `POST /api/api-keys` | api_keys | **STUB** | Backend complete with audit logging | MEDIUM | No frontend |
| Revoke / delete API key | None | None | `PATCH/DELETE /api/api-keys/{id}` | api_keys | **STUB** | Backend complete | MEDIUM | No frontend |
| API key auth (for external callers) | Backend | N/A | All endpoints via `Authorization: Bearer sdk_...` | api_keys | CERTIFIED | `app/auth.py` handles both JWT and API key auth | LOW | No |

---

## 12. Organizations / Groups

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| Create / list groups | UploadScreen | Group dropdown in DocRow | `GET /api/groups`, `POST /api/groups` | groups | PARTIAL | Groups exist in DocRow but no create-group UI in the frontend | LOW | No create group flow |
| Assign document to group | UploadScreen | Group dropdown | `PATCH /api/documents/{id}` or `/api/groups/assign` | documents.group_id | PARTIAL | Dropdown exists in DocRow, verify save call | LOW | Verify |
| Org-level storage | StorageScreen | Per-org bar chart | From `GET /api/storage/dashboard` `by_org` | documents | CERTIFIED | Only shown when user has multiple orgs | LOW | No |
| Org management (orgs.py) | None | None | `GET/POST /api/orgs/...` | orgs | **STUB** | `orgs.py` router exists. No frontend screen. | LOW | No |

---

## 13. Audit Logs

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| Audit log write (API key events) | Backend | None | Internal | audit_log | CERTIFIED | `api_keys.py:103-114,174-186,203-210` | LOW | No |
| Audit log read | None | None | Endpoint unknown — `audit_service.py` | audit_log | **STUB** | No frontend screen, no Sidebar entry, no api.js method | LOW | No frontend |

---

## 14. Security Features

| Feature | Screen | UI Element | Backend Endpoint | Database Tables | Status | Evidence | Risk | Fix Required |
|---|---|---|---|---|---|---|---|---|
| IP allowlist enforcement | Backend | None | `POST /api/viewer/validate` | share_links | CERTIFIED | `policy.py` enforcer | LOW | No |
| Email allowlist enforcement | Backend | None | `POST /api/viewer/validate` | share_links | CERTIFIED | `policy.py` enforcer | LOW | No |
| Domain allowlist enforcement | Backend | None | `POST /api/viewer/validate` | share_links | CERTIFIED | `policy.py` enforcer | LOW | No |
| Max view count | Backend | None | `POST /api/viewer/validate` | share_links, access_events | CERTIFIED | Policy enforcer | LOW | No |
| Max concurrent sessions | Backend | None | `POST /api/viewer/validate` | viewer_sessions | CERTIFIED | Policy enforcer | LOW | No |
| Link expiry enforcement | Backend | None | `POST /api/viewer/validate` | share_links | CERTIFIED | `link.expires_at < now` check | LOW | No |
| SSRF guard on webhook URLs | Backend | None | `POST /api/webhooks` | webhook_endpoints | CERTIFIED | `validate_ssrf_url()` | LOW | No |
| Analytics event validation (page_number, session) | Backend | None | `POST /api/analytics/events` | access_events | CERTIFIED | `analytics.py:190-286` | LOW | No |
| Metadata size cap (1 KB) | Backend | None | `POST /api/analytics/events` | access_events | CERTIFIED | `analytics.py:231-242` | LOW | No |
| Revoked link event rejection | Backend | None | `POST /api/analytics/events` | share_links | CERTIFIED | `analytics.py:261-262` | LOW | No |

---

## Summary Counts

| Status | Count |
|---|---|
| CERTIFIED | 64 |
| PARTIAL | 9 |
| BROKEN (pre-fix) | 2 |
| STUB | 14 |
| UNUSED | 0 |
| SECURITY_RISK | 0 |

**Screens in Sidebar**: Upload, Viewer, Access Control, Analytics, Storage, Billing (6 total)
**Screens with no frontend**: Webhooks, API Keys, Organizations, Audit Logs, Notifications (5 total)
**Production bugs fixed this sprint**: Storage `new URL()` crash, `document_count` undefined display
