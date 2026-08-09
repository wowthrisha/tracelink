# Regression Report — JWKS outage fix

## New tests

**File**: `backend/tests/integration/test_jwks_outage.py` (new, 6 tests)

| Test | Reproduces / proves |
|---|---|
| `TestJWKSFetchErrorHandling::test_fetch_jwks_raises_typed_error_on_dns_failure` | A DNS/connect failure during JWKS fetch raises the typed `JWKSUnavailableError`, not a raw `httpx.ConnectError` |
| `TestJWKSFetchErrorHandling::test_get_public_key_returns_503_with_no_cache` | With no cache and Supabase unreachable, `_get_public_key` raises `HTTPException(503)` |
| `TestJWKSFetchErrorHandling::test_get_public_key_falls_back_to_stale_cache` | With an expired-but-present cache and Supabase unreachable, `_get_public_key` returns the stale key instead of failing |
| `TestJWKSFetchErrorHandling::test_get_current_user_returns_503_not_500_when_supabase_unreachable` | `get_current_user` — the shared dependency behind every JWT-gated route — surfaces `503`, explicitly asserting `!= 500` |
| `TestDocumentsEndpointDuringOutage::test_list_documents_returns_503_not_500` | **End-to-end reproduction of the reported incident**: a real HTTP request to `GET /api/documents` with the JWKS endpoint down returns `503` with a clean JSON `detail`, not a `500`/stack trace |
| `TestDocumentsEndpointDuringOutage::test_list_documents_succeeds_on_warm_cache_despite_outage` | With a warm cache, `GET /api/documents` returns `200` and the network is asserted **not** to be touched at all — proves the fix doesn't add latency/risk to the healthy path |

All 6 initially caught real bugs in the test-writing process itself
(fake-JWT padding, and two tests that inadvertently patched the *test
client's own* `httpx.AsyncClient.get` instead of just the internal JWKS
fetch) — both were fixed by scoping the mock to `app.auth._fetch_jwks`
directly for router-level tests, which is the correct boundary since the
lower-level httpx behavior is already covered by the unit-level tests in the
same file.

## Full suite result

```
$ PYTHONPATH=. python -m pytest tests/ -q
1699 passed, 1 skipped, 20 warnings in 75.43s
```

- **0 regressions** relative to the pre-fix baseline (also 1699 passed / 1
  skipped before this change; the 1 skip and warning set are pre-existing
  and unrelated — Redis connection-teardown warnings under Python 3.13's
  asyncio and a `datetime.utcnow()` deprecation warning inside `botocore`,
  neither touched by this fix).
- The existing `tests/unit/test_auth.py` suite (11 tests covering the
  pre-existing JWT verification paths — valid token, missing header, wrong
  scheme, expired token, invalid token, unsupported algorithm, key-rotation
  retry) all still pass unchanged, confirming the fix is purely additive
  around the network-failure path and doesn't alter behavior when Supabase
  is reachable.

## What is intentionally NOT covered by these tests

- The actual Supabase project's DNS/pause state — that's infrastructure,
  not application code, and isn't something a unit/integration test can
  assert against (see `DEPLOYMENT_VERIFICATION.md`).
- Behavior of routes that use `get_optional_user` (public/anonymous-capable
  routes) during an outage — that path already swallows `HTTPException` and
  returns `None`, so it degrades correctly by construction; adding a
  dedicated test was judged unnecessary since no code in that path changed
  ordering or exception types.

---

## Sprint V12.0 — Final Production Certification (2026-07-26)

Full backend suite run after every fix this sprint, not just at the end:

| Checkpoint | Backend | Frontend | Build |
|---|---|---|---|
| Baseline (start of sprint) | 1705 passed, 1 skipped | 13/13 passed | clean |
| After audit-commit fix (`links.py` create/revoke/update + `audit.py` allowlist) | **1708 passed**, 1 skipped | not touched | not touched |

**Zero regressions.** The 3 new tests added this sprint (`test_link_created_is_audit_logged`, `test_link_revoked_is_audit_logged`, `test_link_updated_is_audit_logged` in `tests/regression/test_link_lifecycle.py`) were verified to be genuinely meaningful, not tautological: each was run against the pre-fix code (via `git stash`) and confirmed to **fail** there, then re-run against the fix and confirmed to **pass** — proving the tests actually catch the bug class they claim to, not just checking something trivially true.

