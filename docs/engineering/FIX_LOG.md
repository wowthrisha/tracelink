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

---

## Historical entries merged from root `FIX_LOG.md` (V18.0 documentation cleanup, 2026-07-31)

The root-level `FIX_LOG.md` (base commit `2c1795f`, V4.0 remediation through Sprint 7.0) was never folded into this canonical log, leaving a gap between "Sprint C" above and "Sprint V10.0" below. Merged here verbatim, in its original chronological order (V4.0 remediation first, then Sprint 7.0, then Sprint V6.0 — the root file's own internal ordering), before archiving the root copy. Evidence: source-verified during the V18.0 repository certification sprint's documentation audit.

### V4.0 remediation (committed as `31e2966`, pushed to `origin/main`)

- **AUTH-001** — No password requirements shown during signup. `LoginScreen.jsx`: added a conditional hint ("At least 6 characters.") under the password field in signup mode, matching the existing 6-char minimum used in reset-password validation. Tests: 13/13 frontend, build succeeded (306.1kb). Regression risk: none — additive, scoped to `mode === 'signup'`.
- **AUTH-002** — No show/hide password toggle. `LoginScreen.jsx`: added `showPassword` state + toggle button switching the input's `type` between `password`/`text`. Regression risk: low — new state only, no existing handler changed.
- **AUTH-007** — Raw "Failed to fetch" error shown on connection failure. `LoginScreen.jsx`: added a case-insensitive branch catching `failed to fetch`/`network`/`load failed` before the catch-all, replacing it with "Unable to reach the server. Check your connection and try again." Regression risk: low — purely additive, existing special-cased messages checked first.
- **DASH-001** — "Upload Dashboard" title was misleading (the screen is a full document hub, not just uploads). `atoms.jsx`: `'Upload Dashboard'` → `'Documents'` in the shared `titles[screen]` map. Regression risk: none, copy-only.
- **DASH-003** — Security notice not prominent. `UploadScreen.jsx`: moved the "documents converted to images, downloads disabled" notice from a 10px footer span into a bordered banner directly under the page header. Regression risk: none, layout-only.
- **DASH-008** — "+ New group" button easy to miss. `UploadMetadataPanel.jsx`: `variant="ghost"` → `variant="secondary"` (existing `Btn` variant, no new styling code). Regression risk: none, prop-only.
- **ANAL-006** — Groups sidebar widget silently capped at 5 with no indication more exist. `AnalyticsScreen.jsx`: added `showAllGroups` toggle state; "Show all N"/"Show fewer" button appears when `groupStats.length > 5`. Regression risk: low — new state defaults to the prior capped behavior.
- Suite-wide verification: frontend 13/13, build succeeded (306.1kb), backend 1699 passed/1 skipped, `TODO`/`FIXME`/`console.log`/`debugger` grep clean on touched files.

### Sprint 7.0 (17 items fixed; full reasoning was in the now-archived `WORKFLOW_COMPLETENESS.md`/`ARCHITECTURE_SCORECARD.md`/`SECURITY_STATUS.md`/`REPOSITORY_HEALTH.md`)

- **View-limit-reached mislabeled as "Link Expired"** — `useViewerSession.js` classified every non-`revoked` 410 as `'expired'`; added a `detail.includes('view')` branch producing a distinct `view_limit_reached` status with a matching `AccessGate.jsx` message.
- **Broken network-error fallback in the viewer (dead end)** — `usePageLoader.js`'s catch block fell back to a bare `<img src=...>` with no auth header, guaranteed to 400 with no explanation. Removed the broken fallback, set a real `pageError`, added a `retryPage()` + Retry button in `ViewerScreen.jsx`.
- **Garbled HTML-entity icons in `AccessGate`** — literal `"&#x1F50D;"`-style strings don't decode inside a JSX `{expression}`; replaced all 5 with real emoji characters.
- **No warning for protected links with no expiry** — `AccessScreen.jsx`: added a conditional hint on the Expiry field when `(password || allowedEmails) && !expiry`.
- **No tooltip distinguishing Revoke from Delete (ACCESS-002)** — `atoms.jsx`'s shared `Btn` gained a forwarded `title` prop (backward-compatible addition); wired on `AccessScreen.jsx`'s Revoke/Delete buttons.
- **"Revoke All Access" always claimed success** — `AccessScreen.jsx`'s `handleRevoke` swallowed per-link failures in a bare `try{}catch{}` then unconditionally toasted success. Switched to `Promise.allSettled` with accurate success/partial/failure reporting.
- **Storage retention change fired with no confirmation (STOR-002)** — `StorageScreen.jsx`: retention `<select>`'s `onChange` now opens a confirmation modal describing the consequence; the PATCH only fires on explicit confirm.
- **Storage per-document table had no empty state** — `StorageScreen.jsx`: added a "No documents yet..." empty row.
- **Document/group delete: missing loading state, modal-closes-before-resolve** — `UploadScreen.jsx`: wired `loading={deleting}` on the document-delete button; added `deletingGroupId` and moved the group-delete modal's close to only happen on success.
- **API key delete confirmation had wrong copy** — was copy-pasted from the webhook delete modal ("delivery history"); corrected to API-key-accurate copy.
- **Password reset left a stale, reusable-looking token in the URL** — `LoginScreen.jsx`: calls `history.replaceState` to strip the `#access_token=...&type=recovery` fragment after a successful reset.
- **Audit log export silently truncated at 500 with no warning** — `AuditLogScreen.jsx`: CSV/JSON export handlers now compare exported row count against the known filtered total and show an accurate "Exported N of M" warning when truncated.
- **Org member self-removal ("leave org") was broken for non-admins** — `orgs.py:remove_member` called `_get_org_and_member(..., minimum_role="admin")`, raising 403 before the function's own self-removal bypass ever ran, contradicting the code's own "allow self-removal at any role" comment. Resolved caller at `minimum_role="viewer"`, enforcing the admin requirement only when `not is_self`. 2 new regression tests + all pre-existing member-removal tests passed (54/54 in `test_enterprise_phase4.py`).
- **Org member removal had no confirmation dialog** — `OrgsScreen.jsx`: added a `removeModal` confirmation matching the existing org-delete pattern.
- **`groups.py` missing scope enforcement** — all 7 endpoints used bare `Depends(get_current_user)` instead of `Depends(require_scope(...))`, unlike `documents.py`/`links.py`/`webhooks.py` — an API key scoped only to `documents:read` could mutate group membership. Fixed to match the existing convention; zero behavior change for JWT/browser users (94/94 tests passed across 3 affected suites).
- **`groups.py:assign_documents_to_group` N+1 query** — replaced a per-document-ID `SELECT` loop with a single `WHERE Document.id.in_(doc_uuids)` query.
- **Document upload missing audit log entry** — `document.uploaded` wasn't audited while `document.deleted` was, with no technical justification; added, mirroring the existing best-effort try/except-swallow pattern.
- **Misleading "uploader-facing" comment on `resolve_annotation`** — comment claimed owner-only access; the route is actually reachable by any session on the link with no ownership check. Doc-only fix; the permission question itself was deliberately left for a product/security decision.
- **Duplicated `_get_session_id`, `fmtDate`, and `admin.py` role-check logic** — consolidated onto existing shared implementations across `annotation_service.py`, `admin.py`, `viewer.js`, and 4 screen files.
- **Unused imports removed** — `documents.py` (`get_current_user`), `webhooks.py` (`Optional`, `get_current_user`), `storage.py` (`func`), `orgs.py` (`Query`) — each confirmed unused via full-file grep before removal.
- **Test fragility: bundle-mangling regex didn't account for `$`-prefixed minified names** — `test_bundle_ends_with_reactdom_render` used `\w+`; esbuild's minifier can emit `$`-prefixed identifiers once it exhausts short alphanumeric ones. Changed to `[\w$]+`.
- Suite-wide verification: frontend 13/13, build succeeded (310.0kb), backend 1701 passed/1 skipped, single linear Alembic head (`026`), `TODO`/`FIXME`/`console.log`/`debugger`/stray `print(` grep clean.

### Sprint V6.0 — Engineering Governance fixes (full reasoning was in the now-archived `ENGINEERING_GOVERNANCE.md`/`MODULE_BOUNDARIES_AND_CODE_QUALITY.md`/`UI_API_CONTRACT.md`/`SECURITY_GOVERNANCE.md`/`SCALABILITY_REVIEW.md`/`CONSISTENCY_MATRIX.md`/`REPOSITORY_HEALTH.md`)

- **Webhook deliveries silently non-functional in production (most severe finding this sprint)** — `celery_app.py`'s `include=[...]` omitted `app.workers.webhook_tasks`; a real worker process only registers tasks from modules listed in `include=`, so `securedoc.deliver_webhook` was never registered and every enqueue silently went nowhere. One-line fix adding the missing module; added `test_all_task_modules_are_registered_with_the_worker` asserting all 8 expected task names register after `import_default_modules()` (mirrors real worker boot — directly importing the module, which other tests did, masks an `include=` omission entirely).
- **`annotations.py` wrongly denying org members access to shared documents** — 10 inline ownership checks were narrower than `documents.py`'s existing `_get_accessible_document()` (which also grants org-member access via `OrgMembership`). Consolidated all 10 sites onto the shared helper; denied access now returns 404 instead of 403, matching `documents.py`'s no-existence-leak convention.
- **`links.py`/`link_service.py` duplicated "is link active" logic** — the router's display flag and the service's actual enforcement independently computed revoked/expired/max-views status and disagreed at the exact expiry boundary. Extracted a single `is_link_active(link, now)` predicate matching real enforcement; the display flag is now strictly more accurate.
- **`orgs.py` duplicated "last owner" check** — extracted `ensure_not_last_owner(db, org_id)`, called from both `update_member_role` and `remove_member`.
- **Webhook audit-logging gap** — entire webhook screen had zero audit coverage; added `webhook.created`/`webhook.updated`/`webhook.deleted`, mirroring the existing document-audit pattern.
- **Storage retention-change audit-logging gap** — added `document.retention_changed`.
- **`api_key.rotated` missing from the filterable audit-event enum** — logged correctly but never added to `AUDIT_EVENT_TYPES`, making it permanently unselectable in the Audit Log filter and rejected 422 if queried directly.
- **Three CSV exports in `AccessScreen` with zero error handling** — `exportFeedback`/`exportReviewerActivity`/`exportVisualAnnotations` were bare un-awaited promise expressions; wrapped in `try/await/catch` with a toast, matching every other action on the screen.
- **Copy-to-clipboard reports success even when the copy fails (3 screens)** — `AccessScreen.jsx`/`ApiKeysScreen.jsx`/`WebhooksScreen.jsx` showed a success toast without awaiting the clipboard promise; toast now fires only on confirmed success, with a failure branch.
- **Viewer search: network error indistinguishable from "no matches"** — `SearchPanel.jsx`: added a `searchError` state so a failed request shows "Search failed — check your connection and try again" instead of the misleading "No matches found."
- **Extract Sidecars: silent failure** — `ViewerInfoPanel.jsx`: replaced an empty `catch {}` with a toast on failure.
- **Billing Refresh: completely silent failure** — `BillingScreen.jsx`'s `load()` never set the screen's `error` state on a non-OK response and had an empty catch block — the only action across all 12 screens with zero user-facing failure feedback at the time. Fixed to reuse the screen's existing error-display block.
- **Two destructive-dialog consistency fixes** — Delete Document modal now names the document itself, not just its share links; Storage retention modal uses the standard warning template for destructive changes and a lighter style for the safe "never" option.
- **Dead code removed**: `frontend/src/components/analytics/RangeBtn.jsx` (deleted, zero references), `frontend/api.js:formatBytes()` (removed, `StorageScreen.jsx` has its own), CSS classes `.header-btn-label`/`.screen-enter` (removed, zero usages), and **`frontend/docs/`** (removed — a 3-level-deep directory tree with zero files at any level). *(Note, added during the V18.0 merge: this is why `archive/README.md`'s references to `frontend/docs/production/`, `frontend/docs/governance/`, etc. are stale — that tree no longer exists; corrected as part of this same cleanup pass.)*
- **`WebhookDelivery` composite index** — `get_deliveries()` filters on `webhook_id` and sorts by `created_at DESC`; the prior index only covered the filter. Added a composite index covering both.
- Suite-wide verification: frontend 13/13, build succeeded (311.3kb), backend 1702 passed/1 skipped.

---

## Sprint V10.0 — Autonomous Product Excellence (2026-07-23)

Continuation of the V6.0/V7.0 governance-sprint backlog, executed under explicit autonomous-fix authority ("fix it, or document exactly why not — without asking for confirmation"). Full narrative in `ACTION_LOG.md`; this section is the condensed fix-by-fix record.

### V10-1: Broken wrong-password shake animation

- **Root cause**: `AccessGate.jsx` referenced `animation: 'shake .4s'` but `@keyframes shake` was never defined in the shared stylesheet.
- **Files changed**: `frontend/SecureDoc.html`
- **Fix**: added the missing keyframe next to the app's other 8 shared keyframes.
- **Tests**: `npm test` (13/13), `npm run build` (clean).
- **Regression risk**: none — purely additive CSS.

### V10-2: 9 hand-rolled modals migrated onto the shared `Modal` component

- **Root cause**: `ApiKeysScreen.jsx` (2 modals), `WebhooksScreen.jsx` (3), `OrgsScreen.jsx` (4) each hand-rolled their own `position:fixed` overlay instead of using the shared, accessible `Modal` component — losing focus-trap, Escape-to-close, and entrance animation simultaneously.
- **Files changed**: `frontend/src/screens/{ApiKeysScreen,WebhooksScreen,OrgsScreen}.jsx`
- **Fix**: converted each to `<Modal open onClose={...} title="..." width={...}>`. Two modals with subtitles (webhook URL, member count) had their subtitle moved into the body since `Modal`'s `title` prop is rendered via `aria-label={title}` and must stay a plain string. One modal (`MembersPanel`) had a "+ Invite Member" action button in its header row, which `Modal` doesn't support alongside title+close — moved into the body as a first-row action instead. `OrgsScreen.jsx`'s `MembersPanel` also renders two sibling overlays (`InviteMemberModal`, a remove-confirmation `Modal`) that previously lived inside the same hand-rolled wrapper `<div>` — restructured as a `<>` fragment with three independent top-level overlays instead of one nesting the others.
- **Tests**: `npm test` (13/13), `npm run build` (clean, bundle shrank 311.3kb→308.4kb from removed duplicate header markup). Live browser verification was attempted via the `run` skill but not completed — no project-specific run skill exists and the app requires real Supabase credentials not available in this environment; see `SCREENSHOT_INDEX.md` for the full reasoning. Verification instead relied on build success, the test suite, and direct comparison of each converted site against `Modal`'s exact prop contract read from `atoms.jsx`.
- **Regression risk**: low-medium given the lack of live verification — flagged honestly rather than claimed as fully verified. The mechanical transformation (strip manual header, add `title`/`width` props, remove one level of DOM nesting) is the same pattern applied 9 times with no logic changes to any handler, which bounds the risk.

### V10-3: `Toggle` component missing accessible names

- **Root cause**: `AccessScreen.jsx`'s two `Toggle` usages never passed the `label` prop despite the label text already being in scope at both call sites.
- **Files changed**: `frontend/src/screens/AccessScreen.jsx`
- **Fix**: pass `label={labelText}` at both sites.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none.

### V10-4: Blocking synchronous PDF write in `download_document`

- **Root cause**: `viewer.py:download_document`'s final `writer.write(tmp_f)` call was synchronous CPU+disk-bound work executed directly on the event loop, unlike the per-page watermarking step immediately above it, which correctly used `run_in_executor`.
- **Files changed**: `backend/app/routers/viewer.py`
- **Fix**: wrapped the write + `os.path.getsize` in a helper function, offloaded via `run_in_executor`, mirroring the existing pattern one line above.
- **Tests**: full backend suite (1702 passed) plus a targeted run of every test file referencing the download endpoint (20/20 passed). **Regression risk**: low — behavior-preserving, only the execution context of the write changed.

### V10-5: Two genuinely silent failure points given real logging

- **Root cause**: `links.py:_get_base_url_for_doc`'s custom-domain lookup and `webhooks.py`'s test-ping Celery dispatch both wrapped their only failure path in `except Exception: pass` with zero logging — a broker-connectivity problem or a broken custom-domain lookup would have been completely invisible.
- **Files changed**: `backend/app/routers/links.py`, `backend/app/routers/webhooks.py` (both gained a module logger)
- **Fix**: added `logger.warning`/`logger.error` calls with `exc_info=True` before falling through to the existing (unchanged) fallback behavior.
- **Tests**: full backend suite (1702 passed). **Regression risk**: none — logging-only addition, no control-flow change.

### V10-6: Spacing-token scale added

- **Files changed**: `frontend/src/constants/tokens.js`
- **Fix**: added an `S` export (`xs`/`sm`/`md`/`lg`/`xl`/`xxl` = 4/8/12/16/20/24) matching the values that had already organically converged across the app, per V7.0's frontend-maturity research. Existing call sites were deliberately NOT retrofitted — that's a broad mechanical sweep, correctly out of scope for a same-session addition (see `ARCHITECTURE_DECISIONS.md`).
- **Tests**: `npm run build` (clean — the export is unused by existing code, so this is a zero-risk addition). **Regression risk**: none.

### V10-7: Delete/revoke toast severity standardized

- **Root cause**: `AccessScreen.jsx`'s single-link revoke/delete toasts used `'info'` severity while every other screen's equivalent action (`ApiKeysScreen`, `WebhooksScreen`, `OrgsScreen`, `UploadScreen`) uses `'success'`.
- **Files changed**: `frontend/src/screens/AccessScreen.jsx`
- **Fix**: changed both to `'success'`. Left the bulk "Revoke All Access" toast's `'error'` severity unchanged — that's a pre-existing, seemingly deliberate choice to visually emphasize a higher-stakes bulk action, not the same inconsistency.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none, cosmetic only.

### Investigated and correctly NOT fixed — false positives caught before acting

- **H-2** (viewer arrow-key navigation "missing"): `useViewerLayout.js:70-96` already implements this correctly; the earlier research agent's grep missed the hook file. No change made.
- **H-6** (no production enforcement for `ip_hash_salt`/`domain_verify_salt`): `main.py:27-54` already enforces this at import time, bundled with other production-readiness checks. A redundant duplicate validator was briefly added to `config.py` then reverted once this was found.
- **M-4 (13 of 15 sites)**: wrap `log_audit_event()`, which already self-logs every failure internally (`audit_service.py`) — not actually silent despite looking that way at the call site.
- **M-2** (6 screens with zero `aria-label`): every interactive control on those 6 screens already has an accessible name via visible text content; `AppShell.jsx` has no interactive controls of its own. No redundant labels added.

Catching these before acting on them is treated as real, valuable output of this session — implementing a "fix" for a problem that doesn't exist is worse than doing nothing, and the mission's autonomy grant doesn't waive the obligation to verify.

---

## Suite-wide verification (Sprint V10.0, run after all fixes above)

- `cd backend && python -m pytest tests/unit tests/integration tests/regression -q` → **1702 passed, 1 skipped, 0 failed** (run 4 times across this session's checkpoints, consistently clean)
- `cd frontend && npm test` → **13/13 passed**
- `cd frontend && npm run build` → succeeded, `dist/app.bundle.js` 308.4kb (down from 311.3kb)

---

## Sprint V11.0 — Viewer Excellence (2026-07-25)

Mission asked for a from-scratch "Adobe Acrobat + DocSend + Kindle" Viewer redesign. Before writing code, confirmed via research pass that the reading status bar (timer, tab-blur pause/resume, page progress) and the entire backend Reading Intelligence Engine (3 tables, EWMA speed model, 6 engagement scores, drop-off detection, NL insights, 6 REST endpoints) **already exist** from an earlier sprint — rebuilding them would have been pure waste. Full reasoning for what was deliberately scoped out (generic feature-toggle framework, device/browser/country/timezone capture, reading replay, speed-trend charts, blanket pixel-level UI review): `ARCHITECTURE_DECISIONS.md` AD-7 through AD-11.

### V11-1: INSIGHTS-PUBLIC-001 — Insights modal exposed to public share-link viewers

- **Root cause**: `frontend/src/screens/ViewerScreen.jsx` — `hasInsights` (passed to `ViewerToolbar`) and the `InsightsModal` render condition both checked only `doc?.id || session?.document_id`, never `publicToken`. A genuinely anonymous share-link viewer could see and click the "Insights" button (a comment even claimed "owner-only" without the code enforcing it). All 4 underlying fetches require `analytics:read` scope and 401 for a public viewer — and `frontend/api.js`'s `getDocumentReadingSummary/Heatmap/Insights/Viewers` all call `_clearAndReload()` on 401, which force-reloads the viewer's page mid-session.
- **Fix**: added `!publicToken` to `hasInsights`, the modal's render condition, and the data-fetch callback (defense in depth — even if `showInsights` were somehow set true another way, the fetches never fire for a public viewer).
- **Files**: `frontend/src/screens/ViewerScreen.jsx`.
- **Tests**: frontend suite 13/13, build clean. No dedicated regression test added (pure conditional-rendering change, not independently testable without a browser — verified via source/prop-usage confirmation, consistent with how `useViewerSession.js`'s READ-OWNER-001 fix was verified in the prior sprint).

### V11-2/V11-3: Viewer-facing page-insights panel + show_reading_insights permission

New, genuinely-missing feature (not a bug fix): the mission's "average reading time on this page / difficulty / predicted remaining / pace vs. average reader" panel didn't exist for viewers — those concepts were computed server-side but only ever exposed via uploader-only endpoints.

- **Backend**: extended `ReadingAnalyticsService.get_viewer_session_summary()` (the existing viewer-safe `/api/reading/session/{id}` endpoint — no new endpoint needed) with 3 new fields: `difficulty` (Easy/Moderate/Complex, derived from the existing `DocumentComplexity.complexity_factor` via a new `_complexity_to_difficulty_label()` helper), `current_page_avg_ms` (average `active_time_ms` across all sessions for this exact page, a simple indexed `AVG()` query against `page_reading_events`), and `pace_vs_average` (`faster`/`typical`/`slower`, comparing this session's `avg_ms_per_page` against the mean of all *other* sessions' `avg_ms_per_page` for the same document, with a 10% deadband to avoid noise).
- **Permission gate**: added `show_reading_insights` (default `false`) to the existing `ShareLink.permissions` JSON blob — reusing the established pattern (`backend/app/services/viewer_session_service.py`'s defaults dict, `AccessScreen.jsx`'s hints/defaults/grid in both the Create-Link and Edit-Link forms) rather than building a new toggle subsystem. The 3 new fields are nulled out in the router (`backend/app/routers/reading.py`) unless the link's permission is on — deliberately done as a response-filter in the router (not a query-skip in the service) so the logic stays in one obvious place. **Bug caught and fixed during implementation**: `ShareLink.permissions` is a `Text` column storing a JSON *string*, not an ORM-level dict — the first draft of the router code called `.get()` directly on the raw string, which would have thrown `AttributeError` on every single request. Caught via source re-verification before running any test, not by a failing test.
- **Frontend**: `useReadingAnalytics.js` gained a new `insights` return value, populated by a 20s-interval fetch of the (already-existing, previously-unused-by-any-frontend-code) `getViewerReadingSummary()` API client method. `ReadingStatusBar.jsx`'s existing "Reading Insights" expanded panel now shows a Difficulty stat plus two natural-language sentences ("Most readers spend about Xs on this page." / "You are reading faster/slower/at a typical pace...") when the uploader has enabled the toggle — and renders nothing extra when they haven't, since the backend simply returns nulls (no permission flag needs to be threaded through the frontend).
- **Files**: `backend/app/services/reading_analytics_service.py`, `backend/app/routers/reading.py`, `backend/app/services/viewer_session_service.py`, `frontend/src/hooks/useReadingAnalytics.js`, `frontend/src/screens/ViewerScreen.jsx`, `frontend/src/components/ReadingStatusBar.jsx`, `frontend/src/screens/AccessScreen.jsx` (3 duplicated permission-key locations, all updated for consistency).
- **Tests**: 2 new integration tests added — `test_viewer_session_insights_hidden_by_default` (confirms all 3 new fields are null with the permission off) and `test_viewer_session_insights_shown_when_enabled` (confirms difficulty + current-page-average populate when it's on; pace_vs_average asserted `None` since a single-session document has nothing to compare against — not faked). Full existing `test_reading_analytics.py` + `test_reading_api.py` suites re-run clean (67 → 69 passed). Full backend suite: 1705 passed (up from 1703), 1 skipped, 0 regressions.

### V11-4: Error boundary leaked raw error text

- **Root cause**: `frontend/src/components/ViewerErrorBoundary.jsx` rendered `String(this.state.error)` directly to the user — for a standard JS `Error`, that's `"Error: <internal message>"`, not a stack trace, but still raw internal error text a non-technical user shouldn't see (and support has no way to correlate it to console/server logs).
- **Fix**: replaced with a fixed, friendly message ("Something went wrong opening this document... try again, or contact support with the reference code below") plus a generated correlation ID (`err_<timestamp36><random4>`) shown in the UI and logged alongside the real error object in `componentDidCatch`'s `console.error` call — the real error never leaves the console.
- **Files**: `frontend/src/components/ViewerErrorBoundary.jsx`.
- **Tests**: frontend suite 13/13, build clean.

### Suite-wide verification (Sprint V11.0, run after all fixes above)

- `cd backend && python3 -m pytest tests/unit tests/integration tests/regression -q` → **1705 passed, 1 skipped, 0 failed**
- `cd frontend && npm test` → **13/13 passed**
- `cd frontend && npm run build` → succeeded, `dist/app.bundle.js` 312.2kb
- **Deploy status**: all 4 fixes exist only in the local working tree — not committed, not pushed, not deployed, consistent with this session's standing git policy.

---

## Sprint V12.0 — Final Production Certification (2026-07-26)

Golden rule this sprint: browser evidence over source code, re-verify everything rather than trusting prior reports. Method: Playwright against the live deployed instance, starting from the browser (not source) for every check.

### First: re-verified all 3 V10.0 fixes are live in production

Before any new work, re-checked WATERMARK-001, READ-OWNER-001, and BILLING-PLAN-BADGE-001 (all fixed and committed as `e7ddf47` in the V10.0 sprint, but never explicitly deployed by this session). Discovery: `origin/main` was already at `e7ddf47` — the commit had been pushed (not by this session) and Railway's auto-deploy had shipped it. Confirmed all 3 fixes live:
- Watermark: fetched a real live page via a genuinely anonymous, password-verified session; 8x-contrast-enhanced crop shows a correctly tiled, visible watermark (was invisible before the fix).
- Owner-lockout: clicking a document with an active password-protected link from the owner's own dashboard no longer shows the password gate.
- Plan badge: 3 fresh page loads all correctly show "PRO" in the sidebar (was "FREE" before the fix, confirmed via the identical 3-fresh-loads methodology used to originally find the bug).

### V12-1: AUDIT-LINK-COMMIT-001 — Link lifecycle events silently never appeared in the Audit Log (High, security-relevant)

**Found via**: live browser evidence, not source reading. After editing a link's Annotations permission (see V12-2 below) and confirming it correctly propagated to the viewer, checked the Audit Log expecting to see the edit recorded — the log's own description promises "configuration changes" are tracked. Queried the raw `/api/admin/audit-log` API directly (bypassing the frontend) to rule out a display bug: **zero `link.*` events existed among any of this session's link creations/edits**, despite `links.py` visibly calling `log_audit_event(event_type="link.created", ...)` on every request.

**Root cause**: `log_audit_event()` (`app/services/audit_service.py`) does `db.add(entry); await db.flush()` — it never commits, by design (so callers can batch it into their own transaction). In 3 of `links.py`'s 4 audit-logging call sites (`create_link`, `revoke_link`, `update_link`), the *primary* action (`link_svc.create_link()`, `link_svc.revoke_link()`, or the router's own field updates) had **already called `db.commit()` before** the audit-log call — meaning the audit entry was added and flushed into a *new*, separate transaction that nothing ever committed. On a real per-request session lifecycle, that transaction rolls back when the session closes, silently discarding the audit row. The 4th call site (`delete_link_permanently`) was already correct — its `db.commit()` comes *after* the audit-log block, in the same transaction.

**Why local tests never caught this**: the test suite's `db_session` fixture shares one long-lived, never-closed `AsyncSession` across the whole test (both the app's `get_db()` override and the test's own assertions use the identical session object) — so a flushed-but-uncommitted row is still visible to an in-test query, masking the exact failure mode that breaks on a real, isolated per-request session.

**Fix**: added `await db.commit()` immediately after the audit-log call in all 3 buggy sites (`links.py`). Also added `link.created`, `link.updated`, `link.deleted` to `AUDIT_EVENT_TYPES` (`app/models/audit.py`) — only `link.revoked` was previously in that allowlist, meaning even a correctly-committed `link.created`/`link.updated`/`link.deleted` event couldn't be selected as an explicit filter option in the Audit Log UI (though it would still have appeared in the unfiltered "All events" view).

**Regression tests**: 3 new tests in `tests/regression/test_link_lifecycle.py`, using a rollback-based verification helper (`_assert_audit_event_truly_committed`) that calls `db_session.rollback()` before querying — this is the one technique that actually distinguishes "flushed" from "committed" within the shared-session test fixture, closing the exact gap that let this bug ship unnoticed. **Verified the tests are meaningful, not tautological**: ran them against the pre-fix code via `git stash` — all 3 failed with a clear assertion message; restored the fix — all 3 passed.

**Files**: `backend/app/routers/links.py`, `backend/app/models/audit.py`, `backend/tests/regression/test_link_lifecycle.py`.
**Tests**: full backend suite 1708 passed (up from 1705), 1 skipped, 0 failures.
**Deploy status**: fixed locally, not yet deployed.

### V12-2: Verified live — Edit Link permission changes propagate immediately to active viewers (no bug, but genuinely load-bearing verification)

Direct test of the mission's explicit "Edit Link MUST update immediately... permissions... everything updates live" requirement: created a link with Annotations OFF, confirmed via a real anonymous browser session that the annotation toolbar was absent; as the owner, edited that *same* link's Annotations permission to ON and saved (confirmed via network trace: `PATCH /api/links/{id}` fired); re-opened the *same* anonymous session against the *same* link URL (no new link, no page reload of an existing tab — a fresh navigation simulating the viewer re-visiting) and confirmed the annotation toolbar now appears, and that clicking it fires a real `GET /api/viewer/annotations/{token}/{page}` call with no console errors. This is genuine, correct, working functionality — recorded as positive verification, not a fix.

### V12-3: Verified live — Reading Intelligence pause/resume on tab blur, with a stronger-than-expected security behavior

Dispatched real `blur` and `visibilitychange` (`document.hidden = true`) events against a live, actively-reading anonymous session. Result: not only does the reading timer pause (status bar changes from a live-incrementing value to "Waiting…"), the **entire document content visibly blurs** while the tab is hidden/unfocused — a deliberate anti-shoulder-surfing/anti-screen-capture behavior beyond what the mission's checklist named. On resume (`focus` + `document.hidden = false`), content un-blurs and the timer resumes from near-zero, confirming inactive time is correctly never counted (screenshots: `docs/ui-audit/Screenshots/Viewer/`).

### V12-4: Verified live — Reading Intelligence uploader-side data is real, not fabricated

Opened the owner-only Insights modal after generating real anonymous reading activity. Pages tab: "53 TOTAL VIEWS" with a real per-page breakdown matching actual test traffic. Reading tab: aggregate engagement score computed from "1 SESSION" (only sessions with enough batched active-time data are counted — most of this session's very-short test visits correctly did *not* inflate the session count), with `AVG ACTIVE`/`COMPLETION`/`MEDIAN` showing `0s`/`—`/`—` rather than fabricated numbers when there isn't enough data to compute them meaningfully. This directly satisfies the mission's "No fabricated metrics" requirement.

### V12-5: Verified live — Keyboard-only navigation works correctly

Sidebar nav items are `<div role="button" tabIndex={0}>` (not native `<button>`/`<a>`), which looked like a potential accessibility gap on first glance — but they correctly implement `onKeyDown` for Enter/Space (`app/components/atoms.jsx`). Verified functionally, not just by reading source: Tab×3 + Enter from a fresh page load correctly navigated to the Access Control screen with no mouse interaction.

### Verified as correct, not a bug: mobile block

Loading the app at a 390×844 mobile viewport shows a clear, deliberate message: "SecureDoc beta requires a desktop browser... Mobile support is planned for a future release." Matches the existing, already-documented product decision (`ARCHITECTURE_DECISIONS.md` AD-6) — re-confirmed live rather than assumed from the earlier finding.

### Noted, not fixed: owner's own preview watermark shows "anonymous"

When the document owner previews their own document (through the owner-preview link mechanism — see `READ-OWNER-001` from V10.0), the watermark reads "anonymous · <date> · sess:<id>" rather than the owner's real, known email. Minor, cosmetic, not a security issue (the owner already knows it's their own preview) — noted for completeness rather than fixed this sprint, since it touches the same owner-preview-link machinery as READ-OWNER-001 and deserves its own scoped look rather than a rushed change alongside everything else found this sprint.

### Suite-wide verification (Sprint V12.0)

- `cd backend && python3 -m pytest tests/unit tests/integration tests/regression -q` → **1708 passed, 1 skipped, 0 failed**
- Live browser verification: `docs/ui-audit/Screenshots/{Viewer,Access_Control,Upload}/` (this sprint's shots interleaved with earlier sprints' — see `docs/engineering/SCREENSHOT_INDEX.md` for the full index)
- **Deploy status**: V12-1 (the audit-commit fix) is local-only, not deployed. Everything else this sprint was verification of already-live (V10.0) or already-correct behavior — no other new code changes.

---

## Sprint V13.0 — Repository Cleanup (2026-07-26)

Method: `ruff` (installed for this session) for AST-verified unused-import/unused-variable detection — not manual grep guessing. Every finding below is source-code verified; nothing was removed on a "looks unused" heuristic.

### Unused imports (26 found, 23 removed, 3 restored with explanation)

`ruff check --select F401 --fix` removed 26 genuinely unused imports across 7 files (`metrics.py`, `models/reading_analytics.py`, `routers/{analytics,annotations,api_keys,documents,links,reading,viewer}.py`, `services/{analytics_service,org_service,reading_analytics_service,retention,text_processor,viewer_cache}.py`). Zero regression risk by construction — an unused import cannot affect runtime behavior.

**Caught before it became a real break**: the auto-fix removed `clear_page_cache`, `clear_thumb_cache`, `clear_metadata_caches` from `routers/viewer.py`'s imports — these looked unused *within that file*, but are actually imported directly from `app.routers.viewer` by 6 test files (`test_phase1.py`, `test_phase3.py`, `test_phase4.py`, `test_stability.py`, `test_viewer_pipeline.py`), a re-export pattern the file's own pre-existing comment already explained ("imported here so tests that patch `app.routers.viewer.*` names continue to work"). Ruff's single-file analysis can't see cross-file usage. Caught by running the full test suite immediately after the auto-fix (5 collection errors) rather than trusting the tool blindly; restored the 3 imports with a `# noqa: F401` + comment explaining exactly why, so future tooling doesn't remove them again.

### Unused local variables (6 found, reviewed individually — not batch-removed)

- **`services/toc/cache.py`**: `raw = None` was the tip of a larger finding — the entire sync `get_cached_toc()` function has **zero callers anywhere in the repo** (confirmed via `grep -rn "get_cached_toc\b"` across the full backend, including tests). The async version (`get_cached_toc_async`) is what's actually used everywhere; the sync one appears to have been an earlier, incomplete implementation attempt (its own inline comment says "Callers in async routes should use get_cached_toc_async instead") that was superseded but never deleted. **Removed the whole function**, not just the unused variable.
- **`routers/viewer.py:445`**: `supported = True` — read the full function; every response hardcodes its own literal `"supported": True/False` directly, never referencing this variable. Removed.
- **`services/analytics_service.py:301`**: `page_views = sum(pageviews_by_link...)` — traced back further than the variable itself: `pageviews_by_link` (line 281) is populated by a **dedicated database query** (`SELECT link_id, COUNT(*) ... WHERE event_type = 'page_viewed' GROUP BY link_id`) that runs on every call to this analytics function, whose result was used *only* to compute this one dead variable. Removed the variable, the query, and its else-branch default — a real query-count reduction, not just a cosmetic diff.
- **`services/reading_analytics_service.py:571`**: `global_median_ms = statistics.median(all_times)` — confirmed via search of the rest of the (long) function that only its sibling `global_avg_ms` is ever used; `global_median_ms` is computed once and never read. Removed.
- **`services/reading_analytics_service.py:1073`**: `complexity = await get_or_create_document_complexity(...)` — the *variable* is unused, but the *call* has a real side effect (lazily creates the document's `DocumentComplexity` row on first access if missing) that other code paths depend on existing. Kept the call, dropped only the assignment, with a comment explaining why the call isn't itself dead code.
- **`services/watermark.py:170`**: `text_width = bbox[2] - bbox[0]` inside the lower-left forensic stamp function — confirmed by direct comparison with its sibling (the lower-right stamp function, which *does* use `text_width` to right-align text) that the lower-left version left-aligns to a fixed margin and never needed this value. Likely a copy-paste leftover from the sibling function. Removed.

### Debug artifacts, TODO/FIXME, unused components/CSS

- `grep` sweep for `print(`, `import pdb`/`breakpoint()`, `console.log`/`debugger;`, and `TODO`/`FIXME` across `backend/app/` and `frontend/src/` (excluding tests/pycache): **zero matches in every category.** The codebase was already clean of debug artifacts and TODO markers going into this sprint.
- Every file under `frontend/src/components/` and `frontend/src/hooks/` checked for being referenced by name anywhere else in `src/`: **zero orphaned files found.**
- Every CSS class defined in `SecureDoc.html`'s embedded stylesheet checked for actual `className` usage in component code: **zero newly-found unused classes** (the one already-known piece of dead CSS — the unreachable 640px responsive breakpoint — was already documented as a deliberate non-fix in an earlier sprint, `ARCHITECTURE_DECISIONS.md` AD-6, and is intentionally left alone since removing it would require the same product decision about mobile support that AD-6 already declined to make unilaterally).

### Verification

`ruff check --select F401,F811,F841 app/` → **All checks passed** (0 remaining). Full backend suite: `cd backend && python3 -m pytest tests/unit tests/integration tests/regression -q` → **1708 passed, 1 skipped, 0 failed** — identical to the pre-cleanup baseline, confirming zero regressions from every change in this section.

### What this cleanup did NOT cover

- **Frontend unused-import detection** — no equivalent AST tool (ESLint with `no-unused-vars`) was installed/run this sprint; the `frontend/src/components`/`hooks` orphaned-*file* check above is not the same as an unused-*import-within-a-used-file* check. Flagged as a real gap, not silently skipped.
- **Duplicate business logic / duplicate validation / duplicate permission checks** — the one significant instance already on record (the 7-key `permissions` dict duplicated across 3 locations in `AccessScreen.jsx` + `viewer_session_service.py`) was identified in an earlier sprint (V11.0) and deliberately extended rather than consolidated, per that sprint's own reasoning (`ARCHITECTURE_DECISIONS.md` AD-7) — not re-litigated here.
- **Oversized components** (`AccessScreen.jsx`, ~900 lines) — already tracked as `ISSUE_DATABASE.md` M-13, a deliberate large-refactor deferral, not revisited this sprint.

## Sprint V14.0 — ENG-001: Analytics screen overflow at 768px (2026-07-26)

**Issue**: `ENGINEERING_BACKLOG.md` ENG-001. The Analytics screen's KPI card row and two two-column panel rows (`AnalyticsScreen.jsx:339,344,390`) used fixed CSS grid templates with no responsive fallback — `repeat(6,1fr)` and two fixed-ratio `Nfr Mfr` templates. At the app's own enforced minimum width (768px), this caused the "Completion" KPI card and the entire "Groups at a glance" sidebar panel (blocked-today/active-links/expiring-soon counts) to render fully off-screen, with `overflow-x: hidden` on an ancestor providing no scroll escape — genuinely lost, not degraded.

**Fix**: Replaced all three fixed grid templates with `repeat(auto-fit, minmax(Npx, 1fr))`, matching the same file's own already-correct pattern at line 272. KPI row: `minmax(140px,1fr)`. Charts row: `minmax(320px,1fr)`. Table/sidebar row: `minmax(280px,1fr)`.

**Verification**: Stood up the full local Docker stack (own Postgres/Redis, same Supabase auth project as production, separate local data — no production data touched) specifically so the fix could be browser-verified before ever reaching `origin/main`. Re-measured the previously-clipped elements' DOM bounding boxes at 768px, 834px, and 1440px: both elements now fall fully inside the viewport at all three widths, with no visual regression at 1440px (confirmed via screenshot — the desktop-only 2:1 chart ratio becomes 1:1, which reads as clean, not cramped).

**Tests**: Frontend 13/13 passed. Backend 1708 passed, 1 skipped, 0 failed — identical to baseline (frontend-only change).

**Files**: `frontend/src/screens/AnalyticsScreen.jsx` (lines 339, 344, 390 — 3 lines changed, no logic touched).

## Sprint V14.0 — ENG-002: Notifications feed lacks document identity (2026-07-26)

**Issue**: `ENGINEERING_BACKLOG.md` ENG-002. `GET /api/analytics/events` (`backend/app/routers/analytics.py`) never returned a document title/filename — only an opaque `link_id` — so the Notifications screen's Activity Feed rendered every event as a generic "Page viewed" / "Viewer opened" with no way to identify which document was involved, even though the frontend already had a code path (`NotificationsScreen.jsx eventDetail()`) designed to display `document_title` if it were present.

**Fix**: The endpoint already builds `doc_ids` and `link_ids` to scope its query — extended both existing queries to also select `Document.filename` and `ShareLink.document_id`, building two small in-process maps to attach `document_title` to each event in the response. No new database query added. Also surfaced `page_number` (already present in the payload, never displayed) in the frontend detail line for `page_viewed` events.

**Verification**: Browser-verified against the local Docker stack — created a real share link, generated live view events by opening it anonymously and navigating pages, confirmed the owner's Notifications feed now shows the real document name and page number on every entry (e.g. `"sem6 (1).pdf · page 3"`) instead of a bare, undifferentiated "Page viewed".

**Tests**: Backend 1708 passed, 1 skipped, 0 failed (unchanged — additive response field only). Frontend 13/13 passed.

**Files**: `backend/app/routers/analytics.py`, `frontend/src/screens/NotificationsScreen.jsx`.

## Sprint V14.0 — ENG-003: Cross-account IDOR verification (2026-07-26)

**Not a fix — a verification.** `ENGINEERING_BACKLOG.md` ENG-003 was the largest cited evidence gap from V13.0's security work: the authorization pattern was sound by code inspection but never proven live against a real second account. Created a genuine second account against the local Docker stack (separate local DB, zero production risk) and directly attempted cross-account access to Account A's document, share link, and a disposable API key. Every attempt was correctly blocked (404 on documents/API-keys, 403 on links) with zero data leakage and zero unauthorized modification, confirmed by re-checking Account A's resources afterward.

**Result**: No defect found. **New finding logged, not fixed yet**: link-mutation endpoints (`links.py` revoke/update/hard-delete) return 403 for cross-account access instead of the 404 used everywhere else in the app — tracked as ENG-021 (Low priority, not practically exploitable since link IDs are unguessable UUIDs).

**Files**: None changed. Test API key created for this verification was deleted immediately after (`DELETE /api/api-keys/{id}` as its rightful owner, 204).

## Sprint V14.0 — ENG-004: Document picker disambiguation (2026-07-26)

**Issue**: `ENGINEERING_BACKLOG.md` ENG-004. `components/DocumentPicker.jsx` rendered only filename + page count + view count, with no date or ID — documents sharing a filename (common with repeated drafts) were completely indistinguishable in the share-link creation flow.

**Fix**: Added an "uploaded {date}" suffix using the app's existing `fmtDate()` helper (`utils/viewer.js`), matching the disambiguation pattern already used on the Upload and Storage screens.

**Verification**: Browser-verified on the local Docker stack — both real local documents now display their upload date in the picker.

**Tests**: Frontend 13/13 passed. Backend 1708 passed, 1 skipped, 0 failed (unchanged — frontend-only change).

**Files**: `frontend/src/components/DocumentPicker.jsx`.

## Sprint V14.0 — ENG-006: Storage blocking-I/O audit (2026-07-26)

**Not a fix — a clean audit.** `ENGINEERING_BACKLOG.md` ENG-006, flagged because this exact bug class already caused one real production issue once before (V4.0, `viewer.py`'s download path). Grepped the full backend for boto3/S3 usage — confined entirely to `services/storage.py`. Read all 6 methods directly: every one wraps its blocking boto3 call in `run_in_executor(_STORAGE_EXECUTOR, ...)`. No defect found — the pattern is already correct and self-documented in the module's own docstring.

**Files**: None changed.

## Sprint V15.0 — ENG-007: Audit Log scroll affordance (2026-07-27)

**Issue**: `ENGINEERING_BACKLOG.md` ENG-007. The Audit Log events table's Details column was reachable via horizontal scroll at narrow widths but had no visual hint that more content existed off-screen.

**Fix**: Gave the table its own dedicated `overflow-x: auto` wrapper (rather than relying on an ancestor's incidental overflow behavior), and added a scroll-position-aware right-edge gradient fade — shown only while there's genuinely unscrolled content to the right, driven by an `onScroll` handler plus a mount/resize check, not a static decoration.

**Verification**: Browser-verified at 834px (real overflow) — fade renders with the correct gradient at the table's right edge; at 900px/1440px (no overflow) — fade correctly absent.

**Tests**: Frontend 13/13 passed. Backend 1708 passed, 1 skipped, 0 failed. Build succeeded. Migration validation passed (exit 0). Repo-wide TODO/FIXME/console.log/debugger/print() sweep: 5 backend matches, all false positives (instructional comments); 0 frontend matches.

**Files**: `frontend/src/screens/AuditLogScreen.jsx`.

## Sprint V15.0 — ENG-008: Rate-limit 429 boundary verification (2026-07-27)

**Not a fix — a clean verification.** `ENGINEERING_BACKLOG.md` ENG-008. Sent exactly 21 wrong-password `POST /api/viewer/validate` attempts against one disposable test link: requests 1-20 returned `401`, request 21 returned `429`. The configured `20/minute` limit (`viewer.py:158`) is exact in practice, not just in configuration. No defect found. Test link revoked immediately after.

**Files**: None changed.

## Sprint V15.0 — ENG-009: XSS verification beyond link labels (2026-07-27)

**Not a fix — a clean verification.** Tested the same payload already proven inert for link labels (`<img src=x onerror=alert(1)>`) against organization names, API key names, and webhook descriptions — the three remaining fields flagged as untested in `SECURITY_CERTIFICATION.md`. All three rendered as literal text, zero injected DOM nodes, zero dialogs, zero console errors. Also confirmed via repo-wide grep: zero `dangerouslySetInnerHTML` usage anywhere in the frontend. No defect found.

**Files**: None changed.

## Sprint V15.0 — ENG-010: Expired-link live confirmation (2026-07-27)

**Not a fix — a clean verification.** `_check_link_active` was source-verified as identical to the already-tested revocation path, but never itself live-tested (the dashboard UI's expiry field is date-only). Confirmed the backend schema accepts full datetime precision regardless of the UI constraint, created a disposable link expiring 75 seconds out, and confirmed `200` before / `410 {"detail":"Link expired"}` after waiting 80 seconds. No defect found. **This closes the last "Not enough evidence" item from `SECURITY_CERTIFICATION.md`'s original review** — cross-account IDOR (ENG-003), rate-limit boundary (ENG-008), XSS beyond link labels (ENG-009), and expired-link enforcement (this entry) are all now live-confirmed.

**Files**: None changed.

## Sprint V15.0 — ENG-021: Link mutation endpoints return 404 not 403 cross-account (2026-07-27)

**Issue**: found during ENG-003's IDOR verification (V14.0). `links.py`'s `revoke_link`, `update_link`, `delete_link_permanently` returned `403 "Not authorized"` for cross-account access, confirming to an unauthorized caller that a link with that ID exists — inconsistent with the app-wide `404` pattern (`documents.py`, `api_keys.py`, and even `links.py`'s own `create`/`list` endpoints).

**Fix**: Changed all 3 authorization-failure branches to `404 "Link not found"`, collapsing the "link doesn't exist" and "link exists but isn't yours" cases into one indistinguishable response.

**Test discovery**: 2 existing tests asserted the old `403`, inconsistent with sibling tests in the same class already expecting `404` — updated both. Added a third test for the hard-delete endpoint, which had no prior cross-account coverage. Reverted the source fix via `git stash` to confirm all 3 fail pre-fix, restored, confirmed all pass — proving the tests are meaningful.

**Verification**: Browser/API-verified on the local Docker stack with fresh Account A/B logins — all 3 endpoints now return `404 {"detail":"Link not found"}` for cross-account attempts.

**Tests**: 1709 passed (up from 1708 — new test added), 1 skipped, 0 failed.

**Files**: `backend/app/routers/links.py`, `backend/tests/regression/test_auth_enforcement.py`.

## Sprint V16.0 — ENG-029: Architecture docs corrected to match verified source (2026-07-28)

**Issue**: `ENGINEERING_BACKLOG.md` ENG-029 (merged from `ISSUE_DATABASE.md` L-3). `docs/architecture/ARCHITECTURE.md` and `OVERVIEW.md` disagreed on cache TTLs and the watermark model.

**Fix**: Source-verified ground truth against `viewer_cache.py` and `watermark.py` directly. `ARCHITECTURE.md` had 2 real errors — link/session cache TTLs both stated as 30s (actual: 10s/5s), and the visible per-session watermark mislabeled as "forensic" while the two actual (separate) forensic stamps went unmentioned. `OVERVIEW.md` was already correct on both. Corrected `ARCHITECTURE.md` to match, with a source-of-truth file citation added to prevent future drift.

**Tests**: Backend 1709 passed, 1 skipped, 0 failed (unchanged — docs-only).

**Files**: `docs/architecture/ARCHITECTURE.md`.

## Sprint V16.0 — ENG-013: Frontend lint tooling + dead-code cleanup (2026-07-29)

**Issue**: `ENGINEERING_BACKLOG.md` ENG-013. No frontend equivalent of the backend's `ruff` dead-code sweep existed.

**Fix**: Added a minimal ESLint flat config (`no-unused-vars` only, deliberately narrow — not a style-guide migration) and a `lint` script. Ran it: 19 findings across 9 files, each investigated individually before removal (not blind auto-fix). Notable: `TocSidebar.jsx`'s `error` state was set but never read — traced the render to confirm the existing empty-state already covers the failure case, so nothing user-visible was lost by removing it. `ViewerScreen.jsx`'s unused destructures (`sidecarExtracted`, `drawingState`/`setDrawingState`) come from hooks that still use that state internally — only the unused *consumer-side* binding was removed. 5 unused `catch (e)` parameters converted to parameter-less `catch { }` (ES2019+, within the esbuild target range).

**Real bug found and fixed as a side effect**: the Docker build broke after adding the new devDependencies — `package-lock.json` regenerated on macOS didn't include Linux/Alpine-only optional platform packages for `esbuild`. Regenerated the lockfile from inside a `node:20-alpine` container (matching the actual Dockerfile stage) instead of locally.

**Verification**: `npm run lint` exits 0. Full Docker rebuild succeeded. Browser-verified on the local stack — Upload/Access Control/API Keys/Webhooks/Billing/Viewer all clean, zero console errors, Viewer opens and renders correctly.

**Tests**: Backend 1709 passed, 1 skipped, 0 failed. Frontend 13/13 passed. Build succeeded (312.5kb, down from 312.9kb).

**Files**: `frontend/eslint.config.js` (new), `frontend/package.json`, 9 source files.

## Sprint V17.0 — ENG-014: Duplicate-code scan + real fix (2026-07-29)

**Issue**: `ENGINEERING_BACKLOG.md` ENG-014. No systematic duplicate-code detection had ever run. Installed `jscpd`, ran against `frontend/src` + `backend/app`: 24 clones, 1.70%/0.25% duplicated lines (Python/JSX) — low by industry norms.

**Fix**: One genuine case — `analytics_service.py`'s `get_document_analytics` and `get_group_analytics` both independently ran the identical 4-5-query batch link-event-aggregation block. Extracted into a shared `_aggregate_link_event_counts()` helper, removing real drift risk (a query fix applied to one copy but not the other). The other 23 findings were individually reviewed and judged not to warrant extraction (small same-file patterns, expected adapter-contract similarity, or a genuine-but-shape-mismatched pair where the abstraction cost exceeds the ~15-line saving) — full reasoning in `ENGINEERING_BACKLOG.md`.

**Side effect fixed**: installing `jscpd` reintroduced ENG-013's lockfile platform-drift issue, this time breaking the local Mac dev environment (vitest/rolldown missing its darwin-arm64 binding — a known npm bug). Fixed properly this time by installing on both platforms in sequence against one lockfile, then verifying `npm ci` independently on each in isolation.

**Verification**: Browser-verified — Analytics screen and its "By Group" tab (the two refactored code paths) both render real data, zero console errors, on the local Docker stack.

**Tests**: Backend 1709 passed, 1 skipped, 0 failed. `test_analytics.py` 20/20. Frontend 13/13 (verified on both platforms). Build succeeded. Lint exit 0.

**Files**: `backend/app/services/analytics_service.py`, `frontend/package.json`, `frontend/package-lock.json`.

## Sprint V17.0 — ENG-024: Date-formatting consistency (2026-07-29)

**Issue**: `ENGINEERING_BACKLOG.md` ENG-024. Re-verified per V17.0's STEP 1 process before touching anything: `StorageScreen.jsx`/`BillingScreen.jsx`/`InsightsModal.jsx` each reimplemented date-only formatting ad hoc instead of using the existing shared `fmtDate()`; `AccessScreen.jsx` repeated an identical date+time expression 3 times.

**Fix**: Swapped the 3 screens to `fmtDate()`. Added a small local `fmtDateTime()` helper in `AccessScreen.jsx` for its 3 duplicate date+time call sites. Explicitly investigated and declined to touch `NotificationsScreen.jsx`/`AuditLogScreen.jsx`'s same-named but semantically-different `fmtTime()` functions (relative vs. absolute time) — not true duplication.

**Verification**: Browser-verified — Storage, Billing, Access Control all render cleanly on the local Docker stack, zero console errors.

**Tests**: Backend 1709 passed, 1 skipped, 0 failed. Frontend 13/13 passed. Build succeeded. Lint exit 0.

**Files**: `frontend/src/screens/StorageScreen.jsx`, `frontend/src/screens/BillingScreen.jsx`, `frontend/src/components/InsightsModal.jsx`, `frontend/src/screens/AccessScreen.jsx`.

## Sprint V17.0 — ENG-025, ENG-027, ENG-028: Reviewed, not implemented (2026-07-29)

**Issue**: Empty-state pattern inconsistency (ENG-025), modal-entrance-animation duration drift (ENG-027), and icon-language mixing (ENG-028) — all Low-severity cosmetic items, all re-verified reproducible per STEP 1.

**Decision**: None implemented. ENG-025 and ENG-028 both require a design judgment call (a canonical empty-state pattern for passive screens; a replacement glyph for the one emoji) that exceeds a pure engineering decision. ENG-027's four differing durations are a defensible, common motion-design sequencing pattern (backdrop resolves faster than content), not unambiguously a bug, and the differences (30-100ms) sit below typical user-perceptible threshold. Full STEP 2 reasoning recorded per-issue in `ENGINEERING_BACKLOG.md`.

**Files**: None.

## Sprint V17.0 — ENG-030: Button-variant consistency for row-level delete/revoke (2026-07-30)

**Issue**: `ENGINEERING_BACKLOG.md` ENG-030. `AccessScreen.jsx`'s row-level Links-list "Revoke"/"Delete" triggers used `variant="outline-danger"`, diverging from the `ghost` + inline `style={{ color: C.error }}` pattern used for the identical row-level delete-trigger semantic in `WebhooksScreen.jsx`, `ApiKeysScreen.jsx`, and `DocRow.jsx`.

**Fix**: Changed `AccessScreen.jsx`'s two row-level trigger buttons to `variant="ghost"` + `style={{ color: C.error }}`, matching the majority pattern. Left the page-level "✕ Revoke All Access" button as `outline-danger` (a distinct, standalone confirmation action).

**Verification**: Isolated-diff-verified (3 lines, exactly the intended change) + lint/test/build-verified. No browser-automation tool available in this environment — pure prop/style change, so lint+test+build+source-pattern-match is the applicable ceiling; not claimed as browser-verified.

**Tests**: Frontend 13/13 passed. Build succeeded (309.1kb). Lint exit 0.

**Files**: `frontend/src/screens/AccessScreen.jsx`.

## Sprint V17.0 — ENG-031: Owner preview watermark shows real email (2026-07-30)

**Issue**: `ENGINEERING_BACKLOG.md` ENG-031. The document owner's own preview-link watermark always showed "anonymous" instead of their real email. Root cause: the owner-preview flow (`AppShell.jsx` → `ViewerScreen.jsx` → `useViewerSession.js`) auto-validates against an auto-selected unrestricted "Admin Preview" link with `email` hardcoded to `null`, even though the owner's authenticated email is already available client-side (`AppShell.jsx`'s `userEmail`, derived from the JWT).

**Fix**: Threaded `ownerEmail` from `AppShell.jsx` through `ViewerScreen.jsx` into `useViewerSession.js`'s two `doValidate(...)` call sites. Security-checked first: the auto-selected link is specifically chosen for having no `allowed_emails`/`allowed_domains` restrictions, so passing a real email cannot trigger an unrelated access-gate check. Public share-link viewers are unaffected (no `ownerEmail` is ever passed on that path).

**Verification**: Isolated-diff-verified (3 files, 9 insertions/6 deletions) + lint/test/build-verified. Additionally verified end-to-end against the local Docker stack: rebuilt the `api` container, authenticated as the real test account against the real local Supabase project, and called `/api/viewer/validate` directly — confirmed `watermark_text` changes from `"anonymous · ..."` to `"23z274@psgtech.ac.in · ..."` when the owner's email is passed, exactly as the fix now causes. No browser-automation tool available in this environment, so classified as Source + Integration/API-verified, not Browser-verified.

**Tests**: Frontend 13/13 passed. Build succeeded (308.9kb). Lint exit 0.

**Files**: `frontend/src/screens/AppShell.jsx`, `frontend/src/screens/ViewerScreen.jsx`, `frontend/src/hooks/useViewerSession.js`.

## Sprint V18.0 — Repository Certification: dead code + dependency hygiene (2026-07-31)

**Issue**: `REPOSITORY_CERTIFICATION.md`/`DEAD_CODE_REPORT.md`/`DEPENDENCY_AUDIT.md`. Full sweep found: 2 dead imports + malformed `noqa` suppressions in `backend/tests/conftest.py`; 3 zero-usage Python packages in `requirements-dev.txt`; 5 floating dependency pins in `requirements.txt`; a CI job installing only `requirements.txt` while running pytest against dev-only packages; 2 zero-usage npm devDependencies; 1 duplicate `fmtDate()` in `AccessScreen.jsx`.

**Fix**: Removed `asyncio`/`json` imports from `conftest.py`, fixed the `noqa` directives on the 6 remaining model-registration imports to actual rule codes (`# noqa: F401`). Removed `factory-boy`, `pytest-cov`, and the direct `anyio` pin from `requirements-dev.txt`. Pinned `prometheus-client`/4 OpenTelemetry packages to the exact versions confirmed running in the live Docker `api` container. Added `-r requirements-dev.txt` to the CI `backend-test` job's install step. Removed `@testing-library/user-event`/`@vitest/coverage-v8` from `package.json`, regenerated and cross-platform-reconciled `package-lock.json`. Swapped `AccessScreen.jsx`'s locally-redefined `fmtDate()` for the shared `utils/viewer.js` import (byte-identical implementation, 7 other screens already used the shared version).

**Verification**: Backend suite 1709 passed/1 skipped/0 failed (unchanged). Frontend 13/13 passed, lint exit 0, build succeeded (309.0kb). `npm ci --ignore-scripts` verified independently on macOS and Alpine.

**Files**: `backend/tests/conftest.py`, `backend/requirements.txt`, `backend/requirements-dev.txt`, `.github/workflows/ci.yml`, `frontend/package.json`, `frontend/package-lock.json`, `frontend/src/screens/AccessScreen.jsx`.

## Sprint V18.0 — Repository Certification: dead function + dead CSS removal (2026-07-31)

**Issue**: `get_optional_user()` (`backend/app/auth.py`) had zero production callers — confirmed via repo-wide grep, only exercised by its own dedicated unit-test class. `@keyframes progressAnim` (`frontend/SecureDoc.html`) had zero `className`/inline-`style` references anywhere.

**Fix**: Removed both, plus the now-unused `TestGetOptionalUser` test class and its `get_optional_user` import in `test_auth.py`.

**Contamination note**: both files carried substantial pre-existing uncommitted work (a JWKS-outage resilience fix in `auth.py` — new `JWKSUnavailableError` class and graceful-degradation logic; unrelated content in `SecureDoc.html`). Applied the established backup→isolate→verify→restore technique: backed up the full state, reset to clean HEAD, applied only this fix, verified the isolated diff (auth.py: 9 deletions; test_auth.py: 29 deletions; SecureDoc.html: 10 deletions — nothing else), committed, then restored the pre-existing work on top of the new commit, reapplying the same dead-code removal to the restored files so nothing regressed.

**Verification**: `pytest tests/integration/test_jwks_outage.py tests/unit/test_auth.py` — 13/13 passed, confirming the restored JWKS work and the dead-code removal coexist correctly. Full backend suite: 1705 passed/1 skipped/0 failed (1709 baseline − 4 tests removed alongside the function they tested). Docker `api` container rebuilt, `/health` returns all-ok.

**Files**: `backend/app/auth.py`, `backend/tests/unit/test_auth.py`, `frontend/SecureDoc.html`.

## Sprint V18.0 — Repository Certification: documentation archival (2026-07-31)

**Issue**: 41 days of accumulated sprint reports (2026-07-14 through 2026-07-30) sitting uncleaned at repository root and in `docs/engineering/`, despite this exact cleanup being recommended twice before and executed once (Sprint 6.3). Full reasoning in `DOCUMENTATION_CLEANUP_PLAN.md`.

**Fix**: Archived 48 files to `archive/sprint7-18/`, following the existing `archive/sprint5-6/` convention. Merged root `FIX_LOG.md`'s unique V4.0/Sprint-7.0/V6.0 history into this canonical log (see the "Historical entries" section above, inserted at its correct chronological position). Re-surfaced 3 genuine open findings as new `ENGINEERING_BACKLOG.md` entries (ENG-032/033/034). Corrected `archive/README.md`'s stale references.

**Verification**: No code touched — documentation-only commit. `docs/governance/ARCHIVED_FILES.md`/`CLEANUP_LOG.md` updated with dated, append-only sections per the existing convention.

**Files**: 48 archived files (see `docs/governance/ARCHIVED_FILES.md` for the full list), `archive/README.md`, `docs/governance/ARCHIVED_FILES.md`, `docs/governance/CLEANUP_LOG.md`, `docs/engineering/FIX_LOG.md`, `ENGINEERING_BACKLOG.md`.

## Sprint V20.0 — ENG-032: corrected, no fix needed (2026-08-01)

**Issue**: `ENGINEERING_BACKLOG.md` ENG-032 claimed no production-startup guard existed for `ip_hash_salt`/`domain_verify_salt`.

**Finding**: The guard already exists — `backend/app/main.py:27-54`. Both the original source finding and this session's own V18.0 re-verification had only checked `config.py` and missed it. A redundant fix was implemented in `config.py`, caught by its own regression run (broke 2 pre-existing `test_phase8.py` tests encoding the real `main.py` behavior), and reverted.

**Result**: Closed, no longer reproducible. Zero net code change.

**Verification**: Full backend suite 1705 passed/1 skipped/0 failed after revert (confirmed identical to pre-attempt baseline). `git status` confirmed byte-identical to HEAD on the touched files.

**Files**: None (net).

## Sprint V20.0 — ENG-018, ENG-020: large-PDF stress + Reading Intelligence hand-verification (2026-08-01)

**Issue**: `ENGINEERING_BACKLOG.md` ENG-018 (large-PDF Viewer stress not retested) and ENG-020 (Reading Intelligence metrics not hand-verified against backend math).

**Verification, not a fix**: no browser-automation tool available — verified via direct API calls against the real local Docker stack. Generated a genuine 120-page synthetic PDF, uploaded and processed successfully (`ready`, `page_count: 120`), confirmed rendering/thumbnails/search/word-positions all correct at scale. Submitted a controlled reading-event batch and hand-verified `total_active_ms`, `completion_pct`, and `reading_speed_wpm` against `reading_analytics_service.py`'s source formulas — all matched exactly, including confirming the `700.0` wpm result was the documented physiological-plausibility clamp firing correctly (not a placeholder), by reading the clamp logic and independently recomputing the pre-clamp EWMA.

**Result**: Both closed — verified, no defect found.

**Files**: None — no code changed.

## Sprint V20.0 — ENG-019: partial verification, remains open (2026-08-01)

**Issue**: `ENGINEERING_BACKLOG.md` ENG-019 (dashboard modals/toggles not re-exercised).

**Verification, not a fix**: verified 2 representative toggles (API key `is_active`, webhook `is_active`) round-trip correctly via `PATCH` + a fresh re-fetch confirming persistence. Explicitly did not extend this claim to the rest of the item's scope (other screens' toggles, actual rendered UI feedback) — no browser tool available to verify those, and asserting otherwise would overclaim the evidence.

**Result**: Remains open. Partial evidence now on record instead of none.

**Files**: None — no code changed.

## Sprint V21.0 — State recovery: 62 files of pre-existing work committed (2026-08-02)

**Issue**: `git status` showed 62 modified/new files with no relation to this session's own commits — implemented-but-never-committed work from multiple earlier sprints, never committed under the "commit only when explicitly requested" policy in effect before this session's mega-prompts started authorizing atomic commits.

**Verification before committing**: full backend suite (1705 passed/1 skipped/0 failed) and frontend suite (13/13) run against the complete as-found working tree to confirm coherence. Live database query confirmed migration 027 (part of the diff) was already applied. ~15 of the 62 files spot-checked against `FIX_LOG.md`'s own existing historical sections, which already documented most of this work when it was originally done.

**Fix**: committed in 8 logically-grouped commits — Sprint V6.0 governance fixes (webhook task registration, scope enforcement, dedup, audit logging, migration 027), JWKS-outage resilience, annotation/session consolidation + Reading Intelligence backend, Viewer/Reading-Intelligence frontend, dashboard-screen fixes, historical CHANGELOG/README/DEVELOPER_GUIDE corrections, live-QA screenshot evidence, and a bundle rebuild.

**Verification**: full suites re-run after the batch — 1705 passed/1 skipped/0 failed, 13/13, lint exit 0, build 309.0kb. Docker `api`+`migrate` rebuilt and healthy.

**Result**: working tree fully clean for the first time this session.

**Files**: 62 files across backend/, frontend/, docs/ — see commits `87d2c7d`, `8e8c6d9`, `b87aae2`, `28bb563`, `93a4ffe`, `912b1b8`, `9492f0e`, `8ccf594`.

## Sprint V21.0 — ENG-035, ENG-036: Reading Insights toggle + self-inclusive average (2026-08-02)

**Issue**: found during targeted re-verification of the just-committed `show_reading_insights` feature. ENG-035: fully built backend, zero UI toggle to enable it. ENG-036: `current_page_avg_ms` didn't exclude the requesting viewer's own session, unlike the sibling `pace_vs_average` calculation.

**Fix**: added the toggle to both of `AccessScreen.jsx`'s permission grids. Added `PageReadingEvent.session_id != session_id` to the average-query's `WHERE` clause, matching the existing exclusion pattern immediately below it.

**Verification**: the pre-existing test for this endpoint was asserting the buggy self-inclusive behavior as correct; running the fix caught the regression immediately (`assert None is not None`). Corrected the test and added a new positive-case test with two sessions of deliberately different active-time values, asserting the returned average exactly equals the *other* session's value. Full backend suite: 1706 passed (1705 + 1 new test)/1 skipped/0 failed. Frontend: lint exit 0, 13/13, build 309.1kb.

**Files**: `frontend/src/screens/AccessScreen.jsx`, `backend/app/services/reading_analytics_service.py`, `backend/tests/integration/test_reading_api.py`.

## Sprint V21.0 — Documentation consolidation + final certification (2026-08-04)

**Issue**: V18.0's 6 certification deliverables were still sitting at root, `SECURITY_HARDENING_PLAN.md` was at root instead of alongside the repo's other security docs, and no single authoritative release certification existed (only scattered `FINAL_*`/certification-style documents across multiple sprints).

**Fix**: archived the 6 V18.0 deliverables to `archive/sprint18-certification/`; relocated `SECURITY_HARDENING_PLAN.md` to `docs/security/`; corrected every cross-reference; corrected 3 stale README numbers and removed an unbacked "Supabase SAML integration" claim (zero SAML code found anywhere in the repo); added a README documentation index; produced ONE `docs/release/FINAL_RELEASE_CERTIFICATION.md` with every claim classified VERIFIED/INFERRED/NOT VERIFIED/BLOCKED, plus a companion `KNOWN_LIMITATIONS.md`.

**Verification**: full regression re-run after the structural moves (mandatory per this sprint's own Section 14) — 1706 passed/1 skipped/0 failed, 13/13, lint exit 0, build 309.1kb, Docker `api`+`migrate` rebuilt and healthy.

**Files**: `README.md`, `docs/release/FINAL_RELEASE_CERTIFICATION.md` (new), `docs/release/KNOWN_LIMITATIONS.md` (new), 6 files moved to `archive/sprint18-certification/`, `SECURITY_HARDENING_PLAN.md` moved to `docs/security/`, `docs/governance/ARCHIVED_FILES.md`, `ENGINEERING_BACKLOG.md`.
