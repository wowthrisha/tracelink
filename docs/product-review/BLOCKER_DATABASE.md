# SecureDoc Blocker Database
**Date:** 2026-06-30  
**Reviewer Persona:** QA Lead + Principal Backend Engineer  
**Definition:**  
- **Critical Blocker:** Prevents the product from being used for its stated purpose in a given context  
- **High:** Causes significant user harm, data loss risk, or enterprise deal failure  
- **Medium:** Causes user frustration or workarounds but doesn't break core functionality  

---

## Critical Blockers

### BLOCK-001 — Organizations: Member Management Completely Non-Functional

**Screen:** OrgsScreen.jsx  
**Category:** Feature gap — critical product failure  
**Description:** The Organizations feature exists in navigation, has a backend with full CRUD + RBAC, but the frontend exposes zero member management capability. Members panel is read-only. There is no invite, role change, or remove action anywhere in the UI.  
**Backend API exists:** YES — POST /api/orgs/{id}/members, PATCH /api/orgs/{id}/members/{uid}, DELETE /api/orgs/{id}/members/{uid}  
**Additional blockers within BLOCK-001:**
- Even if frontend were built, `add_member` requires a UUID, not an email address
- No invitation email system at backend level
- No pending invite state  

**User impact:** Teams cannot collaborate. Organizations cannot function.  
**Enterprise blocker:** YES — any multi-user enterprise use case is impossible.  
**Fix estimate:** 2–3 weeks (backend email invite system + frontend UI)

---

### BLOCK-002 — Audit Log: No Filter or Export

**Screen:** AuditLogScreen.jsx  
**Category:** Missing feature — compliance critical  
**Description:** The audit log shows all events in reverse-chronological order with no filter (date, actor, event type) and no export capability. With any meaningful usage, the log becomes impossible to use for compliance investigations.  
**User impact:** Cannot answer compliance questions like "show me all delete actions by user X in Q1 2026"  
**Enterprise blocker:** YES — SOC 2, GDPR, and HIPAA compliance reviews will reject.  
**Fix estimate:** 1 week (add query params to backend endpoint + filter UI + CSV export)

---

### BLOCK-003 — "⟳ New Share Link" Creates Zero-Restriction Link Without Confirmation

**Screen:** AccessScreen.jsx:328-341  
**Category:** Unintended data exposure risk  
**Description:** The "⟳ New Share Link" button on the Create Link policy tab creates a share link with NO restrictions instantly — no password, no expiry, no IP restriction, no allowed emails, unlimited views. This bypasses the entire policy form the user just configured.  

```jsx
<Btn variant="secondary" disabled={creating || !docId} onClick={async () => {
  setCreating(true);
  try {
    await window.SecureDocAPI.createLink({ document_id: docId });
    // Only passes document_id — all other fields are defaults (unrestricted)
```

A user who clicks this button thinking it's "generate another link with the same settings" accidentally creates a publicly accessible unrestricted link to a confidential document.  
**User impact:** Accidental data exposure to anyone with the link  
**Enterprise blocker:** YES — document DRM policies can be trivially bypassed  
**Fix estimate:** 1 hour (remove button or add confirmation + show "unrestricted" warning)

---

### BLOCK-004 — Organization Delete: No Confirmation Dialog

**Screen:** OrgsScreen.jsx  
**Category:** Catastrophic irreversible action without friction  
**Description:** Deleting an organization fires immediately with no confirmation modal. Behavior on cascade delete of org-scoped documents is unknown.  
**User impact:** Accidental org deletion with no recovery path  
**Enterprise blocker:** YES — enterprise customers require confirmation for account-level destructive operations  
**Fix estimate:** 2 hours

---

### BLOCK-005 — Group Delete: No Confirmation Dialog

**Screen:** UploadScreen.jsx  
**Category:** Destructive action without friction  
**Description:** Deleting a document group fires immediately with no confirmation modal. While documents may not be deleted (only the group concept), the group color, membership, and organization information is lost permanently.  
**User impact:** Accidental group deletion with no undo  
**Fix estimate:** 2 hours

---

### BLOCK-006 — Session Blur: No Explanation Shown to Viewer

