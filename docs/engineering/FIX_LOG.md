# SecureDoc Fix Log
**Generated:** 2026-06-30  
**Program:** Autonomous Engineering Improvement Program  
**Engineer persona:** Principal Engineer / Staff Product Engineer / Principal QA / Accessibility Specialist

---

## Sprint A — Critical Safety (Completed)

### A-1: Confirmation Modals — ALL Destructive Actions

| File | Action | Fix | Status |
|------|--------|-----|--------|
| `UploadScreen.jsx` | Delete Group | Added `deleteGroupModal` state + `<Modal>` confirmation | ✅ |
| `OrgsScreen.jsx` | Delete Organization | Added `deleteOrgModal` state + `<Modal>` confirmation | ✅ |
| `ApiKeysScreen.jsx` | Revoke API Key | Added `revokeKeyModal` state + `<Modal>` confirmation | ✅ |
| `ApiKeysScreen.jsx` | Delete API Key | Added `deleteKeyModal` state + `<Modal>` confirmation | ✅ |
| `WebhooksScreen.jsx` | Delete Webhook | Added `deleteWebhookModal` state + `<Modal>` confirmation | ✅ |
| `AccessScreen.jsx` | Revoke Single Link | Added `revokeLinkModal` state + `<Modal>` confirmation | ✅ |
| `AccessScreen.jsx` | Delete Revoked Link | Replaced `window.confirm()` with `deleteLinkModal` `<Modal>` | ✅ |

**Pattern standardized:** All 7 destructive actions now use `<Modal>` with:
- Colored warning banner (red for delete, amber for revoke)
- "This cannot be undone" where applicable
- Cancel + Confirm buttons, Confirm in `variant="danger"`

**BLOCK-004, BLOCK-005, BLOCK-008, BLOCK-009, BLOCK-010, BLOCK-017 resolved.**

---

### A-2: Fix "⟳ New Share Link" Dangerous Button (BLOCK-003)

**File:** `AccessScreen.jsx:329–340`  
**Fix:** Renamed button to "+ Quick Link", replaced instant-create with a `quickLinkModal` confirmation modal that warns:  
> "This creates a link with no restrictions. Anyone with the link can view the document with no password, no expiry, and no view limit."  
User must click "Create Anyway" to proceed.

**BLOCK-003 resolved.**

---

### A-5: Fix Feedback Empty State Copy (BLOCK-015)

**File:** `AccessScreen.jsx:571`  
**Before:** `"No feedback yet — viewers need can_annotate permission enabled"`  
**After:** `"No feedback yet. Viewers can leave comments when they view this document."`

**BLOCK-015 resolved.**

---

### A-6: Accessibility — aria-labels on Icon-Only Buttons

**Files:** `AccessScreen.jsx`, `OrgsScreen.jsx`, `ApiKeysScreen.jsx`, `WebhooksScreen.jsx`

| Button | Added Attribute |
|--------|----------------|
| All `✕` close buttons in custom modals | `aria-label="Close"` |
| Rename link button (`✎`) | `aria-label="Rename link"` |
| Open in new tab button (`↗`) | `aria-label="Open share link in new tab"` |
| Group delete button (`✕`) | `aria-label="Delete group {name}"` |

**AX-005 partially resolved.** Remaining: some inline ✕ buttons in dynamic lists need sweep.

---

### A-7: Accessibility — Toast aria-live (AX-009)

**File:** `frontend/src/contexts/toast.jsx:39`  
**Fix:** Added `role="status"` and `aria-live="polite"` and `aria-atomic="false"` to the toast container div.

**AX-009 resolved.**

---

### A-8: Storage Screen — Org Name Fix

**File (backend):** `backend/app/routers/storage.py:112`  
**Fix:** Backend now JOINs the Organization table to include `org_name` in the `by_org` response.

**File (frontend):** `frontend/src/screens/StorageScreen.jsx:93`  
**Fix:** Display `org.org_name` instead of `org.org_id.slice(0, 8) + '…'`.

---

### Accessibility — Modal role/aria-modal/aria-label (AX-002, AX-003)

**File:** `frontend/src/components/atoms.jsx` — `Modal` component  
**Fix:** Added `role="dialog"`, `aria-modal="true"`, `aria-label={title}` to the modal container. Added `aria-label="Close"` to the close button.

---

### Accessibility — Field Label Association (AX-004)

**File:** `frontend/src/components/atoms.jsx` — `Field` component  
**Fix:** Changed from `<div>...<label>...<input>` (unassociated) to `<label><span>...<input>` (label wraps input — implicit association). All form fields now correctly associate labels with inputs for screen readers.

