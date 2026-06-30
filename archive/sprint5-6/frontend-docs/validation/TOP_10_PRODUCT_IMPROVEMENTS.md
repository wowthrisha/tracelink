# Top 10 Product Improvements
Date: 2026-06-22
Perspective: Founder + Product Lead
Ranking: Impact × Frequency × Simplicity
NOT ranked by engineering complexity.

Impact = how much it changes the product for the better
Frequency = how often users will feel this
Simplicity = how clear the value is to a first-time user

---

## Rank 1 — Quick Share Button on Document Rows

**Impact: 10/10 | Frequency: 10/10 | Simplicity: 10/10**

**The problem:**
The most common action in the product — sharing a document — requires navigating to a different screen, selecting the document again, reading 11 form fields, clicking "Save Policy," then navigating to another tab to copy the link. 5+ steps, 45-65 seconds. Every competitor does this in 2 clicks.

**The improvement:**
Add a "↗ Share" button directly on each document row in the Upload screen. Clicking it instantly creates a share link with sensible defaults (watermark on, download off) and surfaces the URL in a popover. The user copies the link and leaves. Policy configuration remains available for power users.

**What this unlocks:**
- All three owner personas (architect, consultant, builder) go from FAIL to PASS on the 30-second test
- The core value loop (upload → share → track) becomes discoverable without reading instructions
- First-time users succeed on their first session

**Engineering estimate:** 4-6 hours. No new API. Uses existing `createLink`. One new popover component.

---

## Rank 2 — Real-Time "Document Opened" Notification

**Impact: 10/10 | Frequency: 8/10 | Simplicity: 10/10**

**The problem:**
When a viewer opens a shared document, the document owner hears nothing. The `link.viewed` event is defined in the system and would trigger both webhook delivery and an SSE toast — but it is never dispatched from the viewer validation endpoint. A consultant who shares a proposal before a meeting has no way to know in real-time if the prospect opened it.

**The improvement:**
1. Fix `viewer.py` to dispatch `link.viewed` when a session is created (15-minute backend change — two `try/except` blocks matching the existing pattern in `tasks.py`)
2. Wire SSE EventSource in AppShell (`useNotificationStream` hook, 0.5 days)
3. Show toast: "📄 Your document 'Proposal.pdf' was just opened"

**What this unlocks:**
- The consultant persona's primary need is fulfilled
- DocSend's #1 value proposition ("know when your document is opened") is matched
- Every webhook subscriber starts receiving `link.viewed` deliveries simultaneously

**Engineering estimate:** 1 day total. Backend: 30 minutes. Frontend: 4-6 hours (includes SSE auth decision).

---

## Rank 3 — Rename & Simplify the Share Screen

**Impact: 9/10 | Frequency: 10/10 | Simplicity: 9/10**

**The problem:**
The screen where you share a document is called "Access Control." The primary tab is called "Policy." The primary button is called "Save Policy." None of these words mean "share a document" to a normal person. Every owner visits this screen every time they share something — which means every owner experiences this confusion every time.

**The improvement:**
- Rename "Access Control" nav item → "Share"
- Rename "Policy" tab → "Share Settings"
- Rename "Save Policy" button → "Create Share Link"
- Rename "Share Link" tab → "Active Links"
- Rename "Access Log" tab → "Who Viewed"
- Move 5 advanced fields (IP allowlist, CIDR, max concurrent sessions, email list, right-click disable) behind an "Advanced" disclosure triangle
- Default form: 6 fields visible (password, domain restriction, expiry, max views, download toggle, watermark toggle)

**What this unlocks:**
- First-time users understand what the screen does without a tutorial
- Power features remain available to users who want them
- No behavior changes — pure labeling and layout

**Engineering estimate:** 2-3 hours. Pure UI text and layout changes.

---

## Rank 4 — Fix the Analytics Range Filter

**Impact: 8/10 | Frequency: 7/10 | Simplicity: 8/10**

**The problem:**
The range selector (24h / 7d / 30d / 90d) on the Analytics screen changes visual state but never filters the data. A user who selects "24h" is looking at 90 days of data, thinking they're seeing today's activity. This is a lie. Known issue, deferred from Sprint 4.5A.

**The improvement:**
Pass the `range` state as a query parameter to `getAnalyticsOverview()`, `getDocumentAnalytics()`, and `getGroupAnalytics()`. Verify the backend accepts a `range` or `from_date` parameter. If not, add it.

