# Production Regression Certification — V23.0 Sprint

**Date:** 2026-08-11
**Commits this sprint:** `7c5e7eb`..`b71185d` (9 commits, all on `main`, local only — **none pushed to `origin/main`**)

## Deployment status — read this first

`origin/main` auto-deploys to the live Railway production instance on push. **Nothing from this sprint has been pushed.** The live production app is running whatever was deployed before this session and has received none of these fixes. Everything below was verified against the **local Docker stack** (`localhost:8000`), which was rebuilt and redeployed after every commit.

Do not push to `origin/main` without the user's explicit, separate confirmation — that decision is outside this sprint's scope.

## Regression suite

| Check | Result |
|---|---|
| Backend test suite (`pytest tests/`) | **1763 passed, 1 skipped, 0 failed** |
| Frontend test suite (`vitest run`) | **56 passed, 0 failed** (10 files) |
| Frontend lint (`eslint src`) | Clean |
| Frontend build (`esbuild`) | Succeeds — `dist/app.bundle.js` rebuilt and committed |
| Migration | No schema changes this sprint (BUG-004 only added reads of already-existing `expires_at`/`lifecycle_state` columns) |
| Local Docker stack | `api`, `worker`, `db`, `redis`, `beat` all healthy; `api`/`worker` rebuilt and redeployed after each fix |

## Per-workflow re-verification

Per the governing mandate, every touched workflow was re-opened from scratch rather than trusting prior audit results.

| Workflow | Status | Evidence |
|---|---|---|
| Viewer — page/session load | ✅ Verified | Live public share-link session opened, paged through, TOC/Search exercised (BUG-001 investigation) |
| Viewer — TOC navigation | ✅ Verified | Forward + backward jumps across chunk boundaries, live browser clicks |
| Viewer — Search | ✅ Verified | Live search, correct chunk auto-navigation |
| Viewer — Insights/Analytics panel | ✅ Verified (source + tests) | BUG-002 fix; crash reproduced with pre-fix code shape, proven non-throwing post-fix |
| Viewer — Download/Print restrictions | ✅ **Browser Verified** | BUG-005: live focus + click test, before/after |
| Viewer — document expiry enforcement | ✅ **API Verified** | BUG-004: live curl against `/validate`, `/gate`, `/page`, `/thumb` with an expired document — all correctly return 410/expired status |
| Documents list — Expires column | ✅ Verified (source + tests) | BUG-004 frontend half |
| Analytics — Overview/By Document/By Group | ✅ Verified (source + tests) | BUG-003 labeling fix; underlying numbers were never wrong |
| Analytics — help tooltips | ✅ Verified (source + tests) | BUG-008 |
| Access Control — Feedback Export | ⏳ Source + test verified only | BUG-006 — needs owner login for live visual check |
| Webhooks — New Webhook checkboxes | ⏳ Source + test verified only | BUG-007 — needs owner login for live visual check |
| Sign-in / auth hydration | ✅ **Reproduced and fixed, browser-verified both states** | OBS-001 |
| Storage, API Keys, Audit Log, Organizations, Notifications, Billing | Not touched this sprint | No changes made; not re-verified (out of scope — no reported defect) |

## Retention/cleanup job (BUG-004 collateral finding)

While verifying BUG-004, ran `securedoc.cleanup_expired_documents` directly against a disposable test document with a past `expires_at`. It correctly marked the document expired and deleted it (DB row + storage). **Noted but not fixed:** the run's own audit-log call (`log_audit_event(..., actor_user_id=None, ...)`) throws internally (`uuid.UUID(None)` — caught by the function's own try/except, so the cleanup itself is unaffected, but no audit trail is written for automatic retention deletions). This is a separate, low-priority gap requiring a schema change (`actor_user_id` is currently `nullable=False`) — out of scope for this sprint, flagged here rather than silently dropped.

## What was NOT verified

- **Production Railway app** — not touched, not deployed to, not browser-tested this session.
- **BUG-006, BUG-007, BUG-008 live browser rendering** — fixed and unit-tested, but the actual pixel/interaction verification needs an authenticated owner session, which requires the user to sign in themselves (the assistant does not enter credentials into login forms, regardless of authorization).
- Any workflow not listed above (Storage, API Keys, Audit Log, Organizations, Notifications, Billing) — untouched this sprint, so re-verification was out of scope per the governing instruction to avoid speculative scope beyond reported defects.

## Certification

**LOCAL STACK: READY.** All 9 findings resolved or correctly classified (1 unconfirmed/not-reproducible, 7 fixed, 1 reproduced-and-fixed), zero regressions in 1763+56 automated tests, zero new lint/build issues.

**PRODUCTION: NOT YET DEPLOYED.** Requires an explicit, separate decision to push `main` → `origin/main` before any of this reaches the live app.

**OUTSTANDING BEFORE FULL SIGN-OFF:** BUG-006/007/008 live visual re-verification, pending owner sign-in.
