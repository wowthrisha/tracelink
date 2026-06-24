# Remaining Bug Backlog — Sprint 4.6C
Date: 2026-06-22
Source: Production Walkthrough & Feature Certification
Scope: Bugs found by tracing UI → API → Backend → Database across all screens.

Note: The storage screen crash (new URL) and undefined docs display were fixed during this sprint.
This backlog covers all outstanding unfixed issues.

---

## P0 — Release Blockers (0)

No P0 bugs remain after Sprint 4.6C storage fixes.

---

## P1 — Must Fix Before Beta

### BUG-001: Analytics range selector is entirely non-functional
- **Priority**: P1
- **Screen**: Analytics → Overview tab
- **Element**: 24h / 7d / 30d / 90d range toggle buttons
- **Evidence**:
  - `AnalyticsScreen.jsx:14`: `const [range, setRange] = useState('7d')` — range stored in state
  - `AnalyticsScreen.jsx:78`: `setRange(r)` called on button click
  - `AnalyticsScreen.jsx:27`: `useEffect(() => { fetchAll() }, [])` — empty dependency array, never re-runs on range change
  - `api.js:431`: `getAnalyticsOverview()` — no range parameter exists in function signature
  - `backend/analytics.py`: `GET /api/analytics/overview` — no `range` or `period` query parameter
  - `SparkChart.jsx:8-10`: When `sparkData` is present, `range` prop is ignored entirely. Uses `views_last_7_days` regardless.
  - `AnalyticsScreen.jsx:262`: Label reads "Daily view count · {range}" — lying to users
- **Impact**: Users believe they are filtering by time range. They are not. All KPIs and charts always show the same data regardless of button state.
- **Fix**: Either (a) add `range` parameter to `getAnalyticsOverview()` and the backend endpoint and add `range` to `useEffect` deps, or (b) remove the range buttons and update the label to accurately reflect that data shows all-time stats.

---

### BUG-002: No frontend for Webhooks (backend complete)
- **Priority**: P1
- **Screen**: None — no frontend screen exists
- **Backend**: `backend/app/routers/webhooks.py` — full CRUD: create, list, get, update, delete, test ping, delivery history
- **Evidence**: No `<SidebarItem>` for webhooks in `AppShell.jsx`, no `getWebhooks`/`createWebhook` methods in `api.js`, no `WebhooksScreen.jsx` file
- **Impact**: Webhooks feature is invisible to users. Developers delivering on this feature receive no value.
- **Risk**: Webhook dispatch already runs in production (viewer.opened, analytics.completed events fire via Celery). Users have no way to register webhook endpoints.

---

### BUG-003: No frontend for API Keys (backend complete)
- **Priority**: P1
- **Screen**: None — no frontend screen exists
- **Backend**: `backend/app/routers/api_keys.py` — full CRUD with audit logging, rate limiting, key rotation
- **Evidence**: No Sidebar entry, no `api.js` methods (`getApiKeys`, `createApiKey`), no `ApiKeysScreen.jsx`
- **Impact**: The API key authentication path (`Authorization: Bearer sdk_...`) works in `app/auth.py`, but users cannot create or manage keys through the UI. SDK integration is blocked.

---

### BUG-004: `getEvents()` called with wrong argument order in AccessLog
- **Priority**: P1 (functionally benign today, P1 for API contract correctness)
- **Screen**: Access Control → Access Log tab
- **Element**: Event table
- **Evidence**:
  - `AccessLog.jsx:15`: `window.SecureDocAPI.getEvents(docId, 50)`
  - `api.js` signature: `getEvents(documentId, groupId, limit = 50, offset = 0)`
  - `50` is passed as `groupId`, not `limit`
  - Backend (`analytics.py`): attempts `uuid.UUID('50')`, catches `ValueError`, sets `group_uuid = None`
  - Actual limit defaults to 50 anyway — so the displayed result is correct by accident
- **Impact**: Silent contract violation. If the default limit ever changes, or if this pattern is copied to another call, it will break silently. Also prevents any actual group_id filtering in the log tab.
- **Fix**: Change to `getEvents(docId, null, 50)` in `AccessLog.jsx:15`.

---

### BUG-005: react/react-dom devDependencies pinned to v19, production CDN is v18
- **Priority**: P1
- **File**: `frontend/package.json`
- **Evidence**:
  - `package.json`: `"react": "^19.2.7", "react-dom": "^19.2.7"`
  - `frontend/index.html`: `<script src="https://unpkg.com/react@18.3.1/...">` (React 18 CDN)
  - Tests run against React 19 hooks internals; production users run React 18
- **Impact**: If any React 19 behavior (new hooks, strict mode changes, concurrent mode differences) is exercised in tests, tests pass but the feature fails in production. The divergence is invisible.
- **Fix**: Pin devDependencies to `"18.3.1"` (exact, no caret) to match the CDN version.

---

## P2 — Should Fix Before Launch

### BUG-006: Analytics — `useEffect` missing `range` dep causes stale data label
- **Priority**: P2 (UI correctness)
- **Screen**: Analytics → Overview tab
- **Element**: Spark chart subtitle "Daily view count · {range}"
- **Evidence**: `AnalyticsScreen.jsx:262` — label changes when button is clicked, but the data does not. Users see "Daily view count · 90d" while looking at 7-day data.
- **Fix**: Part of BUG-001 fix. At minimum, remove the "· {range}" from the label if range is not actually applied.

---

### BUG-007: SparkChart generates fabricated data when `sparkData` is empty
- **Priority**: P2
- **Screen**: Analytics → Overview tab
- **Element**: Spark chart (SVG line chart)
- **Evidence**:
  - `SparkChart.jsx:12-17`: when `sparkData` is empty/falsy, generates a sine-wave curve using `Math.sin` seeded from `range`
  - No label, disclaimer, or "no data" state shown
  - Users cannot distinguish real data from the placeholder