**What this unlocks:**
- Analytics becomes trustworthy data, not confusing noise
- A consultant checking "did anyone open my document today" can actually see today's data
- The range selector becomes a real feature instead of a visual lie

**Engineering estimate:** 2-4 hours (frontend: 1 hour; backend: 1-2 hours if range param needs adding).

---

## Rank 5 — "Pre-Select Document" When Navigating from Upload

**Impact: 8/10 | Frequency: 9/10 | Simplicity: 8/10**

**The problem:**
When a user clicks on a document row in the Upload screen and navigates to Access Control (or Analytics), they are dropped into a DocumentPicker — they must manually re-select the document they just came from. The system knows exactly which document the user was looking at. Not pre-selecting it is the product forgetting who you are between screens.

**The improvement:**
Pass the selected document as state when navigating between screens. When AccessScreen or AnalyticsScreen receives a `doc` prop from the parent (AppShell), skip the DocumentPicker and go directly to the configured view.

AppShell already passes `doc` as a prop to screens — but there is no mechanism for the user to set the active document from the Upload screen's row actions. Adding a "View in Access Control" or "View Analytics" action per document row, with state propagation, fixes this.

**What this unlocks:**
- 5 seconds saved on every cross-screen navigation
- Users feel like the product remembers their context
- Eliminates one of the most common moments of friction

**Engineering estimate:** 2-3 hours. State propagation in AppShell + document row action buttons.

---

## Rank 6 — Forensic Watermark Discovery

**Impact: 9/10 | Frequency: 3/10 | Simplicity: 10/10**

**The problem:**
SecureDoc applies a forensic steganographic watermark to every page served to every viewer, uniquely encoding their session ID and email. This is a feature that no competitor offers. It means that if a document leaks, you can trace the exact session that leaked it — even if the document was photographed on a phone. This is a genuine enterprise security differentiator.

Nobody knows it exists. There is no badge, no tooltip, no mention in the UI. The product is hiding its best feature.

**The improvement:**
- In the Viewer, show a small "🔒 Forensic watermark active" badge in the info panel or toolbar
- On the Policy/Share Settings form, add a line: "Forensic watermark applied automatically — every viewer's copy is uniquely traceable"
- In the Access Log, show a "Download" entry with a forensic marker that confirms watermark was applied

**What this unlocks:**
- Security-conscious buyers understand why SecureDoc is different from Google Drive
- "Forensic tracing" becomes a sales talking point
- Users who care about document leaks (legal, finance, NDA-sensitive content) have a reason to choose SecureDoc over any competitor

**Engineering estimate:** 1-2 hours. Static copy + small UI badge in the viewer info panel. Zero backend changes.

---

## Rank 7 — Promote Feedback as a First-Class Feature

**Impact: 8/10 | Frequency: 5/10 | Simplicity: 7/10**

**The problem:**
SecureDoc has a structured feedback system: viewers can leave threaded comments on specific pages, owners can reply inline, and everything is exportable to CSV with per-reviewer activity. This is better than what DocSend charges for on its highest tier. It lives in the 4th tab of a screen called "Access Control."

Nobody finds it. There's no visual invitation to viewers to leave feedback. There's no badge on the document row showing "3 new feedback items." There's no notification to the owner when feedback arrives.

**The improvement:**
- Add a "💬 Feedback" count badge on document rows in the Upload screen (shows unread count)
- When a viewer has annotation permission, show a prominent "Leave feedback on this document →" CTA above the first page in the viewer
- Rename the "Feedback" tab in the Share screen to "Reviews" — language that documents reviewers understand
- Add feedback count to the document summary card in the Share screen header

**What this unlocks:**
- The feedback loop (owner shares → viewer reviews → owner sees feedback) becomes visible
- Architects and consultants who share for review get a genuine collaboration tool, not just a tracker
- This is the feature that separates SecureDoc from every "share a link" product

**Engineering estimate:** 2-4 hours. Mostly UI additions (badges, CTA text). No new API calls needed.

---

## Rank 8 — Storage Screen Removal from Primary Nav

**Impact: 6/10 | Frequency: 1/10 | Simplicity: 8/10**

