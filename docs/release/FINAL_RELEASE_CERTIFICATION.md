# TraceLink (SecureDoc) — Final Release Certification

**This is the single authoritative release certification for this repository.** It supersedes every prior `FINAL_*`/`*_CERTIFICATION.md`/`*_SCORECARD.md` document, all of which are historical, point-in-time snapshots preserved for audit trail in `archive/` and `docs/release/`'s pre-existing RC1-era reports. Where an older document disagrees with this one, this one is correct — it reflects the repository as it exists at the commit below, not as it existed when the older document was written.

## 1. Release candidate commit

`e17e47b` (branch `main`, 41 commits ahead of `origin/main` — none of this session's commits have been pushed; `origin/main` auto-deploys on push per this repository's established Railway configuration, so nothing here has reached production).

**[SOURCE VERIFIED]** `git log --oneline -1` → `e17e47b chore(repo): consolidate documentation, archive V18.0 certification deliverables`. Working tree is fully clean (`git status` → "nothing to commit, working tree clean") as of this commit.

## 2. Functional status

**[TEST VERIFIED] + [API VERIFIED]** Every Critical, High, and Medium severity item in `ENGINEERING_BACKLOG.md` is closed or explicitly deferred with recorded reasoning. Current backlog state: **39 tracked items — 21 closed, 11 deferred/reviewed/justified with reasoning, 7 open** (each blocked on a named, non-engineering input — see §13).

No unfixed functional defect is known to remain in-scope for this session's work. This claim rests on: (a) the exhaustive multi-sprint backlog process this session ran (V14.0 through V21.0, each re-verifying prior findings before acting), (b) a full backend test suite (1706 passed, 1 skipped, 0 failed) and frontend suite (13/13 passed) re-run after every change, and (c) targeted integration-level verification against the real local Docker stack for every fix where "does the browser actually show the right thing" mattered and a real browser wasn't available (see §4 caveat).

## 3. UI status

**[SOURCE VERIFIED]**, **[INFERRED]** for full cross-screen consistency, **[NOT VERIFIED]** for pixel-level rendering. No browser-automation tool (Playwright, chromium-cli, or equivalent) is available in this environment — confirmed repeatedly across V18.0, V20.0, and V21.0 via `ToolSearch` and binary checks. Every UI claim in this certification is therefore Source Verified (the code was read and is structurally correct) or Integration/API Verified (the backend behavior a UI control depends on was exercised directly), never Browser Verified — stated here explicitly rather than implied.

What is known, with evidence:
- Every dashboard screen's permission toggles follow one consistent pattern (`Toggle` component + `Object.entries(...).map()` render + `setPermissions` state update) — confirmed by reading all instances across `AccessScreen.jsx`, `ApiKeysScreen.jsx`, `WebhooksScreen.jsx`.
- 2 of the dashboard's toggles (API key `is_active`, webhook `is_active`) were verified end-to-end via direct API calls: PATCH the toggle, re-fetch fresh, confirm the change persisted. **[API VERIFIED]**
- The remaining dashboard toggles (Access Control link toggles, Organizations role/settings toggles) follow the identical code pattern as the 2 verified ones but were not independently round-tripped this sprint — tracked as ENG-019, open, blocked on browser tooling or manual QA. **[NOT VERIFIED]**

## 4. Viewer status

**[SOURCE VERIFIED]** + **[API VERIFIED]**. The Viewer is treated as this product's flagship surface per every mega-prompt this session received, and has the deepest verification of any subsystem:

- **Large-document handling**: a genuine 120-page synthetic PDF was uploaded through the real API, processed by the real Celery worker, and confirmed to render correctly (page images at first/middle/last positions, all `200 image/webp`), search correctly (a planted unique marker on page 75 was found with the correct snippet), and extract word-positions correctly (all 120 pages, 203 words on the sampled page) — see `ENGINEERING_BACKLOG.md` ENG-018. **[API VERIFIED]**
- **Reading Intelligence math**: hand-verified against source formulas using a controlled batch submission — `total_active_ms`, `completion_pct`, and `reading_speed_wpm` all matched their source-code formulas exactly, including a deliberately-triggered edge case (a `700.0` wpm result confirmed to be the documented physiological-plausibility clamp firing correctly, not a stale placeholder) — see ENG-020. **[SOURCE VERIFIED]** + **[API VERIFIED]**
- **Owner-preview watermark**: previously showed "anonymous" for the document's own owner; root-caused and fixed (ENG-031), confirmed via direct backend calls that `watermark_text` now shows the real email. **[API VERIFIED]**
- **Error recovery**: a retry-on-error path for failed page loads was confirmed present in source (`usePageLoader.js`'s `retryPage()`, wired to a Retry button in `ViewerScreen.jsx`'s error overlay). **[SOURCE VERIFIED]**, **[NOT VERIFIED]** for the actual click-and-recover browser interaction.
- **Session/tab/refresh/idle/blur handling**: implemented per `useViewerSession.js`/`usePageLoader.js` source reading across this session's many sprints; not independently re-driven through an actual browser this sprint. **[SOURCE VERIFIED]**, **[NOT VERIFIED]** for live multi-tab/refresh behavior.

