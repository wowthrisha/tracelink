# Sprint 4.8 — Final Recommendation

**Basis:** Evidence from WORKFLOW_OPTIMIZATION_AUDIT.md, SHARE_LINK_MANAGEMENT_REVIEW.md, VIEWER_NAVIGATION_REVIEW.md, STORAGE_GROUPS_REVIEW.md, and FIRST_100_USERS_READINESS.md.  
**Scoring:** Impact (1–5) × Frequency (1–5) / Engineering Cost (days) = Priority Score  
**Scope:** Frontend-only or small backend additions. No new infrastructure. No new database tables (unless noted).

---

## Priority 1 — Wire the Link Edit Endpoint

**Score: 5 × 5 / 1 = 25**

### Problem
Every click of "Save Policy" in `AccessScreen.jsx:116` calls `createLink()` — creating a NEW link with a NEW URL. `PATCH /api/links/{id}` is fully implemented in the backend (`links.py:200–252`) with cache invalidation, ownership verification, and audit logging already in place. It is never called from the frontend.

Users who update their allowed email list, permission settings, or expiry are silently creating ghost links while the original distributed URL remains unchanged. This is the most severe product defect in the current build.

### Exact files impacted

| File | Change |
|------|--------|
| `frontend/api.js` | Add `updateLink(linkId, patch)` → `PATCH /api/links/{id}` |
| `frontend/src/screens/AccessScreen.jsx` | Add "Edit" button per link card on the Share Link tab; build `EditLinkModal` that fetches current link settings and patches on save |
| `frontend/src/screens/AccessScreen.jsx:116` | Rename "Save Policy" button to "Create New Link" to clarify it always creates (not edits) |
| `frontend/src/screens/AccessScreen.jsx:43–60` | Load the most recent active link's settings into the Policy form on mount so user sees current state |

### Backend changes required
None. `PATCH /api/links/{id}` (`links.py:200`) is complete.

### Database changes required
None. `updated_at` is already on `share_links` with `onupdate=func.now()`.

### Risk level
**Low.** Backend is tested and already in production. Frontend change adds a new path (edit existing) without removing the existing path (create new). Both coexist.

### Expected user value
**Critical.** Every paying customer who tries to update a link discovers this bug within their first week. It is the single most likely cause of churn in the first 100 users.

---

## Priority 2 — Add "Back to Documents" to Viewer Toolbar

**Score: 5 × 5 / 0.5 = 50 (trivially small cost pulls score up)**

### Problem
The Viewer has no visible way to switch documents or return to the document list. Once `activeDoc` is set in `AppShell.jsx:29`, the Viewer always loads that document. The only escape is clicking a sidebar item — discoverable only by users who read the sidebar carefully. This is a navigation dead-end for every new user.

The DocumentPicker component already exists (`src/components/DocumentPicker.jsx`) and is already used as the fallback when no document is selected.

### Exact files impacted

| File | Change |
|------|--------|
| `frontend/src/components/ViewerToolbar.jsx` | Add a "← Docs" button at the left edge of the toolbar, before the document name; wire to `onBack` prop |
| `frontend/src/screens/ViewerScreen.jsx` | Pass `onBack` prop down to `ViewerToolbar`; `onBack` = `() => setActiveDoc(null)` or `() => setScreen('upload')` |
| `frontend/src/screens/AppShell.jsx` | Pass `setActiveDoc` or a wrapper to `ViewerScreen` |

### Backend changes required
None.

### Database changes required
None.

### Risk level
**Minimal.** Additive change. No existing state is removed. The button is new; the behavior it triggers (DocumentPicker) already works.

### Expected user value
**High.** Every user who has viewed more than one document needs this. Without it, switching documents requires knowing that the sidebar "Upload" screen has a "View" button per row. This is not intuitive.

---

## Priority 3 — Add Resolve Action to Feedback Threads

**Score: 4 × 4 / 1 = 16**

### Problem
The Feedback tab in `AccessScreen.jsx` displays feedback threads with a "Status" column showing "Open" or "Resolved". The `resolved_at` column is displayed (`AccessScreen.jsx:550–554`). There is no button to transition from Open → Resolved. The feedback management screen is read-only for resolution status.