**The problem:**
Storage occupies the same navigation weight as Upload, Share, and Analytics. But users visit Storage once (to set retention policy) and never return unless they're approaching their storage limit. It creates visual clutter in the sidebar and suggests that storage management is a core activity.

**The improvement:**
- Move Storage data to a collapsible "Usage" section in the Billing screen: "X GB used of Y GB available. Upgrade for more storage."
- Show retention policy in the same location
- Remove "Storage" from the primary navigation
- If a user is approaching their storage limit, show a warning banner on the Upload screen: "You've used 85% of your storage — manage in Billing"

**What this unlocks:**
- Primary navigation is reduced to 5 meaningful items (Upload, Preview, Share, Analytics, Billing)
- Storage management becomes contextual (visible when relevant) rather than permanent
- The sidebar communicates what SecureDoc does: Upload, Share, Analyze, Pay

**Engineering estimate:** 3-4 hours. Data surfaced in BillingScreen. Storage route removed from nav.

---

## Rank 9 — Laser Pointer and Magnifier Removal from Viewer Toolbar

**Impact: 5/10 | Frequency: 1/10 | Simplicity: 9/10**

**The problem:**
The viewer toolbar has 15+ icons. Most users need 5: page navigation, zoom, download, annotate, close. The laser pointer (a cursor trail effect for presentations) and magnifier (a second zoom mechanism) add cognitive load to a toolbar that is already dense. These tools compete visually with the annotation tools and the links panel that users actually want.

**The improvement:**
Remove the laser pointer and magnifier from the default toolbar. If there is a genuine use case for the laser pointer (e.g., live presentations of shared documents), it can be hidden behind an "advanced view options" overflow menu.

**What this unlocks:**
- Toolbar becomes scannable — users find the tools they need faster
- The links panel, annotations, and TOC become more discoverable
- The viewer feels polished rather than overwhelming

**Engineering estimate:** 30 minutes. Two icon toggles removed.

---

## Rank 10 — Active Link Status Badge on Upload Screen

**Impact: 6/10 | Frequency: 8/10 | Simplicity: 9/10**

**The problem:**
The document table in the Upload screen shows document name, file type, status, and size. It does not show whether a document has an active share link. An owner who uploads 10 documents and shares 3 of them cannot tell at a glance which ones are currently shared without navigating to Access Control for each one.

**The improvement:**
Add a "🔗 Shared" or "📎 Active link" badge on document rows that have at least one active (non-revoked, non-expired) share link. The badge can show the view count inline: "🔗 4 views."

**What this unlocks:**
- Instant overview of document exposure from the primary screen
- Owners know at a glance what's "out in the world" without navigating
- The badge creates a sense of engagement — "my documents are being read"
- Clicking the badge could jump directly to the Access Control / Share screen for that document

**Engineering estimate:** 3-4 hours. Additional field in `getDocuments()` response: `active_link_count` and `total_views`. Minimal backend query change.

---

## Summary Ranking

| Rank | Improvement | Impact | Frequency | Simplicity | Est. Days |
|---|---|---|---|---|---|
| 1 | Quick Share button on document rows | 10 | 10 | 10 | 0.5 |
| 2 | Real-time "doc opened" notification | 10 | 8 | 10 | 1.0 |
| 3 | Rename & simplify Share screen | 9 | 10 | 9 | 0.5 |
| 4 | Fix analytics range filter | 8 | 7 | 8 | 0.5 |
| 5 | Pre-select document between screens | 8 | 9 | 8 | 0.5 |
| 6 | Surface forensic watermark as a feature | 9 | 3 | 10 | 0.25 |
| 7 | Promote Feedback feature | 8 | 5 | 7 | 0.5 |
| 8 | Remove Storage from primary nav | 6 | 1 | 8 | 0.5 |
| 9 | Remove laser pointer + magnifier | 5 | 1 | 9 | 0.1 |
| 10 | Active link status badge on Upload rows | 6 | 8 | 9 | 0.5 |

**Total estimated effort: ~5 days.**
**Expected outcome: 30-second task completion for all owner personas. Competitive parity with DocSend on discoverability. Unique differentiation maintained on security depth and analytics depth.**

---

## The One Sentence Summary

SecureDoc is a security-grade document sharing product wearing an enterprise compliance interface. Strip the jargon, add the quick-share button, wire the notification — and this product beats DocSend for any professional who cares about where their documents go.
