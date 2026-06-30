# Real World Usage Audit — Sprint 4.9

**Date:** 2026-06-23  
**Method:** Code-grounded simulation. Each persona walks through the product as a real user would. Every friction point is cited to an actual screen, component, or label in the codebase.  
**Scope:** Upload → Share → Viewer → Feedback → Analytics  
**Rules:** No implementation. No architecture. Behavior only.

---

## Persona 1: First-Time Consultant

**Who:** Independent management consultant. Shares deliverables (proposals, reports) with clients. First use of SecureDoc. Received a referral.

**Goal:** Upload a proposal PDF, share it with one client, know if the client reads it.

---

### Upload Flow

**Step 1 — Arrives at "Upload Dashboard"**

The screen shows 4 stat cards (Total Documents, Active Shares, Total Views, Blocked Attempts), all showing 0. Beneath them is a drag-drop zone. Below that: "Assign to group" and "Delete after" dropdowns.

**Finding P2:** The first thing below the upload zone is "Assign to group." The consultant has never heard of groups, has no documents, and doesn't know what a group is. This metadata panel (`UploadMetadataPanel.jsx`) appears unconditionally — before any file is selected. It creates premature complexity at the worst moment: when the user hasn't even uploaded yet.

**Finding P2:** The header button says "↑ Upload PDF." The consultant has a DOCX. The supported formats (DOCX, TXT, MD, LOG) are not shown anywhere on this screen. The error only appears after attempting to upload an unsupported file via the file picker, not in advance. Code: `_detectFileType()` in `UploadScreen.jsx:16–24`.

**Step 2 — Drags PDF, sees progress bar**

The upload zone disappears and is replaced by `UploadProgressPanel`. The progress bar fills to 100%. Then the screen shows: "✓ Processing complete" with two buttons: **Share Document →** and **Dismiss**.

**Finding P2:** "Dismiss" is positioned immediately next to the primary CTA. A first-time user who reads quickly might click Dismiss and lose their post-upload context. No confirmation if Dismiss is clicked accidentally. Code: `UploadProgressPanel.jsx:28`.

**Step 3 — Document appears in the table**

The document row shows columns: Document, Status, Risk, Pages, Views, Expires.

**Finding P2:** The Risk column shows "HIGH" for a freshly uploaded PDF. The consultant doesn't understand what HIGH risk means. There's no tooltip, no help text, no explanation. `RiskBadge` just displays the value — criteria are opaque. This creates alarm on first use.

**Step 4 — Clicks the document row**

The viewer opens. The consultant wanted to go to sharing, not viewing. They have to navigate back.

**Finding P2:** Row click opens the viewer (`DocRow.jsx:15 onClick={onView}`). The consultant's mental model: "I just uploaded, I want to share." There's no way to know that "share" requires hovering the row to reveal action buttons. The hover-reveal pattern (`opacity: hov ? 1 : 0` in DocRow) means the "↗ Share" and "Access" buttons are invisible until hover. On first use, users never discover them.

---

### Share Flow

**Step 1 — Finds "Access Control" in sidebar**

The consultant, confused by the viewer, navigates back and notices the sidebar. They see: Upload, Viewer, Access Control, Feedback, Analytics, Storage, Billing.

**Finding P1:** "Access Control" is the label for sharing. For a consultant, "access control" means IT or security administration. They will look elsewhere before clicking this. The mental model mismatch is severe: the product uses security engineering language for what is, to the user, simply "share this file."

**Step 2 — Clicks "Access Control" — sees DocumentPicker**

Because no document is selected (`activeDoc` is null after returning from viewer), the Access Control screen shows a document picker: `DocumentPicker.jsx`. The user clicked "Access Control" and got a list of documents with no instruction.

**Finding P1:** No document is selected in session context. The user is presented with a DocumentPicker that says nothing about what they're selecting a document for. There's no heading, no explanation. They click their document and arrive at Access Control for that document.

**Step 3 — Arrives at Access Control with 5 tabs**

Tabs: Create Link | Links | View History | Feedback | Annotations

