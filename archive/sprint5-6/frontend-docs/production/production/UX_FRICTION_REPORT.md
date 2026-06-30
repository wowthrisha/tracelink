# UX Friction Report — Sprint 5.5 Production Audit

**Date:** 2026-06-28  
**Sprint:** 5.5  
**Method:** Heuristic evaluation + Playwright visual inspection

---

## Summary

| Friction Level | Count |
|---------------|-------|
| HIGH | 2 |
| MEDIUM | 4 |
| LOW | 4 |

---

## HIGH Friction

### UX-001 — Viewer Sidebar Nav Leads to Dead End
**Screen:** Viewer  
**Friction type:** Confusion / Dead End

When users click "Viewer" in the sidebar before opening a document, they see "Email Verification Required" — an unauthenticated public viewer gate. There is no path forward from this screen for authenticated users. The "Open Document" button is non-functional in this context.

**Friction path:** User wants to view a document → clicks "Viewer" → sees email form → confused → has to guess they need to go back to Upload first.

**Fix:** Show contextual empty state: "Select a document from Upload Dashboard, then click View" with a button that navigates to Upload.

---

### UX-002 — Dashboard Stats Not Reflecting Real Data
**Screen:** Upload Dashboard  
**Friction type:** Loss of trust / Misleading zeros

Four summary metric cards all show "0" while the document list below shows real view counts (47, 12). Users will assume the product is broken or tracking is disabled. The discrepancy between the stat cards and per-document counts creates confusion.

**Friction path:** User uploads and shares documents → comes back to dashboard → sees "TOTAL VIEWS: 0" → files support ticket or assumes product broken.

---

## MEDIUM Friction

### UX-003 — No Loading Timeout or Error Recovery for Storage/Notifications
**Screens:** Storage, Notifications  
**Friction type:** Infinite wait / No recovery

Both screens show "Loading..." with no timeout, no retry button, and no error message. If the API is slow or returns an unexpected response, users are stuck staring at a spinner forever. The 30-second auto-refresh on Notifications makes this worse — it keeps showing "Loading..." on each refresh cycle.

**Fix:** Add a 10s loading timeout that transitions to an error state with a "Retry" button.

---

### UX-004 — Two-Step Revoke + Delete is Undiscoverable
**Screen:** Access Control — Links Tab  
**Friction type:** Discoverability

Permanently deleting a link requires two separate steps: first Revoke, then Delete. While this is a deliberate safety gate, the flow is not communicated anywhere. Users who want to delete a link will click "Revoke" expecting to delete it, then be surprised to see it still listed as REVOKED with a new "Delete" button.

**Improvement:** Add a tooltip or confirmation message on Revoke: "This will revoke access. You can permanently delete the link afterward."

---

### UX-005 — Link Name Field Buried in Corner of Create Tab
**Screen:** Access Control — Create Link  
**Friction type:** Low discoverability of key feature

The LINK NAME field is placed at the bottom-right of the permissions grid — the last visible item before the action buttons. Users scanning the form top-to-bottom will see Authentication → Domains → Emails → Access Limits → Permissions before reaching the name field. The most user-friendly action (naming the link) is the least prominent.

**Improvement:** Move LINK NAME to the top of the Create Link form, above Authentication, as the primary first field.

---

### UX-006 — Analytics Showing All-Zero Metrics Destroys Trust
**Screen:** Analytics  
**Friction type:** Loss of trust

The Analytics screen's six summary cards all show 0/—. Even if the chart renders correctly, users scanning the page see what appears to be an empty analytics product. This is especially damaging for a product that sells itself on viewer analytics.

---

## LOW Friction

### UX-007 — Embed Code Always Visible (Low Signal-to-Noise on Links Tab)
**Screen:** Access Control — Links Tab  
**Friction type:** Information overload

Every link card on the Links tab shows a full `<iframe>` embed code block by default. For users who don't need embedding, this is visual noise. The embed code takes up ~4 lines per card and pushes the second link below the fold.

**Improvement:** Collapse embed code behind a "Show Embed" toggle button by default.

---

### UX-008 — Webhook "PAUSED" State Has Ambiguous Label
**Screen:** Webhooks  
**Friction type:** Misleading state label

A webhook labeled "PAUSED" with a "Resume" button implies the user previously paused it. If it was never paused (just newly created or active), this label is misleading. Users may not know the difference between "PAUSED" and "INACTIVE" or "PENDING".

---

### UX-009 — Billing Screen Lacks Usage Meter
**Screen:** Billing  
**Friction type:** Missing information

The Billing screen shows the current plan's limits (Up to 10 uploads, etc.) but does not show current usage against those limits (e.g. "3 of 10 documents used"). Users cannot see how close they are to plan limits.

**Improvement:** Add a usage bar for document count and storage consumption.

---

### UX-010 — Inline Rename Pencil Icon Not Labeled
**Screen:** Access Control — Links Tab  
**Friction type:** Low discoverability

The inline rename pencil icon (✎) next to link URLs is the correct affordance but has no tooltip or label. First-time users won't know it triggers a rename input. The icon is small (using the CSS `transform: scale` approach) and easily missed.

**Improvement:** Add `title="Rename link"` tooltip to the pencil icon.

---

## Positive UX Observations

| Feature | UX Verdict |
|---------|-----------|
| Edit modal completeness | Excellent — all 9 fields including max_concurrent_sessions |
| Revoked link visual differentiation | Clear — REVOKED badge + "link revoked" text + grey styling |
| Delete confirmation dialog | Appropriate — window.confirm() with clear warning text |
| Watermark toggle default ON | Good security-first default |
| PASSWORD badge on links | Clear at-a-glance security indicator |
| "All systems operational" in sidebar footer | Trust signal |
| Embed code always available | Power user feature, but see UX-007 |
| Navigation sidebar organization | Clear grouping: SECURITY / INSIGHTS / DEVELOPERS / WORKSPACE / ACCOUNT |