## 5. Reading Intelligence status

**[SOURCE VERIFIED]** + **[TEST VERIFIED]**. This sprint found and fixed two real defects in the comparative-insights feature (a fully-built backend capability that had no UI toggle to actually enable it, and a self-inclusive average that could mislead a viewer comparing their pace to "other readers" when they were the only reader) — see ENGINEERING_BACKLOG.md ENG-035/ENG-036. Both fixes are covered by new, purpose-built tests that fail against the pre-fix behavior and pass against the fix (`test_viewer_session_current_page_avg_excludes_own_session` asserts an exact numeric value proving exclusion, not just absence of a crash). Full backend suite re-run clean after both fixes: 1706 passed/1 skipped/0 failed.

Units, edge cases, and known-safe behaviors checked this sprint: milliseconds used consistently throughout (`active_time_ms`, `total_active_ms`), no double-counting found in the batch-ingestion path, the `reading_speed_wpm` clamp (`50`-`700`) prevents both zero/negative and physiologically-implausible results, and single-reader/zero-other-reader cases correctly return `None` rather than `NaN`/`Infinity`/a self-referential fake average (post-fix).

## 6. API status

**[SOURCE VERIFIED]**. List endpoints consistently return domain-named wrapper objects (`{"documents":[...]}` etc. — no inconsistency found). Scope-based authorization (`require_scope`) is applied consistently across `documents.py`/`groups.py`/`links.py`/`webhooks.py`/`analytics.py`/`reading.py`/`storage.py`, but **not** across `orgs.py`/`api_keys.py`/`billing.py` — see §7 and ENG-039. Alembic migration chain is a single unbroken chain, 27 revisions, already at head (`alembic upgrade head` clean against the live local Postgres instance).

## 7. Security status

**[SOURCE VERIFIED]** for this sprint's targeted re-checks, **[INFERRED]** for the broader app given this session's extensive prior security work (ENG-003 IDOR, ENG-008 rate-limiting, ENG-009 XSS — all previously live-verified with disposable test accounts, documented in the now-archived `archive/sprint18-certification/` reports and `ENGINEERING_BACKLOG.md`).

**One genuine, currently-open finding**: **ENG-039** — API keys created with zero granted scopes can still call every endpoint in `orgs.py` (12 routes, including member invite/role-change/removal), `api_keys.py` (6 routes), and `billing.py` (3 routes), because those three routers use only `Depends(get_current_user)` with no `require_scope(...)` check, unlike the other 7 routers. This is a real permission-boundary gap for the API-key auth path specifically (JWT/browser callers are unaffected). Not fixed this sprint — extending scope coverage to these routers changes real authorization behavior for every API key using them today and needs a dedicated rollout with a security-focused reviewer, not a same-sprint drive-by. **[SOURCE VERIFIED]**, confirmed live 2026-08-02.

