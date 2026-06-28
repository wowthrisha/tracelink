# Sprint 5.4 Revalidation — Evidence-Based Link Management Audit
**Date:** 2026-06-28  
**Sprint:** 5.4 Revalidation  
**Auditor:** Source code trace + live UI verification  
**Primary source:** `frontend/src/screens/AccessScreen.jsx` (891 lines)  
**Status:** COMPLETE

---

## Mandate

> "Do NOT trust previous reports. Treat all prior conclusions as unverified until proven through source code and running UI."

Every answer below is backed by:
- Exact file + exact line number(s) from current source code
- Screenshot filename proving the UI state

---

## Screenshots Captured

| File | Content |
|------|---------|
| `~/Downloads/link_mgmt_audit/01_login_screen.png` | SecureDoc login page |
| `~/Downloads/link_mgmt_audit/02_app_state.png` | Authenticated Upload Dashboard |
| `~/Downloads/link_mgmt_audit/03_access_control_no_doc.png` | Access Control — no document selected |
| `~/Downloads/link_mgmt_audit/04_access_control_with_doc.png` | **Create Link tab — NO label field present** |
| `~/Downloads/link_mgmt_audit/05_links_tab.png` | Links tab (mocked data) — Edit, Revoke, ✎ pencil, REVOKED state |
| `~/Downloads/link_mgmt_audit/05_links_tab_v2.png` | **Links tab (live backend) — "Untitled Link", Edit button, ✎ pencil icon** |
| `~/Downloads/link_mgmt_audit/06_edit_modal.png` | **Edit modal open — all policy fields + "Save Changes" button** |

---

## A. Can a user rename an existing link?

**YES — WORKING**

Two UI paths exist, both call `PATCH /api/links/{id}`:

**Path 1 — Inline ✎ pencil rename:**
- `AccessScreen.jsx:371-377` — pencil button rendered when `!link.revoked_at && renamingLinkId !== link.id`:
  ```jsx
  <button onClick={() => { setRenamingLinkId(link.id); setRenameValue(link.label || ''); }}>✎</button>
  ```
- `AccessScreen.jsx:350-376` — when `renamingLinkId === link.id`, renders `<input autoFocus value={renameValue} onBlur={() => handleRename(link.id)} />`
- `AccessScreen.jsx:155-163` — `handleRename()`:
  ```js
  await window.SecureDocAPI.updateLink(linkId, { label: trimmed || null })
  ```

**Path 2 — Edit modal Label field:**
- `AccessScreen.jsx:838-840` — `<Field label="Label"><input value={label_txt} onChange={e => setLabel(e.target.value)} /></Field>`
- `AccessScreen.jsx:820-831` — `handleSubmit()` includes `label: label_txt || null` in patch
- `AccessScreen.jsx:759-775` — `await window.SecureDocAPI.updateLink(editLinkModal.id, patch)` → PATCH

**Backend:**
- `api.js:289-295` — `updateLink(linkId, patch)` → `PATCH /api/links/{linkId}`
- `backend/app/routers/links.py:233` — `if payload.label is not None: link.label = payload.label`
- `backend/app/routers/links.py:256` — `await db.commit()` — same row, same token
- `backend/app/routers/links.py:263-278` — audit log: `link.updated` event

**UI evidence:** `05_links_tab_v2.png` (✎ pencil icon), `06_edit_modal.png` (Label field pre-filled "Untitled Link")

---

## B. Is there a visible Edit button?

**YES — WORKING**

- `AccessScreen.jsx:381-383`:
  ```jsx
  {!link.revoked_at && (
    <Btn variant="ghost" size="sm" onClick={() => setEditLinkModal(link)}>Edit</Btn>
  ```
- Gate: only shown when `link.revoked_at` is null (non-revoked links only)
- `AccessScreen.jsx:20` — `const [editLinkModal, setEditLinkModal] = useState(null);` — clicking Edit sets this state to the link object, triggering EditLinkModal to render

**UI evidence:** `05_links_tab_v2.png` — "Edit" button visible top-right of the "Untitled Link" card

---

## C. Is there a visible pencil icon?

