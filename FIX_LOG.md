# Fix Log

Base commit: `2c1795f` (all changes below are currently uncommitted in the working tree — no commit has been created per this session's git policy of not committing without explicit request).

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