**Screen:** ViewerScreen.jsx  
**Category:** Viewer experience failure  
**Description:** When a session is invalidated (link revoked, max views reached, link expired, max concurrent sessions hit), the document blurs. The viewer sees a blurred page with no explanation of why or what to do.  
**User impact:** Viewers think the product is broken. Support tickets generated. Enterprise client shows a demo with an expired link and looks incompetent.  
**Fix estimate:** 2 hours (add session state message overlay above blur)

---

### BLOCK-007 — No URL Routing: Page Refresh Loses All Navigation State

**Screen:** AppShell.jsx  
**Category:** Architecture gap  
**Description:** The app has no URL routing. Every URL is the base URL. Refreshing the page always returns to the Upload (Documents) screen. Deep linking, sharing a specific document's analytics, bookmarking a screen — all impossible.  
**User impact:** Productivity loss on every refresh; support URL sharing impossible; navigation state cannot be restored  
**Enterprise blocker:** YES — enterprise admins expect deep links in support tickets  
**Fix estimate:** 1–2 weeks (adopt React Router or custom hash-based routing)

---

### BLOCK-008 — Link Revoke (Single): No Confirmation

**Screen:** AccessScreen.jsx:393  
**Category:** Irreversible action without friction  
**Description:** The "Revoke" button for individual share links fires immediately. Revoking a link terminates all active sessions for that link. A viewer mid-session is kicked out without warning. There is NO confirmation, unlike "Revoke All Access" which has an excellent modal.  
**User impact:** Accidental revocation during active customer viewing session  
**Fix estimate:** 1 hour

---

### BLOCK-009 — API Key Delete/Revoke: No Confirmation

**Screen:** ApiKeysScreen.jsx:154-161, 144-151  
**Category:** Irreversible actions without friction  
**Description:** Both "Revoke" and "Delete" on API keys fire immediately. Revoking a key that is currently in production use by an integration breaks that integration instantly.  
**User impact:** Production integration downtime from accidental revoke  
**Fix estimate:** 1 hour

---

### BLOCK-010 — Webhook Delete: No Confirmation

**Screen:** WebhooksScreen.jsx:208-215  
**Category:** Irreversible action without friction  
**Description:** "Delete" on a webhook fires immediately. Deleting a webhook that has a delivery history in a production integration removes all history and breaks the integration.  
**Fix estimate:** 1 hour

---

### BLOCK-011 — Free Plan Document Limit: No UI Enforcement at Upload Time

**Screen:** UploadScreen.jsx  
**Category:** User experience gap + billing issue  
**Description:** The free plan allows up to 10 documents. When this limit is reached, the upload attempt fails with a server error. There is no counter visible ("7 / 10 documents used"), no warning as the user approaches the limit, and no upgrade prompt when the limit is hit — just a generic error toast.  
**User impact:** Users hit a wall with no context and no clear next step. Conversion opportunity missed.  
**Fix estimate:** 1 day (add document count to stats bar, check against limit before upload)

---

## High Priority Blockers

### BLOCK-012 — Audit Log: No Export Capability

Same as BLOCK-002 but specifically: even without filters, having a CSV export would allow external filtering. The absence of export is a separate deliverable from the filter UI.  
**Fix estimate:** 2 hours (add CSV export button calling the API with all events)

---

### BLOCK-013 — Analytics: No Date Range Picker

**Screen:** AnalyticsScreen.jsx  
**Category:** Feature gap  
**Description:** All analytics are fixed to "last 7 days" (sparkline) or "all-time aggregates". There is no way to view analytics for a custom date range. A user preparing a board report or reviewing a campaign period cannot query historical data.  
**Fix estimate:** 1 week (add date picker, pass date range params to API endpoints)

---

### BLOCK-014 — DRM Block Without Explanation

**Screen:** ViewerScreen.jsx (via useViewerSession DRM enforcement)  
**Category:** Viewer experience failure  
**Description:** When print, copy, right-click is blocked, the action is silently prevented. Viewers receive no message explaining why the action is blocked. They experience the product as "broken" rather than "secured by policy."  
**Fix estimate:** 3 hours (add toast or overlay: "Printing is disabled for this document by its owner")

---

### BLOCK-015 — AccessScreen Feedback Empty State Is Misleading

