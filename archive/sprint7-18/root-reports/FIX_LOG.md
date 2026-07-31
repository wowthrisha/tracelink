# Fix Log

Base commit: `2c1795f` (V4.0 remediation, entries below through ANAL-006, committed as `31e2966` and pushed to origin/main). Sprint 7.0 entries below that point are on top of `31e2966` and are currently uncommitted in the working tree, pending an explicit commit instruction.

---

## AUTH-001 — No password requirements shown during signup

- **Root cause**: `LoginScreen.jsx`'s password field renders identically for login and signup; no hint text existed, so a user only learns the password policy after the server rejects a too-short password.
- **Files changed**: `frontend/src/screens/LoginScreen.jsx`
- **Why the fix works**: Adds a conditional `<span>` hint ("At least 6 characters.") under the password field when `mode === 'signup'`, matching the 6-character minimum already used elsewhere in this file's own reset-password validation (`newPassword.length < 6` check).
- **Tests executed**: `npm test` (13/13 passed), `npm run build` (succeeded, 306.1kb).
- **Regression risk**: None — additive UI text, no logic change, login/reset modes unaffected (conditional is scoped to `mode === 'signup'`).

## AUTH-002 — No show/hide password toggle

- **Root cause**: Password `<input>` was hardcoded `type="password"` with no visibility control.
- **Files changed**: `frontend/src/screens/LoginScreen.jsx`
- **Why the fix works**: Added `showPassword` state and a `Show`/`Hide` button that toggles the input's `type` between `password` and `text`. Positioned absolutely inside the existing input wrapper; input gets `paddingRight: 40` so the button doesn't overlap typed text.
- **Tests executed**: `npm test`, `npm run build` (see above).
- **Regression risk**: Low — new state variable, no change to existing `onChange`/`onFocus`/`onBlur` handlers or form submission logic.

## AUTH-007 — Raw "Failed to fetch" error shown on connection failure

- **Root cause**: The `catch` block in `handleSubmit` special-cased a few known error substrings (`confirm`, `expired`, `invalid`, `otp`, `token`) but fell through to displaying `err.message` verbatim for anything else, including the browser's raw `TypeError: Failed to fetch` on network/DNS failure.
- **Files changed**: `frontend/src/screens/LoginScreen.jsx`
- **Why the fix works**: Added a branch that catches `failed to fetch`, `network`, and `load failed` (case-insensitive) and replaces them with "Unable to reach the server. Check your connection and try again." — placed before the final catch-all `else`, so it doesn't affect any of the existing special-cased messages.
- **Tests executed**: `npm test`, `npm run build`.
- **Regression risk**: Low — purely additive `else if` branch; existing error paths (confirm/expired/invalid/otp/token) are unchanged since they're checked first.

## DASH-001 — "Upload Dashboard" title is misleading

- **Root cause**: `Header`'s hardcoded `titles` map in `atoms.jsx` labeled the `upload` screen "Upload Dashboard," but the screen is a full document management hub (search, groups, sharing, deletion), not just an upload tool.
- **Files changed**: `frontend/src/components/atoms.jsx`
- **Why the fix works**: Single string change, `'Upload Dashboard'` → `'Documents'`, in the one place this title is defined. `Header` is a shared component used by every screen via the same `titles[screen]` lookup, so no other screen's title is touched.
- **Tests executed**: `npm test`, `npm run build`.
- **Regression risk**: None functionally — pure copy change. Cosmetic-only; no logic, routing, or test currently asserts on this specific string (confirmed via `npm test` pass).

## DASH-003 — Security notice not prominent

- **Root cause**: The "documents converted to images, downloads disabled" notice lived as a 10px `<span>` in a footer `<div>` below the documents table — easy to miss.
- **Files changed**: `frontend/src/screens/UploadScreen.jsx`
- **Why the fix works**: Removed the footer version and added a bordered, tinted banner (`C.infoBg`/`C.infoBdr` tokens, 12px text) directly under the page header, above the stats grid — the first thing visible on the screen instead of the last.
- **Tests executed**: `npm test`, `npm run build`.
- **Regression risk**: None — layout-only change; no state, no data flow touched. `StatusDot` (already imported and used elsewhere in this file) is reused, no new import needed.

## DASH-008 — "+ New group" button easy to miss

