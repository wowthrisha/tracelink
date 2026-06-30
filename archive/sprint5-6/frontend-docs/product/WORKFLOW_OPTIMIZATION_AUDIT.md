# Workflow Optimization Audit — Sprint 4.8 Phase 0

**Method:** Full source-code trace. Every finding references exact file and line.  
**Scope:** 7 real user workflows evaluated for friction, confusion, and dead-ends.

---

## Workflow 1 — Upload → Share → Viewer Opens

### Step-by-step trace

1. User drops file onto `UploadDropZone` (UploadScreen.jsx:218)
2. `simulate()` fires, uploads, polls status every 2 s (UploadScreen.jsx:73–98)
3. On success: `UploadProgressPanel` shows two buttons:
   - **"Configure Access →"** → navigates to AccessScreen with the new doc
   - **"Dismiss"** → closes the panel, user is left staring at the document list
4. On AccessScreen: Policy tab is default. User fills out policy, clicks **"Save Policy"**
5. `handleSave()` at AccessScreen.jsx:116 calls `createLink()` — **always creates a new link**
6. Tab auto-switches to `link`. User copies the URL.
7. Viewer: user must click **"Viewer"** in sidebar, document list has been lost (sidebar nav to viewer shows DocumentPicker since `activeDoc` is still set if they came from the doc table)

### Issues found

| # | Type | Evidence |
|---|------|---------|
| W1-01 | **Missing action** | After upload, "Dismiss" gives no onward path. No "Share now" button on success panel. | UploadProgressPanel.jsx:24–30 |
| W1-02 | **Confusing row click** | Clicking a document row fires `onAccess` (Access Control), not `onView` (Viewer). A new user expects a click to open the document. | DocRow.jsx:15 `onClick={onAccess}` |
| W1-03 | **Redundant step** | Quick Share (inline on the row) already creates a link in 1 click. "Configure Access →" on upload panel adds 3–4 more steps. Users who just want to share fast are forced into a full policy form. | UploadProgressPanel.jsx:25 |
| W1-04 | **Hidden Quick Share** | The ↗ Share button is opacity-0 until hover. New users never discover it. | DocRow.jsx:59 `opacity: hov ? 1 : 0` |
| W1-05 | **No direct link from upload to viewer** | After upload + dismiss, user must click "Viewer" in sidebar, then pick the document again from DocumentPicker, costing 2+ extra clicks. | AppShell.jsx:108 |

---

## Workflow 2 — Upload → Feedback → Resolve

### Step-by-step trace

1. Share link created. Viewer opens document, leaves a comment.
2. Owner navigates to Access Control (sidebar), clicks document row, goes to Feedback tab.
3. Sees the feedback table: Reviewer, Page, Comment, Replies, Status, Created At.
4. Clicks **"↩ Reply"** — inline reply textarea appears.
5. Owner types reply, clicks Send.
6. After reply, feedback status remains **"Open"** — there is no "Resolve" button anywhere in the Feedback tab.

### Issues found