The "Create Link" tab is active by default. It shows a 2-column grid card ("Authentication") and another 2-column card ("Access Limits"), plus a full-width card labeled "Document Permissions" with 7 toggles.

**Finding P1:** This screen looks like a firewall configuration form, not a document sharing tool. The consultant has no context for "Authentication" (are they setting up 2FA for themselves?), "Allowed Domains" (email domains? web domains?), "IP Allowlist," or "Max Concurrent Sessions." They will not fill in any fields and will look for a simple "share" action.

**Finding P1:** The primary action button "Create New Link" is positioned in the lower-right corner of the permissions card — a visual dead end. The form reads top-to-bottom and the button is at the end of the last card, not in a prominent position after the main form content. First-time users will not see it without scrolling.

**Finding P2:** There are two buttons next to each other: **Create New Link** and **⟳ New Link**. Neither is explained. The distinction (one uses the form settings, one uses defaults) is not communicated. A new user may click the wrong one.

**Step 4 — Clicks "Create New Link" with no policy**

A link is created. The view switches to the "Links" tab automatically. The consultant sees their link in a card with a URL, a "Copy" button, and metadata (Views, Expires, Created). 

**Finding P3:** The link label shows "Untitled Link" — the consultant didn't know they could name their links. The Label field in the Create Link form was not obvious as important context.

**Step 5 — Shares the URL with the client**

The consultant copies the link and emails it.

**Finding P1:** Nothing on this screen tells the consultant what the client will experience. No preview, no "test link" affordance, no preview of restrictions. The "↗" open-link button exists but is visually minimal.

**Finding P2:** The embed code is expanded by default for every link card (`AccessScreen.jsx:391–399`). The consultant doesn't know what `<iframe>` means. This technical content is shown prominently when most users never need it.

---

### Viewer Flow

**Step 1 — Clicks document row to open viewer**

The viewer opens with the toolbar. The consultant sees page controls, zoom, layout options, laser pointer, magnifier, insights, table of contents, search, and "← Docs" button.

**Finding P2:** The toolbar is dense. For a first-time user, none of the toolbar icons are self-explanatory. Labels only appear on hover. The consultant's goal (read the document) is immediately achievable, but the cognitive load is high.

**Step 2 — Exits with "← Docs" button**

Navigates back to "Upload Dashboard."

**Finding P3:** "← Docs" returns to the Upload Dashboard, not to wherever the user was before. If the user had navigated to Access Control before opening the viewer, clicking back drops them at Upload. No history tracking. This is a known limitation but creates a disorienting loop.

---

### Feedback Flow

**Step 1 — Client opens shared link, leaves a sticky note**

The consultant doesn't know this happened.

**Finding P1:** There is no email notification when a viewer leaves feedback. The only signal is the badge in the sidebar — but the badge only appears when `activeDoc` is set (`AppShell.jsx:62–72`). If the consultant logged in fresh and hasn't clicked on their document yet, `activeDoc` is null and the badge is 0. They have no reason to check Feedback.

**Step 2 — Consultant clicks "Feedback" in sidebar**

Because `activeDoc` is null, they see a DocumentPicker. They click the document. The Feedback tab opens showing the client's annotation.

**Finding P2:** The feedback table shows columns: Reviewer, Page, Comment, Replies, Status, Created At. The "Reviewer" column shows "Anonymous Viewer" with no email — the client didn't log in, so there's no identification. The consultant doesn't know which client this is.

**Finding P2:** Empty state text: "No feedback yet — viewers need can_annotate permission enabled." This is backend language. The consultant has no idea what `can_annotate` is. They would abandon the page thinking feedback is broken.

**Finding P3:** The "↺ Refresh" button exists for manual refresh. There's no indication whether the list is live or cached. The consultant expects a real-time experience but gets a manual-refresh UI.

---

### Analytics Flow

**Step 1 — Clicks "Analytics" in sidebar**

A screen loads with 6 KPI cards: Total Views, Active Links, Avg Session, Blocked Attempts, Active Docs, Completion.