- **Root cause**: `UploadMetadataPanel.jsx`'s "+ New group" button used the `Btn` component's `ghost` variant — per `atoms.jsx`, `ghost` renders with no border and no background, only muted text.
- **Files changed**: `frontend/src/components/upload/UploadMetadataPanel.jsx`
- **Why the fix works**: Changed `variant="ghost"` to `variant="secondary"`, which per the same `Btn` component definition renders with a visible background (`C.accentBg`) and border (`C.borderMed`) — no new styling code, just selecting an existing, already-styled variant.
- **Tests executed**: `npm test`, `npm run build`.
- **Regression risk**: None — `onClick` handler and button text unchanged; only the visual variant prop changed.

## ANAL-006 — Groups sidebar widget silently capped at 5

- **Root cause**: `AnalyticsScreen.jsx`'s "Groups at a Glance" widget always rendered `groupStats.slice(0, 5)` with no indication that more groups might exist beyond the five shown.
- **Files changed**: `frontend/src/screens/AnalyticsScreen.jsx`
- **Why the fix works**: Added local `showAllGroups` state. When `groupStats.length > 5`, a "Show all N" / "Show fewer" toggle button now appears below the list; the render swaps between `.slice(0, 5)` and the full array based on that state. No API/data-fetch change — `groupStats` was already fetched in full (`getGroupAnalytics()`), only the render was truncating it.
- **Tests executed**: `npm test`, `npm run build`.
- **Regression risk**: Low — new local state defaults to `false` (existing capped behavior preserved by default), toggle only appears when there are actually more than 5 groups to show.

---

## Suite-wide verification (run once, after all 7 fixes)

- `cd frontend && npm test` → **13/13 passed**
- `cd frontend && npm run build` → **succeeded**, `dist/app.bundle.js` 306.1kb, no errors
- `cd backend && python -m pytest tests/unit tests/integration tests/regression -q` → **1699 passed, 1 skipped, 0 failed**
- `git diff` scanned for `TODO`/`FIXME`/`console.log`/`debugger` in all touched files → none found

---

# Sprint 7.0 fixes

Full reasoning and evidence for every item (fixed and deferred) is in `WORKFLOW_COMPLETENESS.md`, `ARCHITECTURE_SCORECARD.md`, `SECURITY_STATUS.md`, and `REPOSITORY_HEALTH.md`. This log covers root cause / files / rationale for each of the 17 items actually fixed.

## View-limit-reached mislabeled as "Link Expired"

- **Root cause**: `useViewerSession.js` classified every non-`revoked` 410 response as `'expired'`; a 410 for "max views reached" (`link_service.py:257`) has no "revoked" substring, so it fell into the wrong bucket.
- **Files changed**: `frontend/src/hooks/useViewerSession.js`, `frontend/src/components/AccessGate.jsx`
- **Why it works**: added a `detail.includes('view')` branch producing a distinct `view_limit_reached` status, with a matching `GateMessage` in `AccessGate.jsx`.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none — additive branch, existing `revoked`/`not_found`/`expired` paths unchanged.

## Broken network-error fallback in the viewer (dead end)

- **Root cause**: `usePageLoader.js`'s fetch catch block fell back to `<img src={url}>` with no `X-Session-ID` header — image tags can't send custom headers, so this always 400s, and `pageError` was never set, leaving a broken image with no explanation.
- **Files changed**: `frontend/src/hooks/usePageLoader.js`, `frontend/src/screens/ViewerScreen.jsx`
- **Why it works**: removed the broken fallback, set a real `pageError` message instead; added a `retryPage()` export and wired a Retry button into the error overlay.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: low — only the catch branch changed; the success and HTTP-error paths are untouched.

## Garbled HTML-entity icons in AccessGate

- **Root cause**: icon props were literal strings like `"&#x1F50D;"` passed through a JSX `{expression}` child — React does not decode HTML entities there, so the raw entity text rendered instead of an emoji.
- **Files changed**: `frontend/src/components/AccessGate.jsx`
- **Why it works**: replaced all 5 entity strings with real emoji characters.
- **Tests**: `npm run build` (visual — cannot be asserted by the existing test suite). **Regression risk**: none, cosmetic-only.

## No warning for protected links with no expiry

