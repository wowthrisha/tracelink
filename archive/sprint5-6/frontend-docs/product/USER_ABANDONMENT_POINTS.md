# User Abandonment Points — Sprint 4.9

**Date:** 2026-06-23  
**Basis:** REAL_WORLD_USAGE_AUDIT.md — 5 personas across 5 flows  
**Priority scale:**  
- P0 = User cannot complete workflow  
- P1 = User likely abandons  
- P2 = User confusion, likely partial abandonment or wrong path  
- P3 = Friction, annoyance, reduced trust

---

## P0 — User Cannot Complete Workflow

None identified. All primary workflows are technically completable by a user willing to explore the interface.

---

## P1 — User Likely Abandons

### AP-1 · "Access Control" label kills sharing intent
**Where:** Sidebar nav item; `atoms.jsx:232`  
**What happens:** User uploads a document and wants to share it. They look at the sidebar for a "Share" option. They see: Upload, Viewer, Access Control, Feedback. None of these say "Share." They may not click "Access Control" because it sounds like an IT security function, not a sharing tool. They bounce.  
**Personas:** All 5  
**Flow:** Share  
**Evidence:** Label is `'Access Control'` in `NAV_SECTIONS` at `atoms.jsx:232`. There is no "Share" or "Sharing" label anywhere in the sidebar.

---

### AP-2 · Feedback badge invisible on fresh login
**Where:** `AppShell.jsx:62–72`  
**What happens:** The feedback badge (unread thread count) is fetched via `useEffect` that depends on `activeDoc?.id`. On a fresh login, `activeDoc` is null. The badge does not appear. Users who logged in to check feedback see no signal that anything is waiting. They open Feedback, see DocumentPicker, pick a document — and only then see feedback. High probability of skipping this entirely.  
**Personas:** 1, 4, 5  
**Flow:** Feedback  
**Evidence:** `useEffect(() => { if (!activeDoc?.id ... ) return; ... }, [activeDoc?.id]);` at `AppShell.jsx:62`.

---

### AP-3 · Sharing model never explained
**Where:** Upload screen, QuickShare modal, Access Control  
**What happens:** The product is link-based (create URL, send via your own email). New users from DocuSign, Dropbox, and email-attachment workflows expect "enter email address, click send." No screen explains the link model. The construction PM and sales AE will look for a "Send to" field, not find it, and assume the product cannot do what they need.  
**Personas:** 3, 5  
**Flow:** Share  
**Evidence:** `handleSave()` at `AccessScreen.jsx:118` — `payload` has `document_id`, `label`, `password`, etc. No `recipient_email`. No email sending. Nothing in the UI explains this.

---