**YES — WORKING**

- `AccessScreen.jsx:371-377`:
  ```jsx
  {!link.revoked_at && renamingLinkId !== link.id && (
    <button onClick={() => { setRenamingLinkId(link.id); setRenameValue(link.label || ''); }}>✎</button>
  )}
  ```
- Gate: only shown when link is not revoked AND not currently being renamed

**UI evidence:** `05_links_tab_v2.png` — ✎ icon visible to the right of the Copy button on the "Untitled Link" card; `05_links_tab.png` — ✎ icon also confirmed on "Client Review Q2" card

---

## D. Can a user edit allowed_emails, allowed_domains, expiry, password, permissions, watermark, max_views, IP allowlist without creating a new link?

**YES — WORKING** (with one display gap for max_concurrent_sessions — see note)

All fields editable via EditLinkModal (`AccessScreen.jsx:804-890`) which calls `PATCH`, not `POST`:

| Field | EditLinkModal Line | PATCH Handler Line |
|-------|-------------------|-------------------|
| Label | 838–840 | `links.py:233` |
| Password | 841–843 (`hint="Leave blank to keep existing"`) | `links.py:250-254` |
| Expiry Date | 844–845 | `links.py:234` |
| Max Views | 846–848 | `links.py:235` |
| Max Concurrent Sessions | 849–851 | `links.py:240` |
| Allowed Domains | 853–855 | `links.py:237` |
| Allowed Emails | 857–863 | `links.py:236` |
| IP Allowlist | 863 | `links.py:238` |
| Permissions (7 toggles incl. watermark_enabled) | 864–882 | `links.py:241-249` |

**Backend schema** (`backend/app/schemas/link.py` — `LinkUpdateRequest`):
```python
class LinkUpdateRequest(BaseModel):
    label: Optional[str] = None
    expires_at: Optional[datetime] = None
    max_views: Optional[int] = None
    max_concurrent_sessions: Optional[int] = None
    allowed_emails: Optional[List[str]] = None
    allowed_domains: Optional[List[str]] = None
    ip_allowlist: Optional[List[str]] = None
    permissions: Optional[Dict[str, bool]] = None
    password: Optional[str] = None
```

**PATCH guard pattern** (`links.py:233-246`): All fields use `if payload.field is not None:` — sending null does not overwrite existing values (except expires_at and max_views which explicitly allow null to clear).

**UI evidence:** `06_edit_modal.png` — Edit modal open showing all fields: Label, New Password, Expiry Date, Max Views, Max Concurrent Sessions, Allowed Domains, Allowed Emails, IP Allowlist, Permissions grid (Download, Print, Copy Text, Right Click, Watermark, Annotations, Info Panel)

**Known gap — max_concurrent_sessions display:**
- `backend/app/schemas/link.py` — `LinkSummary` does NOT include `max_concurrent_sessions`
- `AccessScreen.jsx:809-811` — modal initializes from `link.max_concurrent_sessions` which is always `undefined` from GET `/api/links` response
- Result: Max Concurrent Sessions field always shows "Unlimited" (empty) even if a value was previously set
- Classification: `PARTIALLY_WORKING` — can set the value but cannot read back what was set

---

## E. Does "Save Policy" / "Save Changes" update an existing link or create a new one?

**UPDATES EXISTING LINK — WORKING**

The button labeled **"Save Changes"** (in EditLinkModal) calls PATCH, not POST:

- `AccessScreen.jsx:885` — `<Btn variant="primary" onClick={handleSubmit}>Save Changes</Btn>`
- `AccessScreen.jsx:820-831` — `handleSubmit()` builds patch object
- `AccessScreen.jsx:759-775`:
  ```js
  await window.SecureDocAPI.updateLink(editLinkModal.id, patch)  // PATCH — not createLink
  ```
- `api.js:289-295` — `updateLink()` → `PATCH /api/links/{linkId}`
- `backend/app/routers/links.py:256` — `await db.commit()` on the existing link row
- `backend/app/routers/links.py:261` — `invalidate_link(link.token, link_id=link.id)` — cache cleared for same token
- Backend returns `_link_to_summary(link, base_url)` — same `id`, same `token`, same `share_url`