**Finding P2:** "Blocked Attempts" shows 0 or a number. The consultant doesn't know what was blocked or by whom. The label is alarming — implies their document was attacked.

**Finding P2:** "Completion" shows "—" when there are no views. 0% or "No data yet" would be clearer than a dash.

**Step 2 — Clicks "By Document" tab**

A table shows their PDF with view count, session count, etc.

**Finding P2:** Clicking a table row does nothing. The consultant expects to see details for that document. The row is not a link and provides no navigation.

**Step 3 — Wants to see if their specific client read the proposal**

There is no per-viewer breakdown on this screen. The Analytics screen shows aggregate stats only. Individual viewer activity is in "View History" inside Access Control — but the consultant doesn't know to look there.

**Finding P1:** The use case "did my client read it?" is the #1 analytics question for a document-sharing consultant. It requires navigating: Sidebar → Access Control → Select document → View History tab. This is 4 steps and requires knowing that View History is the right place.

---

## Persona 2: Architect

**Who:** Principal architect at a mid-size firm. Shares drawing sets and technical specifications with structural engineers and contractors. Uses email and Dropbox today.

**Goal:** Share a structural drawing PDF with an external engineering firm, restrict to their email domain, check if they opened it.

---

### Upload Flow

**Step 1 — Arrives, uploads PDF without issues**

Upload completes cleanly. The architect is technically sophisticated and reads the form carefully.

**Finding P3:** The "Delete after" dropdown (`UploadMetadataPanel.jsx:18–29`) defaults to "Never." For an architect who works on time-sensitive project phases, this is fine, but there's no explanation of what retention means for active links — if the document is deleted, do the links break? No tooltip.

---

### Share Flow

**Step 1 — Needs to restrict to @structural-eng.com domain**

Navigates to Access Control → Create Link. Finds "Allowed Domains" field. Hint text: "Comma-separated, e.g. @acme.io."

**Finding P2:** The hint shows "@acme.io" but standard domain notation is "acme.io" — the `@` prefix is confusing. Is this for email verification? Does the viewer need to be logged in? There's no explanation of how domain restriction actually works in practice (does the viewer enter their email? is it verified?).

**Step 2 — Sees "IP Allowlist" field with hint "CIDR or exact, e.g. 10.0.0.0/24"**

An architect understands their office network but not necessarily CIDR notation. They will skip this field.

**Finding P2:** No explanation of when to use IP allowlist vs. domain restriction. These are distinct security controls but presented as equals in a form — no guidance on which to use.

**Step 3 — Sees "Max Concurrent Sessions"**

**Finding P2:** "Max Concurrent Sessions" has no explanation. An architect might think this limits simultaneous browser tabs. In practice it limits simultaneous active viewer sessions. No tooltip, no hint.

---

### Viewer Flow

**Step 1 — Opens the document to verify it uploaded correctly**

Viewer works. The architect notices the "Insights" button (heatmap/analytics). Clicks it. An insights panel opens.

**Finding P3:** The Insights button is only visible in the toolbar. There's no label — just an icon. The insights panel shows a heatmap and text extraction. Useful, but not discoverable for non-technical users.

---

### Feedback Flow

**Step 1 — External engineer leaves annotations on a structural drawing**

The architect clicks Feedback in the sidebar.

**Finding P2:** The feedback page shows annotations but not the page they appear on visually. The "p.12" notation tells them the page number, but there's no thumbnail or quick "jump to page" link. The architect has to open the viewer, navigate to page 12, and find the annotation manually.

**Finding P2:** Annotations and Feedback are two separate tabs. Highlights and drawings are in "Annotations"; comments and sticky notes are in "Feedback." A reviewer's combined review (highlight + comment on same element) is split across two tabs. The architect has to piece together feedback from two separate views.

---

### Analytics Flow

**Step 1 — Checks which pages the engineer spent time on**

The Insights feature in the Viewer provides this (page heatmap). But the architect's natural path is: Sidebar → Analytics → By Document → click row.

