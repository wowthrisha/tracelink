# Checkpoint — V14.0 Owner Mode Sprint

Running state snapshot, updated after every closed backlog item. See `PROGRESS.md` for the narrative log and `ENGINEERING_BACKLOG.md` for full issue detail.

**Last updated**: 2026-07-31 17:00, after the V18.0 Repository Certification sprint.

## Burndown (backlog expanded 31 → 34 items in V18.0 — see PROGRESS.md)

| Priority | Total | Closed | Deferred (reasoned) | Open |
|---|---|---|---|---|
| Critical | 0 | 0 | 0 | 0 |
| High | 4 | 3 | 0 | 1 |
| Medium | 8 | 3 | 3 | 2 |
| Low | 14 | 8 | 6 | 0 |
| Enhancement | 8 | 2 | 2 | 4 |
| **Total** | **34** | **16** | **11** | **7** |

Overall completion: **47.1%** (16/34). High/Medium/Low tiers were fully closed out as of V17.0; V18.0's documentation-cleanup pass then surfaced 3 genuine new items (ENG-032/033/034) that had fallen out of prior backlog reconciliation — not yet triaged. Per V17.0's explicit gate, the complete repository certification pass ran this sprint (see below) before any Enhancement work begins.

## V18.0 Repository Certification — complete

Full "Zero Technical Debt" sweep across backend/, frontend/, tests/, scripts/, docs/, docker/, .github/. 6 deliverables produced (`REPOSITORY_CERTIFICATION.md`, `DEAD_CODE_REPORT.md`, `DEPENDENCY_AUDIT.md`, `MODULE_BOUNDARY_REPORT.md`, `DOCUMENTATION_CLEANUP_PLAN.md`, `FINAL_REPOSITORY_SCORECARD.md`). 4 code commits (all backend/frontend suites re-verified green after each) + 1 documentation-archival commit (48 files, root `.md` count 55→14). Verdict: 8/10 stop conditions fully Met, remaining 8 Substantially met, 0 Not Met. Everything found-but-not-fixed is documented with file:line evidence, effort estimate, and regression risk — nothing silently dropped. Full verdict in `FINAL_REPOSITORY_SCORECARD.md`.

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

Repository certification is **complete** (this sprint, V18.0). Next: triage the 3 new items it surfaced (ENG-032 salt defaults, ENG-033 no profile screen, ENG-034 no CD job) through the same STEP 1/2/3 process used for the rest of the backlog — each is already re-verified reproducible, but not yet judged for implementation. Also still due: an "every 5 closed issues" full browser regression sweep (Upload/Viewer/Reading Intelligence/Analytics/Access Control/Organizations/Notifications/Audit Log/API Keys/Webhooks/Storage/Billing/Share Links) per V17.0's cadence rule — not yet run this cycle (last full regression was the post-ENG-024 partial spot-check; V18.0's changes were verified via lint/test/build/isolated-diff, not a full manual UI sweep, since no browser-automation tool is available in this environment). Only after that gate does Enhancement-tier work (ENG-017/018/019/020) begin, per the FINAL ENGINEERING GATE.

## Environment note — browser automation unavailable this session

No Playwright/chromium-cli or other browser-automation tool is installed in this environment (checked via `ToolSearch` and `which`). ENG-030 and ENG-031 were verified via source trace + isolated diff + lint/test/build, and for ENG-031 additionally via direct integration testing against the real `/api/viewer/validate` endpoint on the local Docker stack with a genuine Supabase-authenticated session (confirmed the `watermark_text` field changes exactly as the fix intends). Neither is claimed as "Browser-verified" — classified honestly per the Evidence Policy as Source-verified (+ Integration/API-verified for ENG-031). If a full visual browser regression sweep is required to satisfy V17.0's "every 5 closed issues" rule, that step needs either a browser-automation tool made available or manual/user-driven verification.

## Disposable/dev environment state

- `frontend/package-lock.json` now correctly reconciles **both** macOS/arm64 and Linux/Alpine optional platform dependencies (verified via isolated `npm ci` checks on each) — fixed twice this sprint (ENG-013, then again ENG-014 after adding `jscpd`). Both platforms confirmed working independently before each commit.

## Disposable test accounts created this sprint (local stack only)

- `eng003.idor.test2@mailinator.com` — Account B for ENG-003's IDOR test. Confirmed, logged in, holds zero real resources. Local database only, does not exist in production.