---

### Accessibility — Table `scope="col"` (AX-006)

**Files:** `UploadScreen.jsx`, `ApiKeysScreen.jsx`, `OrgsScreen.jsx`, `AuditLogScreen.jsx`  
**Fix:** Added `scope="col"` to all `<th>` elements in data tables.

---

### Btn Component — Loading State (UX)

**File:** `frontend/src/components/atoms.jsx` — `Btn` component  
**Fix:** Added `loading` prop support. When `loading={true}`: shows "…" text, `aria-busy="true"`, disabled state without strikethrough.

---

## Sprint B — Core UX (Completed)

### B-5: Audit Log — Date/Action Filters + CSV Export (BLOCK-002, BLOCK-012)

**Backend (`backend/app/routers/admin.py`):**
- Added `date_from` (ISO date, inclusive), `date_to` (ISO date, inclusive end-of-day), `event_type` query params
- Added `available_event_types` to response (sorted list from `AUDIT_EVENT_TYPES`)
- Imported `datetime` and `AUDIT_EVENT_TYPES`

**Frontend API (`frontend/api.js`):**
- Updated `getAuditLog(orgId, limit, offset, { dateFrom, dateTo, eventType })` to pass new filter params

**Frontend (`frontend/src/screens/AuditLogScreen.jsx`):**
- Added filter bar with date-from/date-to date inputs and event-type dropdown
- "Apply" and "Clear" filter buttons
- "↓ Export CSV" button in header — fetches up to 500 events with current filters, downloads `audit-log-YYYY-MM-DD.csv`
- Empty state responds to active filters: "No events match the current filters."
- "Filtered" chip shown when filters are active

**BLOCK-002, BLOCK-012 resolved.**

---

### B-6: Webhook Edit Modal (BLOCK-019)

**File:** `frontend/src/screens/WebhooksScreen.jsx`  
**Fix:** Added "Edit" button to each webhook row. Opens `editWebhookModal` — a `<Modal>` with URL, description, and events fields. Calls `window.SecureDocAPI.updateWebhook(id, patch)`.

**BLOCK-019 resolved.**

---

### B-7: API Key Edit Modal (BLOCK-020)

**File:** `frontend/src/screens/ApiKeysScreen.jsx`  
**Fix:** Added "Edit" button to each key row. Opens `editKeyModal` — a `<Modal>` with name field and scopes checklist. Calls `window.SecureDocAPI.updateApiKey(id, { name, scopes })`.

**Frontend API (`frontend/api.js`):** Added `updateApiKey(keyId, patch)` method.

**BLOCK-020 resolved.**

---

## Sprint C — Enterprise (Partially Completed)

### C-1: Organization Member Management (BLOCK-001)

**Backend (`backend/app/routers/orgs.py`):**
- Added `POST /api/orgs/{org_id}/members/invite` endpoint
  - Accepts `{ email, role }` body
  - Looks up user by email via Supabase admin API (`/auth/v1/admin/users`)
  - Adds user directly if found; returns 404 if not registered
  - Returns 503 if `SUPABASE_SERVICE_ROLE_KEY` not configured

**Frontend (`frontend/api.js`):**
- Added `inviteOrgMember(orgId, email, role)` 
- Added `updateOrgMemberRole(orgId, userId, role)`
- Added `removeOrgMember(orgId, userId)`

**Frontend (`frontend/src/screens/OrgsScreen.jsx`):**
- Added `InviteMemberModal` component (email + role fields)
- Rebuilt `MembersPanel` with:
  - "+ Invite Member" button
  - Role change inline select (calls `updateOrgMemberRole` on change)
  - "Remove" button per member (disabled for last owner)
  - Correct empty state: "No members yet. Use '+ Invite Member' to add your first team member."
  - Member count in panel header

**BLOCK-001 partially resolved.** Users must already have a SecureDoc account. Full email invite flow (pending invites, email notification) remains as REMAINING_DECISIONS.

---

## Consistency Fixes

- British spelling: "organise" → "organize" in `AnalyticsScreen.jsx`
- `Modal` component standardized: `role="dialog"`, `aria-modal`, `aria-label`

---

## Tests

| Run | Result |
|-----|--------|
| After Sprint A | 1624 passed, 1 skipped |
| After Sprint B | 1624 passed, 1 skipped |
| After Sprint C | 1624 passed, 1 skipped |

Frontend bundle: 268.0 KB (from 249.3 KB — +18.7 KB for new features)