**Note:** There is no button labeled "Save Policy" in the current UI. The Create Link tab has "Create New Link" (always POST) and the Edit modal has "Save Changes" (always PATCH). If prior reports referenced "Save Policy" that label does not exist in the current codebase.

**UI evidence:** `06_edit_modal.png` — "Save Changes" button at bottom of Edit modal

---

## F. Does "New Link" create a duplicate link?

**NO — creates a blank new link, NOT a copy of any existing link**

- `AccessScreen.jsx:321-332` — "⟳ New Link" button:
  ```jsx
  await window.SecureDocAPI.createLink({ document_id: docId })
  ```
  No label, no policy fields — bare POST creates an empty link
- `api.js:261-270` — `createLink(payload)` → `POST /api/links` — always creates NEW record with NEW token/URL
- Result: A new "Untitled Link" is created with no password, no expiry, no email/domain restrictions, no max views

**UI evidence:** `04_access_control_with_doc.png` — "⟳ New Link" button visible at bottom of Create Link tab

---

## G. Are existing links still shown as "Untitled Link"?

**YES — links with no label display as "Untitled Link"**

- `AccessScreen.jsx:366-369`:
  ```jsx
  <span>{link.label || 'Untitled Link'}</span>
  ```
- Fallback `'Untitled Link'` applies whenever `link.label` is null, undefined, or empty string
- Since no label field exists during creation (see H/I below), all newly created links default to "Untitled Link"

**UI evidence:** `05_links_tab_v2.png` — "Untitled Link" shown as the link title

---

## H. Is link label creation exposed anywhere in the UI?

**PARTIALLY — NO during creation, YES after creation**

**During creation (Create Link tab) — NO:**
- State variable `label_txt` exists at `AccessScreen.jsx:55` but NO JSX in lines 238–337 renders an input bound to it
- Grep of lines 238–337: zero occurrences of `setLabel`, zero occurrences of `label="Label"` or any label-name input field
- `AccessScreen.jsx:120-139` — `handleSave()` includes `if (label_txt) payload.label = label_txt` but the user can never set `label_txt` through the UI — it is permanently `''`
- **UI evidence:** `04_access_control_with_doc.png` — Create Link tab has: Password Protection, Allowed Domains, Allowed Emails, Expiry Date, Max View Count, Max Concurrent Sessions, IP Allowlist, Permissions toggles. **Zero label/name field.**

**After creation (Edit modal) — YES:**
- `AccessScreen.jsx:805` — `const [label_txt, setLabel] = useState(link.label || '');` — initialized from existing link
- `AccessScreen.jsx:838-840` — `<Field label="Label"><input value={label_txt} placeholder="Untitled Link" /></Field>`
- **UI evidence:** `06_edit_modal.png` — "LABEL" field shown as first input in Edit modal, pre-filled with "Untitled Link"

---

## I. Can a user assign a link name during creation?

**NO — NOT DEPLOYED**

- The Create Link tab (`AccessScreen.jsx:238-337`) renders no label/name input
- The underlying state `label_txt` (`AccessScreen.jsx:55`) is wired in `handleSave()` at line 120-139 but permanently empty because no input writes to it
- The "Create New Link" button (`AccessScreen.jsx:318-319`) always fires `handleSave()` which sends `label_txt = ''` → no label is sent

**Classification:** `NOT_DEPLOYED` — the code scaffolding exists (`label_txt` state, payload wiring) but the UI input field was never added to the Create tab.

**UI evidence:** `04_access_control_with_doc.png` — confirmed no label field in Create Link tab

---

## J. Can a user assign a link name after creation?

**YES — WORKING**

Two paths, both confirmed:

**Path 1 — Inline rename via ✎ pencil:**
- `AccessScreen.jsx:371-377` — click ✎ to enter rename mode
- `AccessScreen.jsx:350-361` — inline `<input>` appears; `onBlur` or Enter key triggers save
- `AccessScreen.jsx:155-163` — `handleRename()` → `PATCH {label}`

