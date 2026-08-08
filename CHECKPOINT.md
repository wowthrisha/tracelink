# Checkpoint — V14.0 Owner Mode Sprint

Running state snapshot, updated after every closed backlog item. See `PROGRESS.md` for the narrative log and `ENGINEERING_BACKLOG.md` for full issue detail.

**Last updated**: 2026-08-08 (V23.0 — ENG-019 browser sweep completion + ENG-045 fix).

## V23.0 update — ENG-019 closed, ENG-045 opened and closed same sprint

The browser-automation blocker that kept ENG-019 partially open since V20.0 is resolved (Playwright+Chromium confirmed working via the host miniconda3 environment, against both the live Railway app and the local Docker stack). Completed the full remaining sweep — Access Control link toggles (create + edit, with a hard-reload persistence check), Organizations role/settings toggles (RBAC boundary source- and live-verified), and all remaining ~8 dashboard screens — genuinely Browser Verified. **ENG-019 closed.** The sweep surfaced one real, reproducible defect (the "Feedback" sidebar shortcut silently landed on the wrong tab after picking a document) — root-caused, fixed with a 3-line diff, and regression-verified (backend 1751/1/0 unchanged, frontend 13/13, isolated diff, browser-verified both the fixed and unaffected code paths on the local Docker stack). **Filed and closed same-sprint as ENG-045.** Full detail in `ENGINEERING_BACKLOG.md` and `PROGRESS.md`'s V23.0 section.

Net effect: **45 items total, 29 closed** (27 from V22.0 + ENG-019 + ENG-045). The 5 still-open items are unchanged from V22.0 and remain correctly not engineering-actionable this session — see the V22.0 summary immediately below, which still applies to all of them.

## Burndown (44 items, all triaged as of V22.0 — see PROGRESS.md; V23.0 closed ENG-019 and opened+closed ENG-045, see above)

| Priority | Total | Closed | Deferred (reasoned) | Open (blocked on external input / low-risk) |
|---|---|---|---|---|
| Critical | 0 | 0 | 0 | 0 |
| High | 4 | 3 | 0 | 1 |
| Medium | 12 | 7 | 4 | 1 |
| Low | 20 | 12 | 6 | 2 |
| Enhancement | 8 | 5 | 2 | 1 |
| **Total** | **44** | **27** | **12** | **5** |

Overall completion: **61.4%** (27/44) as of V22.0; **29/45 (64.4%)** as of V23.0. **Every Critical/High/Medium/Low item is closed, deferred, or classified as a decision item with fresh, on-record reasoning.** The 5 remaining open items are each blocked on a named external input or an evidence-based low-risk classification, not unilaterally engineering-actionable: ENG-033 (new profile screen — product/design direction, decision record in `docs/governance/ENG-033_DECISION.md`), ENG-034 (CD/deploy job — deployment-target decision, decision record in `docs/governance/ENG-034_DECISION.md`), ENG-044 (Celery worker metrics invisible cross-process — ops/infra multiprocess-registry decision, found this sprint), ~~ENG-019 (remainder of the dashboard toggle sweep — browser-automation tooling or manual QA)~~ **closed V23.0**, and ENG-038 (TOCTOU race, reclassified low-risk-inference after 2 clean live reproduction attempts found no race). ENG-039/017/040/037 were all closed in V22.0 (see below); AUTH-006 remains a documented, unimplemented architectural risk (severity revised Medium-High→Medium after a new CSP mitigation finding).

## V22.0 Residual Risk Closure — complete

Closed the entire canonical remaining-items list from the V22.0 mandate. **ENG-039**: root-caused and fixed a real API-key zero-scope-means-unlimited-access defect across `orgs.py`/`api_keys.py`/`billing.py` (21 routes, 6 new scopes, scope-escalation guard, 28 new regression tests proven via stash-revert). Extending the same matrix found 3 more instances — **ENG-041/042/043** — fixed identically; 7 other routers confirmed already correct. **ENG-017**: re-classified observability with full evidence (most already correct), fixed one real gap (Celery worker metrics), found and filed one new gap (**ENG-044**, cross-process registry visibility, ops/infra-blocked). **ENG-040**: verification-only Viewer-toggle sweep, 7/8 already correct, 8th already fixed pre-sweep. **ENG-037**: investigated a code merge, deliberately didn't do it (would add complexity for a theoretical risk), added a 6-test tripwire instead. **ENG-038**: genuine concurrent-request reproduction attempts against the real stack found no race — reclassified from assumed-exploitable to low-risk inference, no fix applied without evidence. **ENG-033/034**: full decision records written (`docs/governance/`), both left open pending product/ops input. **AUTH-006**: re-evaluated with a new CSP-mitigation finding, severity revised down, migration plan preserved unimplemented pending an approved decision. Final regression: backend 1751 passed/1 skipped/0 failed (host-run), frontend 13/13, migration head 027 confirmed live, live API smoke + full link-lifecycle check against the real Docker stack. Final certification: `docs/release/V22_RESIDUAL_RISK_CERTIFICATION.md` — **RELEASE STATUS: READY WITH DOCUMENTED LIMITATIONS**.

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

V23.0's ENG-019 browser sweep + ENG-045 fix is **complete**. Every remaining open item (ENG-033, 034, 038, 044) is blocked on a named external input this session cannot unilaterally supply — product/design direction, an ops/deployment-policy decision, infra/multiprocess-registry access — or is an evidence-based low-risk classification (ENG-038). No further engineering-actionable backlog work remains pending. The fix (ENG-045) is committed locally on `main`, one commit ahead of `origin/main` per this repo's standing policy (never push without explicit confirmation — `origin/main` auto-deploys to the live Railway production instance the credentials in this session's task target). **The live Railway app has NOT yet received this fix** — it still runs the pre-fix behavior until a push+deploy happens; only the local Docker stack currently serves the corrected build.

## Environment note — browser automation now available (V23.0 correction)

Prior sprints' claim ("no browser-automation tool installed") only ever checked for Claude-Code-native browser tools (`claude-in-chrome`, which is not connected in this environment) and never checked the host's own Python environment. **A working Playwright+Chromium install exists in the host's miniconda3 environment** (`playwright==1.58.0`, confirmed via `python3 -c "import playwright"` and a real headless launch). V23.0 used it directly via Python scripts (not pytest-playwright) against both the live Railway app and the local Docker stack — this unblocks genuine Browser Verified evidence for future UI/workflow verification steps that previously had to be down-classified to Source or API Verified. ENG-030/ENG-031 (closed in earlier sprints as Source/API-verified only) remain correctly classified as-is — not retroactively reclassified, since re-verifying already-closed items isn't this sprint's mandate — but any *future* sprint citing "no browser tool available" should check for this first.

## Disposable/dev environment state

- `frontend/package-lock.json` now correctly reconciles **both** macOS/arm64 and Linux/Alpine optional platform dependencies (verified via isolated `npm ci` checks on each) — fixed twice this sprint (ENG-013, then again ENG-014 after adding `jscpd`). Both platforms confirmed working independently before each commit.

## Disposable test accounts created this sprint (local stack only)

- `eng003.idor.test2@mailinator.com` — Account B for ENG-003's IDOR test. Confirmed, logged in, holds zero real resources. Local database only, does not exist in production.
