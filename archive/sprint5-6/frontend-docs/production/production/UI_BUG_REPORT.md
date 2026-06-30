# UI Bug Report — Sprint 5.5 Production Audit

**Date:** 2026-06-28  
**Sprint:** 5.5  
**Auditor:** Principal QA / SDET  
**Method:** Playwright automated + visual screenshot inspection  
**Severity Scale:** CRITICAL > HIGH > MEDIUM > LOW

---

## Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 1 |
| MEDIUM | 3 |
| LOW | 3 |
| **Total** | **7** |

---

## HIGH Severity

### UI-BUG-003 — Viewer Shows Email Verification Gate for Authenticated Users
**Screen:** Viewer  
**Screenshot:** `016_viewer.png`  
**Reproducible:** YES — navigate to Viewer from sidebar without opening a document first

**Description:**  
When an authenticated user clicks "Viewer" in the sidebar without first opening a document from the Upload Dashboard, the Viewer screen shows:

> *"Email Verification Required — Enter your email address to verify you have access to this document"*

along with an "Open Document" button. This is the **public anonymous viewer email gate** being displayed to an authenticated owner. The viewer is receiving `doc={null}` and falling into the unauthenticated code path.

**Visual Evidence:**  
`016_viewer.png` — Authenticated session (demo@securedoc.io in sidebar footer), yet Email Verification Required dialog occupies the full content area.

**Impact:**  
- Confusing UX for authenticated users
- Dead-end state — the "Open Document" button has no valid context
- Could be reported as a bug by users who discover this path

**Fix:**  
`AppShell.jsx` line 147 — add guard:
```jsx
{screen === 'viewer' && !activeDoc && (
  <div style={{...emptyState}}>Select a document from Upload Dashboard to view it.</div>
)}
{screen === 'viewer' && activeDoc && (
  <ViewerErrorBoundary><ViewerScreen doc={activeDoc} ... /></ViewerErrorBoundary>
)}
```

---

## MEDIUM Severity

### UI-BUG-001 — Upload Dashboard Stats Cards Stuck at Zero
**Screen:** Upload Dashboard  
**Screenshot:** `001_upload.png`  
**Reproducible:** YES — confirmed on every load

**Description:**  
The four aggregate stat cards show:
- TOTAL DOCUMENTS: 0 (actual: 2 ready)
- ACTIVE SHARES: 0
- TOTAL VIEWS: 0 (actual: 59 across docs)
- BLOCKED ATTEMPTS: 0

The document list directly below these cards correctly shows Q2_Financial_Report.pdf (47 views) and Vendor_Contract_v3.pdf (12 views). The per-document data loads correctly; only the stat card aggregates are zero.

**Fix:** Verify the summary stats API call endpoint and response shape in `UploadScreen.jsx`.

---

### UI-BUG-002 — Analytics Dashboard Metric Cards All Zero
**Screen:** Analytics  
**Screenshot:** `008_analytics.png`  
**Reproducible:** YES

**Description:**  
All six summary metric cards show zero or dash:
- TOTAL VIEWS: 0
- ACTIVE LINKS: 0
- AVG SESSION: —
- BLOCKED ATTEMPTS: 0
- ACTIVE DOCS: 0
- COMPLETION: —

The Views Over Time line chart **does** render with real data points. The Document Performance table shows Q2_Financial_Report.pdf correctly. Only the top-level metric cards are empty.

**Fix:** Verify response field names for the analytics summary endpoint in `AnalyticsScreen.jsx`.

---

### UI-BUG-004 — Storage Dashboard Shows Loading Indefinitely
**Screen:** Storage  
**Screenshot:** `009_storage.png`  
**Reproducible:** Confirmed in test environment; verify in production

**Description:**  
Storage screen renders the layout frame correctly but shows "Loading..." in the content area with no timeout, fallback, or error message. The screen calls `getStorageDashboard()` and `getStorageForecast()` on mount.

**Fix:** Add loading timeout + error fallback to `StorageScreen.jsx`. If data doesn't arrive within 5s, show an error state with retry button.

---

## LOW Severity

### UI-BUG-005 — Notifications Activity Feed Stuck Loading
**Screen:** Notifications  
**Screenshot:** `014_notifications.png`  
**Counter shows:** 0 events

**Description:**  
Notifications screen header says "0 events" and the RECENT ACTIVITY section shows "Loading..." indefinitely. No error state is shown.

---

### UI-BUG-006 — Webhook Shown as PAUSED When Active
**Screen:** Webhooks  
**Screenshot:** `011_webhooks.png`

**Description:**  
Webhook at `https://acme.io/webhooks/securedoc` has `active: true` in the API response but the UI renders a "PAUSED" badge. The action buttons show "History / Test / **Resume** / Delete" — implying the user needs to resume a webhook that is already running.

**Impact:** Could lead users to double-activate running webhooks.

---

### UI-BUG-007 — Link Name Placeholder Text Truncated
**Screen:** Access Control — Create Link  
**Screenshot:** `002_access_create_tab.png`

**Description:**  
The LINK NAME input field in the Permissions card sidebar shows `e.g. Client Review, Tende...` — the placeholder text is clipped at the field's right edge. Full placeholder: `e.g. Client Review, Tender Submission`.

**Fix:** Shorten placeholder to `e.g. Client Review` or increase field width in the sidebar column.

---

## Screens with No UI Bugs

| Screen | Status |
|--------|--------|
| Access Control — Create Link | ✅ Clean (BUG-007 cosmetic only) |
| Access Control — Links Tab | ✅ Clean |
| Access Control — Edit Modal | ✅ Clean |
| Access Control — View History | ✅ Clean |
| Access Control — Feedback | ✅ Clean |
| Webhooks | ✅ Functional (BUG-006 display) |
| Organizations | ✅ Clean |
| Billing | ✅ Clean |
