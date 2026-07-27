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

**Zero regressions.** ENG-001 was a CSS-only change (3 `gridTemplateColumns` values); no backend code touched, so the identical backend pass count was expected and confirmed, not just assumed.

### Why a local Docker stack instead of testing against production or trusting source alone

The deployed instance auto-deploys from `origin/main` on push — verifying a fix there would mean shipping unverified code to production first. `docker compose up --build` (Postgres 16 + Redis 7 + the API + worker, all local-only) uses the same Supabase auth project as production but a completely separate local database, so real production data was never at risk, while still giving genuine, real-browser evidence rather than a source-code assumption that a CSS change "should" fix the clipping.