- **Root cause**: `handleSave` in `AccessScreen.jsx` validated expiry-in-the-past and view-count but never warned about a password/email-gated link left with no expiry (indefinite protected access).
- **Files changed**: `frontend/src/screens/AccessScreen.jsx`
- **Why it works**: added a conditional inline hint on the Expiry field when `(password || allowedEmails) && !expiry`.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none — display-only, doesn't block submission.

## No tooltip distinguishing Revoke from Delete (ACCESS-002)

- **Root cause**: neither button had a `title`/`aria-label`; the shared `Btn` component didn't accept or forward a `title` prop at all.
- **Files changed**: `frontend/src/components/atoms.jsx` (added `title` prop, forwarded on all 6 `Btn` variants), `frontend/src/screens/AccessScreen.jsx`
- **Why it works**: additive optional prop — every existing `Btn` call site that doesn't pass `title` renders identically to before.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none — backward-compatible prop addition.

## "Revoke All Access" always claimed success

- **Root cause**: `handleRevoke` looped per-link with a `try{}catch{}` that silently swallowed every failure, then unconditionally toasted "All access revoked" — a false-positive claim if any link failed to revoke.
- **Files changed**: `frontend/src/screens/AccessScreen.jsx`
- **Why it works**: switched to `Promise.allSettled`, counts failures, and reports accurate success/partial/failure outcomes.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none — same per-link calls, only the aggregation/reporting changed; no link that would have been revoked before is now skipped.

## Storage retention change fired with no confirmation (STOR-002)

- **Root cause**: the retention `<select>`'s `onChange` called the PATCH directly — a fat-fingered selection could schedule a document for deletion with no confirmation.
- **Files changed**: `frontend/src/screens/StorageScreen.jsx`
- **Why it works**: `onChange` now opens a confirmation modal describing the exact consequence (`RETENTION_LABELS`); the actual API call only fires on explicit confirm. The `<select>` stays a controlled input bound to server data, so Cancel naturally reverts the displayed value with no extra state needed.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none — same `handleRetentionChange` call, now gated behind one extra confirm step.

## Storage per-document table had no empty state

- **Files changed**: `frontend/src/screens/StorageScreen.jsx`
- **Why it works**: added a `colSpan={7}` row rendering "No documents yet..." when `by_document` is empty, matching the pattern used elsewhere in the app.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none — additive conditional row.

## Document/group delete: missing loading state, modal-closes-before-resolve

- **Root cause**: `UploadScreen.jsx`'s document-delete confirm button never wired the existing `deleting` state to its `loading` prop (double-click risk); group-delete had no per-group loading state at all and closed its modal *before* the async call resolved, so a failed delete gave no in-modal feedback.
- **Files changed**: `frontend/src/screens/UploadScreen.jsx`
- **Why it works**: added `loading={deleting}` to the document-delete button; added a new `deletingGroupId` state, moved the group-delete modal's close to only happen on success (matching every other delete flow in the app), and wired `loading={deletingGroupId === deleteGroupModal?.id}`.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: low — `handleDeleteGroup`'s success/error paths are unchanged, only when the modal closes and what the button shows while in-flight changed.

## API key delete confirmation had wrong copy

- **Root cause**: copy-pasted from the webhook delete modal — referenced "delivery history," a webhook concept, not an API-key one.
- **Files changed**: `frontend/src/screens/ApiKeysScreen.jsx`
- **Why it works**: replaced with copy accurate to API keys (integration impact).
- **Tests**: `npm run build`. **Regression risk**: none, copy-only.

## Password reset left a stale, reusable-looking token in the URL

- **Root cause**: after a successful reset, the `#access_token=...&type=recovery` fragment was never cleared; a refresh would re-parse it and drop the user back into a reset form with an already-used token.
- **Files changed**: `frontend/src/screens/LoginScreen.jsx`
- **Why it works**: calls `history.replaceState` to strip the fragment immediately after a successful reset.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none — runs only in the success branch, after the reset already succeeded.

## Audit log export silently truncated at 500 with no warning

- **Files changed**: `frontend/src/screens/AuditLogScreen.jsx`
- **Why it works**: both CSV and JSON export handlers now compare the exported row count against the known filtered `total` (already tracked in component state from the last `fetchPage` call) and show an accurate "Exported N of M — narrow your date range" warning toast instead of a plain success message when truncated.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none — export logic itself unchanged, only the toast message.

