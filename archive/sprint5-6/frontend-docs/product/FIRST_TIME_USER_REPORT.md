# First-Time User Report — Sprint 4.8B Phase 3

**Method:** Step-by-step walkthrough of the authenticated app as a new user with zero prior knowledge. Every friction point is traced to a specific file and line.  
**Roles:** Founder (shares investor decks), Consultant (shares client deliverables), Paying Customer (any professional)

---

## Starting Conditions

- User has just registered and is logged in
- `screen = 'upload'` (default in `AppShell.jsx:29`)
- `docs = []` — no documents yet
- `activeDoc = null`
- No onboarding modal, no welcome state, no product tour

---

## Workflow 1: Upload a Document

### Step-by-step

1. User arrives at the "Upload Dashboard" header — recognizes this as the home screen
2. Upload zone is large and prominent (`UploadDropZone`) — drag-and-drop or click to browse
3. User drags a PDF → upload starts → progress bar appears
4. Processing completes → "✓ Processing complete" with two buttons:

```
[Configure Access →]  [Dismiss]
```

**Friction point #1 — `UploadProgressPanel.jsx:25`: "Configure Access →"**  
A founder who just uploaded their investor deck wants to "share it." The button says "Configure Access" — a security/IT phrase. A founder reads this as "set permissions" not "share with someone." Estimated confusion rate: high for non-technical users.

### Verdict: PASS with friction
Upload itself works and the flow is discoverable. The post-upload CTA label creates a branch-point where non-technical users may hesitate or dismiss.

---

## Workflow 2: Share a Document

### Path A: Via "Configure Access →" (recommended path after upload)

1. User clicks "Configure Access →" → arrives at "Access Control" screen
2. Header says "Access Control · [filename]"
3. First tab visible: "Policy"
4. Policy tab shows: Password Protection, Allowed Domains, Allowed Emails, Max View Count, etc.

**Friction point #2 — Tab label "Policy" (`AccessScreen.jsx:154`)**  
User intent: "Share with someone." First thing they see: a form for password protection and IP allowlists. There is no explanatory text. A non-technical user will read "Allowed Domains" and "IP Allowlist" and wonder if they've done something wrong.

5. User fills in nothing (or sets expiry) and clicks "Create New Link"
6. Screen switches to "Share Link" tab — link appears
7. User clicks "⧉ Copy" → copies URL → sends to recipient

**This path works.** 6 steps, 2 friction points.

### Path B: Via QuickShare (fastest path — completely hidden)

1. User hovers over a document row in the Upload screen
2. Hover buttons appear (opacity transitions from 0): "View", "Access", "↗ Share", group dropdown, "✕"
3. User clicks "↗ Share" → `QuickShareModal` opens
4. Link is auto-created and displayed within 1–2 seconds
5. User clicks "⧉ Copy" → done

**Friction point #3 — Hover discoverability (`DocRow.jsx:59`: `opacity: 0`)**  
The fastest path to sharing is `opacity: 0` until hover. A user who does not hover over the document row will not discover QuickShare. No tooltip, no indicator, no affordance that hovering reveals actions.

**Discovery probability:** Low on first session. A first-time user who just uploaded typically looks at the header buttons (Upload, Filter) or the sidebar — not the document row.

**Friction point #4 — "↗ Share" button label vs QuickShareModal title**  
The button says "Share" (not "Quick Share"). The modal says "Quick Share" in bold. The button label and the action name differ. (`DocRow.jsx:64`, `QuickShareModal.jsx:17`)

### Verdict: PASS via configure-access path (with friction); FAIL for discoverability of quick-share path

---

## Workflow 3: Discover Feedback

### Discovery path

1. User shares a document. Recipient opens it, leaves a comment.
2. User wants to see comments.
3. Where does a first-time user look?

**Sidebar options:** Upload, Viewer, Access Control, Analytics, Storage, API Keys, Webhooks, Audit Log, Organizations, Notifications, Billing

None of these say "Comments" or "Feedback." 

4. User is likely to check "Analytics" (closest to "see what happened") or "Notifications"
5. **Analytics:** Shows view counts, session duration, completion rate — no comments
6. **Notifications:** Shows activity feed with "Link viewed" events — no comments
7. User is now stuck.

**Friction point #5 — Feedback is inside "Access Control" with no indication**  
To find feedback: Sidebar → "Access Control" (assumes user associates "Access Control" with managing a document) → click a document in the picker → "Feedback" tab.

Three-step navigation into a screen named after security/permissions to reach a collaboration feature.

**Abandonment risk:** HIGH for founders and consultants who expect feedback to be a top-level feature. If they do not find it within 2 minutes, they assume the product does not support it.

### Verdict: FAIL for discoverability