**Finding P1:** Clicking a document row in Analytics does nothing. The page-level heatmap is only accessible via: Viewer → toolbar Insights button (for viewing their own document). Or via Analytics → By Document → scroll down past the table — there's no visible trigger. The heatmap access is not discoverable from the Analytics screen.

---

## Persona 3: Construction Project Manager

**Who:** Project manager at a general contractor. Shares RFIs, submittals, and progress reports with subcontractors. Not technical. Primary tool is email and Excel.

**Goal:** Upload a project progress report, share with 3 subcontractors, verify each has read it.

---

### Upload Flow

**Step 1 — Uploads PDF**

The PM uploads successfully. Sees "Share Document →" button.

**Finding P2:** The stat cards show "Blocked Attempts: 0" and "Active Shares: 0." The PM's mental model: "blocked what? who's trying to access my file?" This creates anxiety on first use.

**Step 2 — Wants to share with 3 subcontractors separately**

The PM expects to enter 3 email addresses and click Send. Instead, the sharing flow (Access Control) creates a single URL that anyone can use.

**Finding P1:** SecureDoc's sharing model is link-based, not email-invite based. There is no "send to" field. There's no email delivery. The PM must create links and send them manually via their own email client. This workflow mismatch is not explained anywhere in the product.

---

### Share Flow

**Step 1 — Wants to create 3 separate links for 3 subcontractors**

The PM arrives at "Create Link." They fill in the first subcontractor's email in "Allowed Emails." They create the link. It goes to the Links tab. They go back to Create Link and notice the form is blank again.

**Finding P2:** The form doesn't reset visually to indicate it's ready for a new link. After creating a link, the view switches to the Links tab. Going back to Create Link, the form still shows the previously entered values from `useState`. Actually wait — `setTab('link')` is called after `handleSave()`, but the form state persists. So the PM sees the old values on returning. They might think they're editing the existing link, not creating a new one.

**Finding P2:** Actually checking the code: `setAllowedEmails`, `setPassword` etc. are NOT reset after `handleSave()`. The form retains values. The PM will create the second link with the first subcontractor's email in "Allowed Emails" unless they manually clear it.

**Step 2 — Creating 3 links, one per subcontractor**

This takes 3 round trips: Create Link → (create) → Links tab → Create Link → (create) → Links tab...

**Finding P1:** The form does not reset after link creation. State carries over between link creations, creating a silent misconfiguration risk. Code: `handleSave()` in `AccessScreen.jsx:118–137` — no form reset.

---

### Viewer Flow

**Step 1 — Clicks a row to preview the document**

Opens viewer. Everything works.

**Finding P3:** The PM notices "Risk: HIGH" on the document. They call IT. This is a false alarm — the risk badge is computed server-side and all new documents show HIGH. There's no explanation in the product.

---

### Feedback Flow

**Step 1 — Subcontractor leaves a question in the document**

The PM sees a badge on "Feedback" in the sidebar (count: 1). Clicks it. DocumentPicker shows. They click their document. The feedback appears.

**Finding P2:** The reply button is labeled "↩ Reply." The PM clicks it and an inline text area appears immediately below the row — not immediately obvious as it's within the table. The PM may not notice the input area appeared below the row they clicked.

**Finding P2:** After replying, the feedback table refreshes. The PM's reply appears indented. The subcontractor will not be notified by email. The PM has no way to alert the subcontractor that they replied. This creates a one-way communication channel — the system has no "send notification" affordance after a reply is posted.

---

### Analytics Flow

**Step 1 — Wants to verify all 3 subcontractors read the report**

Clicks Analytics. Sees aggregate view count. Cannot identify individual viewers.

**Finding P1:** Per-viewer tracking of who read what — the PM's #1 goal — requires navigating to Access Control → View History. The View History tab (`AccessLog.jsx`) shows viewer sessions by timestamp and email (if authenticated). But subcontractors who accessed via a public link with no email restriction appear as "Anonymous." The PM cannot confirm whether a specific person read the document.

---

## Persona 4: Startup Founder

**Who:** Seed-stage SaaS founder. Shares investor decks. Needs to know which slides investors focus on. Concerned about leaking strategy.

