# Bug Remediation Report — V23.0 Evidence-Driven Sprint

**Date:** 2026-08-11
**Scope:** BUG-001 through BUG-008, OBS-001 (live browser-reported backlog)
**Environment:** Local Docker stack (`localhost:8000`) — production Railway app was **not** touched or deployed to this session; see `PRODUCTION_REGRESSION_CERTIFICATION.md` for what that means for rollout.

## Summary

| ID | Severity | Root Cause | Fix | Verification | Commit | Status |
|---|---|---|---|---|---|---|
| BUG-001 | Medium | None found — TOC/Search chunk-jump logic is correct end-to-end for a real multi-chunk `.md` document (backend chunk math, TOC extraction, frontend `setPage` wiring all verified independently) | N/A | Browser Verified (live TOC + Search jumps, forward and backward, across chunk boundaries, using the exact section names from the report — all succeeded) | — | **UNCONFIRMED / NOT REPRODUCIBLE** |
| BUG-002 | High | `ViewerScreen.jsx` handed the raw `/insights` and `/viewers` API envelope objects straight through to `InsightsModal`, instead of unwrapping their `.insights`/`.viewers` array like the sibling `/heatmap` → `.pages` pattern already does | Unwrap envelopes in `ViewerScreen.jsx`; harden `ViewersTab`/`InsightsTab` guards to `Array.isArray()` | Source Verified + Regression Verified (10 new frontend tests, incl. the exact pre-fix envelope shape proven non-throwing) | `7c5e7eb` | **FIXED** |
| BUG-003 | Medium-High | Not a data bug — Overview's `blocked_attempts_today` and By Document/By Group's `blocked_attempts` are two intentionally different, both-correct metrics (today vs. all-time) with no UI label saying so | Renamed Overview card to "Blocked Attempts (Today)" (matches existing "Views Today" convention); added disambiguating tooltips to the all-time "Blocked" columns/cells | Source Verified + Regression Verified (7 new frontend tests) | `5a34cca` | **FIXED** |
| BUG-004 | High / Security | Document retention expiry (`expires_at`/`lifecycle_state`) was never checked in the viewer access path — only the daily cleanup job's eventual row deletion enforced it (up to 24h gap, or indefinitely if the job doesn't run); separately, the Documents-list "Expires" column read a nonexistent field (`doc.expires`) against a hardcoded stale date | Added `_check_doc_not_expired()` to the shared viewer cache-lookup, `LinkService.validate_link()`, and `/gate`; added `expires_at`/`lifecycle_state` to `DocumentSummary` and fixed `DocRow.jsx` to read the real field with a rolling "expiring soon" window | Browser/API Verified (retention job re-run locally against a disposable expired document; live curl against `/validate`, `/gate`, `/page` all correctly reject) + Regression Verified (12 new backend tests, 7 new frontend tests); full backend suite 1763 passed/1 skipped/0 failed | `d4dcdbb` | **FIXED** |
| BUG-005 | Low-Medium | Toolbar Download/Print buttons used native `disabled`, which removes them from the Tab order entirely (verified: `.focus()` silently no-ops) — keyboard/screen-reader users could never reach the button to hear why it was blocked; the click handlers also silently no-opped for mouse users | Switched to `aria-disabled` (stays focusable/clickable, still visually inert); `onDownload`/`onPrint` now show an explanatory toast, reusing the existing Ctrl+S/Ctrl+P keyboard-block message | **Browser Verified** — live: `.focus()` now succeeds, clicking each blocked button shows the toast | `08054c6` | **FIXED** |
| BUG-006 | Low | Export `<select>`'s `<option>` elements had no dark styling, so the browser rendered its native light system listbox on open | Styled each `<option>` with the existing dark surface design tokens (no shared dropdown component exists in this codebase to swap in instead) | Source Verified + Regression Verified (3 new frontend tests) — **Browser Verification pending owner sign-in** | `247bafe` | **FIXED, PENDING LIVE VERIFY** |
| BUG-007 | Low | Global `input, textarea, select { width: 100%; ... }` CSS rule (meant for text inputs) has no `[type="checkbox"]` exclusion, stretching the webhook event checkboxes | Applied the same inline-style override `LinksPanel.jsx`'s checkbox already uses | Source Verified + Regression Verified (2 new frontend tests) — **Browser Verification pending owner sign-in** | `2002eb3` | **FIXED, PENDING LIVE VERIFY** |
| BUG-008 | Low | The "?" help icon had an `aria-label` but was a non-focusable `<span>` — keyboard/screen-reader users could never Tab to it | Converted to a real `<button>` (natively focusable, `title` fires on focus too) | Source Verified + Regression Verified (4 new frontend tests) — **Browser Verification pending owner sign-in** | `80e09ce` | **FIXED, PENDING LIVE VERIFY** |
| OBS-001 | Low (was Unconfirmed) | A stored token past its own `exp` claim was trusted at face value on first render — the authenticated shell mounted and fired 3 API calls before any 401 came back, then a hard reload bounced back to Sign In | Client-side `exp` check before the first render decision — no network round trip needed | **Reproduced and Browser Verified both before and after** — live network log showed 3× 401 after shell mount (before fix), then 0 API calls with immediate Sign In (after fix) | `1359d61` | **CONFIRMED, FIXED** |

## Verification legend

- **Browser Verified** — driven live via `claude-in-chrome` against the local Docker stack (public share links + synthetic localStorage token manipulation; no credentials were ever entered).
- **API Verified** — exercised via direct HTTP calls against the running local API, bypassing the browser.
- **Source Verified** — root cause and fix confirmed by reading the actual code path, not inferred.
- **Regression Verified** — covered by new automated tests, run and passing.

## What's still pending

BUG-006, BUG-007, BUG-008 need **owner-authenticated** screens (Access Control, Webhooks, Analytics) to browser-verify. The assistant does not enter credentials into login forms under any circumstances — this is a standing boundary, not a preference. All three are fixed, unit-tested, deployed to the local Docker stack, and ready for a five-minute visual check once signed in.

## Regression status (full suite, this session)

- **Backend:** `PYTHONPATH=. python -m pytest tests/` → **1763 passed, 1 skipped, 0 failed**
- **Frontend:** `npm test -- --run` → **56 passed, 0 failed** (10 test files)
- **Lint:** `npm run lint` → clean
- **Build:** `npm run build` → succeeds, bundle rebuilt and committed
- **Local Docker stack:** rebuilt and redeployed after every fix; `api`/`worker` healthy throughout

See `PRODUCTION_REGRESSION_CERTIFICATION.md` for the full re-verification matrix and what remains before any of this reaches the live Railway app (nothing has been pushed to `origin/main`).
