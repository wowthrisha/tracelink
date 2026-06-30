# SecureDoc Priority Fix List
**Date:** 2026-06-30  
**Synthesized from:** BLOCKER_DATABASE.md, PRODUCT_REVIEW.md, UX_REVIEW.md, WORKFLOW_GAPS.md  
**Persona:** SaaS Founder + Product PM — deciding what ships in the next 3 sprints

---

## Prioritization Criteria

Each fix is scored on:
1. **User harm** (1–5): How badly does this hurt users?
2. **Blast radius** (1–5): How many users are affected?
3. **Fix effort** (S/M/L/XL): Relative engineering cost
4. **Enterprise blocker** (Y/N): Would this prevent closing enterprise deals?

High user harm × high blast radius × low effort = fix first.

---

## Sprint A — "Confidence Sprint" (2–3 days of focused work)

These are all high-impact, low-effort fixes. Each is a few lines of code or a small component addition. Fixing all 8 in this sprint transforms perceived quality significantly.

### A-1 — Add confirmation modals to all destructive actions

**Files to change:** OrgsScreen.jsx, UploadScreen.jsx, ApiKeysScreen.jsx, WebhooksScreen.jsx, AccessScreen.jsx  
**What to do:** Add a `<Modal>` confirmation before: delete org, delete group, revoke API key, delete API key, delete webhook. Replace `window.confirm()` with Modal in link delete.  
**User harm:** 5/5 — causes irreversible data loss  
**Effort:** S (template exists — copy the pattern from the "Revoke All Access" modal)  
**Enterprise blocker:** YES

### A-2 — Fix the "⟳ New Share Link" danger button

**File:** AccessScreen.jsx:328–341  
**What to do:** Either (a) remove the button entirely, or (b) add a warning before it fires: "This creates a link with no restrictions. Anyone with the link can access the document without a password or expiry." Require a click to confirm.  
**User harm:** 5/5 — accidental data exposure  
**Effort:** S  
**Enterprise blocker:** YES

### A-3 — Add session-invalid explanation to viewer blur

**File:** ViewerScreen.jsx, useViewerSession hook  
**What to do:** When the session is blurred (revoked, expired, max views, max sessions), show a message overlay on the blurred document explaining the reason. Map session state to human-readable explanation.  
**User harm:** 4/5 — confused viewers create support tickets  
**Effort:** S  
**Enterprise blocker:** YES (customer demos show a blurred page)

### A-4 — Add DRM block explanation

**File:** ViewerScreen.jsx (Ctrl+P, Ctrl+C, right-click handlers)  
**What to do:** When a DRM-blocked action is attempted (print, copy, right-click), show a brief toast: "Printing is disabled for this document." / "Copying is not permitted for this document."  
**User harm:** 3/5 — viewers think the product is broken  
**Effort:** S

### A-5 — Fix feedback empty state copy

**File:** AccessScreen.jsx:576  
**What to do:** Change "No feedback yet — viewers need can_annotate permission enabled" to "No feedback yet. Viewers can leave comments when they view this document."  
**User harm:** 3/5 — causes wrong user behavior  
**Effort:** XS (one line change)

### A-6 — Add `aria-label` to all icon-only buttons

**Files:** All screen files + atoms.jsx  
**What to do:** Add `aria-label` prop to all `✕`, `⧉`, `↗`, `✎` buttons.  
**User harm:** 3/5 (affects screen reader users)  
**Effort:** S

### A-7 — Add `aria-live="polite"` to toast container

**File:** contexts/toast.jsx  
**What to do:** Wrap the toast container in a `div` with `role="status"` and `aria-live="polite"`.  
**User harm:** 4/5 (affects screen reader users — toasts are the primary feedback mechanism)  
**Effort:** XS

### A-8 — Fix org name display in Storage screen

**File:** StorageScreen.jsx:97  
**What to do:** Change `org.org_id === '_personal' ? 'Personal' : org.org_id.slice(0, 8) + '…'` to use `org.org_name` from the dashboard response.  
**User harm:** 2/5 — confusing for multi-org users  
**Effort:** XS (if `org_name` is in the API response; may require backend update)

---

## Sprint B — "Core UX Sprint" (1 week)

These are medium-effort, high-value fixes that address the most visible workflow gaps.

### B-1 — Add document sort controls to Upload screen

**File:** UploadScreen.jsx  
**What to do:** Add column-header click handlers for Name, Date Uploaded, Size, Views. Default sort: Date Uploaded descending (most recent first).  
**User harm:** 4/5 for power users with 20+ documents  
**Effort:** M

### B-2 — Add single-link revoke confirmation

**File:** AccessScreen.jsx  
**What to do:** Wrap the single "Revoke" link action in a confirmation modal similar to the "Revoke All Access" pattern but less alarming copy ("Revoke this share link? Active viewers will be disconnected.")  
**User harm:** 4/5 — accidental revocation mid-session  
**Effort:** S

### B-3 — Analytics date range picker

**File:** AnalyticsScreen.jsx  
**What to do:** Add a date range selector (7d / 30d / 90d / Custom) in the Header area. Pass `start_date`/`end_date` to all three analytics API calls.  
**User harm:** 4/5 — product is nearly unusable for reporting without this  
**Effort:** M  
**Enterprise blocker:** YES

### B-4 — Define metric tooltips (Risk, Completion, Avg Session)