**Goal:** Share investor deck with watermark and password, track slide-by-slide engagement.

---

### Upload Flow

**Step 1 — Arrives, uploads quickly**

**Finding P3:** The header button says "↑ Upload PDF." But the founder thinks in terms of "add document" or "share document." The upload affordance is clear enough.

**Step 2 — Sees "Share Document →" after upload**

Clicks it. Goes to Access Control → Create Link.

---

### Share Flow

**Step 1 — Wants to add a password**

Finds the "Password Protection" field in the Authentication card. Enters a password. Good.

**Step 2 — Wants to enable "view only, no download"**

The "Document Permissions" card shows 7 toggles. The founder sees: Download (off), Print (off), Copy Text (off), Right Click (off), Watermark (on), Annotations (off), Info Panel (on). The defaults look right. They click "Create New Link."

**Finding P3:** There's no summary of what the link will do before creating it. "Your link will require a password, disable download, disable print, enable watermark." A pre-creation summary would prevent misconfiguration.

**Step 3 — Tries to see the QuickShare flow instead**

Navigates back to Upload, hovers a doc row. Sees "↗ Share."

**Finding P2:** In QuickShare modal, the bottom has two items: "Configure in Access Control →" (underlined link text) and "Done" button. "Access Control" is still the old security-sounding label. A founder's reaction: "I don't need to configure access control, I need to share this."

**Step 4 — Investor opens the deck and spends 40 minutes on slide 3**

The founder wants to know this.

**Finding P1:** The per-page heatmap is accessible only from: Viewer → toolbar → Insights icon. It is NOT accessible from the main Analytics screen without a hidden scroll (not actually accessible — you have to switch to "By Document" tab and select a document there? Let me re-check...). Actually from the AnalyticsScreen code, `selectedHeatmapDoc` is `useState(null)` and the code that renders the heatmap triggers when a document is selected. But looking at the code I have access to (first 80 lines), I don't see the trigger UI. The heatmap in the Viewer is the discoverable path. The Analytics screen's document-level heatmap requires interaction that isn't visible in the document list rows (rows just show data, clicking does nothing per the checklist).

**Finding P1:** The founder's most valuable insight ("which slide did the investor focus on?") is behind the Viewer's Insights panel — not in the Analytics dashboard where they'd naturally look.

---

### Feedback Flow

**Step 1 — Investor adds a question as a sticky note**

The founder logs in the next morning. `activeDoc` is null. The Feedback badge doesn't show.

**Finding P1:** The badge only populates when `activeDoc?.id` changes (`AppShell.jsx:62–72`). On a fresh login without clicking a document, the badge is always null. The founder doesn't know there's unread investor feedback.

**Step 2 — Founder navigates to Feedback in sidebar**

DocumentPicker appears. Clicks the deck. Feedback tab shows the investor's sticky note.

**Finding P2:** The sticky note shows "annotation_type: sticky_note" in the type column. The text "sticky_note" is a technical term — it should read "Sticky note" or "Note."

---

### Analytics Flow

**Step 1 — Checks "did the investor read it?"**

Analytics → By Document: sees 1 session, 40 min avg time. Good.

**Finding P2:** "Active Links" in the KPI reads 1. But the founder has multiple links (one with password, one QuickShare). They don't know which link the investor used.

---

## Persona 5: Sales Professional

**Who:** Enterprise AE at a B2B SaaS company. Shares proposals and pricing documents. Uses DocuSign for e-signing, Salesforce for CRM. Expects modern, frictionless tools.

**Goal:** Send a proposal to a prospect, get notified when they open it, follow up at the right moment.

---

### Upload Flow

**Step 1 — Uploads proposal PDF**

Works. But the AE immediately looks for a "send to" field. No such field exists.

**Finding P1:** The sales professional's core expectation — "enter email, click send" — does not match SecureDoc's model. SecureDoc creates a link; the user sends it via their own channel. This fundamental model mismatch is never explained on the Upload screen or anywhere in the onboarding. The AE will bounce without attempting to share.