A consultant or founder who uses the feedback loop to manage document review cycles has no way to close the loop in the UI.

### Exact files impacted

| File | Change |
|------|--------|
| `frontend/api.js` | Verify or add `resolveFeedback(docId, annotationId)` method → check backend for a `PATCH /api/annotations/{id}` that sets `resolved_at` |
| `frontend/src/screens/AccessScreen.jsx:558–563` | Add "Resolve" button alongside "↩ Reply" button on each open feedback thread row |
| `frontend/src/screens/AccessScreen.jsx:604–617` | After sending a reply, optionally also offer "Send & Resolve" |

### Backend changes required
Verify: does `PATCH /api/annotations/{id}` exist with a `resolved` or `resolved_at` field? If not, add a simple `PATCH` endpoint that sets `resolved_at = now()` on the annotation. This is a ~15-line addition to `annotations.py`.

### Database changes required
None. `resolved_at` already exists on the annotation model (it is displayed in the UI from existing data).

### Risk level
**Low.** Additive. Read paths are unchanged; only a new write path is added.

### Expected user value
**High for team users.** Any customer using SecureDoc for document review workflows (consultants, legal, procurement) will hit this gap immediately.

---

## Priority 4 — Fix Row Click: Documents → Viewer (not Access Control)

**Score: 5 × 5 / 0.5 = 50**

### Problem
`DocRow.jsx:15`: `onClick={onAccess}` — clicking any document row navigates to Access Control. This violates the most basic UX convention that clicking a document opens it.

New users click their document expecting to see it. They land on a password field form. The correct default is `onView` (open the Viewer). "Access" should be a secondary action (hover button, right-click, or a gear icon).

### Exact files impacted

| File | Change |
|------|--------|
| `frontend/src/components/upload/DocRow.jsx:15` | Change `onClick={onAccess}` → `onClick={onView}` |
| `frontend/src/components/upload/DocRow.jsx:62` | The "View" hover button becomes redundant if row click is View; consider removing or demoting |
| `frontend/src/components/upload/DocRow.jsx:63` | Keep "Access" as an explicit hover button |

### Backend changes required
None.

### Database changes required
None.

### Risk level
**Low for behavior, medium for existing muscle memory.** Any existing user who has learned to "click a row to manage access" will experience a change. Given we are pre-launch with first 100 users, this is the right time to fix it.

### Expected user value
**Critical for new user activation.** The first 3 minutes of a new user's experience determines whether they continue. Landing on an empty Access Control policy form when expecting to see their document is a strong negative signal.

---

## Priority 5 — Remove Non-Functional ⌕ Filter Button

**Score: 3 × 5 / 0.25 = 60 (trivially small cost)**

### Problem
`UploadScreen.jsx:204`:
```jsx
<Btn variant="secondary" size="sm" onClick={() => toast('Search feature coming soon', 'info')}>⌕ Filter</Btn>
```

A prominent button in the primary screen header that fires a toast saying "coming soon" is a credibility problem. It signals to users (especially technical ones) that the product is incomplete. This is the first thing an Architect or Procurement Manager evaluating the product will notice.

### Exact files impacted

| File | Change |
|------|--------|
| `frontend/src/screens/UploadScreen.jsx:204` | Remove the `⌕ Filter` button entirely |

The search input already exists inline above the document table (`UploadScreen.jsx:268–269`). The Filter button duplicates a feature that already works.

### Backend changes required
None.

### Database changes required
None.

### Risk level
**None.** Removing a non-functional button cannot break anything.

### Expected user value
**High for credibility.** No non-functional UI elements in a product used by paying customers.

---

## Priority 6 — Collapse Developer Section in Sidebar by Default

**Score: 3 × 5 / 0.5 = 30**

### Problem
The sidebar has 12 items across 6 sections. The "Developers" section (API Keys, Webhooks, Audit Log) and "Workspace" section (Organizations, Notifications) are shown at the same visual weight as Upload, Viewer, and Access Control.

For a startup founder or consultant, "API Keys" and "Webhooks" in the primary nav create cognitive overload. These features are powerful but low-frequency for most users.

### Exact files impacted