### AP-4 · Form state not cleared between link creations
**Where:** `AccessScreen.jsx:44–62` (policy state), `handleSave()` at `AccessScreen.jsx:118`  
**What happens:** A user creates a link for Subcontractor A (with A's email in "Allowed Emails"). The view switches to the Links tab. They return to Create Link. All form values (allowed emails, password, domain, expiry) persist. They create a new link for Subcontractor B — but it silently carries Subcontractor A's email restrictions. Misconfiguration is invisible.  
**Personas:** 3  
**Flow:** Share  
**Evidence:** `handleSave()` does not call `setAllowedEmails('')`, `setPassword('')`, or any form reset. State variables at `AccessScreen.jsx:44–62` are initialized once and never cleared after a successful link creation.

---

### AP-5 · Per-page heatmap not in Analytics dashboard
**Where:** `AnalyticsScreen.jsx`, Analytics → By Document tab  
**What happens:** The primary analytics use case for a founder or sales professional is "which pages did my viewer spend time on?" This data exists (page heatmap), but it is only accessible via the Viewer's Insights panel — not from the Analytics screen. Clicking a document row in the By Document table does nothing. Users look at the analytics dashboard, see only aggregate data (total views, avg session), conclude the product offers shallow analytics, and abandon.  
**Personas:** 2, 4, 5  
**Flow:** Analytics  
**Evidence:** `DocAnalyticsRow` renders per-document rows. No `onClick` that navigates to a heatmap. The heatmap in `ViewerScreen.jsx:178–191` is only reachable from the viewer's toolbar Insights button.

---

### AP-6 · No notifications outside the open browser tab
**Where:** `NotificationsScreen.jsx:POLL_INTERVAL = 30000`  
**What happens:** The sales professional's key use case is "alert me when the prospect opens my proposal." The product polls for events every 30 seconds — but only while the browser tab is open. There is no email notification, no push notification, no webhook for personal alerts (webhooks exist for developers, not end-users). A user who closes the tab gets zero signal.  
**Personas:** 5, 4  
**Flow:** Feedback / Analytics  
**Evidence:** `POLL_INTERVAL = 30000` in `NotificationsScreen.jsx`. No evidence of email notification dispatch in any user-facing flow. Webhooks exist (`WebhooksScreen.jsx`) but require developer configuration.

---

### AP-7 · Viewer feedback reply never notifies the reviewer
**Where:** `AccessScreen.jsx:619–629` — reply submitter  
**What happens:** The owner replies to a viewer's annotation. The reply is saved to the database. The viewer — who left feedback via a shared link and may not return — has no way to know a reply exists. No email, no indicator on the shared link page. The conversation dies. If this is a reviewer (architect, investor), they abandon the feedback loop.  
**Personas:** 5, 2  
**Flow:** Feedback  
**Evidence:** `replyToFeedback()` in `AppShell` calls `window.SecureDocAPI.replyToFeedback(docId, a.id, replyText.trim())`. No notification dispatch. The shared link viewer has no notification surface.

---

### AP-8 · "Blocked Attempts" creates alarm, triggers support
**Where:** `UploadScreen.jsx:198` — stats panel; `AnalyticsScreen.jsx:46`  
**What happens:** First-time users see "Blocked Attempts: 0" or higher on their dashboard. A project manager or consultant reads this as "someone is trying to hack my document." They call support, leave the product, or lose trust. The stat is actually measuring authentication failures (wrong password attempts). For most users, it should not be surfaced on the first screen.  
**Personas:** 1, 3, 5  
**Flow:** Upload / Analytics  
**Evidence:** Stat card at `UploadScreen.jsx:198`: `{ label: 'Blocked Attempts', value: ..., icon: '⊗', color: C.warning }`. Color is `C.warning` — orange. This amplifies alarm.

---

### AP-9 · "PRIMARY" Create Link button below fold / hard to find
**Where:** `AccessScreen.jsx:305–307`  
**What happens:** The Create Link form fills most of the viewport. The "Create New Link" button is in the lower-right corner of the full-width permissions card. Users who fill in the top fields (Authentication, Access Limits) may scroll down, see 7 toggles, and look for a button to click. The button is at the end of this card, next to a secondary "⟳ New Link" button with no explanation of the difference. Many users will not complete the flow.  
**Personas:** 1, 3  
**Flow:** Share  
**Evidence:** `AccessScreen.jsx:305–323` — `Create New Link` and `⟳ New Link` are siblings in a flex column at the right side of the permissions card. Neither has a tooltip or inline description.

---

## P2 — User Confusion / Partial Abandonment

### AP-10 · Risk badge shows HIGH on every new document
**Where:** `DocRow.jsx:49` — `RiskBadge level={doc.risk}`  
**What happens:** Every newly uploaded document shows "HIGH" risk. The criteria are never explained. New users assume something is wrong with their document. Some users will not share a "HIGH" risk document until they understand what it means.  
**Personas:** 1, 3, 4  
**Flow:** Upload  

---

### AP-11 · Hover-reveal action buttons not discovered
**Where:** `DocRow.jsx:59` — `opacity: hov ? 1 : 0`  
**What happens:** The document row's action buttons (View, Access, Share, Delete) are invisible until hover. Users who use keyboard navigation or scan the page without hovering never discover these actions. They click the row, open the viewer, and don't find the share path. The primary sharing trigger (hover → "↗ Share") requires discovering the hover pattern first.  
**Personas:** 1, 2  
**Flow:** Upload / Share  

---

### AP-12 · DocumentPicker dead-end in Access Control and Viewer sidebar clicks
**Where:** `AccessScreen.jsx:163–171`; `ViewerScreen.jsx:152–160`  
**What happens:** When no document is selected and the user clicks "Access Control" or "Viewer" in the sidebar, they see a list of documents with no explanation of what they're selecting for. New users don't understand what to do. The empty state is a raw list, not an instruction.  
**Personas:** 1, 3  
**Flow:** Share / Viewer  

---

### AP-13 · "Allowed Domains" hint uses @ prefix incorrectly
**Where:** `AccessScreen.jsx:247`  
**What happens:** The hint shows `@acme.io`. Standard domain notation is `acme.io`. The `@` is email syntax, not domain syntax. Users may enter `@acme.io` or `acme.io` or `@acme.io, @partner.com` — all with different mental models. If the server expects one format and the user enters another, the restriction silently fails.  
**Personas:** 1, 2  
**Flow:** Share  
**Evidence:** `hint="Comma-separated, e.g. @acme.io"` at `AccessScreen.jsx:247`.

---

### AP-14 · Embed code shown by default for every link
**Where:** `AccessScreen.jsx:391–399`  
**What happens:** Every link card in the Links tab renders an expanded `<iframe>` embed code block. Most users don't know what an iframe is and are confused by this technical content displayed prominently. It creates visual noise and makes the links list harder to scan.  
**Personas:** 1, 3, 5  
**Flow:** Share  

---

### AP-15 · Feedback empty state uses technical language
**Where:** `AccessScreen.jsx:514`  
**What happens:** When no feedback exists, the empty state reads: "No feedback yet — viewers need can_annotate permission enabled." "can_annotate" is a backend field name, not user language. A first-time user reads this as an error message about a technical configuration issue and doesn't understand what action to take.  
**Personas:** 1, 3  
**Flow:** Feedback  
**Evidence:** `AccessScreen.jsx:514` empty state message.

---

### AP-16 · "Configure in Access Control →" still uses old label in QuickShare
**Where:** `QuickShareModal.jsx:98`  
**What happens:** The QuickShare modal has a link "Configure in Access Control →". The feature was renamed to sharing but this specific string still uses the old security-system label. It creates a term inconsistency: the modal just helped you "share" something, but now asks you to go to "Access Control."  
**Personas:** 4, 5  
**Flow:** Share  
**Evidence:** `QuickShareModal.jsx:98` literal string.

---

### AP-17 · No "what will the recipient see?" preview
**Where:** Create Link form (no preview button), QuickShare modal  
**What happens:** After configuring a link with password, watermark, and email restriction, the user has no way to see what the recipient will experience before sending. They must send the link to themselves or guess.  
**Personas:** 4, 5  
**Flow:** Share  

---

### AP-18 · Analytics rows not clickable — expected navigation doesn't happen
**Where:** `AnalyticsScreen.jsx` — By Document tab  
**What happens:** The document table in Analytics looks like a navigable list. Users click rows expecting to drill into per-document analytics. Nothing happens. The cursor is `default` (not `pointer`). This is a dead UX pattern that breaks trust.  
**Personas:** 2, 4, 5  
**Flow:** Analytics  

---

### AP-19 · "Dismiss" button next to "Share Document →" invites accidental click
**Where:** `UploadProgressPanel.jsx:28`  
**What happens:** After a successful upload, two buttons appear side-by-side: "Share Document →" (primary) and "Dismiss" (ghost). The Dismiss button is the second button in a flex row. A user who clicks slightly right of the primary button dismisses the success state. The upload zone reappears but the next step context is gone.  
**Personas:** 1, 3  
**Flow:** Upload  

---

## P3 — Friction / Reduced Trust

### AP-20 · "← Docs" returns to Upload, not previous context
**Where:** `AppShell.jsx:147` — `onBack={() => setScreen('upload')}`  
**What happens:** Pressing "← Docs" always returns to the Upload Dashboard, even if the user came from Access Control or Analytics. No history stack. Reduces confidence in navigation.  
**Personas:** All  
**Flow:** Viewer  

---

### AP-21 · Upload header button says "↑ Upload PDF" but supports more formats
**Where:** `UploadScreen.jsx:204`  
**What happens:** The button label is "↑ Upload PDF". The product supports DOCX, TXT, MD, LOG. A user with a DOCX may not try the button. The error only appears after attempting upload.  
**Personas:** 1  
**Flow:** Upload  

---

### AP-22 · Metadata panel (group + retention) appears before any file is selected
**Where:** `UploadScreen.jsx:218` — `UploadMetadataPanel` renders unconditionally  
**What happens:** The "Assign to group" and "Delete after" options appear below the drop zone before the user has uploaded anything. For a first-time user with no groups, this creates cognitive load at the wrong moment. It suggests decisions must be made before uploading, when the user just wants to get the file in.  
**Personas:** 1, 3  
**Flow:** Upload  

---

### AP-23 · "Avg Session" KPI — no unit explanation
**Where:** `AnalyticsScreen.jsx:42–49`  
**What happens:** "Avg Session: 4m 12s" — is this per page? Per document? Per session? No tooltip. Users have to guess what they're measuring.  
**Personas:** 5  
**Flow:** Analytics  

---

### AP-24 · Completion shows "—" with no data
**Where:** `AnalyticsScreen.jsx` — `avgCompletion > 0 ? ... : '—'`  
**What happens:** When there are no views, Completion shows "—". This could mean "not applicable," "error," or "0%." "0%" would be clearer. The dash creates uncertainty about whether the metric is loading or simply empty.  
**Personas:** 1, 5  
**Flow:** Analytics  

---

### AP-25 · Sidebar section label "Developers" for API Keys, Webhooks, Audit Log
**Where:** `atoms.jsx:244`  
**What happens:** A project manager or consultant scrolling the sidebar sees a section labeled "Developers." They mentally skip it. This is fine for the beta audience (largely technical), but creates a perception that the product requires a developer to use fully.  
**Personas:** 3  
**Flow:** General navigation  

---

## Abandonment Risk Summary

| Priority | Count | Key areas |
|----------|-------|-----------|
| P0 | 0 | — |
| P1 | 9 | Share labeling, link model, form state, notifications, analytics depth |
| P2 | 9 | Risk badge, hover-reveal, empty states, term inconsistency |
| P3 | 6 | Upload polish, analytics labels, navigation memory |

**Highest-risk flows:** Share (5 P1 items) → Analytics (2 P1 items) → Feedback (2 P1 items)

**Most at-risk persona:** Sales professional (AP-1, AP-3, AP-5, AP-6, AP-7, AP-8) — all core use cases hit abandonment points.

---

*Generated: Sprint 4.9 — Real World Validation Audit. No implementation.*