## Sprint V12.0 — what was NOT regression-tested (and why)

- **The live-propagation fix verification** (Access Control → Edit Link → active viewer session sees the change immediately) was verified live via Playwright against the deployed instance, not via a new automated backend/frontend test — this is inherently a live, multi-context, multi-request-cycle behavior (owner edits, then a *separate* already-open anonymous session re-fetches) that the existing test harness's single-shared-session fixture can't faithfully simulate (the same limitation that masked the audit-commit bug originally — see `FIX_LOG.md` V12-1). Recorded as verified-live evidence (`docs/ui-audit/Screenshots/Access_Control/`) rather than a unit test.
- **Reading Intelligence pause-on-blur** was verified live by dispatching real `blur`/`visibilitychange` events in a real browser and screenshotting the visible content-blur + timer-pause response — this is a DOM/rendering behavior not meaningfully testable via the backend test suite, and the frontend test suite (vitest, jsdom-based) doesn't exercise real `document.hidden` transitions realistically enough to be worth adding a test for here.

---

## Sprint V14.0 — Owner Mode fix cycle (2026-07-26)

Full backend + frontend suite run after every fix, plus live browser re-verification against a local Docker stack (not production) for every UI change, per the sprint's "browser evidence overrides assumptions" rule.

| Checkpoint | Backend | Frontend | Build | Browser re-check |
|---|---|---|---|---|
| Baseline (start of V14.0) | 1708 passed, 1 skipped | 13/13 passed | clean | — |
| After ENG-001 (Analytics grid overflow fix) | **1708 passed**, 1 skipped (unchanged) | **13/13 passed** (unchanged) | not rebuilt as a static bundle — verified via full Docker image rebuild instead | 768px/834px/1440px re-measured, zero clipping, zero visual regression |
| After ENG-002 (Notifications feed document identity) | **1708 passed**, 1 skipped (unchanged) | **13/13 passed** (unchanged) | Docker image rebuild (API + frontend bundle) | Live event generated via a real share link on the local stack; Notifications feed confirmed showing real document name + page number on every entry |
| After ENG-003 (cross-account IDOR verification) | N/A — no code changed | N/A — no code changed | N/A | Direct API cross-account access attempts (documents, links, API keys) all correctly blocked (404/403); Account A's resources confirmed untouched afterward |
| **Post-High-tier regression pass** (before starting Medium tier) | **1708 passed**, 1 skipped (unchanged) | **13/13 passed** (unchanged) | N/A | Fresh re-login on both test accounts (original tokens were ~1hr old); Analytics re-verified clean at 768/834/1440px; Notifications feed re-verified still showing document names; IDOR cross-account block re-verified with fresh tokens — all three High-tier fixes hold under independent re-verification, not just their original test run |
| After ENG-004 (document picker disambiguation) | **1708 passed**, 1 skipped (unchanged) | **13/13 passed** (unchanged) | Docker image rebuild | Access Control document picker now shows upload date on both local test documents; no layout regression |
| After ENG-006 (storage blocking-I/O audit — no code changed) | **1708 passed**, 1 skipped (unchanged) | **13/13 passed** (unchanged) | N/A | N/A — audit only |
| **Medium-tier completion regression pass** (before starting Low tier) | **1708 passed**, 1 skipped (unchanged) | **13/13 passed** (unchanged) | N/A | Fresh re-login; all 10 dashboard screens re-checked (Upload, Access Control, Analytics, Storage, API Keys, Webhooks, Audit Log, Organizations, Notifications, Billing) — zero raw error text, zero console errors across the full sweep; ENG-004's document-picker fix re-confirmed still showing upload dates |
| After ENG-007 (Audit Log scroll affordance) — first issue under V15.0's expanded regression policy | **1708 passed**, 1 skipped (unchanged) | **13/13 passed** (unchanged) | esbuild succeeded, 312.9kb | Fade renders exactly when the table genuinely overflows (834px) and is absent when it doesn't (900px/1440px); migration container exit 0; repo-wide TODO/FIXME/console.log/debugger/print() sweep clean (5 backend matches, all instructional comments, not real debug code) |
| After ENG-008 (rate-limit 429 boundary — no code changed) | **1708 passed**, 1 skipped (unchanged) | N/A (no frontend change) | N/A | 21 bounded requests against a disposable test link: attempts 1-20 → 401, attempt 21 → 429. Boundary exact, no defect found. Link revoked immediately after |
| After ENG-009 (XSS beyond link labels — no code changed) | **1708 passed**, 1 skipped (unchanged) | N/A (no frontend change) | N/A | Payload tested on org name/API key name/webhook description — literal text on all 3, 0 injected `<img>` elements, 0 dialogs, 0 console errors. Repo-wide grep confirms 0 `dangerouslySetInnerHTML` usage. All 3 disposable test resources deleted after |
| After ENG-010 (expired-link live confirmation — no code changed) | **1708 passed**, 1 skipped (unchanged) | N/A (no frontend change) | N/A | Disposable link with 75s expiry: validate returned 200 before, 410 "Link expired" after an 80s wait. Test link deleted after |
| After ENG-021 (link 403→404 consistency fix) | **1709 passed** (+1 new test), 1 skipped, 0 failed | N/A (backend-only) | N/A | Reverted fix via git stash, confirmed 3 tests fail pre-fix (403 vs 404), restored, confirmed pass. Fresh Account A/B logins on local Docker stack: PATCH/DELETE/DELETE-hard on A's link as B all now return 404 |
| **Low-tier completion regression pass** (before starting Enhancement tier) | **1709 passed**, 1 skipped, 0 failed | **13/13 passed**, build 312.9kb | migrate exit 0 | Fresh logins, all 10 dashboard screens re-checked (zero raw errors, zero console errors); ENG-007's scroll fade re-confirmed present at 834px; ENG-021's cross-account 404 re-confirmed (PATCH as B on A's link → 404) |
| After ENG-029 (architecture doc corrections — docs-only) | **1709 passed**, 1 skipped (unchanged) | N/A (no frontend change) | N/A | Pure documentation fix; TTL/watermark claims re-verified against source before and after edit |
| After ENG-013 (frontend lint tooling + 19 dead-code fixes) | **1709 passed**, 1 skipped (unchanged) | **13/13 passed**, build 312.5kb (down from 312.9kb), `npm run lint` exit 0 | migrate exit 0 | Full Docker rebuild succeeded (after fixing a real lockfile/platform-dependency break found along the way); fresh login, Upload/Access Control/API Keys/Webhooks/Billing/Viewer all clean, zero console errors |
| After ENG-014 (duplicate-code scan + analytics_service.py extraction) | **1709 passed**, 1 skipped (unchanged); `test_analytics.py` 20/20 | **13/13 passed** (verified on both Mac and Alpine independently), build 312.5kb, lint exit 0 | migrate exit 0 | Docker rebuild succeeded (second lockfile platform-drift issue found and fixed properly this time — verified both platforms independently, not just one); fresh login, Analytics screen + "By Group" tab both render real data, zero console errors |
| After ENG-024 (date-formatting consistency) | **1709 passed**, 1 skipped (unchanged) | **13/13 passed**, build 309.0kb, lint exit 0 | N/A (frontend-only) | Docker rebuild succeeded; fresh login, Storage/Billing/Access Control all render cleanly, zero console errors |
| After ENG-025/027/028 (reviewed, not implemented — no code changed) | N/A — no code changed | N/A — no code changed | N/A | N/A — review only, no regression surface |
| After ENG-030 (button-variant consistency, `AccessScreen.jsx`) | Not re-run (frontend-only, no backend surface touched) | **13/13 passed**, build 309.1kb, lint exit 0 | N/A (frontend-only) | No browser-automation tool available this session (see note below); isolated-diff-verified (3 lines) + source-pattern-matched against 3 precedent files instead |
| After ENG-031 (owner preview watermark, `AppShell.jsx`/`ViewerScreen.jsx`/`useViewerSession.js`) | Not re-run (frontend-only, no backend code touched — backend watermark logic itself was unchanged, only the client-submitted `email` value now flows correctly) | **13/13 passed**, build 308.9kb, lint exit 0 | N/A (frontend-only) | Docker `api` container rebuilt and confirmed healthy; direct integration test against the real `/api/viewer/validate` endpoint with a genuine local-Supabase-authenticated session confirmed `watermark_text` changes from `"anonymous · ..."` to `"23z274@psgtech.ac.in · ..."` exactly as the fix intends. No browser-automation tool available this session — not claimed as browser-verified. |

**Zero regressions.** ENG-001 was a CSS-only change (3 `gridTemplateColumns` values); no backend code touched, so the identical backend pass count was expected and confirmed, not just assumed.

| After V18.0 batch 1 (dead-code + dependency hygiene: `conftest.py`, `requirements*.txt`, `ci.yml`, `package.json`, `AccessScreen.jsx`) | **1709 passed**, 1 skipped, 0 failed (unchanged) | **13/13 passed**, build 309.0kb, lint exit 0 | `npm ci --ignore-scripts` verified independently on macOS + Alpine | No browser-automation tool available this session — isolated-diff + lint/test/build verified for each of the 7 files; `requirements.txt`'s OTel version pins additionally Runtime-verified via `pip show` inside the live Docker `api` container before pinning |
| After V18.0 batch 2 (`get_optional_user()` + `@keyframes progressAnim` removal, `auth.py`/`test_auth.py`/`SecureDoc.html`) | **1705 passed**, 1 skipped, 0 failed (1709 baseline − 4 tests removed alongside the dead function they tested) | **13/13 passed**, build succeeded | Docker `api` container rebuilt, `/health` → `{"status":"ok",...}` all subsystems ok | `pytest tests/integration/test_jwks_outage.py tests/unit/test_auth.py` — 13/13 passed, confirming a pre-existing uncommitted JWKS-outage fix (restored via this session's backup→isolate→verify→restore technique after being temporarily reset during isolation) coexists correctly with this commit's dead-code removal |

**Zero regressions across the V18.0 Repository Certification sprint.** Full findings, evidence, and the handful of proven-but-not-fixed items (each with an effort/risk estimate) are in `archive/sprint18-certification/{DEAD_CODE_REPORT,DEPENDENCY_AUDIT,MODULE_BOUNDARY_REPORT}.md` (archived as part of V21.0's documentation consolidation). Documentation archival (48 files, commit `4862abb`) touched zero code and needed no test re-run.

### Note — browser automation unavailable this session (ENG-030, ENG-031)

Every prior "Browser re-check" entry in this table used a real browser driven manually against the local Docker stack. Starting with ENG-030, no browser-automation tool (Playwright, chromium-cli, etc.) was available in this environment (confirmed via `ToolSearch` and a `which`/`ls` check for common binaries). Rather than mislabel source/API-level checks as "browser-verified," both entries above are recorded honestly as their actual evidence class: isolated-diff + lint/test/build verification for the pure-CSS ENG-030 change, and Source + Integration/API verification (direct backend endpoint calls, not a rendered page) for ENG-031. **Full visual browser regression sweep for the "every 5 closed issues" cadence (Upload/Viewer/Reading Intelligence/Analytics/Access Control/Organizations/Notifications/Audit Log/API Keys/Webhooks/Storage/Billing/Share Links) is still owed and not yet satisfied this cycle** — flagged as an open item, not silently skipped.

### V20.0 backlog triage (2026-08-01)

| Checkpoint | Backend | Frontend | Notes |
|---|---|---|---|
| ENG-032 attempted fix (before self-revert) | **2 failed** (`test_phase8.py::TestStartupValidation` x2), 1707 passed, 1 skipped | N/A (no frontend touched) | Caught by this same regression discipline mid-fix — the 2 failures correctly identified that the "fix" was redundant with an existing guard. Reverted, not shipped. |
| After ENG-032 revert | **1705 passed**, 1 skipped, 0 failed (identical to pre-attempt baseline) | N/A | `git status` confirmed byte-identical to HEAD on both touched files before re-running |
| ENG-018/ENG-020 (verification only, no code changed) | N/A — no code changed | N/A | Integration/API-verified against the real local Docker stack with a genuine 120-page synthetic PDF: upload→process→render→search→word-positions→reading-analytics-ingestion all confirmed correct. Full disposable-resource cleanup confirmed (404 on GET post-delete). |
| ENG-019 (partial verification, no code changed) | N/A — no code changed | N/A | 2 toggles (API key, webhook `is_active`) confirmed round-trip correctly via PATCH + fresh re-fetch; both disposable resources deleted after (204 confirmed) |

**Zero regressions.** The one near-miss (ENG-032) was caught and reverted by the mandatory validation step before it could ship — exactly the scenario that step exists to catch.

### V21.0 Production Release Closure (2026-08-02 to 2026-08-04)

| Checkpoint | Backend | Frontend | Notes |
|---|---|---|---|
| Before committing the 62-file pre-existing-work batch | **1705 passed**, 1 skipped, 0 failed (full suite, against the complete as-found working tree, before any of it was staged) | **13/13 passed**, lint exit 0, build succeeded | Confirms the body of work was internally coherent as a whole before trusting any of it |
| After all 8 grouped commits | **1705 passed**, 1 skipped, 0 failed (unchanged) | **13/13 passed** | Docker `api`+`migrate` rebuilt, `/health` all-ok, migration already at head (idempotent, no new migration needed) |
| After ENG-035/ENG-036 (Reading Insights toggle + self-inclusive-average fix) | **1706 passed** (1705 + 1 new test), 1 skipped, 0 failed | **13/13 passed**, lint exit 0, build 309.1kb | The pre-existing test for this endpoint was asserting the *buggy* self-inclusive behavior as correct — running the fix against it caught the regression immediately (`assert None is not None`), confirming both the bug and the fix in one step |
| After documentation consolidation (6 files archived, 1 relocated, README corrected) | **1706 passed**, 1 skipped, 0 failed (unchanged, as expected for a docs-only move) | **13/13 passed** | Re-run per Section 14's explicit mandate to test after structural moves |
| Final state (`d607216`) | **1706 passed**, 1 skipped, 0 failed | **13/13 passed**, lint exit 0, build 309.1kb | Docker `api`+`migrate` rebuilt and healthy; `git status` clean |

**Zero regressions across the V21.0 sprint.** No browser-automation tool available in this environment (checked again this sprint) — all verification above is Test/API/Source-verified, explicitly not claimed as Browser Verified. Full evidence and classification in `docs/release/FINAL_RELEASE_CERTIFICATION.md`.

### V22.0 Residual Risk Closure (2026-08-04 to 2026-08-08)

| Checkpoint | Backend | Frontend | Notes |
|---|---|---|---|
| After ENG-039 (API-key scope enforcement, `orgs.py`/`api_keys.py`/`billing.py`) | **1734 passed** (1706 + 28 new), 1 skipped, 0 failed | N/A (backend-only) | 28 new tests in `test_eng039_org_api_key_scopes.py`; proven meaningful via `git stash` revert — 12/28 failed against pre-fix code, all 28 pass post-fix |
| After ENG-041/042/043 (admin/annotations/notifications scope gaps) | **1742 passed** (1734 + 8 new), 1 skipped, 0 failed | N/A (backend-only) | 8 new tests in `test_priority2_scope_consistency.py`; 3 of 4 fix classes stash-revert-confirmed to fail pre-fix (audit-log, annotations-list, annotations-write); the 4th (SSE stream) not revert-tested the same way — pre-fix code hangs the test consuming a live stream rather than failing cleanly, documented explicitly rather than silently skipped |
| After ENG-017 (Celery task metrics) | **1745 passed** (1742 + 3 new), 1 skipped, 0 failed | N/A (backend-only) | 3 new unit tests in `test_celery_metrics.py`; live-verified via a real document upload processed by the real local Docker worker, `/metrics` checked before/after |
| After ENG-040 (Viewer-toggle inventory — verification only, no code changed) | N/A — no code changed | N/A | Pure audit deliverable; relies on already-passing suite for the 3 server-enforced capabilities' existing coverage |
| After ENG-037/038 (link-active tripwire + TOCTOU reproduction attempt) | **1751 passed** (1745 + 6 new), 1 skipped, 0 failed | N/A (backend-only) | 6 new tests in `test_eng037_link_active_consistency.py`. ENG-038 had no new automated test — 2 live concurrent-request trials against the real Docker stack (asyncio.gather on both owners' removal requests) found no race in either trial; a 3rd trial hit a network-level timeout under real DB contention and was discarded as inconclusive, not counted as evidence either way |
| After ENG-033/034 decision docs + AUTH-006 re-evaluation (docs-only, no code changed) | N/A — no code changed | N/A | Pure documentation; CSP finding for AUTH-006 sourced from a fresh read of `backend/app/middleware/security_headers.py`, cross-checked against zero `dangerouslySetInnerHTML` matches repo-wide |
| Final re-certification (`953def4`) | **1751 passed**, 1 skipped, 0 failed (host-run, `cd backend && python3 -m pytest tests/unit tests/integration tests/regression`) | **13/13 passed**, build 309.2kb | Migration head 027, live DB `alembic current` = 027; `git status` clean; live API smoke pass (`/health`, documents/orgs/links/api-keys/webhooks/admin-audit-log/billing all 200, `/metrics` correctly 403 from outside the allowlist) plus a full disposable-link lifecycle check (create → validate reflects `can_download:false` → edit → validate immediately reflects `can_download:true` → revoke → validate returns 410) against the real Docker stack |

**Zero regressions across the V22.0 sprint.** One environment-selection artifact encountered and resolved: running the backend suite via `docker compose exec api pytest` (rather than host-side) surfaces 25 failures, all traced to pre-existing tests that hardcode the host absolute path `/Users/thrisha/traceview/securedoc/...` (not present inside the container's `/app` filesystem) — not a regression, and not present when run via this repository's established host-side invocation. No browser-automation tool available in this environment (checked again this sprint) — all verification above is Test/API/Source-verified, explicitly not claimed as Browser Verified. Full evidence and classification in `docs/release/V22_RESIDUAL_RISK_CERTIFICATION.md`.

### V23.0 ENG-019 browser sweep + ENG-045 fix (2026-08-08)

| Checkpoint | Backend | Frontend | Notes |
|---|---|---|---|
| ENG-019 sweep (Access Control + Organizations + 8 screens, no code changed until ENG-045) | N/A — no code changed | N/A | Browser Verified via Playwright against the live Railway app; disposable link created/toggled/reloaded/verified/revoked/deleted, cleanup confirmed (0 remaining); zero console errors across all screens visited |
| After ENG-045 fix (`AppShell.jsx`, Feedback nav routing) | **1751 passed**, 1 skipped, 0 failed (host-run, unchanged — frontend-only change) | **13/13 passed**, `eslint` clean, build succeeded (309.2kb, unchanged from V22.0's 309.2kb) | Isolated diff confirmed exactly 3 lines changed in exactly one file (`git diff --stat`); Docker `api` rebuilt from the fixed source and browser-verified on the local stack: Feedback nav → pick doc → lands on Feedback tab (fixed); Access Control nav → pick doc → still lands on Create Link tab (unaffected, confirming the fix didn't touch that path) |

**Zero regressions.** This is the first sprint since V17.0 with genuine Browser Verified evidence — see `CHECKPOINT.md`'s "Environment note — browser automation now available" for why prior sprints incorrectly reported no browser tool as available.

### V24.0 tracking reconciliation + ENG-046 lint fixes (2026-08-09)

| Checkpoint | Backend | Frontend | Notes |
|---|---|---|---|
| Step 1 reconciliation (docs-only, no code changed) | N/A — no code changed | N/A | Fixed a real pre-existing contradiction: ENG-037's detail entry said "Closed" since V22.0 but every summary table said "Open." Recomputed all backlog totals programmatically (not by hand) and verified the arithmetic closes exactly. |
| After ENG-046 fixes (`backend/ruff.toml` + 7 files) | **1751 passed**, 1 skipped, 0 failed (host-run, unchanged) | N/A (backend-only) | `ruff check backend/app` → "All checks passed!" post-fix (was 23 errors under the newly-pinned `E4,E7,E9,F` ruleset). Every fix individually reviewed before applying — 7 confirmed ruff false positives (6 SQLAlchemy string-forward-refs, 1 legitimate closure) suppressed with specific `# noqa` comments, not blanket-disabled; 14 import-ordering fixes verified circular-import-safe before moving; 2 direct style fixes. `ruff check backend/app backend/tests` (the literal CI command) now shows exactly 206 errors, down from 229 — confirming the fix touched only what it claimed to and `backend/tests`' pre-existing debt (explicitly quantified, not fixed this pass) is untouched. |

**Zero regressions.** `backend/tests`' 206 remaining lint violations are real, pre-existing, zero-runtime-impact debt — tracked as ENG-046's open remainder, not silently dropped or claimed fixed.

### ENG-048 investigation (2026-08-09) — no code changed

| Checkpoint | Backend | Frontend | Notes |
|---|---|---|---|
| Reading Intelligence pause/resume investigation | N/A — no code changed | N/A — no code changed | Browser Verified defect confirmed (5+ independent Playwright reproductions against the live Railway app); root cause not pinned despite a full 511-line source read of `useReadingAnalytics.js`. No fix attempted — filed as ENG-048 rather than guess-fixed, per the mandate's discipline against fixing subtle state/timing bugs on intuition. |

No regression risk since no code changed. This is the one open item this sprint that isn't a decision-blocker or quantified low-priority cleanup — it's a genuine, unresolved, High-severity product defect, and the next session should treat it as the first priority.

### ENG-048 fix, root-caused via instrumentation, closed (2026-08-09, follow-up pass)

| Checkpoint | Backend | Frontend | Notes |
|---|---|---|---|
| Root-cause instrumentation (temporary, reverted before the real fix) | N/A — backend untouched | N/A — instrumentation-only build, not committed | `console.log` tracing at every state transition in `useReadingAnalytics.js`, rebuilt, reproduced against the local Docker stack. Proved `s.currentPage` stayed `null` for the entire session — a `useEffect` dependency-array race, not the `_pause`/`_accumulate` logic itself (both read correctly on paper, as V24.0's earlier source reads had found). |
| After the real fix (3-line functional change + comment) | **1751 passed**, 1 skipped, 0 failed (host-run, unaffected — frontend-only change) | **15/15 passed** (13 pre-existing + 2 new regression tests), `eslint` clean, build succeeded (309.2kb, unchanged) | Isolated diff confirmed via `git status --short`: exactly 2 files changed (`useReadingAnalytics.js` + rebuilt `dist/app.bundle.js`) plus 1 new test file. Migration head `027` confirmed live. |
| Regression test proof | N/A | 2/2 new tests pass post-fix; **both proven to fail against pre-fix code** via `git stash` — one because `batchReadingEvents` was never called at all (pre-fix bug meant `pageDataSnapshot` was always empty), the other with a `TypeError` on `undefined` for the same reason | Not tautological — genuinely detects the bug class, confirmed by reverting and re-testing. |
| 10-test mandated browser verification (local Docker stack, real timing) | N/A | **9/10 PASS**: blur-freeze (TEST 1, re-run fairly after investigating an initial false-alarm caused by sampling on opposite sides of one legitimate "settle tick"), blur-then-additive-resume (TEST 2), 5× repeated blur/focus (TEST 3), simulated tab-hide via `visibilitychange` override (TEST 5), page navigation across 3 pages (TEST 6), refresh + re-open (TEST 7), 30s idle threshold (TEST 8), uploader-facing View History/Analytics (TEST 9), predicted-remaining-time display (TEST 10). **1 indeterminate**: genuine multi-tab switching (TEST 4) — a second real Playwright page in the same browser context doesn't actually flip `document.hidden` on the original tab in headless Chromium; not an app defect, directly covered by TEST 5's `visibilitychange`-override test which exercises the identical underlying mechanism real tab-switching triggers. | Screenshots captured at each checkpoint (before/mid/after-blur, after-focus, after 5 cycles, after page nav, after refresh, after idle). |

**Zero regressions.** This closes ENG-048 — the first (and, as of this reconciliation, only) High-severity defect V24.0 found, with a complete root-cause → fix → regression-test → browser-verify chain, not a partial or assumed closure.

### Why a local Docker stack instead of testing against production or trusting source alone

The deployed instance auto-deploys from `origin/main` on push — verifying a fix there would mean shipping unverified code to production first. `docker compose up --build` (Postgres 16 + Redis 7 + the API + worker, all local-only) uses the same Supabase auth project as production but a completely separate local database, so real production data was never at risk, while still giving genuine, real-browser evidence rather than a source-code assumption that a CSS change "should" fix the clipping.