- **Fix**: Show a "No data yet" message when `sparkData` is empty, instead of synthetic data.

---

### BUG-008: StorageScreen header title renders undefined
- **Priority**: P2
- **Screen**: Storage
- **Element**: Screen title in Header component
- **Evidence**:
  - `atoms.jsx:390`: `const titles = { upload: 'Upload Dashboard', viewer: 'Document Viewer', access: 'Access Control', analytics: 'Analytics' }`
  - `StorageScreen.jsx:64`: `<Header screen="storage">` — `titles['storage']` is `undefined`
  - `atoms.jsx:400`: `{titles[screen]}` renders `undefined` → blank title
- **Fix**: Add `storage: 'Storage'` and `billing: 'Billing'` to the `titles` map in `atoms.jsx:390`.

---

### BUG-009: BillingScreen doesn't re-fetch status after Stripe return
- **Priority**: P2
- **Screen**: Billing
- **Element**: Plan status display
- **Evidence**:
  - `AppShell.jsx:47-53`: on `?billing=success`, the URL param is cleared and the screen switches to billing
  - `BillingScreen.jsx:18`: `getStatus()` is called in `useEffect([], [])` — only runs on mount
  - The Stripe checkout → redirect → AppShell → BillingScreen flow mounts BillingScreen fresh, so `getStatus()` DOES fire on return
  - Actual issue: if the user refreshes the billing screen manually after confirming, they might see stale plan data because Stripe webhooks can lag
- **Fix**: Minor — after `?billing=success` redirect, show a "Checking your plan status…" message and poll `getStatus()` once more after 2s to catch webhook lag.

---

### BUG-010: No notification when viewer opens document (uploader side)
- **Priority**: P2
- **Screen**: None — Notifications system not built
- **Evidence**: `viewer_session_service.py:116-133` dispatches `viewer.opened` events via SSE/Redis. Backend notification stream exists at `GET /api/notifications/stream`. No frontend consumes it.
- **Impact**: Uploaders have no real-time awareness when recipients open their documents. This is a planned Sprint 4.6B feature.

---

### BUG-011: No org management UI (groups / orgs.py)
- **Priority**: P2
- **Screen**: None
- **Evidence**: `backend/app/routers/orgs.py` exists. `GroupDropdown` in DocRow allows assignment but doesn't expose a "create group" flow. Users cannot create groups through the UI.
- **Fix**: Add minimal group creation UI (likely a modal from the group dropdown "New group…" option).

---

### BUG-012: Audit log backend has no frontend
- **Priority**: P2
- **Screen**: None
- **Evidence**: `audit_service.py` and `api_keys.py:103-114,174-186,203-210` write audit events on API key operations. No read endpoint is surfaced to the frontend. No audit log screen or export exists.

---

## P3 — Nice to Have

### BUG-013: AccessLog group filter never triggers (related to BUG-004)
- **Priority**: P3
- **Screen**: Access Control → Access Log tab
- **Evidence**: Even if BUG-004 is fixed, AccessLog has no UI for selecting a group — the component only accepts `docId` as prop. The `groupId` capability in the API is unused from this UI.

---

### BUG-014: AnalyticsScreen Overview KPI uses misleading label "Total Views"
- **Priority**: P3
- **Screen**: Analytics → Overview
- **Evidence**: `AnalyticsScreen.jsx:44` — card labeled "Total Views" actually renders `overview.total_views_today` (a today-only metric). The label should be "Today's Views" or "Views Today".

---

### BUG-015: Viewer — heartbeat call vs. analytics event not confirmed
- **Priority**: P3
- **Screen**: Viewer
- **Evidence**: `useViewerSession.js` logs events via `POST /api/analytics/events`. No heartbeat call to a `/api/viewer/heartbeat` endpoint was found. If concurrent session tracking depends on a heartbeat, inactive tabs may not release sessions. Requires verification.

---

### BUG-016: Group assignment in DocRow — save call not confirmed
- **Priority**: P3
- **Screen**: Upload → Document table row
- **Element**: Group dropdown
- **Evidence**: `DocRow.jsx:75` — group dropdown exists, but the exact API call made on group selection was not traced to completion. Likely calls `PATCH /api/documents/{id}` with `group_id`. Requires verification that the save actually fires and the correct field is sent.

---

### BUG-017: Plan enforcement (doc upload limit) — frontend not verified
- **Priority**: P3
- **Screen**: Upload
- **Evidence**: Backend plan enforcement likely exists in `documents.py` (e.g., Free tier limited to 10 docs). Frontend does not show remaining upload quota, does not surface a "You've reached your plan limit" message.
- **Impact**: Free users may hit a silent 403/422 on upload with no human-readable error.

---

## Summary

| Priority | Count | Items |
|---|---|---|
| P0 | 0 | — |
| P1 | 5 | BUG-001 through BUG-005 |
| P2 | 7 | BUG-006 through BUG-012 |
| P3 | 5 | BUG-013 through BUG-017 |
| **Total** | **17** | |

---

## Already Fixed This Sprint

| Bug | Fix | Commit |
|---|---|---|
| Storage screen crash (`new URL()` in production) | Replace with `fetch(template-string)` in `api.js:181-188` | 77598f8 |
| Storage screen "undefined docs" display | `?? 0` fallback in `StorageScreen.jsx:74` | 77598f8 |
| Railway build failure (npm 11 lockfile vs npm 10 CI) | Regenerate lockfile with npm 10.8.2 (Node 20) | 65f1dd9 |