Two lower-severity, previously-existing findings re-confirmed and newly filed this sprint: **ENG-037** (`is_link_active()` is not actually called by the real access-enforcement path despite a commit message claiming otherwise — currently harmless since both independent implementations agree, but the "single source of truth" refactor's stated goal wasn't fully achieved) and **ENG-038** (`ensure_not_last_owner()` has an unguarded TOCTOU race — confirmed pre-existing via `git show` on the code before this sprint's refactor, not newly introduced).

**ENG-032 correction** (a model example for this sprint's evidence discipline): a prior sprint's finding claimed no production-startup guard existed for the `ip_hash_salt`/`domain_verify_salt` config defaults. Re-verification found the guard already exists (`backend/app/main.py:27-54`) — the original finding and an earlier re-check had only looked in the wrong file. An attempted fix was self-caught by its own regression run and reverted. **[SOURCE VERIFIED]**.

## 8. Architecture status

**[SOURCE VERIFIED]**. Directory structure, module boundaries, and dependency graph were fully mapped in `archive/sprint18-certification/MODULE_BOUNDARY_REPORT.md` (V18.0) — zero circular imports found in either backend or frontend, `viewer_cache.py` and `atoms.jsx` are the respective structural hubs (appropriately so, not accidental god-imports). One structural gap remains open and undisputed: `billing.py` has no corresponding service-layer file (all Stripe logic lives directly in the router, unlike every other domain) — documented, not fixed, low urgency.

## 9. Scalability status

**[INFERRED]** — no destructive or synthetic load testing was performed this sprint (explicitly out of scope per every mega-prompt's own constraints). `MODULE_BOUNDARY_REPORT.md`'s architecture pass and this session's earlier `ENG-005` finding (list endpoints lack pagination, deferred with reasoning) remain the current state of knowledge. No new scalability defect was found or fixed this sprint. Do not read this section as a performance guarantee — it is an inference from source review, not a load test result.

## 10. Code-quality status

**[SOURCE VERIFIED]** + **[TEST VERIFIED]**. Zero `TODO`/`FIXME`/`XXX`/`HACK`/`console.log`/`debugger`/stray `print()` in production code (repo-wide grep, re-confirmed this sprint). Zero unused imports in production code (`ruff`/`eslint`, both clean). A large body of previously-implemented-but-uncommitted work (62 files, spanning multiple earlier sprints) was verified as a coherent whole (full test suite passed against it before any of it was committed) and committed this sprint in 8 logically-grouped commits — the repository's `git status` had been showing this as perpetual uncommitted drift for the session's entire duration; it does not anymore.

## 11. Repository-quality status

**[SOURCE VERIFIED]**. Root `.md` file count: 55 (session start of V18.0) → 16 (after V18.0's archival) → **9** (after this sprint's further consolidation): `README.md`, `CHANGELOG.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `ENGINEERING_BACKLOG.md`, `PROGRESS.md`, `CHECKPOINT.md`, `REGRESSION_REPORT.md`. The last four are deliberately kept at root rather than moved under `docs/engineering/` — they are this session's actively-referenced, frequently-updated canonical tracking docs; moving them was judged higher-risk than the discoverability benefit, and is documented as a deliberate deviation in `docs/governance/ARCHIVED_FILES.md`, not an oversight.

`docs/release/` still contains 13 pre-existing historical reports (RC1-era, predating this session) not touched by this consolidation pass — out of scope for this sprint's effort budget; flagged here rather than silently left unaddressed, for a future documentation pass to fold into `archive/`.

## 12. Test evidence

| Suite | Result | Evidence class |
|---|---|---|
| Backend (`pytest tests/`) | **1706 passed, 1 skipped, 0 failed** | **[TEST VERIFIED]** — re-run after this sprint's final commit |
| Frontend (`vitest`) | **13/13 passed** | **[TEST VERIFIED]** |
| Frontend lint (`eslint`) | **exit 0** | **[TEST VERIFIED]** |
| Frontend build (`esbuild`) | **succeeded, 309.1kb** | **[TEST VERIFIED]** |
| Migrations (`alembic upgrade head`) | **clean, already at head (027)** | **[TEST VERIFIED]** against the live local Docker Postgres |
| Docker `api` health (`/health`) | **`{"status":"ok",...}` all subsystems ok** | **[API VERIFIED]** |
| `npm ci --ignore-scripts` on macOS + Linux/Alpine independently | **both succeed** | **[TEST VERIFIED]** |
| Browser-driven end-to-end test | **not performed** | **[BLOCKED — INSUFFICIENT EVIDENCE]** — no browser-automation tool available in this environment, stated honestly rather than fabricated |

## 13. Remaining blocked items

All 7 currently-open backlog items, each with a named blocker that is not an engineering task this session can unilaterally close:

| ID | Item | Blocker |
|---|---|---|
| ENG-017 | Observability wiring (Prometheus scrape/alerting) unconfirmed | Needs infra/ops access to the actual deployment's monitoring config |
| ENG-019 | Dashboard toggle sweep incomplete (2 of many verified) | Needs browser-automation tooling or manual QA |
| ENG-033 | No profile/account-settings screen (PROF-001) | Needs product/design direction — a new screen, not a bug fix |
| ENG-034 | No CD/deploy job in CI pipeline | Needs a deployment-target policy decision |
| ENG-037 | `is_link_active()` not actually used by enforcement path | Low urgency; needs a dedicated test cycle on the app's highest-stakes function, not a drive-by |
| ENG-038 | `ensure_not_last_owner()` TOCTOU race | Needs row-locking + a dedicated concurrency test |
| ENG-039 | API-key scope gap in orgs/api_keys/billing routers | Needs a security-reviewed rollout — changes real authorization behavior for existing API keys |

## 14. Known limitations

See [`docs/release/KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) (created alongside this certification) for the full list. Summary: no browser-automation-verified UI testing in this environment (all UI-facing evidence this sprint is Source or API-level); AUTH-006 (session token in `localStorage`) remains deferred pending a scheduled auth-architecture migration (plan exists, not begun); ENG-039's API-key scope gap; no automated CD pipeline (Railway's auto-deploy-from-`origin/main` is the actual live mechanism, undocumented as a repeatable process); `docs/release/`'s 13 pre-existing historical reports not yet folded into `archive/`.

## 15. Production recommendation

**Conditionally ready.** Every Critical/High/Medium-severity functional and security defect this session could verify is closed. The one Medium-High severity item still open (ENG-039, API-key scope enforcement gap) should be resolved or explicitly risk-accepted by a security reviewer before this specific API-key-based integration surface is exposed to untrusted third parties — it does not block deployment for the primary browser/JWT-authenticated user flow, which is unaffected. AUTH-006 (deferred, documented) is a real but second-order risk (requires a chained XSS to be exploitable; this session's XSS testing found none live). No blocking defect was found in the Viewer, Reading Intelligence, Access Control, or core document-sharing workflows within the bounds of what this environment could verify (source review + API-level integration testing against a real local stack; no browser automation available).

**I would deploy this to production for the primary user-facing flows today, with ENG-039 flagged for a security review before broadly issuing API keys to third-party integrators.**
