# Sprint 4.8A — Workflow Defect Elimination: Implementation Report

**Sprint:** 4.8A  
**Objective:** Fix the highest-impact workflow defects discovered in Sprint 4.8.  
**Commits:** 5 (one per workflow fix, as required)  
**Date:** 2026-06-23  
**Tests:** 13/13 passing throughout  
**Build:** Clean after every commit  
**Push:** Completed — all commits pushed to `origin/main`

---

## Summary Table

| # | Priority | Fix | Commit | Files Changed |
|---|----------|-----|--------|---------------|
| 1 | P1-1 | Wire `PATCH /api/links/{id}` — add `updateLink()` to api.js | `b4e04b9` | `frontend/api.js` |
| 2 | P1-2 | Edit Link workflow — EditLinkModal + "Create New Link" rename | `01b8892` | `frontend/src/screens/AccessScreen.jsx`, `backend/app/schemas/link.py`, `backend/app/routers/links.py` |
| 3 | P1-3 | Fix document row click — opens Viewer instead of Access Control | `4547d73` | `frontend/src/components/upload/DocRow.jsx` |
| 4 | P1-4 | Add "← Docs" back button in ViewerToolbar | `1c3aaac` | `frontend/src/components/ViewerToolbar.jsx`, `frontend/src/screens/ViewerScreen.jsx`, `frontend/src/screens/AppShell.jsx` |
| 5 | P2-6 | Feedback Resolve/Reopen action | `0b09848` | `backend/app/routers/annotations.py`, `frontend/src/screens/AccessScreen.jsx` |
| 6 | P2-5 | Group column in Storage screen | `741d537` | `frontend/src/screens/StorageScreen.jsx`, `backend/app/routers/storage.py` |

---

## P1-1: Wire `PATCH /api/links/{id}`

**Commit:** `b4e04b9`  
**File:** `frontend/api.js`

### Problem
`PATCH /api/links/{id}` has been fully implemented in `backend/app/routers/links.py:200–252` since V3, including cache invalidation (`invalidate_link()`), ownership verification, and audit logging. It was never called from the frontend.

### Fix
Added `updateLink(linkId, patch)` to `window.SecureDocAPI` in `api.js`, between `revokeLink` and the Viewer section. Also added `resolveFeedback(docId, annotationId)` for P2-6 in the same edit.

```js
async updateLink(linkId, patch) {
  const r = await fetch(`${API_BASE}/api/links/${linkId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify(patch),
  });
  if (r.status === 401) { _clearAndReload(); return; }
  if (!r.ok) throw await r.json();
  return r.json();
},
```

### Verification
- Endpoint: `PATCH /api/links/{link_id}` at `links.py:200` — verified exists, has auth, ownership check, cache invalidation, audit log.
- Pattern matches all other authenticated mutations in `api.js`.
- Tests: 13/13 pass.

---

## P1-2: Edit Link Workflow

**Commit:** `01b8892`  
**Files:** `AccessScreen.jsx`, `schemas/link.py`, `routers/links.py`

### Problem
Every click of "Save Policy" in `AccessScreen.jsx:116` called `createLink()` — creating a NEW link with a NEW URL, silently. Users who updated their allowed email list or expiry were creating ghost links while the original distributed URL remained unchanged.

### Fix: Backend — `LinkSummary` extension

Added `allowed_emails`, `allowed_domains`, `ip_allowlist` to `LinkSummary` in `schemas/link.py`:

```python
allowed_emails: Optional[List[str]] = None
allowed_domains: Optional[List[str]] = None
ip_allowlist: Optional[List[str]] = None
```

Updated `_link_to_summary()` in `routers/links.py` to parse these fields from their JSON Text columns via a `_parse_json_list()` helper.

### Fix: Frontend — EditLinkModal and button rename

1. **"Save Policy" → "Create New Link"** — the button always creates, so the label now reflects that.
2. **Edit button** added to each active link card in the Share Link tab, opening `EditLinkModal`.
3. **`EditLinkModal`** — a new component (at the bottom of `AccessScreen.jsx`) that:
   - Pre-populates all fields from the link's current `LinkSummary` (label, expiry, max_views, max_concurrent_sessions, allowed_emails, allowed_domains, ip_allowlist, permissions)
   - Submits via `window.SecureDocAPI.updateLink(link.id, patch)`
   - Refreshes the link list on success

### Verification
- Backend endpoint fully implemented — no new code added to `links.py` handler.
- `LinkSummary` schema extension is backward-compatible (all new fields are Optional with None defaults).
- The existing token is never changed by PATCH — distributed URLs remain valid.
- Tests: 13/13 pass.

---

## P1-3: Fix Document Row Click

**Commit:** `4547d73`  
**File:** `frontend/src/components/upload/DocRow.jsx`

### Problem
`DocRow.jsx:15`: `onClick={onAccess}` — clicking a document row navigated to Access Control. New users click a document expecting to open it in the Viewer.

### Fix
One-line change:

```jsx
// Before
onClick={onAccess}