| File | Change |
|------|--------|
| `frontend/src/components/atoms.jsx:222–263` | Add `collapsible: true` property to "Developers" and "Workspace" sections in `NAV_SECTIONS` |
| `frontend/src/components/atoms.jsx:302–313` | Add collapse toggle to section headers in the `Sidebar` render; persist collapsed state in `localStorage` |

### Backend changes required
None.

### Database changes required
None.

### Risk level
**Low.** Collapsed sections can always be expanded. No feature is removed; it's just one click away.

### Expected user value
**Medium.** Reduces first-impression overwhelm for non-technical users. Technical users who need API keys will find them.

---

## Priority 7 — Add Group Column to Storage Screen

**Score: 3 × 3 / 1 = 9**

### Problem
`StorageScreen.jsx` shows a per-document storage table with no group information. Users who organize documents into groups have no way to understand storage consumption by group. This is the most straightforward cross-screen consistency gap identified in Phase 3.

### Exact files impacted

| File | Change |
|------|--------|
| `frontend/src/screens/StorageScreen.jsx:114` | Add "Group" column to table header |
| `frontend/src/screens/StorageScreen.jsx:120–151` | Render `doc.group_name` in new column (requires backend to include it) |
| `backend/app/routers/storage.py` | Extend storage dashboard query to JOIN `document_groups` and include `group_name`, `group_color` in `by_document` response |

### Backend changes required
Minor — add a LEFT JOIN to the storage dashboard query. No new endpoint required.

### Database changes required
None.

### Risk level
**Low.** Additive column in an existing table.

### Expected user value
**Medium.** Useful once users have 10+ documents and multiple groups.

---

## Full Priority Table

| Priority | Item | Impact | Frequency | Cost (days) | Score | Risk |
|----------|------|--------|-----------|-------------|-------|------|
| 1 | Wire link edit PATCH | 5 | 5 | 1 | 25 | Low |
| 2 | Back button in Viewer | 5 | 5 | 0.5 | 50 | Minimal |
| 3 | Feedback resolve action | 4 | 4 | 1 | 16 | Low |
| 4 | Fix row click → Viewer | 5 | 5 | 0.5 | 50 | Low |
| 5 | Remove ⌕ Filter stub | 3 | 5 | 0.25 | 60 | None |
| 6 | Collapse Dev sidebar | 3 | 5 | 0.5 | 30 | Low |
| 7 | Group col in Storage | 3 | 3 | 1 | 9 | Low |

**By raw score (impact × frequency / cost):** 5, 4, 6, 2, 1, 3, 7

**By user-impact severity for first 100 customers:** 1, 4, 5, 3, 2, 6, 7

The score difference between #1 and #4–5 in raw score reflects that items 4 and 5 are trivially small (half-day or less). Do them first because they unblock new user activation. Item 1 (link edit) is highest strategic value but takes a full day. Item 3 (feedback resolve) requires backend verification first.

---

## What NOT to Do in Sprint 4.8

Per sprint instructions, the following are explicitly out of scope regardless of any arguments in the above analysis:

- AI features
- Dashboard redesigns
- New infrastructure (SSO, email service, Redis, CDN)
- Nested groups / multi-group documents (migration risk)
- Cross-user shared groups (auth architecture change)
- Org member management (blocked by UUID lookup gap)
- Mobile optimization (out of scope for this sprint)

---

## Recommended Sprint 4.8 Execution Order

1. Remove ⌕ Filter stub (15 minutes, zero risk)
2. Fix row click to open Viewer (30 minutes, zero backend)
3. Add Back button to Viewer toolbar (2 hours, zero backend)
4. Collapse Developer sidebar section (2 hours, zero backend)
5. Wire `updateLink` to PATCH endpoint + Edit button on share link cards (1 day)
6. Add feedback resolve action (pending backend verify: 4 hours + 1 hour backend if needed)
7. Add group column to Storage screen (2 hours frontend + 1 hour backend)

Total estimated effort: **~3 engineering days**

All items are frontend-primary. Items 5, 6, and 7 require small backend additions. No database migrations required for any Priority 1–6 item.

---

*Generated: Sprint 4.8 Phase 5 — no implementation performed. Do not commit. Do not push.*
