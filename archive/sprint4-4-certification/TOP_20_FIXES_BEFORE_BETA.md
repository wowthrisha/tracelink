# Top 20 Fixes Before Beta — Sprint 4.6C
Date: 2026-06-22
Source: Production Walkthrough Certification
Rule: No new features. Fixes only. Ranked by user impact × production risk.

---

## Priority Rankings

| Rank | ID | Priority | Title | Effort | Impact |
|---|---|---|---|---|---|
| 1 | FIX-001 | P0 (fixed) | Storage screen crash in production | Done | Critical |
| 2 | FIX-002 | P1 | Analytics range selector does nothing | Low | High |
| 3 | FIX-003 | P1 | No UI for API Keys (backend complete) | High | High |
| 4 | FIX-004 | P1 | No UI for Webhooks (backend complete) | High | High |
| 5 | FIX-005 | P1 | React 18 / React 19 devDep mismatch | Low | Medium |
| 6 | FIX-006 | P1 | AccessLog wrong arg order (BUG-004) | Low | Low |
| 7 | FIX-007 | P2 | SparkChart fabricates data when empty | Low | Medium |
| 8 | FIX-008 | P2 | StorageScreen header title is undefined | Low | Low |
| 9 | FIX-009 | P2 | No notification on viewer open | High | High |
| 10 | FIX-010 | P2 | "Total Views" label is actually today | Low | Low |
| 11 | FIX-011 | P2 | BillingScreen should re-check plan after Stripe return | Low | Low |
| 12 | FIX-012 | P2 | No group creation UI | Medium | Medium |
| 13 | FIX-013 | P2 | Audit log has no frontend | High | Medium |
| 14 | FIX-014 | P3 | Heartbeat vs. analytics event — verify concurrent sessions | Low | Unknown |
| 15 | FIX-015 | P3 | Group assignment in DocRow — verify save fires | Low | Unknown |
| 16 | FIX-016 | P3 | Plan upload limit — surface as human-readable error | Low | Medium |
| 17 | FIX-017 | P3 | AccessLog has no group filter UI | Low | Low |
| 18 | FIX-018 | P3 | SparkChart always shows 7 date labels regardless of range | Low | Low |
| 19 | FIX-019 | P3 | BillingScreen title not in Header titles map | Low | Low |
| 20 | FIX-020 | P2 | Quick Share defaults duplicated with AccessScreen | Low | Low |

---

## Fix Details

---

### FIX-001 — Storage screen crash in production ✅ DONE
- **Priority**: P0 (fixed, commit 77598f8)
- **Root cause**: `new URL('/api/storage/dashboard')` throws `TypeError: Failed to construct 'URL': Invalid URL` in production where `API_BASE = ''`.
- **Fix applied**: `api.js:181-188` — replaced `new URL()` with `fetch(template-string)`.
- **Secondary fix**: `StorageScreen.jsx:74` — `?? 0` fallback for `document_count`.
- **Verification**: `npm run build` ✅, `npm test` 13/13 ✅.

---

### FIX-002 — Analytics range selector does nothing
- **Priority**: P1
- **Files**: `AnalyticsScreen.jsx`, `api.js`, `backend/analytics.py`, `SparkChart.jsx`
- **Root cause**:
  - `useEffect` has empty deps `[]` — never re-fetches on range change
  - `getAnalyticsOverview()` has no range parameter
  - Backend `/api/analytics/overview` has no `period`/`range` query param
  - Chart label "Daily view count · {range}" claims responsiveness that doesn't exist
- **Two options**:
  - **Option A** (correct): Add `period` param to backend endpoint. Pass `range` to `getAnalyticsOverview(range)`. Add `range` to `useEffect` deps. Fix `SparkChart` to not ignore `range` when `sparkData` is present.
  - **Option B** (minimal): Remove range buttons entirely. Change chart label to "Views (last 7 days)". Be honest with users.
- **Recommended**: Option B is faster and more honest. Option A is the full feature.

---

### FIX-003 — No UI for API Keys (backend complete)
- **Priority**: P1
- **Backend**: `backend/app/routers/api_keys.py` — full CRUD, audit logging, Bearer `sdk_...` auth
- **Missing frontend**:
  - No `ApiKeysScreen.jsx`
  - No Sidebar nav item
  - No `api.js` methods: `getApiKeys`, `createApiKey`, `revokeApiKey`, `deleteApiKey`
- **Work required**: Create screen, add 4 api.js methods, add Sidebar entry. High effort but zero backend work.
- **Why P1**: External SDK users cannot authenticate without first creating an API key.

---