| # | Type | Evidence |
|---|------|---------|
| W2-01 | **Missing action** | There is no "Resolve" / "Mark resolved" button on individual feedback threads. The `resolved_at` column exists in the data model and the Status chip shows "Resolved" or "Open" — but there is no UI to transition from Open → Resolved. | AccessScreen.jsx:550–554 shows `resolved_at` display; no mutation action present |
| W2-02 | **Navigation required** | Reaching Feedback requires: sidebar → upload → click doc row → Access Control screen → Feedback tab. This is 4 steps from a different screen. No direct shortcut from notification or analytics. | AppShell:107–118 |
| W2-03 | **Filter complexity shown upfront** | Filters section is collapsed by default (good), but the toggle button label "⚙ Filters ▼" is easy to miss. Users may not know filtering exists. | AccessScreen.jsx:427 |
| W2-04 | **Advanced Filters inside Filters** | Two levels of disclosure: "⚙ Filters" → expands → "Advanced Filters ▼" nested inside. Two identical toggle patterns is confusing. | AccessScreen.jsx:470–499 |
| W2-05 | **No bulk resolve** | No "Resolve all" or "Mark selected as resolved" action. For a document with 20+ comments, resolution requires N individual actions (which don't exist). | AccessScreen.jsx:503–626 |

---

## Workflow 3 — Upload → Analytics Review

### Step-by-step trace

1. User uploads a document and shares it.
2. Viewer accesses the document (generates analytics event).
3. Owner wants to see how many people viewed it and for how long.
4. Must click **Analytics** in sidebar — completely separate screen from Upload.
5. Sees Overview tab. Total Views is site-wide. Must switch to "By Document" tab.
6. Clicks the row to see the page heatmap.

### Issues found

| # | Type | Evidence |
|---|------|---------|
| W3-01 | **No per-document shortcut** | The document list (UploadScreen) shows "Views" as a column, but clicking it doesn't navigate to that document's analytics. Users who want more detail must manually navigate to Analytics > By Document and find the document. | DocRow.jsx — no analytics link |
| W3-02 | **Analytics tab disconnected from document context** | Analytics screen has no concept of "which document I just uploaded." It loads all documents simultaneously. | AnalyticsScreen.jsx:23–32 |
| W3-03 | **Overview is loaded but rarely the right view** | The Overview tab shows aggregate data. Most users want per-document analytics. The tab selection defaults to "overview" every page load — correct tab is "documents". | AnalyticsScreen.jsx:14 `useState('overview')` |
| W3-04 | **Heatmap triggered by row click — no affordance** | To see page heatmap, user clicks a document row. This is invisible to new users — there's no button or hint. The only affordance is a text label "▦ Heatmap" that appears in the last column. | AnalyticsScreen.jsx:172 |

---

## Workflow 4 — Upload → Access Control Update

### Step-by-step trace

1. User shares a document. Sends the link to 5 people.
2. Next day: user wants to add 2 more allowed emails to the existing link.
3. User goes to Access Control, Policy tab.
4. Edits allowed emails field, clicks "Save Policy".
5. `handleSave()` calls `createLink()` — **creates a brand new link with a new URL**.
6. The original link (already distributed to 5 people) **is not modified**.
7. New link must be redistributed to all 7 people.

### Issues found

| # | Type | Evidence |
|---|------|---------|
| W4-01 | **Critical: Save Policy creates a new link, does not edit existing** | `handleSave()` at AccessScreen.jsx:116 calls `window.SecureDocAPI.createLink()`. There is no call to `updateLink()`. Every save creates a NEW link with a NEW token (new URL). Existing distributed links are unchanged. | AccessScreen.jsx:129 `await window.SecureDocAPI.createLink(payload)` |
| W4-02 | **PATCH endpoint exists but is never called from frontend** | `PATCH /api/links/{id}` is fully implemented in `backend/app/routers/links.py:200–252`. It supports updating allowed_emails, allowed_domains, permissions, password, expiry, max_views — with cache invalidation already in place. The frontend has never been wired to call it. | links.py:200; api.js has no `updateLink()` method |
| W4-03 | **No "Edit link" button on Share Link tab** | Share Link tab shows links in cards with Copy and Revoke buttons. No Edit button. | AccessScreen.jsx:326–398 |
| W4-04 | **Policy tab state is blank on load** | When opening the Policy tab, all fields (password, emails, expiry) are empty — they don't reflect the current link's settings. User doesn't know what the current policy is. | AccessScreen.jsx:43–60: all initialized to `''` / `false` |
| W4-05 | **Confusing label: "Save Policy" implies persistence** | Button label "Save Policy" implies saving a configuration. It actually creates a new share link. A user who saves 3 times has created 3 separate links. | AccessScreen.jsx:304 |

---

## Workflow 5 — Upload → Storage Organization

### Step-by-step trace

1. User has 20 documents. Wants to organize them into folders/categories.
2. Groups exist. User creates a group in the upload screen.
3. To assign a document to a group: hover over the row, see the "Group…" dropdown.
4. User selects group from dropdown. Document is assigned.
5. To view all documents in a group: click the group chip in the group filter strip.
6. User goes to Storage screen to see space usage — groups are not visible there.

### Issues found

| # | Type | Evidence |
|---|------|---------|
| W5-01 | **Group assignment is hover-only** | Group assignment dropdown is in the action area that's opacity-0 until hover. Easy to miss on a touch device or for a new user. | DocRow.jsx:59–79 |
| W5-02 | **No drag-and-drop to group** | Assigning documents to groups requires hover interaction per document. No batch selection or drag-to-group. | UploadScreen.jsx — no multi-select |
| W5-03 | **Storage screen has no groups** | StorageScreen.jsx shows per-document table. Groups are absent. User can't see "how much storage does the Q4 Reports group use?" | StorageScreen.jsx — no group_id, no group filter |
| W5-04 | **Groups and Storage are separate flows with no connection** | Editing retention policy in StorageScreen affects a document, but there's no path from StorageScreen to the document's group or to the document list filtered by group. | StorageScreen.jsx:46–55 — no navigation |
| W5-05 | **No group name in Storage table** | The "Storage by Document" table does not show group membership. | StorageScreen.jsx:120–151 |

---

## Workflow 6 — Organization → Multiple Documents

### Step-by-step trace

1. User wants to see all documents in the "Legal" group.
2. Clicks the "Legal" chip in the group filter strip.
3. Document list filters to Legal documents.
4. User wants to share ALL Legal documents — must click ↗ Share on each row individually.

### Issues found

| # | Type | Evidence |
|---|------|---------|
| W6-01 | **No batch actions** | No checkboxes, no "select all", no bulk share, bulk delete, or bulk group-assign. Every document action is single-document. | UploadScreen.jsx — no selection state |
| W6-02 | **Group filter strip invisible until groups exist** | The filter strip (`groups.length > 0`) only renders when groups are created. New users see no grouping affordance. | UploadScreen.jsx:228 `{groups.length > 0 && (` |
| W6-03 | **No group view / folder view** | Filtered list shows documents in table format. No visual distinction from unfiltered view. No group "header" or group-level metadata (e.g., total views for the group). | UploadScreen.jsx:186–300 |
| W6-04 | **Scalability: group filter strip wraps** | With 10+ groups, the filter strip wraps into multiple lines, pushing the document table down. No overflow handling or scrollable chip list. | UploadScreen.jsx:229 `flexWrap: 'wrap'` |

---

## Workflow 7 — Quick Share → Follow-up Changes

### Step-by-step trace

1. User hovers over a document row, clicks ↗ Share.
2. `QuickShareModal` opens, creates a link instantly (label: "Quick Share", default permissions).
3. User copies link and sends it.
4. Next day: user wants to add a password to that link.
5. User goes to Access Control, Share Link tab.
6. Finds the "Quick Share" link. There is no Edit button — only Revoke.
7. User creates a NEW link with a password. Must resend it to all recipients.

### Issues found

| # | Type | Evidence |
|---|------|---------|
| W7-01 | **Quick Share link is immediately a dead-end** | Once created, a Quick Share link cannot be modified. Users must revoke it and create a new link — breaking all in-flight sessions. | AccessScreen.jsx:340–343: only Revoke button |
| W7-02 | **Quick Share creates a permanent link without warning** | The modal says "Share link created — watermark on, download off." It does not say "This link will persist. You can revoke it from Access Control." Users may not know the link is now active and tracked. | QuickShareModal.jsx:65 |
| W7-03 | **No expiry option in Quick Share** | QuickShareModal hardcodes `QUICK_SHARE_DEFAULTS` with no expiry. A link shared casually persists forever. | QuickShareModal.jsx:7–14 |
| W7-04 | **"Configure in Access Control" takes user away** | The link "Configure in Access Control →" in QuickShareModal closes the modal and navigates to Access Control, which is correct. But it does NOT pre-select the newly created link — user lands on the Policy tab with empty fields, not the Share Link tab showing the new link. | QuickShareModal.jsx:91–94 `onClose(); onConfigure(doc)` → AccessScreen sets tab to 'policy' by default |

---

## Summary Table

| Workflow | Most Critical Issue | Severity |
|----------|--------------------|---------:|
| Upload → Share → Viewer | Row click goes to Access, not Viewer | P1 |
| Upload → Feedback → Resolve | No resolve button exists anywhere | P1 |
| Upload → Analytics | Save Policy creates new link silently | P0 |
| Upload → Access Update | **PATCH endpoint exists, never wired** | P0 |
| Upload → Storage | Groups not shown in Storage screen | P2 |
| Org → Multiple Docs | No batch actions | P2 |
| Quick Share → Follow-up | Quick Share link cannot be edited | P1 |

---

*Generated: Sprint 4.8 Phase 0 — all findings derived from source code only.*