**Screen:** AccessScreen.jsx:576  
**Category:** Incorrect copy — causes wrong user action  
**Description:** When there is no feedback, the screen shows: "No feedback yet — viewers need can_annotate permission enabled". This is wrong — text comments (type=comment) do not require can_annotate. Setting can_annotate enables VISUAL annotations (highlight, draw, rectangle, arrow). A document owner following this instruction would enable visual annotations expecting to receive text comments.  
**Fix estimate:** 30 minutes (fix empty state copy)

---

### BLOCK-016 — Notification Read State in localStorage

**Screen:** NotificationsScreen.jsx  
**Category:** State management gap  
**Description:** "Mark all read" stores a timestamp in localStorage. Opening the app in a new browser, incognito, or on a different device resets all notifications to "unread." For enterprise admins using multiple workstations, this means permanently having unread notifications.  
**Fix estimate:** 1 day (persist read state server-side in a user preferences table)

---

### BLOCK-017 — Single Link Revoke Uses `window.confirm()`

**Screen:** AccessScreen.jsx:398  
**Category:** Inconsistent pattern + accessibility failure  
**Description:** The delete action for revoked links uses `window.confirm()` — a browser native dialog — while every other modal in the app is a custom Card-based component. `window.confirm()` is not accessible (screen readers), not styleable, and inconsistent with the design system.  
**Fix estimate:** 1 hour

---

### BLOCK-018 — Webhook Event Coverage: Only 3 of Expected 15 Events

**Screen:** WebhooksScreen.jsx  
**Category:** Feature incompleteness  
**Description:** Only `document.processed`, `link.viewed`, `analytics.completed` are available. Missing events that integrations would reasonably need: `link.created`, `link.revoked`, `link.updated`, `document.deleted`, `document.uploaded`, `org.member_added`, `org.member_removed`, `api_key.created`, `api_key.revoked`.  
**Fix estimate:** 1 week (add event firing in backend services, add events to webhook frontend)

---

### BLOCK-019 — Cannot Edit Webhook URL or Events After Registration

**Screen:** WebhooksScreen.jsx  
**Category:** Feature gap  
**Description:** There is no edit capability for webhooks. Changing the URL requires deleting the webhook (and all delivery history) and recreating it. This is a significant operational burden.  
**Fix estimate:** 1 day (add edit modal using existing `updateWebhook` API)

---

### BLOCK-020 — Cannot Edit API Key Name or Scopes After Creation

**Screen:** ApiKeysScreen.jsx  
**Category:** Feature gap  
**Description:** There is no way to edit an API key's name or add/remove scopes. Must delete and recreate — which breaks any running integration using the old key.  
**Fix estimate:** 1 day (add edit modal for name/scopes if backend supports PATCH on API keys)

---

## Blocker Summary

| ID | Severity | Fix Effort | Category |
|----|----------|-----------|----------|
| BLOCK-001 | Critical | 2–3 weeks | Org member management |
| BLOCK-002 | Critical | 1 week | Audit log filter/export |
| BLOCK-003 | Critical | 1 hour | Accidental data exposure |
| BLOCK-004 | Critical | 2 hours | Org delete confirmation |
| BLOCK-005 | Critical | 2 hours | Group delete confirmation |
| BLOCK-006 | Critical | 2 hours | Session blur explanation |
| BLOCK-007 | Critical | 1–2 weeks | URL routing |
| BLOCK-008 | High | 1 hour | Link revoke confirmation |
| BLOCK-009 | High | 1 hour | API key revoke/delete confirmation |
| BLOCK-010 | High | 1 hour | Webhook delete confirmation |
| BLOCK-011 | High | 1 day | Free plan limit enforcement |
| BLOCK-012 | High | 2 hours | Audit log export |
| BLOCK-013 | High | 1 week | Analytics date range |
| BLOCK-014 | High | 3 hours | DRM silent block |
| BLOCK-015 | High | 30 min | Feedback empty state copy |
| BLOCK-016 | High | 1 day | Notification read state |
| BLOCK-017 | High | 1 hour | window.confirm pattern |
| BLOCK-018 | High | 1 week | Webhook events |
| BLOCK-019 | High | 1 day | Webhook edit |
| BLOCK-020 | High | 1 day | API key edit |

**Total critical: 7 | Total high: 13 | Total: 20 documented blockers**

---

*Blocker database complete — 2026-06-30*