## Org member self-removal ("leave org") was broken for non-admins

- **Root cause**: `orgs.py:remove_member` called `_get_org_and_member(..., minimum_role="admin")`, which raises 403 for any caller below admin *before* the function's own self-removal bypass logic (`is_self`) ever runs — contradicting the code's own comment ("Allow self-removal at any role").
- **Files changed**: `backend/app/routers/orgs.py`, `backend/tests/integration/test_enterprise_phase4.py`
- **Why it works**: caller is now resolved at `minimum_role="viewer"`, and the admin-role requirement is enforced explicitly only when `not is_self`. Self-removal and the last-owner/peer-role guards for *other*-removal are both preserved exactly as before.
- **Tests**: 2 new regression tests (`test_viewer_can_leave_org`, `test_viewer_cannot_remove_other_member`), plus all 3 pre-existing member-removal tests (`test_cannot_remove_last_owner`, `test_remove_member`, and the RBAC suite) — 54/54 passed in `test_enterprise_phase4.py`. **Regression risk**: low — behavior for admin/owner callers acting on someone else is unchanged; only self-removal by a sub-admin role, which previously 403'd unconditionally, now succeeds (matching documented intent).

## Org member removal had no confirmation dialog

- **Root cause**: the only destructive action in the app with a direct `onClick={() => handleRemove(m)}` and no confirm step.
- **Files changed**: `frontend/src/screens/OrgsScreen.jsx`
- **Why it works**: added a `removeModal` state and a confirmation `Modal` matching the existing org-delete pattern; `handleRemove` itself is unchanged, just now gated behind confirm.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none — same removal call, additional confirm step only.

## `groups.py` missing scope enforcement (permission-boundary gap)

- **Root cause**: all 7 `groups.py` endpoints used bare `Depends(get_current_user)` instead of `Depends(require_scope(...))`, unlike `documents.py`/`links.py`/`webhooks.py` — an API key scoped only to `documents:read` could still mutate group membership.
- **Files changed**: `backend/app/routers/groups.py`
- **Why it works**: swapped to `require_scope("documents:read")` (list/get) or `require_scope("documents:write")` (create/update/delete/assign/remove), matching the existing convention exactly. `require_scope` only restricts `auth_method == "api_key"` callers — zero behavior change for JWT/browser users.
- **Tests**: `test_group_ownership.py` (13), `test_phase_a_cleanup.py` (27), `test_enterprise_phase4.py` (54) — 94/94 passed. **Regression risk**: low, scoped to API-key callers only; no existing test exercised an under-scoped API key against these endpoints (confirmed via grep before changing).

## `groups.py:assign_documents_to_group` N+1 query

- **Files changed**: `backend/app/routers/groups.py`
- **Why it works**: replaced a per-document-ID `SELECT` loop with a single `WHERE Document.id.in_(doc_uuids)` query, mirroring the batched pattern already used two functions above in the same file (`list_groups`).
- **Tests**: same 94 tests as above. **Regression risk**: none — identical `assigned` count and per-document ownership check, just one query instead of N.

## Document upload missing audit log entry