// After
onClick={onView}
```

The "Access" button remains available as a hover action (`DocRow.jsx:63`).

### Verification
- `onView` is always passed as a prop — same call site as `onAccess`.
- Hover action buttons (View, Access, Share) are unchanged.
- Tests: 13/13 pass.

---

## P1-4: Add "← Docs" Back Button in Viewer

**Commit:** `1c3aaac`  
**Files:** `ViewerToolbar.jsx`, `ViewerScreen.jsx`, `AppShell.jsx`

### Problem
Once `activeDoc` is set in `AppShell.jsx`, the Viewer had no visible navigation escape. The only exit was clicking a sidebar item — not discoverable by new users.

### Fix
**`ViewerToolbar.jsx`:** Added `onBack` to the props destructure. Added a "← Docs" button at the far left of the toolbar, before the TOC toggle, rendered only when `onBack` is defined:

```jsx
{onBack && (
  <button onClick={onBack} title="Back to Documents" style={...}>
    {/* left-arrow SVG */}
    <span>Docs</span>
  </button>
)}
```

**`ViewerScreen.jsx`:** Added `onBack` to the component props; passed it to `ViewerToolbar`.

**`AppShell.jsx`:** Passes `onBack={() => setScreen('upload')}` to `ViewerScreen`.

### Verification
- `activeDoc` is NOT cleared — viewer hook state is preserved if the user returns to the Viewer tab.
- The button is conditionally rendered: it does not appear in the public viewer (`publicToken` mode, where `onBack` is undefined).
- No existing viewer behavior was changed.
- Tests: 13/13 pass.

---

## P2-6: Feedback Resolve/Reopen Action

**Commit:** `0b09848`  
**Files:** `backend/app/routers/annotations.py`, `frontend/src/screens/AccessScreen.jsx`

### Problem
The Feedback tab showed "Open"/"Resolved" status but had no button to change it. Feedback management was read-only for resolution state.

### Pre-implementation checks
- `resolved_at` column: exists on `ViewerAnnotation` model (`annotation.py:59`). ✓
- Service: `toggle_resolve_annotation()` at `viewer_annotation_service.py:152` requires `link_row` (viewer-session auth). ✗ Not usable from owner JWT.
- Existing owner resolve endpoint: none. Must be added.

### Fix: Backend — owner resolve endpoint

Added to `annotations.py`:

```python
@router.patch("/api/documents/{doc_id}/feedback/{annotation_id}/resolve")
@limiter.limit("30/minute")
async def resolve_feedback(request, doc_id, annotation_id, db, current_user):
    # Verify document ownership via JWT
    # Load annotation, verify it belongs to this document via annotation.link_id → ShareLink.document_id
    # Toggle resolved_at (None → now, or now → None)
```

Ownership chain: `current_user["user_id"] == doc.user_id` and `annotation.link_id → ShareLink.document_id == doc.id`.

### Fix: Frontend

Added `resolveFeedback(docId, annotationId)` to `api.js` (committed in P1-1). Added "✓ Resolve" / "↺ Reopen" button alongside the "↩ Reply" button in the feedback table rows.

### Verification
- Backend verifies ownership at both the document level (user_id) and the annotation level (link → document).
- Toggle pattern matches the viewer-side `toggle_resolve_annotation` behavior.
- Tests: 13/13 pass.

---

## P2-5: Group Column in Storage Screen

**Commit:** `741d537`  
**Files:** `frontend/src/screens/StorageScreen.jsx`, `backend/app/routers/storage.py`

### Problem
The Storage screen showed per-document storage with no group information. Users who organize documents into groups had no way to understand storage by group.

### Pre-implementation checks
- `Document.group_id` FK to `document_groups`: exists. ✓
- `DocumentGroup` model with `name`, `color`: exists. ✓
- No migration required — group_id column already on documents table. ✓

### Fix: Backend

In `storage_dashboard()` (`storage.py`): after fetching documents, collect all distinct `group_id` values, load the corresponding `DocumentGroup` rows in one query, and include `group_id`, `group_name`, `group_color` in each `by_document` entry.

### Fix: Frontend

Added "Group" column between "Document" and "State" in the per-document table. Renders a color-coded chip using `group_color` when the document has a group, or `—` for ungrouped documents.

### Verification
- Additive fields — existing `by_document` consumers are unaffected.
- Bulk-load pattern (collect IDs → one query) avoids N+1.
- No database schema changes.
- Tests: 13/13 pass.

---

## What Was NOT Changed

Per sprint rules, the following were not touched:

- No new database migrations or schema changes
- No new user-visible features beyond the 6 workflow fixes above
- No redesign of any existing screen
- No new pages or navigation items
- No Storage redesign
- No Notifications work
- No Sprint 4.9 items

---

## Test Results

```
Test Files  1 passed (1)
Tests       13 passed (13)
```

All 13 tests passed at every commit point. No regressions.

---

## Build Results

Every commit produced a clean build:

```
dist/app.bundle.js  245.0kb
⚡ Done in ~9ms
```

---

*Sprint 4.8A complete. All commits pushed to origin/main.*
