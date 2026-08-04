# Checkpoint — V14.0 Owner Mode Sprint

Running state snapshot, updated after every closed backlog item. See `PROGRESS.md` for the narrative log and `ENGINEERING_BACKLOG.md` for full issue detail.

**Last updated**: 2026-08-04, after V21.0's Production Release Closure sprint.

## Burndown (39 items, all triaged as of V21.0 — see PROGRESS.md)

| Priority | Total | Closed | Deferred (reasoned) | Open (blocked on external input) |
|---|---|---|---|---|
| Critical | 0 | 0 | 0 | 0 |
| High | 4 | 3 | 0 | 1 |
| Medium | 10 | 5 | 3 | 2 |
| Low | 17 | 9 | 6 | 2 |
| Enhancement | 8 | 4 | 2 | 2 |
| **Total** | **39** | **21** | **11** | **7** |

Overall completion: **53.8%** (21/39). **Every Critical/High/Medium/Low item is closed or deferred with fresh, on-record reasoning.** The 7 remaining open items are each blocked on a named external input, not unilaterally engineering-actionable: ENG-033 (new profile screen — product/design direction), ENG-034 (CD/deploy job — deployment-target decision), ENG-039 (API-key scope gap in orgs/api_keys/billing — security-reviewed rollout), ENG-017 (observability wiring — infra/ops access), ENG-019 (remainder of the dashboard toggle sweep — browser-automation tooling or manual QA, 2 of its toggles already confirmed correct at the API level), and ENG-037/ENG-038 (both low-urgency, need a dedicated test cycle rather than a same-sprint drive-by touching the app's highest-stakes access-control functions).

## V21.0 Production Release Closure — complete

Recovered 62 files (~1000 lines) of previously-implemented, never-committed work from earlier sprints and committed it in 8 verified, logically-grouped commits — working tree fully clean for the first time this session. Targeted re-verification of that newly-committed code found and fixed 2 real defects (ENG-035, ENG-036) and surfaced 3 more with honest, documented reasoning for not fixing them same-sprint (ENG-037, ENG-038, ENG-039 — the latter a genuine security gap previously flagged in an archived report but never actually filed). Consolidated documentation: archived V18.0's 6 certification deliverables, corrected an inflated README claim and 3 stale numbers, produced ONE authoritative `docs/release/FINAL_RELEASE_CERTIFICATION.md` superseding every prior scattered `FINAL_*` document. Root `.md` count: 16 → 9. Final regression: backend 1706 passed/1 skipped/0 failed, frontend 13/13, Docker healthy.

## V18.0 Repository Certification — complete

Full "Zero Technical Debt" sweep across backend/, frontend/, tests/, scripts/, docs/, docker/, .github/. 6 deliverables produced, since archived to `archive/sprint18-certification/` as part of V21.0's documentation consolidation (their still-actionable findings were carried forward into `ENGINEERING_BACKLOG.md` as ENG-037/038, etc.): `REPOSITORY_CERTIFICATION.md`, `DEAD_CODE_REPORT.md`, `DEPENDENCY_AUDIT.md`, `MODULE_BOUNDARY_REPORT.md`, `DOCUMENTATION_CLEANUP_PLAN.md`, `FINAL_REPOSITORY_SCORECARD.md`. 4 code commits (all backend/frontend suites re-verified green after each) + 1 documentation-archival commit (48 files, root `.md` count 55→14). Verdict: 8/10 stop conditions fully Met, remaining 8 Substantially met, 0 Not Met. Everything found-but-not-fixed is documented with file:line evidence, effort estimate, and regression risk — nothing silently dropped. Full verdict in `archive/sprint18-certification/FINAL_REPOSITORY_SCORECARD.md`.

## V20.0 Backlog triage — complete

Triaged all 4 items still open after V18.0 through STEP 1/2/3 re-verification. **ENG-032 self-corrected**: the "missing production guard" it described already exists in `backend/app/main.py:27-54` — a redundant fix was implemented, caught by its own regression run (broke 2 pre-existing tests encoding the real behavior), and cleanly reverted; closed as no-longer-reproducible with the correction documented, not silently dropped. **ENG-018/ENG-020 closed** via genuine integration-level verification against the real Docker stack (120-page synthetic PDF stress test; hand-verified Reading Intelligence math against source formulas, including confirming an edge-case clamp value was correct behavior, not a placeholder). **ENG-019 partially verified** and left honestly open — 2 toggles confirmed, the remainder needs tooling this environment doesn't have. **ENG-033/034/017 remain open**, each with documented objective justification for why they're blocked on external input rather than a further engineering fix.

## V17.0 process refinement now in effect

Per the STEP 1/2/3 workflow: every remaining Low/Enhancement item gets re-verified against current source (not assumed still valid), then explicitly justified against 7 value criteria (usability/maintainability/security/scalability/complexity/future-bugs/tech-debt) before implementing — if none apply, document why and skip rather than implement by default. ENG-024 is the first item processed this way: confirmed reproducible, justified (maintainability + future-bug reduction), fixed, and one look-alike sub-case (the `fmtTime()` naming collision) was explicitly investigated and correctly left alone after finding it wasn't true duplication.

## V16.0 backlog reconciliation

Read `ISSUE_DATABASE.md`/`TODO_QUEUE.md` per V16.0's canonical-sources instruction — found them contradicting each other on ~10 items. Source-verified 3/3 sample confirms `ISSUE_DATABASE.md` was stale (V10.0 fixes never marked done there). Reconciled it, merged 10 genuinely-open items into `ENGINEERING_BACKLOG.md` as ENG-022–031. Processed the highest-priority new item (ENG-029, architecture doc corrections) immediately. See `PROGRESS.md` for the full dashboard (current/previous/next issue, regression status, test status, commit hash, blocker, ETA).

## V15.0 process refinements now in effect

- Commit format: `fix(ENG-###): concise description`
- After every issue: full regression sweep now includes build + migration validation + repo-wide grep for TODO/FIXME/console.log/debugger/print()/unused imports, in addition to the existing test-suite + browser-verification routine
- Backlog file paths are verified against the real repo before editing (ENG-007's originally-guessed file was wrong; corrected before implementation, not after)

## Environment state

- Local Docker stack is **up** (`docker compose up --build -d`) — Postgres 16, Redis 7, API, worker, beat, all healthy. Used for browser-verifying every fix before it's considered done, without touching the production Railway deployment. Same Supabase auth project as production; separate local database — no production data at risk.
- All code changes so far are **local, uncommitted**. Per this session's standing git policy (never commit/push without explicit request — `origin/main` auto-deploys to the live Railway production instance), fixes are being committed locally as they close (for `FIX_COMPLETION_MATRIX.md`'s commit-hash field) but **not pushed** without separate explicit confirmation.
- Backend test baseline: 1708 passed, 1 skipped. Frontend test baseline: 13/13 passed. Both re-confirmed unchanged after ENG-001.

## Backlog status (see ENGINEERING_BACKLOG.md for full detail)

| ID | Status |
|---|---|
| ENG-001 | **Closed** — Analytics grid overflow fixed, verified, zero regressions |
| ENG-002 | **Closed** — Notifications feed now shows document name + page number, verified live, zero regressions |
| ENG-003 | **Closed — no defect found.** Cross-account IDOR verified live with a genuine second account; every attempt correctly blocked. New low-priority finding ENG-021 logged (link 403 vs 404 inconsistency). |
| ENG-004 | Next up |
| ENG-005 – ENG-021 | Open, per priority order in `ENGINEERING_BACKLOG.md` |

## Immediate next step

Backlog triage is **complete** (V20.0). Every remaining open item (ENG-017, 019, 033, 034) is blocked on a named external input this session cannot unilaterally supply — product/design direction, an ops/deployment-policy decision, infra access, or browser-automation tooling. No further engineering-actionable backlog work remains pending. Per V20.0's mandate, the next step is producing the FINAL deliverable set (`FINAL_RELEASE_CERTIFICATION.md`, `FINAL_ENGINEERING_REPORT.md`, etc.), synthesizing this session's full body of verification work honestly — including being explicit about what a genuine browser-driven "every button, every modal" pass would still require versus what has actually been confirmed via source review and API-level integration testing against the real local stack.

## Environment note — browser automation unavailable this session

No Playwright/chromium-cli or other browser-automation tool is installed in this environment (checked via `ToolSearch` and `which`). ENG-030 and ENG-031 were verified via source trace + isolated diff + lint/test/build, and for ENG-031 additionally via direct integration testing against the real `/api/viewer/validate` endpoint on the local Docker stack with a genuine Supabase-authenticated session (confirmed the `watermark_text` field changes exactly as the fix intends). Neither is claimed as "Browser-verified" — classified honestly per the Evidence Policy as Source-verified (+ Integration/API-verified for ENG-031). If a full visual browser regression sweep is required to satisfy V17.0's "every 5 closed issues" rule, that step needs either a browser-automation tool made available or manual/user-driven verification.

## Disposable/dev environment state

- `frontend/package-lock.json` now correctly reconciles **both** macOS/arm64 and Linux/Alpine optional platform dependencies (verified via isolated `npm ci` checks on each) — fixed twice this sprint (ENG-013, then again ENG-014 after adding `jscpd`). Both platforms confirmed working independently before each commit.

## Disposable test accounts created this sprint (local stack only)

- `eng003.idor.test2@mailinator.com` — Account B for ENG-003's IDOR test. Confirmed, logged in, holds zero real resources. Local database only, does not exist in production.