- **Root cause**: `document.deleted` was audited, `document.uploaded` wasn't — an asymmetry with no technical justification found.
- **Files changed**: `backend/app/routers/documents.py`, `backend/app/models/audit.py` (registered the new `document.uploaded` event type so it's filterable in the Audit Log UI)
- **Why it works**: mirrors the exact try/except-swallow pattern already used for `document.deleted`, so an audit-log failure can never break an upload.
- **Tests**: full backend suite (1701 passed) — no test asserts on the fixed set of audit event types in a way that would break from an addition. **Regression risk**: none — additive, best-effort, non-blocking.

## Misleading "uploader-facing" comment on `resolve_annotation`

- **Root cause**: comment claimed owner-only access; the route (`/api/viewer/annotations/{token}/{id}/resolve`) is actually reachable by any session on the link, with no ownership check — unlike the real owner-gated `resolve_feedback` route that exists separately.
- **Files changed**: `backend/app/routers/annotations.py`
- **Why it works**: documentation-only fix, deliberately not a behavior change — see `ARCHITECTURE_SCORECARD.md` for why the permission question itself was left for a product/security decision rather than guessed at.
- **Tests**: full backend suite (1701 passed). **Regression risk**: none, comment-only.

## Duplicated `_get_session_id`, `fmtDate`, and `admin.py` role-check logic

- **Files changed**: `backend/app/services/annotation_service.py`, `backend/app/routers/admin.py`, `frontend/src/utils/viewer.js`, `frontend/src/screens/{OrgsScreen,AccessScreen,ApiKeysScreen,WebhooksScreen}.jsx`
- **Why it works**: see `ARCHITECTURE_SCORECARD.md` for full reasoning per item — all three are behavior-preserving consolidations onto an existing shared implementation, verified via the full test suite both backend and frontend.
- **Tests**: full backend suite (1701 passed), `npm test` (13/13), `npm run build`. **Regression risk**: none — confirmed no circular-import risk before consolidating `_get_session_id`; confirmed no test depends on `admin.py`'s old exact error string before consolidating the role check.

## Unused imports removed

- **Files changed**: `backend/app/routers/documents.py` (`get_current_user`), `backend/app/routers/webhooks.py` (`Optional`, `get_current_user`), `backend/app/routers/storage.py` (`func`), `backend/app/routers/orgs.py` (`Query`)
- **Why it works**: each confirmed unused via a full-file grep before removal, not just a lint hint.
- **Tests**: full backend suite (1701 passed — confirms nothing else in each file relied on the removed names). **Regression risk**: none.

## Test fragility: bundle-mangling regex didn't account for `$`-prefixed minified names

- **Root cause**: `test_bundle_ends_with_reactdom_render` used `\w+` to match esbuild's minified identifier; esbuild's minifier can legitimately produce `$`-prefixed names once it exhausts short alphanumeric ones, which `\w+` doesn't include. This sprint's source changes shifted the bundle's identifier count enough to trigger exactly that case.
- **Files changed**: `backend/tests/integration/test_phase2.py`
- **Why it works**: changed the character class to `[\w$]+`, which matches valid JS identifier characters including esbuild's mangled names, without weakening what the test actually verifies (that a `ReactDOM.render` call with a single identifier argument exists).
- **Tests**: `test_phase2.py` (previously 1 failure) now passes; full suite 1701/1701 passed, 1 skipped. **Regression risk**: none — test-only change, made the assertion more correct, not looser in any way that matters (still requires the exact `ReactDOM.createRoot(...).render(React.createElement(<ident>,null));` structure).

---

## Suite-wide verification (Sprint 7.0, run after all fixes above)

- `cd frontend && npm test` → **13/13 passed**
- `cd frontend && npm run build` → succeeded, `dist/app.bundle.js` 310.0kb, no errors
- `cd backend && python -m pytest tests/unit tests/integration tests/regression -q` → **1701 passed, 1 skipped, 0 failed**
- `alembic heads` → single linear head (`026`), no branching — no schema changes made this sprint, nothing new to migrate
- `git diff` scanned for `TODO`/`FIXME`/`console.log`/`debugger`/stray `print(` in all touched files → none found

---

# Sprint V6.0 — Engineering Governance fixes

Full reasoning, evidence, and the (much larger) documented-not-fixed list for every phase is in `ENGINEERING_GOVERNANCE.md`, `MODULE_BOUNDARIES_AND_CODE_QUALITY.md`, `UI_API_CONTRACT.md`, `SECURITY_GOVERNANCE.md`, `SCALABILITY_REVIEW.md`, `CONSISTENCY_MATRIX.md`, and `REPOSITORY_HEALTH.md`. This log covers root cause / files / rationale for what was actually fixed.

## Webhook deliveries silently non-functional in production (most severe finding this sprint)

- **Root cause**: `backend/app/workers/celery_app.py`'s `include=["app.workers.tasks", "app.workers.cleanup"]` omitted `app.workers.webhook_tasks`. A real Celery worker process only registers `@celery_app.task`-decorated functions from modules listed in `include=` (imported via `celery_app.loader.import_default_modules()` at worker boot) — it does not pick up modules that are only imported by test code. `securedoc.deliver_webhook` was therefore never registered with the worker, so every `celery_app.send_task("securedoc.deliver_webhook", ...)` call from `webhooks.py`/`webhook_service.py` enqueued a task name no worker could execute.
- **Files changed**: `backend/app/workers/celery_app.py`, `backend/tests/unit/test_worker_tasks.py`
- **Why the fix works**: one-line addition of the missing module to `include=`. Verified by calling `celery_app.loader.import_default_modules()` (mirroring real worker boot) before and after — `securedoc.deliver_webhook` now appears in `celery_app.tasks`.
- **Tests**: added `TestTaskRegistration::test_all_task_modules_are_registered_with_the_worker`, asserting all 8 expected task names register after `import_default_modules()` — this specific test form is necessary because directly importing task modules (what other tests/code paths do) masks an `include=` omission entirely. Full suite: 1702 passed.
- **Regression risk**: none — purely additive to the worker's task-discovery list; no existing task's registration or behavior changes.

## `annotations.py` wrongly denying org members access to shared documents

- **Root cause**: 10 inline `str(doc.user_id) != str(current_user["user_id"])` checks in `annotations.py`, narrower than `documents.py`'s existing `_get_accessible_document()`, which also grants access to org members of org-owned documents via `OrgMembership`.
- **Files changed**: `backend/app/routers/annotations.py`, `backend/tests/unit/test_identity_thread_part8.py`
- **Why the fix works**: all 10 sites now call the shared, already-tested `_get_accessible_document()` (imported from `documents.py`) instead of reimplementing the check. As a side effect, denied access now returns 404 instead of 403, matching `documents.py`'s existing no-existence-leak convention.
- **Tests**: one pre-existing test asserted the old 403 and was updated to expect 404 with reasoning recorded inline; full suite 1702 passed (a mid-fix regression, caused by not initially handling both `str` and already-parsed `uuid.UUID` inputs to the new call sites, was caught by the existing test suite and corrected before this fix was considered done).
- **Regression risk**: low — behavior for the true owner is unchanged; only org-member access (previously wrongly denied) and unauthorized-caller status code (403→404) changed.

## `links.py` / `link_service.py` duplicated "is link active" logic

- **Root cause**: `_link_to_summary()` (router, display flag) and `validate_link()` (service, actual enforcement) independently computed revoked/expired/max-views status, and disagreed at the exact expiry boundary (`expires > now` vs. `expires < now` for the inactive condition).
- **Files changed**: `backend/app/services/link_service.py`, `backend/app/routers/links.py`
- **Why the fix works**: extracted a single pure `is_link_active(link, now)` predicate matching `validate_link()`'s actual enforcement exactly; `_link_to_summary()` now calls it instead of reimplementing.
- **Tests**: full backend suite, 1702 passed. **Regression risk**: none — the display flag now matches real enforcement more precisely than before, not less.

## `orgs.py` duplicated "last owner" check

- **Files changed**: `backend/app/services/org_service.py`, `backend/app/routers/orgs.py`
- **Why the fix works**: extracted `ensure_not_last_owner(db, org_id)`, called from both `update_member_role` and `remove_member` instead of each reimplementing the same count-and-raise logic.
- **Tests**: full backend suite, 1702 passed. **Regression risk**: none — identical logic, single copy.

## Webhook audit-logging gap (entire screen had zero coverage)

- **Files changed**: `backend/app/routers/webhooks.py`, `backend/app/models/audit.py` (registered `webhook.created`/`webhook.updated`/`webhook.deleted`)
- **Why the fix works**: mirrors the exact pattern already used for `document.uploaded`/`document.deleted` — `log_audit_event()` called before `db.commit()` so the audit entry lands in the same transaction as the mutation.
- **Tests**: full backend suite, 1702 passed. **Regression risk**: none, additive.

## Storage retention-change audit-logging gap

- **Files changed**: `backend/app/routers/storage.py`, `backend/app/models/audit.py` (registered `document.retention_changed`)
- **Tests**: full backend suite, 1702 passed. **Regression risk**: none, additive.

## `api_key.rotated` missing from the filterable audit-event enum

- **Root cause**: the event was logged correctly but never added to `AUDIT_EVENT_TYPES`, making it permanently unselectable in the Audit Log screen's filter dropdown and rejected with 422 if queried directly.
- **Files changed**: `backend/app/models/audit.py`
- **Tests**: full backend suite, 1702 passed. **Regression risk**: none, additive enum entry.

## Three CSV exports in AccessScreen with zero error handling

- **Root cause**: `exportFeedback`/`exportReviewerActivity`/`exportVisualAnnotations` were called as bare, un-awaited promise expressions — a failure produced an unhandled promise rejection with no toast, no loading state, nothing.
- **Files changed**: `frontend/src/screens/AccessScreen.jsx`
- **Why the fix works**: wrapped each call in `try/await/catch` with `_errMsg(...)` toast, matching every other action on the same screen.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none — success path unchanged, only the failure path now gives feedback.

## Copy-to-clipboard reports success even when the copy fails (3 screens)

- **Root cause**: `AccessScreen.jsx`, `ApiKeysScreen.jsx`, `WebhooksScreen.jsx` each called `navigator.clipboard.writeText(...)` and showed a success toast either synchronously right after (not awaiting the promise) or via a `.then()` with the toast placed outside it — so a clipboard-permission failure or other async rejection still showed "copied" to the user.
- **Files changed**: all three screens above
- **Why the fix works**: toast now fires only inside the resolved `.then()`/after a successful `await`, with a `.catch()`/`catch` branch showing an accurate failure message.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none — success UI is identical on the actual-success path.

## Viewer search: network error indistinguishable from "no matches"

- **Files changed**: `frontend/src/components/SearchPanel.jsx`
- **Why the fix works**: added a `searchError` state, set only in the catch branch; the empty-results message now reads "Search failed — check your connection and try again" (in red) instead of the misleading "No matches found" when the request itself failed.
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none — genuine zero-result searches still show the original message.

## Extract Sidecars: silent failure

- **Files changed**: `frontend/src/components/ViewerInfoPanel.jsx`
- **Why the fix works**: added `useToast` and replaced the empty `catch {}` with a toast on failure. (The separate "success claimed before background task actually completes" timing gap is documented, not fixed — see `UI_API_CONTRACT.md`; that needs a backend status/polling contract, not a frontend patch.)
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none, additive error path.

## Billing Refresh: completely silent failure

- **Root cause**: `load()` never set the screen's `error` state on a non-OK response, and its catch block was empty — the only action across all 12 screens with zero user-facing feedback on failure.
- **Files changed**: `frontend/src/screens/BillingScreen.jsx`
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none — reuses the screen's existing error-display block, already wired for the Upgrade/Manage actions.

## Two destructive-dialog consistency fixes

- **Delete Document modal** now names the document itself (not just its share links) as being deleted (`UploadScreen.jsx`).
- **Storage retention modal** now uses the standard warning template + danger button when the change actually schedules deletion, and a lighter non-alarming style when switching to "never" (which is safe, not destructive) (`StorageScreen.jsx`).
- **Tests**: `npm test`, `npm run build`. **Regression risk**: none, copy/styling only.

## Dead code removed

`frontend/src/components/analytics/RangeBtn.jsx` (deleted, zero references), `frontend/api.js:formatBytes()` (removed, zero references, `StorageScreen.jsx` has its own), CSS classes `.header-btn-label`/`.screen-enter` (removed from `SecureDoc.html`, zero usages), `frontend/docs/` (removed, a 3-level-deep tree with zero files at any level). Full evidence trail in `REPOSITORY_HEALTH.md`.

## WebhookDelivery composite index

- **Files changed**: `backend/app/models/webhook.py`, `backend/alembic/versions/027_webhook_delivery_index.py`
- **Why the fix works**: `get_deliveries()` filters on `webhook_id` and sorts by `created_at DESC`; the prior index only covered the filter, forcing an extra sort step. New composite index covers both.
- **Tests**: migration chain verified (single linear head, `027` is the only file with `down_revision = "026"`). **Regression risk**: none — pure index addition, no data/behavior change.

---

## Suite-wide verification (Sprint V6.0, run after all fixes above)

- `cd frontend && npm test` → **13/13 passed**
- `cd frontend && npm run build` → succeeded, `dist/app.bundle.js` 311.3kb, no errors
- `cd backend && python -m pytest tests/unit tests/integration tests/regression -q` → **1702 passed, 1 skipped, 0 failed**
- `git diff` scanned for `TODO`/`FIXME`/`console.log`/`debugger`/stray `print(` in all touched files → none found