**File:** AnalyticsScreen.jsx + atoms.jsx (RiskBadge)  
**What to do:** Add `title` tooltip (and eventually a `?` icon with popover) to the Completion KPI, Risk badge, and Avg Session KPI explaining each metric.  
**User harm:** 3/5 — enterprise buyers block on undefined metrics  
**Effort:** S

### B-5 — Audit log date and action type filters

**File:** AuditLogScreen.jsx + backend analytics router  
**What to do:** Add date-from, date-to, and action-type filter controls. Pass to `getAuditLog()` API call. Add CSV export button.  
**User harm:** 5/5 for any compliance use case  
**Effort:** M  
**Enterprise blocker:** YES

### B-6 — Add webhook edit modal

**File:** WebhooksScreen.jsx  
**What to do:** Add "Edit" button to each webhook. Open EditWebhookModal with URL, description, events. Call `updateWebhook` API.  
**User harm:** 3/5  
**Effort:** M

### B-7 — Add API key name edit

**File:** ApiKeysScreen.jsx  
**What to do:** Add "Edit" (pencil) inline or modal for API key name. Scope editing is harder (requires secret rotation consideration) and can be deferred.  
**User harm:** 2/5  
**Effort:** S

### B-8 — Free plan document counter in Upload screen

**File:** UploadScreen.jsx  
**What to do:** Show "X / 10 documents" in the stats bar for free plan users. When at 9/10, show warning. When limit hit, show upgrade prompt instead of generic error.  
**User harm:** 4/5 — kills conversion on plan limit  
**Effort:** M

---

## Sprint C — "Enterprise Sprint" (2–3 weeks)

These are larger features required for enterprise go-to-market.

### C-1 — Organization Member Management

**Files:** OrgsScreen.jsx + backend (email invite system)  
**What to do:**
1. Add "Invite Member" button to OrgsScreen MembersPanel
2. Create InviteMemberModal with email field and role selector
3. Backend: add email-based invite API (look up user by email or send invite email)
4. Add "Change Role" action to member rows
5. Add "Remove Member" action to member rows with confirmation
**User harm:** 5/5 — organizations are non-functional  
**Effort:** XL  
**Enterprise blocker:** YES

### C-2 — URL Routing

**Files:** AppShell.jsx + all screens  
**What to do:** Implement hash-based or History API routing. Each screen gets a URL: `#/documents`, `#/access/doc-id`, `#/analytics`, etc. Preserve nav state across refresh.  
**User harm:** 4/5  
**Effort:** L  
**Enterprise blocker:** YES

### C-3 — SAML Configuration UI

**Files:** OrgsScreen.jsx + new SamlConfigModal  
**What to do:** Expose `saml_domain` field in org settings. Add SAML configuration form with ACS URL, Entity ID, IdP metadata URL.  
**User harm:** 3/5 (only for enterprise SSO use cases)  
**Effort:** L  
**Enterprise blocker:** YES

### C-4 — API Key Rotation Flow

**Files:** ApiKeysScreen.jsx + backend  
**What to do:** Add "Rotate" action that: (1) creates a new key with same name + scopes, (2) shows new key once, (3) revokes old key only after user confirms. This enables zero-downtime rotation.  
**User harm:** 3/5  
**Effort:** M

### C-5 — Email Notifications

**Files:** Backend notification service + user preferences API  
**What to do:** Add notification preference settings (which events trigger email). Send email via configured SMTP/Sendgrid when events occur.  
**User harm:** 3/5 — in-app only means admins miss activity  
**Effort:** L

### C-6 — Mobile Responsive View (Viewer)

**Files:** ViewerScreen.jsx + AppShell.jsx  
**What to do:** Remove the hard 768px block. Implement a responsive viewer layout with simplified toolbar. (Or: implement viewer-only mobile support — keep desktop-only block for admin screens.)  
**User harm:** 4/5 — blocks all mobile users  
**Effort:** L

---

## Fix Timeline Summary

| Sprint | Duration | Key Deliverables |
|--------|----------|-----------------|
| Sprint A | 2–3 days | Confirmation modals (8 locations), danger button fix, session blur message, DRM feedback, accessibility quick wins |
| Sprint B | 1 week | Sort controls, analytics date range, audit filters + export, metric tooltips, webhook edit, free plan enforcement |
| Sprint C | 2–3 weeks | Org member management, URL routing, SAML UI, API key rotation, email notifications |

---

## ROI Ranking (Fix Effort vs. Impact)

| Rank | Fix | Effort | Impact |
|------|-----|--------|--------|
| 1 | A-5: Fix feedback empty state copy | XS | High (misleads users into wrong action) |
| 2 | A-7: aria-live on toast | XS | High (screen reader users get zero feedback) |
| 3 | A-8: Org name in storage | XS | Medium |
| 4 | A-2: Remove/confirm danger "New Share Link" button | S | Critical (data exposure risk) |
| 5 | A-3: Session blur explanation | S | High (support ticket reduction) |
| 6 | A-4: DRM block explanation | S | High (viewer experience) |
| 7 | A-1: Confirmation modals everywhere | S (template copy) | Critical (data loss prevention) |
| 8 | A-6: aria-label on icon buttons | S | Medium-high (accessibility) |
| 9 | B-4: Metric tooltips | S | High (sales friction reduction) |
| 10 | B-2: Single link revoke confirm | S | High (accidental revocation) |

---

*Priority fix list complete — 2026-06-30*