### FIX-004 — No UI for Webhooks (backend complete)
- **Priority**: P1
- **Backend**: `backend/app/routers/webhooks.py` — CRUD + test ping + delivery history, SSRF guard
- **Missing frontend**:
  - No `WebhooksScreen.jsx`
  - No Sidebar nav item
  - No api.js methods: `getWebhooks`, `createWebhook`, `updateWebhook`, `deleteWebhook`, `testWebhook`, `getWebhookDeliveries`
- **Note**: Webhook dispatch is already live. Events fire on `viewer.opened` and `analytics.completed`. Users cannot register receivers.

---

### FIX-005 — React 18 / React 19 devDependency mismatch
- **Priority**: P1
- **File**: `frontend/package.json`
- **Change**: `"react": "^19.2.7"` → `"react": "18.3.1"`, `"react-dom": "^19.2.7"` → `"react-dom": "18.3.1"`
- **Why**: Production CDN loads React 18.3.1. Tests run against React 19. Any React 19-only behavior in tests silently diverges from production.
- **Effort**: 2-line change + `npm install` lockfile regeneration.

---

### FIX-006 — AccessLog wrong argument order
- **Priority**: P1
- **File**: `frontend/src/components/access/AccessLog.jsx:15`
- **Before**: `window.SecureDocAPI.getEvents(docId, 50)`
- **After**: `window.SecureDocAPI.getEvents(docId, null, 50)`
- **Why P1**: Silent contract violation. Works today by accident (backend silently ignores invalid UUID). If the default limit changes or this call is copied, it will break silently.

---

### FIX-007 — SparkChart fabricates data when sparkData is empty
- **Priority**: P2
- **File**: `frontend/src/components/analytics/SparkChart.jsx:12-17`
- **Current**: When `sparkData` is empty, generates sine-wave using `Math.sin` seeded from `range`. Renders as a realistic-looking chart with no indicator that data is synthetic.
- **Fix**: Replace synthetic path with an empty state: grey line or "No data yet" label.
- **Effort**: ~10 lines changed in SparkChart.

---

### FIX-008 — StorageScreen header title renders undefined
- **Priority**: P2
- **File**: `frontend/src/components/atoms.jsx:390`
- **Current**: `const titles = { upload: '...', viewer: '...', access: '...', analytics: '...' }` — `storage` and `billing` missing.
- **Fix**: Add `storage: 'Storage', billing: 'Billing'` to the map.
- **Effort**: 1-line change.

---

### FIX-009 — No real-time notification when viewer opens document
- **Priority**: P2 (Sprint 4.6B scope)
- **Backend**: `GET /api/notifications/stream` (SSE), `viewer_session_service.py:116-133` dispatches `viewer.opened`.
- **Missing**: No frontend SSE consumer, no notification bell, no unread count badge.
- **Effort**: High — requires EventSource connection in AppShell, notification state, bell icon component, unread badge.
- **Status**: Planned for Sprint 4.6B. Do not start without approval.

---

### FIX-010 — "Total Views" KPI label is actually today's count
- **Priority**: P2
- **File**: `frontend/src/screens/AnalyticsScreen.jsx:44`
- **Current**: `label: 'Total Views'` renders `overview.total_views_today`
- **Fix**: Change label to `'Views Today'` or `"Today's Views"`.
- **Effort**: 1-line change.

---

### FIX-011 — BillingScreen should surface plan status after Stripe return
- **Priority**: P2
- **Screen**: Billing
- **Context**: User returns from Stripe checkout to `?billing=success`. AppShell navigates to billing screen. `BillingScreen` fetches status on mount — but Stripe webhook processing can lag 2-5 seconds.
- **Fix**: After detecting `?billing=success`, show a brief "Checking your subscription…" spinner, then re-fetch status once after a 2s delay.
- **Effort**: ~20 lines in BillingScreen.

---

### FIX-012 — No way to create a group from the UI
- **Priority**: P2
- **Screen**: Upload → DocRow → Group dropdown
- **Current**: Dropdown shows existing groups for selection, but there is no "New group…" option or group management screen.
- **Fix**: Add "New group…" item at bottom of group dropdown → modal → `POST /api/groups` → refresh dropdown.
- **Effort**: Medium — new modal component + 1 api.js method.

---

### FIX-013 — Audit log backend has no frontend
- **Priority**: P2
- **Backend**: `audit_service.py` — records API key create/revoke/delete/rotate events.
- **Missing**: No read endpoint surfaced in the frontend, no UI screen, no export.
- **Fix**: Add `GET /api/audit-logs` endpoint, `getAuditLogs()` in api.js, and a minimal read-only AuditLogScreen.
- **Effort**: High — needs backend route + frontend screen + Sidebar entry.

---