---

## Workflow 4: Discover Analytics

### Discovery path

1. User clicks "Analytics" in sidebar
2. Analytics screen loads with KPI cards (Total Views, Active Links, Avg Session, Blocked Attempts, Active Docs, Completion)
3. Three tabs: Overview, Documents, Groups

**This is the most discoverable feature after Upload and Share.** Analytics is directly in the sidebar, clearly labeled, and the data is meaningful from day one.

**Friction point #6 — "Avg Session" with no data**  
On a first-day account with 1–2 document views, "Avg Session: —" and "Completion: —" are displayed. Empty dashes with no explanation of when they become populated.

**Friction point #7 — Page heatmap requires knowing to select a document**  
The page heatmap (most powerful analytics feature) is not visible until the user clicks a document name in the Documents tab. No affordance, no "click to see heatmap" prompt.

### Verdict: PASS with minor friction

---

## Workflow 5: Discover Quick Share

Covered in Workflow 2. Verdict: FAIL for independent discovery. Only discoverable via:
- Hovering document rows and happening to see the buttons appear
- Reading documentation
- Being told by another user

The "Configure Access → Create New Link → Copy" path IS discoverable but takes 6 steps vs 2.

---

## Workflow 6: Discover Notifications

### Discovery path

1. User clicks "Notifications" at the bottom of the sidebar
2. Arrives at event feed
3. Events load: "Link viewed", "Document processed", "Document downloaded"

**This works.** The feature is accessible via sidebar.

**Friction point #8 — "Notifications" label implies push alert settings**  
A user who clicks "Notifications" expecting to configure email alerts or push notification preferences will instead find a read-only event stream. The label creates false expectations.

**Friction point #9 — No unread badge on sidebar item**  
`NotificationsScreen.jsx:46` tracks `unread` count in state and `lastSeen` in localStorage, but the sidebar item (`NAV_SECTIONS` in `atoms.jsx:253`) has `badge: null` — the unread count is never displayed on the sidebar. A user who hasn't opened Notifications yet has no indication that new events are waiting.

### Verdict: PASS (accessible) with labeling friction

---

## Friction & Abandonment Point Summary

| # | Workflow | Point | File | Severity | Type |
|---|----------|-------|------|----------|------|
| 1 | Upload | "Configure Access →" CTA misleads sharing as a security action | `UploadProgressPanel.jsx:25` | High | Confusion |
| 2 | Share | "Policy" tab name implies configuration, not link creation | `AccessScreen.jsx:154` | High | Confusion |
| 3 | Quick Share | Hover buttons invisible until hover — no affordance | `DocRow.jsx:59` | High | Discoverability |
| 4 | Quick Share | Button says "Share", modal says "Quick Share" | `DocRow.jsx:64`, `QuickShareModal.jsx` | Medium | Inconsistency |
| 5 | Feedback | Hidden inside Access Control, no sidebar entry, no count | `atoms.jsx:233`, `AccessScreen.jsx:157` | Critical | Abandonment risk |
| 6 | Analytics | Empty dashes for new accounts with no explanation | `AnalyticsScreen.jsx:48` | Low | Confusion |
| 7 | Analytics | Heatmap requires knowing to click a document row | `AnalyticsScreen.jsx` | Medium | Discoverability |
| 8 | Notifications | Label implies preferences; content is event stream | `atoms.jsx:254` | Medium | Confusion |
| 9 | Notifications | Unread count not shown on sidebar badge | `NotificationsScreen.jsx:46`, `atoms.jsx:253` | Medium | Discoverability |
| 10 | All | Non-functional "⌕ Filter" button in Upload header | `UploadScreen.jsx:204` | High | Trust/Credibility |

---

## Predicted First-Session Path

For a first-time user (non-technical, founder persona):

```
Login → Upload screen → Upload PDF → "Configure Access →" (confused by label but clicks it)
→ Access Control → "Policy" tab (confused, fills in nothing) → "Create New Link" 
→ "Share Link" tab → Copy URL → Send to recipient ✓

Later: Returns to check if recipient opened it
→ Tries "Analytics" (finds view count) ✓
→ Tries "Notifications" (finds event stream) ✓ 
→ Wants to see recipient's comment → Checks Analytics (nothing), Notifications (nothing), Audit Log (nothing)
→ Gives up → emails recipient to ask if they have questions ✗

MISSED: Feedback tab hidden inside Access Control
MISSED: QuickShare hover flow
```

**Critical abandonment:** Feedback is invisible to first-time users. If a founder shares a document with an investor who leaves a page comment and the founder never finds that comment, the core document collaboration value proposition is not delivered.

---

*Generated: Sprint 4.8B Phase 3 — no implementation performed.*
