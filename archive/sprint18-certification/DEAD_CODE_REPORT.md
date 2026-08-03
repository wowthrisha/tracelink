# Dead Code Report — V18.0 Repository Certification

Full-repository dead-code sweep across `backend/`, `frontend/`, `tests/`, `scripts/`. Every finding below is classified as exactly one evidence type per the sprint's No-Hallucinations policy: **Compiler verified** (ruff/AST) · **Linter verified** (eslint) · **Source verified** (manually read + repo-wide grep for zero references) · **Runtime verified** (pytest collection/execution) · **Git history verified** · **Insufficient evidence** (flagged explicitly, not asserted).

Nothing below was removed without first confirming zero references across the *entire* repository (backend, frontend, tests) — not just the directory it lives in.

## Fixed this sprint (verified zero-reference, removed, tests/build re-verified after)

| # | Finding | File(s) | Evidence | Verification |
|---|---|---|---|---|
| 1 | `get_optional_user()` — zero production callers, only its own dedicated unit-test class | `backend/app/auth.py`, `backend/tests/unit/test_auth.py` | Source verified — repo-wide grep for `get_optional_user` found only the definition + 4 test methods exercising it directly, no `Depends(get_optional_user)` anywhere | Backend suite 1705 passed/1 skipped/0 failed (1709 − 4 removed tests); Docker rebuild healthy |
| 2 | `@keyframes progressAnim` — zero `className`/inline-`style` references | `frontend/SecureDoc.html` | Source verified — grep for `progressAnim` across `frontend/` returns only the definition | `npm run lint` exit 0, 13/13 tests, build succeeded (309.0kb) |
| 3 | `asyncio`, `json` imports — zero `asyncio.`/`json.` usage in file | `backend/tests/conftest.py` | Source verified — grep confirms no call sites, only `pytest_asyncio.fixture` decorators (different name) | Full backend suite passed |
| 4 | Duplicate local `fmtDate()` — byte-identical to `utils/viewer.js`'s exported version, already used by 7 other screens | `frontend/src/screens/AccessScreen.jsx` | Source verified — diffed both implementations character-for-character | 13/13 tests, lint exit 0, build succeeded |

## Found, NOT fixed this sprint — documented for a future pass