**Path 2 — Edit modal Label field:**
- `AccessScreen.jsx:838-840` — Label input in EditLinkModal
- `AccessScreen.jsx:759-775` — save → `PATCH` with full policy including label

**UI evidence:** `05_links_tab_v2.png` (✎ pencil icon on link card), `06_edit_modal.png` (Label field in Edit modal)

---

## Full Workflow Trace

```
User clicks "Edit" on a link card
  └─ AccessScreen.jsx:383 — setEditLinkModal(link)
       └─ AccessScreen.jsx:804 — EditLinkModal renders
            └─ User edits fields (Label, Password, Expiry, MaxViews, Domains, Emails, IP, Permissions)
                 └─ AccessScreen.jsx:885 — "Save Changes" clicked → handleSubmit()
                      └─ AccessScreen.jsx:820-831 — build patch object
                           └─ AccessScreen.jsx:759 — window.SecureDocAPI.updateLink(editLinkModal.id, patch)
                                └─ api.js:289-295 — PATCH /api/links/{linkId}
                                     └─ backend/app/routers/links.py:211-281
                                          ├─ per-field guards: if payload.field is not None: link.field = payload.field
                                          ├─ await db.commit()      (line 256)
                                          ├─ invalidate_link(...)   (line 261) — cache cleared
                                          └─ returns SAME link, SAME token, SAME share_url
```

---

## Summary Table

| Question | Answer | Classification | Evidence |
|----------|--------|----------------|----------|
| A. Can user rename existing link? | YES | WORKING | `AccessScreen.jsx:155-163`, `371-377`; `06_edit_modal.png` |
| B. Visible Edit button? | YES | WORKING | `AccessScreen.jsx:383`; `05_links_tab_v2.png` |
| C. Visible pencil icon? | YES | WORKING | `AccessScreen.jsx:371-377`; `05_links_tab_v2.png` |
| D. Edit allowed_emails/domains/expiry/password/permissions/watermark/max_views/IP without new link? | YES | WORKING (max_concurrent_sessions display: PARTIALLY_WORKING) | `AccessScreen.jsx:804-890`; `06_edit_modal.png` |
| E. "Save Changes" updates or creates? | UPDATES existing | WORKING | `AccessScreen.jsx:759`; `api.js:289`; `links.py:256` |
| F. "New Link" creates duplicate? | NO — creates blank new link | WORKING | `AccessScreen.jsx:324`; `04_access_control_with_doc.png` |
| G. Links shown as "Untitled Link"? | YES | WORKING | `AccessScreen.jsx:368`; `05_links_tab_v2.png` |
| H. Label creation exposed in UI? | NO during creation / YES after | PARTIALLY_WORKING | `AccessScreen.jsx:55,238-337,838`; `04` + `06_edit_modal.png` |
| I. Assign link name during creation? | NO | NOT_DEPLOYED | `AccessScreen.jsx:55,238-337`; `04_access_control_with_doc.png` |
| J. Assign link name after creation? | YES | WORKING | `AccessScreen.jsx:155-163,838-840`; `05_links_tab_v2.png`, `06_edit_modal.png` |

---

## Known Gaps

| Gap | Severity | Location |
|-----|----------|----------|
| Label field missing from Create Link tab | UX — new links always start as "Untitled Link" | `AccessScreen.jsx:238-337` — state exists, UI input absent |
| `max_concurrent_sessions` missing from `LinkSummary` GET response | Display only — setting works, display always shows "Unlimited" | `backend/app/schemas/link.py` — field absent from `LinkSummary` |

---

## Final Verdict

**YES — a real customer CAN edit an existing link without generating a new link.**

The Edit button (`AccessScreen.jsx:383`) and ✎ pencil icon (`AccessScreen.jsx:371-377`) are both visible and functional on all non-revoked link cards. Clicking Edit opens `EditLinkModal` which presents every policy field and submits via `PATCH /api/links/{id}` — the existing link record is updated in place. The share URL and token are unchanged after the edit.

The only user-facing gap: links cannot be named at creation time (label input absent from Create tab). Every link starts as "Untitled Link" and must be renamed via Edit or ✎ after creation.