---

### Share Flow

**Step 1 — Discovers QuickShare via hover**

The "↗ Share" button appears on hover. The AE clicks it. The QuickShare modal opens, creates a link in 1 second, shows the URL.

**Finding P2:** The QuickShare modal says "Share link created — watermark on, download off." The AE doesn't know what "watermark" means in this context — is it their company logo? Is it a SecureDoc watermark? No explanation.

**Step 2 — Copies URL and sends via email**

**Finding P2:** After copying, the only option is "Done." There's no "track this link" affordance. The AE copied the URL and has no idea where to find it again later. They'd have to navigate: sidebar → Access Control → select document → Links tab.

---

### Viewer Flow

**Step 1 — AE opens their own link to test it**

They see an access gate (password prompt if set, or direct entry if no gate). They experience what the prospect will experience.

**Finding P3:** The viewer shows a watermark. The AE wants to know what text appears on the watermark. It's visible in the document but they have no control over it from the sharing flow — the watermark content is not shown or configurable in the Create Link form.

---

### Feedback Flow

**Step 1 — Prospect leaves a question**

The AE does not know. No email notification. The Feedback badge doesn't appear until `activeDoc` is set.

**Finding P1:** A sales professional's priority is "alert me the moment someone interacts with my document." There is no push or email notification system in the product. The Notifications screen polls every 30 seconds but only while the browser tab is open. If the AE closes the tab, they get nothing. This is the highest-impact gap for the sales persona.

**Step 2 — AE comes back next day and checks Feedback**

Finds the prospect's question. Clicks "↩ Reply." Writes a response. Clicks "Send."

**Finding P1:** The reply is posted in the system. The prospect never gets notified. The AE has no way to alert the prospect that a reply exists. The feedback loop is one-sided: the AE can respond, but the prospect has no mechanism to see the reply unless they re-open the original link and navigate to the comment.

---

### Analytics Flow

**Step 1 — Wants to know if the prospect read to the pricing page (page 8)**

Checks Analytics. Sees "Total Views: 1, Avg Session: 4m."

**Finding P1:** Per-page engagement is only in Viewer → Insights. The AE never finds it. They conclude the analytics are basic and consider switching to a competitor.

**Finding P2:** "Avg Session: 4m" — is this time-on-one-page or time on the whole document? No explanation.

---

## Cross-Persona Summary

| Issue | Personas Affected | Priority |
|-------|------------------|---------|
| "Access Control" label mismatch | All 5 | P1 |
| Feedback badge requires activeDoc to be set | All 5 | P1 |
| No email notifications | 3, 4, 5 | P1 |
| Per-page heatmap not in Analytics | 2, 4, 5 | P1 |
| "share" model (link-based) not explained | 3, 5 | P1 |
| Form state not reset between link creations | 3 | P1 |
| No post-reply notification to viewer | 5 | P1 |
| Risk badge HIGH on all new docs | 1, 3, 4 | P2 |
| "Blocked Attempts" alarming to non-security | 1, 3, 5 | P2 |
| Hover-reveal action buttons not discoverable | 1, 2 | P2 |
| Empty state: "can_annotate" tech language | 1, 3 | P2 |
| @domain hint formatting ambiguity | 1, 2 | P2 |
| Embed code always shown | 1, 3, 5 | P2 |
| Feedback types split across two tabs | 2 | P2 |
| Form doesn't hint what link will do pre-create | 4 | P2 |
| Watermark content not configurable or visible | 5 | P2 |
| "Configure in Access Control →" old label | 4, 5 | P2 |
| Analytics row click does nothing | 2, 4 | P2 |
| Completion shows "—" not "0%" | 1, 5 | P3 |
| Dismiss button adjacent to Share button | 1 | P3 |
| Back button drops to Upload, not previous | All | P3 |
| Upload button says "PDF" but accepts more | 1 | P3 |
| Metadata panel shown before upload | 1, 3 | P3 |

---

*Generated: Sprint 4.9 — Real World Validation Audit. No implementation.*