Each of these is proven dead/duplicate by the same zero-reference standard, but was left alone this sprint either because it sits in a file with substantial pre-existing uncommitted work from earlier sessions (touching it safely requires the full backup→isolate→verify→restore cycle used above, and this sprint's effort budget went to the highest-value items) or because removing it is a larger, riskier refactor than a certification sprint should rush.

### Backend

| Finding | File:line | Evidence | Why not fixed | Effort | Regression risk |
|---|---|---|---|---|---|
| `SUPPORTED_WORD_EXTENSIONS` constant, zero references anywhere in repo | `backend/app/services/text_processor.py:24` | Source verified | File carries unrelated pre-existing uncommitted changes; needs isolation cycle | Trivial (1-line removal) | None |
| 4 unused threshold constants: `PAGE_STARTED_MS`, `PAGE_READING_MS`, `PAGE_COMPLETED_RATIO`, `IDLE_THRESHOLD_MS` | `backend/app/services/reading_analytics_service.py:39-44` | Source verified — zero references in file or repo. Note: `IDLE_THRESHOLD_MS` duplicates a *used* constant of the same name/value in `frontend/src/hooks/useReadingAnalytics.js:24` (see Duplication section) | File is the repo's largest (1304 lines) and carries pre-existing uncommitted changes — highest-risk file to touch without dedicated attention | Trivial removal, but file needs isolation first | Low if isolated correctly |
| ~120 unused imports across `backend/tests/*` and `tests_e2e/*` (mocks, unused model/service imports, stdlib modules) | Many files, full list in the backend research pass | Source verified via `ruff check --select F401,F811,F841` | Bulk mechanical cleanup across dozens of test files — real but low-urgency; a dedicated "test hygiene" pass is a better unit of work than folding into this sprint | Medium (needs per-file review, not blind `ruff --fix`, since some hits are the fixture-import idiom, not true dead code) | Low, but only if reviewed file-by-file (auto-fix could break the `app_page` fixture-import pattern used in `tests_e2e/ui/*.py`) |
| Malformed `# noqa: <free text>` on `backend/tests/conftest.py`'s remaining 6 model-registration imports | `backend/tests/conftest.py:15-20` | Source verified — ruff only parses rule codes after `noqa:`, so free text doesn't suppress anything | **Actually fixed this sprint** — see Fixed table above | — | — |

### Frontend

| Finding | File:line | Evidence | Why not fixed | Effort | Regression risk |
|---|---|---|---|---|---|
| `S` spacing-scale constant, zero imports anywhere | `frontend/src/constants/tokens.js:48-55` | Source verified. **Deliberately not removed** — the file's own preceding comment documents it as intentional scaffolding for future code, not accidental dead code; removing it would be second-guessing a recorded product decision, not cleaning up debt | N/A — judged out of scope, not merely deferred | — | — |
| `frontend/src/screens/AccessScreen.jsx`'s expiry/max-views validation block duplicated at two locations in the same file (create-link vs. edit-link forms) | `AccessScreen.jsx:130-139` vs `:929-934` | Tool verified (jscpd) + source verified | `AccessScreen.jsx` is the largest file in the frontend (1005 lines, 52 `useState` calls) and — even after this sprint's one isolated fix — still carries substantial pre-existing uncommitted work; a structural extraction here needs a dedicated pass, not a certification-sprint drive-by | Medium (extract a shared validator function, thread through both forms) | Medium — touches the two most business-critical forms on the Access Control screen |
| Default-permissions object literal duplicated 3×: create-link form, edit-link form, `QuickShareModal.jsx` | `AccessScreen.jsx:70-78`, `:923-926`, `QuickShareModal.jsx:7-15` | Tool verified (jscpd) + source verified | Same reason as above | Low (extract one shared constant) | Low |
| `'securedoc_token'` localStorage key repeated as a raw string literal in 5 places across 4 files, with no shared constant (contrast: `NotificationsScreen.jsx` already extracts its own localStorage key into `LS_LAST_SEEN`) | `AppShell.jsx:28,49`; `LoginScreen.jsx:57`; `BillingScreen.jsx:6`; `ViewerInfoPanel.jsx:12` | Source verified | All 4 files carry pre-existing uncommitted work | Trivial (one named constant, 5 call-site swaps) | Low |
| Byte-size formatting reimplemented ad hoc — full tiered formatter in `StorageScreen.jsx`, cruder MB-only version in `DocRow.jsx` | `StorageScreen.jsx:7-13`, `components/upload/DocRow.jsx:27` | Source verified | Both files carry pre-existing uncommitted work | Low (extract `formatBytes` into `utils/viewer.js`) | Low |
| `_load_toc_sidecar` duplicated near-verbatim between router and service (a code comment says this is deliberate, for test-patching purposes, but it's still duplicated logic) | `backend/app/routers/viewer.py:54`, `backend/app/services/viewer_service.py:61` | Source verified | Author's own comment claims intentionality — needs a decision from whoever owns that reasoning before overriding it, not a unilateral removal | Low if approved | Low |

### Zero-reference candidates from `ruff`/`vulture` that were investigated and confirmed **NOT** dead (listed so a future pass doesn't re-flag them)

`all_adapters`, `is_available`, `rasterize_document`, `file_exists`, `invalidate_toc`, `clear_page_cache`/`clear_thumb_cache`/`clear_metadata_caches`, `reset_redis_page_cache`, `requeue_orphaned_uploads`, `_resolve_migration_url`, `_configure_worker_logging`, `_validate_production_hsts`, `is_valid`, `af` — all confirmed to have real callers via framework decorators (`@celery_app.task`, `@field_validator`), Celery beat schedules, or Alembic's `env.py`, which static import-grep tools don't always resolve.

## Backend routes with zero frontend caller (dead-route candidates, not removed — see reasoning per row)

| Route | Evidence | Reasoning / recommendation |
|---|---|---|
| `GET /api/notifications/stream` (SSE) | Source verified — `NotificationsScreen.jsx` polls `getEvents()` every 30s instead; no `EventSource` usage anywhere in `frontend/src` | Likely superseded-but-not-removed backend endpoint. **Do not delete blindly** — confirm with whoever owns the notifications roadmap whether SSE is planned to replace polling before removing; low urgency either way |
| `GET /api/orgs/{org_id}/domain/token`, `POST /api/orgs/{org_id}/domain/verify` | Source verified + corroborated by `docs/product-review/WORKFLOW_GAPS.md:92-93`, which independently documents these as unwired | Real gap — custom-domain verification was built backend-side but never wired to any UI. Product/design question (is this feature still wanted?), not an engineering deletion call |
| `GET /api/documents/{document_id}/versions` | Source verified — no `versions` reference anywhere in frontend | Same category — backend capability with no UI consumer |
| `GET /api/api-keys/{key_id}` (single-key fetch) | Source verified — `frontend/api.js` has no wrapper for it at all | Lowest-risk of the four to actually remove (thin single-purpose endpoint, no product ambiguity) — candidate for a future ENG ticket |
| `POST /api/billing/webhook` | N/A | **Not dead** — Stripe-invoked server-to-server webhook, expected to have zero frontend caller |

## Migrations, tests, imports — clean

- **Alembic migration chain**: single unbroken chain, 001→027, no branches, no orphans. Runtime verified (`alembic heads` = single head).
- **Test collection**: `pytest --collect-only` against `backend/tests` (1710 items) and `tests_e2e` (219 items) — zero collection errors, zero broken imports. Runtime verified.
- **Backend broken-import check**: `ruff check app --select F821` — 7 hits, all confirmed false positives (SQLAlchemy string forward-references, a closure-analysis false positive in `viewer.py`). Compiler verified.
- **Frontend broken-import check**: wrote a resolver script matching every relative `import` against its target file's actual exports — zero broken targets. Source verified.
- **Circular imports**: built static import graphs for both `backend/app/` (module-level) and `frontend/src/` — zero cycles in either. Source verified.
- **`console.log`/`debugger`/`print()`/`TODO`/`FIXME`/`XXX`/`HACK`**: zero matches anywhere in `backend/app`, `frontend/src`, `backend/tests`, `tests_e2e`, `scripts/` (excluding legitimate CLI-script prints in `backend/migrate.py`/`backend/demo_storage_patch.py`, and instructional `# Generate with: python -c "...; print(...)"` comments). Source verified.

## Stray non-code artifacts

10 SQLite `.db` files (`test_identity_thread_part8.db`, `test_link_service.db`, `test_purge_sessions.db`, `test_securedoc.db`, `test_viewer_identity.db` in repo root; the same 5 plus `test_phase5.db` in `backend/`) — all confirmed **untracked and gitignored** (`.gitignore:49` matches `*.db`) via `git ls-files`/`git status --ignored`. Not a git-hygiene defect, just local test-run byproducts; not touched (removing files from a user's local working directory outside of git's purview is out of scope for a repository certification, and they cost nothing since they're already excluded from version control).
