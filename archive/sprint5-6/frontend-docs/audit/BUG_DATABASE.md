# Bug Database — Sprint 5.5 Production Audit

**Date:** 2026-06-28  
**Audit Sprint:** 5.5  
**Total Bugs:** 7  
**Critical:** 0 | **High:** 1 | **Medium:** 3 | **Low:** 3

---

## BUG-001 — Upload Dashboard Stats Always Show Zero
**Severity:** MEDIUM  
**Screen:** Upload Dashboard (`upload`)  
**Screenshot:** `001_upload.png`

**Description:**  
The four summary stat cards (TOTAL DOCUMENTS, ACTIVE SHARES, TOTAL VIEWS, BLOCKED ATTEMPTS) all display "0" even when the document list below shows 2 ready documents with 47 and 12 views respectively. The document list renders correctly (showing view counts per document), but the aggregate dashboard metrics are stuck at zero.

**Root Cause Hypothesis:**  
UploadScreen calls a separate summary analytics endpoint (likely `/api/analytics/summary` or `/api/documents/stats`) that returns empty/zero data. The per-document data from `/api/documents` loads correctly but feeds only the list, not the stat cards.

**Impact:** Users see misleading 0-view counts on their dashboard even when documents have significant engagement. Confusing for new users who may think sharing isn't working.

**Reproduction:** Navigate to Upload Dashboard after uploading documents that have been viewed.

---

## BUG-002 — Analytics Dashboard Counters All Zero
**Severity:** MEDIUM  
**Screen:** Analytics (`analytics`)  
**Screenshot:** `008_analytics.png`

**Description:**  
The Analytics screen's six metric cards (TOTAL VIEWS, ACTIVE LINKS, AVG SESSION, BLOCKED ATTEMPTS, ACTIVE DOCS, COMPLETION) all show "0" or "—" while the chart (Views Over Time) renders correctly with actual data points, and the Document Performance table shows Q2_Financial_Report.pdf.

**Root Cause Hypothesis:**  
The summary stats come from a different API response field or sub-endpoint than the chart data. The chart data renders correctly from `/api/analytics` but the metric cards read fields that may be missing or named differently in the current response schema.

**Impact:** The analytics overview appears broken at a glance. Users see an empty headline but have to scroll to the chart to see any meaningful data.

---

## BUG-003 — Viewer Shows Email Gate When Loaded Without Document Context
**Severity:** HIGH  
**Screen:** Viewer (`viewer`)  
**Screenshot:** `016_viewer.png`

**Description:**  
Clicking the "Viewer" nav item in the sidebar (when no document is currently active) shows a centered "Email Verification Required — Enter your email address to verify you have access to this document" dialog with an "Open Document" button. This is the public-link email gate being rendered for a null/undefined document.

**Root Cause Hypothesis:**  
`ViewerScreen` is rendered with `doc={activeDoc}` where `activeDoc` is null when navigated directly. The viewer then falls into its email-gate code path which is intended for anonymous public viewers, not authenticated admin users.

**Impact:** Clicking "Viewer" in the sidebar produces a confusing, dead-end screen. A user who navigates there without first opening a document from Upload Dashboard sees an email verification form that doesn't apply to them.

**Recommended Fix:**  
Add a guard in `AppShell.jsx`: if `screen === 'viewer' && !activeDoc`, show an empty state ("Select a document from Upload to view it") instead of rendering `ViewerScreen` with null doc.

---

## BUG-004 — Storage Dashboard Stuck on Loading
**Severity:** MEDIUM  
**Screen:** Storage (`storage`)  
**Screenshot:** `009_storage.png`

**Description:**  
The Storage screen shows "Loading..." indefinitely. The screen component calls `getStorageDashboard()` and `getStorageForecast()` on mount, but the screen never transitions from loading to data state.

**Root Cause Hypothesis:**  
In the test environment, the storage dashboard API call resolved but the response shape didn't match the component's expectations, leaving the component in a loading state. In production this should work, but if the backend returns `null` or a different shape for any field, the component may fail silently. Recommend adding error boundary/fallback for the storage dashboard.

**Environment:** Confirmed in Playwright mock; production behavior requires verification.

---

## BUG-005 — Notifications Screen Stuck on Loading (0 events)
**Severity:** LOW  
**Screen:** Notifications (`notifications`)  
**Screenshot:** `014_notifications.png`

**Description:**  
Notifications screen displays "Loading..." and shows "0 events" in the counter. The Activity Feed description says it "refreshes every 30 seconds" but the initial load never completes.

**Root Cause Hypothesis:**  
`NotificationsScreen` calls an activity feed endpoint (likely `/api/admin/audit-log` or `/api/activity`) that was not intercepted in the mock environment. In production, if this endpoint is slow or returns 0 events for a new account, users see "Loading..." forever instead of a clean empty state.

---

## BUG-006 — Webhook Active=True Displayed as "PAUSED"
**Severity:** LOW  
**Screen:** Webhooks (`webhooks`)  
**Screenshot:** `011_webhooks.png`

**Description:**  
The webhook for `https://acme.io/webhooks/securedoc` is returned by the API with `active: true` but the UI renders it with a "PAUSED" status badge instead of "ACTIVE".

**Root Cause Hypothesis:**  
The `WebhooksScreen` component may use a different field or threshold to determine active vs paused status — perhaps checking `last_delivery_at` recency or a separate `paused` boolean field rather than the `active` boolean. Alternatively the mock response structure may differ from what the component expects.

**Impact:** If a webhook is genuinely active but shown as PAUSED, users may attempt to "Resume" a running webhook, potentially causing duplicate deliveries.

---

## BUG-007 — Link Name Input Placeholder Text Truncated
**Severity:** LOW  
**Screen:** Access Control — Create Link (`access`)  
**Screenshot:** `002_access_create_tab.png`

**Description:**  
The "LINK NAME" field in the Create Link tab (sidebar column) truncates its placeholder text. The placeholder reads `e.g. Client Review, Tende...` instead of the full `e.g. Client Review, Tender Submission`. The input is too narrow for the placeholder at 1400px viewport width.

**Root Cause Hypothesis:**  
The Link Name field is placed in a narrow sidebar column (~170px) in the permissions grid. The placeholder text at `fontSize: 12` still overflows.

**Impact:** Minor — cosmetic only. The field is fully functional, only the placeholder is clipped.

**Recommended Fix:**  
Shorten placeholder to `e.g. Client Review` or increase the sidebar field width.

---

## Summary Table

| Bug ID | Severity | Screen | Title | Status |
|--------|----------|--------|-------|--------|
| BUG-001 | MEDIUM | Upload | Stats cards always show 0 | OPEN |
| BUG-002 | MEDIUM | Analytics | All metric counters show 0 | OPEN |
| BUG-003 | HIGH | Viewer | Email gate shown for authenticated user without doc | OPEN |
| BUG-004 | MEDIUM | Storage | Dashboard stuck loading | NEEDS PROD VERIFY |
| BUG-005 | LOW | Notifications | Activity feed stuck loading | NEEDS PROD VERIFY |
| BUG-006 | LOW | Webhooks | Active webhook shown as PAUSED | OPEN |
| BUG-007 | LOW | Access Control | Link name placeholder truncated | OPEN |