### FIX-014 — Verify concurrent session tracking (heartbeat vs. event)
- **Priority**: P3
- **File**: `frontend/src/hooks/useViewerSession.js`
- **Question**: Concurrent session limiting (max simultaneous viewers) likely depends on a heartbeat to detect idle tabs. If `POST /api/analytics/events` is the only call made, and if tab inactivity silences events, stale sessions may remain "active" indefinitely.
- **Action**: Read `viewer_session_service.py` concurrent session cleanup logic. Confirm whether events alone are sufficient or a dedicated heartbeat is needed.

---

### FIX-015 — Verify group save fires correctly from DocRow
- **Priority**: P3
- **File**: `frontend/src/components/DocRow.jsx:75`
- **Question**: Group dropdown change handler exists, but the exact PATCH call and payload were not traced. Confirm `group_id` is sent and saved.
- **Action**: Read DocRow in full, trace `onChange` handler to api.js method.

---

### FIX-016 — Plan upload limit should surface as human-readable error
- **Priority**: P3
- **Screen**: Upload
- **Current**: If Free tier limit is enforced in `documents.py`, a failed upload returns a 403 or 422. `UploadProgressPanel` shows a generic error toast.
- **Fix**: Detect `402 Payment Required` or `plan_limit_reached` error code from backend and show "You've reached your Free plan limit. Upgrade to Pro for unlimited documents."
- **Effort**: Small (frontend-only, detect error code, show upgrade prompt).

---

### FIX-017 — AccessLog has no group filter UI
- **Priority**: P3
- **Screen**: Access Control → Access Log tab
- **Note**: Even after FIX-006, the log tab has no group selector. `getEvents(docId, groupId, limit)` supports `groupId` filtering, but `AccessLog.jsx` receives only `docId` as a prop.
- **Fix**: Expose a group filter dropdown in AccessLog and pass selected group_id to `getEvents`.

---

### FIX-018 — SparkChart always shows 7 date labels regardless of range
- **Priority**: P3
- **File**: `frontend/src/components/analytics/SparkChart.jsx`
- **Current**: Chart always renders 7 `x-axis` date labels. If range selector is ever fixed (FIX-002), the label count should match the selected range.
- **Fix**: Derive label count from `range` prop: 7 for 7d, 4 for 30d (weekly), 6 for 90d (biweekly), 24 for 24h (hourly).

---

### FIX-019 — BillingScreen title not in Header titles map
- **Priority**: P3
- **File**: `frontend/src/components/atoms.jsx:390`
- **Note**: Same as FIX-008 (StorageScreen). BillingScreen uses `<Header screen="billing">` but `billing` is not in the titles map. Bundled into the same 1-line fix.

---

### FIX-020 — Quick Share defaults duplicated with AccessScreen initial state
- **Priority**: P3
- **Files**: `frontend/src/components/QuickShareModal.jsx`, `frontend/src/screens/AccessScreen.jsx`
- **Current**: `QUICK_SHARE_DEFAULTS` object in QuickShareModal.jsx duplicates the permissions initial state in AccessScreen.jsx. If one is updated, the other silently diverges.
- **Fix**: Extract shared defaults to `src/constants/linkDefaults.js`. Import from both files.
- **Effort**: ~30 lines moved, zero behavior change.

---

## Sprint Sequencing Recommendation

**Do immediately (1–2 days):**
- FIX-002 (analytics range — Option B: remove buttons) — 1 line
- FIX-005 (react version pin) — 2 lines + lockfile
- FIX-006 (AccessLog arg order) — 1 line
- FIX-008 + FIX-019 (header title map) — 1 line
- FIX-010 (KPI label) — 1 line
- FIX-014 + FIX-015 (verify calls — read-only investigation)

**Sprint 4.6B (planned):**
- FIX-009 (notifications)

**Sprint 4.7 (larger surfaces):**
- FIX-003 (API Keys screen)
- FIX-004 (Webhooks screen)
- FIX-012 (group creation)
- FIX-013 (audit log)

**Background:**
- FIX-007, FIX-011, FIX-016, FIX-017, FIX-018, FIX-020

---

## What Is NOT In This List

These areas were certified as working correctly and need no fix:
- Upload flow (file selection, XHR progress, status polling)
- Viewer rendering, security controls, annotation system
- Access Control policy, link management, feedback, visual annotations
- Quick Share create + copy
- Billing checkout, portal, webhook HMAC verification
- Storage dashboard (post-fix), forecast, retention policy change
- Auth (Supabase sign-in/up, token decode, logout)
- All backend security enforcement (IP, email, domain, expiry, max views, concurrent sessions)
- Stripe integration (checkout, portal, webhook)
- Analytics backend (events POST with rate limiting and session validation)
- API key backend authentication (`sdk_...` prefix auth)
