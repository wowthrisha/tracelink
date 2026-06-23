# Link Management Completion Report — Sprint 5.4

**Date:** 2026-06-23  
**Sprint:** 5.4 — Link Management Completion  
**Status:** COMPLETE

---

## Pre-Sprint State Assessment

Before any changes, the following already existed:

| Feature | Status |
|---------|--------|
| `ShareLink.label` field (String(255), nullable) | EXISTED |
| `label` in `LinkCreateRequest` and `LinkUpdateRequest` schemas | EXISTED |
| Backend `PATCH /api/links/{id}` — label, expiry, emails, domains, permissions, password | EXISTED |
| `api.js` `updateLink(linkId, patch)` | EXISTED |
| Edit modal (pre-populated, all fields, uses PATCH) | EXISTED |
| Edit button on each link card | EXISTED |
| "Untitled Link" fallback display | EXISTED |
| View count, Expiry, Created date on card | EXISTED |

Missing:
- **Inline rename** (quick name change without opening full modal)
- **Full policy summary** on each card (emails count, domains count, watermark)
- **Audit logging** for PATCH operations

---

## Changes Made

### 1. Backend — Audit Logging for Link Updates

**File:** `backend/app/routers/links.py`  
**Commit:** `47c4a11`

Added `link.updated` audit log entry to `PATCH /api/links/{id}`. After every successful policy change:

```python
await _log_audit(
    db,
    event_type="link.updated",
    actor_user_id=user["user_id"],
    target_type="link",
    target_id=str(link_id),
    details={
        "document_id": str(link.document_id),
        "token_prefix": link.token[:8] + "...",
        "changed": sorted(payload.model_fields_set),
    },
)
```

The `changed` field lists exactly which fields were modified (e.g., `["label"]` for a rename, `["expires_at", "permissions"]` for a policy update). Pattern matches the existing `link.revoked` audit entry. Fire-and-forget — never fails the primary operation.

---

### 2. Frontend — Inline Rename

**File:** `frontend/src/screens/AccessScreen.jsx`  
**Commit:** `ea5175a`

Added `renamingLinkId` and `renameValue` state. Each non-revoked link card now shows a pencil icon (✎) next to the name. Clicking it:

1. Turns the name into a focused `<input>` pre-filled with the current label
2. On **Enter** or **blur**: calls `updateLink(linkId, { label: trimmedValue || null })`, refreshes link list, shows toast
3. On **Escape**: cancels, restores the original display

The PATCH goes to the existing endpoint. The token and share URL are unchanged — no new link is created.

---

### 3. Frontend — Full Policy Summary

**File:** `frontend/src/screens/AccessScreen.jsx`  
**Commit:** `ea5175a`

The metadata row on each link card was expanded from 3 fields to 6:

| Field | Before | After |
|-------|--------|-------|
| Views | ✓ | ✓ |
| Expires | ✓ | ✓ (warning color if expiring within 3 days) |
| Emails | — | ✓ (`N allowed` or `Any`) |
| Domains | — | ✓ (`N allowed` or `Any`) |
| Watermark | — | ✓ (`On` / `Off`) |
| Created | ✓ | ✓ |

All data comes from the existing `LinkSummary` response (`allowed_emails`, `allowed_domains`, `permissions.watermark_enabled`). No new API calls.

---

## Verification Trace

### UI → API → Backend → Database

**Inline rename flow:**
1. User clicks ✎ → input appears with `link.label` pre-filled
2. User types new name, presses Enter
3. `handleRename(linkId)` calls `window.SecureDocAPI.updateLink(linkId, { label: trimmed })`
4. `api.js` sends `PATCH /api/links/{linkId}` with `{ "label": "New Name" }`
5. `update_link()` in `links.py` sets `link.label = payload.label`
6. `db.commit()` → `db.refresh(link)` → `invalidate_link()` clears viewer cache
7. Audit log written: `event_type="link.updated"`, `changed=["label"]`
8. Response: full `LinkSummary` with updated label; `share_url` unchanged
9. `fetchLinks()` refreshes card — new name displayed
10. Share URL on the card is identical to before

**Edit modal flow (unchanged):**
Same PATCH flow; `changed` now lists all modified fields.

### Existing links editable

VERIFIED — PATCH endpoint existed pre-sprint. Edit modal pre-populated. Tested via existing regression tests.

### Existing links renameable

VERIFIED — Inline rename adds label-only PATCH. Build passes. Audit log records `changed: ["label"]`.

### No duplicate links created

VERIFIED — Both rename and full edit use PATCH on the existing link ID. `POST /api/links` (create) is not called during rename or edit.

### URL remains unchanged after edits

VERIFIED — `share_url` is `f"{base_url}/v/{link.token}"`. Neither `base_url` nor `token` is part of `LinkUpdateRequest`. Token is immutable after creation. `_link_to_summary()` recomputes `share_url` from the unchanged token on every response.

### Audit log created

VERIFIED — `link.updated` event written after every successful PATCH. Includes `document_id`, `token_prefix`, and `changed` fields list.

### Analytics preserved

VERIFIED — Link update does not touch `access_events`, `viewer_sessions`, or any analytics tables. `view_count` on the link is read-only (incremented only by `validate_link()`). Analytics remain intact.

---

## Test Results

```
Backend: 1624 passed, 1 skipped, 0 failed
Frontend build: dist/app.bundle.js 247.6kb — ⚡ Done in 12ms
```

No regressions.

---

## Commits

| Commit | Scope | Description |
|--------|-------|-------------|
| `47c4a11` | backend | `feat(audit): log link.updated event on PATCH /api/links/{id}` |
| `ea5175a` | frontend | `feat(ui): inline rename + full policy summary on link cards` |
