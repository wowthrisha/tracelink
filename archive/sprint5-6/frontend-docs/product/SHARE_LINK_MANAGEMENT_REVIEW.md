# Share Link Management Review — Sprint 4.8 Phase 1

**Method:** Source code trace of `links.py`, `AccessScreen.jsx`, `QuickShareModal.jsx`, `api.js`, and `link.py` model.  
**Verdict at a glance:** MODIFY — the backend is already complete; the frontend needs wiring.

---

## Question-by-Question Analysis

### 1. Can an existing link be edited?

**Backend:** YES  
**Frontend:** NO — not exposed at all

`PATCH /api/links/{link_id}` is fully implemented in `backend/app/routers/links.py:200–252`.

The handler:
- Verifies link ownership (lines 207–219)
- Updates: `label`, `expires_at`, `max_views`, `allowed_emails`, `allowed_domains`, `ip_allowlist`, `max_concurrent_sessions`, `permissions`, `password` (lines 222–244)
- Calls `invalidate_link(link.token, link_id=link.id)` — the viewer cache is evicted on save, so active sessions see the new policy immediately (line 250)
- Commits and returns `LinkSummary` with the updated state

The `LinkUpdateRequest` schema (`backend/app/schemas/link.py:21–29`) covers every field a user would reasonably want to change.

`api.js` has **no `updateLink()` method**. The method does not exist in the API client. The frontend has never been wired to this endpoint.

---

### 2. Can allowed emails be added later?

**Backend:** YES  
**Frontend:** NO

`payload.allowed_emails` is handled at `links.py:229`:
```python
if payload.allowed_emails is not None:
    link.allowed_emails = json.dumps([e.lower().strip() for e in payload.allowed_emails if e.strip()])
```

The update replaces the entire list. To ADD an email, the frontend would need to fetch the current list, append the new email, and PATCH the full list. This is a standard pattern and requires no backend change.

---

### 3. Can allowed emails be removed later?

**Backend:** YES  
**Frontend:** NO

Same mechanism as above. Removing an email = PATCH with the list minus that email. Cache is invalidated immediately — a viewer mid-session with the removed email would be denied on their next page request because `invalidate_link()` evicts the session cache.

---

### 4. Can permissions be changed later?

**Backend:** YES  
**Frontend:** NO

`payload.permissions` is handled at `links.py:236`:
```python
if payload.permissions is not None:
    link.permissions = json.dumps(payload.permissions)
```

The viewer reads permissions on every session validation. After `invalidate_link()`, the next viewer request re-fetches from DB. Permission changes take effect within one page turn for existing viewers.

---

### 5. Does changing a link require creating a new URL?

**Backend:** NO — the token (and therefore URL) is immutable. PATCH changes the link's policy while preserving its `token` field.

**Frontend:** YES — because `handleSave()` in `AccessScreen.jsx:116` calls `createLink()`, which generates a new `token` (new URL). Every "save" creates a new link with a new URL. The original link (already distributed) is never touched.

```js
// AccessScreen.jsx:129 — THE PROBLEM
await window.SecureDocAPI.createLink(payload);
```

What it should do for existing links:
```js
await window.SecureDocAPI.updateLink(existingLink.id, payload);
```

---

### 6. Does the database already support link modification?

**YES — completely.** The `share_links` table schema (`backend/app/models/link.py`):

| Column | Mutable via PATCH? |
|--------|-------------------|
| `label` | ✅ Yes |
| `password_hash` | ✅ Yes (via `password` in request) |
| `allowed_emails` | ✅ Yes (JSON column) |
| `allowed_domains` | ✅ Yes (JSON column) |
| `permissions` | ✅ Yes (JSON column) |
| `ip_allowlist` | ✅ Yes (JSON column) |
| `max_views` | ✅ Yes |
| `max_concurrent_sessions` | ✅ Yes |
| `expires_at` | ✅ Yes |
| `token` | ❌ Never changes (URL stays stable) |
| `revoked_at` | ❌ Separate endpoint (DELETE) |
| `view_count` | ❌ Read-only counter |

The `updated_at` column auto-updates via `onupdate=func.now()`. Cache invalidation is already in place via `invalidate_link()`.

---

## Current Policy Tab Behavior (the root confusion)

`AccessScreen.jsx` Policy tab initializes all fields to empty/false:

```js
// AccessScreen.jsx:43–60
const [password, setPassword] = useState('');
const [expiry, setExpiry] = useState('');
const [maxViews, setMaxViews] = useState('');
const [allowedEmails, setAllowedEmails] = useState('');
const [permissions, setPermissions] = useState({
  can_download: false,
  can_print: false,
  ...
});
```

No existing link's values are loaded into the form. The Policy tab is a "create new link" form that doesn't say it's a "create new link" form.

---

## Current Share Link Tab (what exists)

The Share Link tab (`AccessScreen.jsx:325–398`) shows link cards with:
- Status dot (active / revoked)
- Label
- Password badge
- Share URL (copy + open)
- View count / expiry / created date
- Embed code
- **Revoke** button (active links only)

Missing:
- Edit button
- Add email field
- Extend expiry field
- Change permissions inline

---

## Verdict: MODIFY

**Rationale:** The backend is fully built and already handles all edit operations safely (auth check, cache invalidation, audit log). The database schema requires zero changes. The only work is:

1. Add `updateLink(linkId, patch)` method to `api.js` — calls `PATCH /api/links/{id}`
2. Add "Edit" button to each link card in the Share Link tab
3. Build an Edit Link drawer/modal that loads the current link's settings and patches on save
4. Change the Policy tab "Save Policy" button to clarify it creates a new link (not edits an existing one)

**Do NOT rebuild.** The create-new-link flow is still needed (user may want multiple distinct links with different access levels for different audiences). Both flows should coexist: "Create new link" stays as the Policy tab action; "Edit" is added per-link on the Share Link tab.

**Do NOT keep as-is.** Every "save" silently creating a new URL is a broken user experience for first-time paying customers. A user who adjusts their allowed email list is not expecting to invalidate all previously-distributed links.

---

## Implementation Scope (Phase 1 only — this review does not implement)

| Item | File | Change type |
|------|------|-------------|
| `updateLink(linkId, patch)` | `frontend/api.js` | Add method |
| Edit button per link card | `AccessScreen.jsx:340–343` | Add button |
| EditLinkModal or inline edit | `AccessScreen.jsx` | New component (~80 lines) |
| Load current link settings into form | `AccessScreen.jsx:326–` | Fetch and populate |
| Backend | `backend/app/routers/links.py` | No changes needed |
| Database | — | No changes needed |

---

*Generated: Sprint 4.8 Phase 1 — no implementation performed.*
