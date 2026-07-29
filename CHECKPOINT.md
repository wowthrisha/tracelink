# Checkpoint — V14.0 Owner Mode Sprint

Running state snapshot, updated after every closed backlog item. See `PROGRESS.md` for the narrative log and `ENGINEERING_BACKLOG.md` for full issue detail.

**Last updated**: 2026-07-29 13:00, after ENG-014.

## Burndown (backlog expanded 21 → 31 items in V16.0 — see PROGRESS.md)

| Priority | Total | Closed | Deferred (reasoned) | Open |
|---|---|---|---|---|
| Critical | 0 | 0 | 0 | 0 |
| High | 3 | 3 | 0 | 0 |
| Medium | 6 | 3 | 3 | 0 |
| Low | 14 | 5 | 3 | 6 |
| Enhancement | 8 | 2 | 2 | 4 |
| **Total** | **31** | **13** | **8** | **10** |

Overall completion: **41.9%** (13/31). **High and Medium tiers: 0 open items.** Every "Not enough evidence" security gap from the original review is live-confirmed. 10 open items remain, all Low/Enhancement severity (cosmetic consistency, tooling audits, deferred product/design decisions) — none blocking per the mission's stop conditions.

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

ENG-018 (large-PDF stress retest) — needs a genuinely large (100+ page) PDF, browser-verify rendering/search/nav/Reading-Intelligence metrics all hold at scale. Also queued: ENG-019 (dashboard modal re-exercise), ENG-020 (Reading Intelligence hand-verification), ENG-017 (observability wiring — likely ops-only, may end up "Not enough evidence" if infra access isn't available), and 6 Low-severity cosmetic items (ENG-024/025/027/028/030/031, of which ENG-028 needs design input). All remaining items are non-blocking per the mission's stop conditions (every Critical/High/Medium closed or deferred, every workflow verified) — proceeding through them for full repository-quality completeness rather than stopping early.

## Disposable/dev environment state

- `frontend/package-lock.json` now correctly reconciles **both** macOS/arm64 and Linux/Alpine optional platform dependencies (verified via isolated `npm ci` checks on each) — fixed twice this sprint (ENG-013, then again ENG-014 after adding `jscpd`). Both platforms confirmed working independently before each commit.

## Disposable test accounts created this sprint (local stack only)

- `eng003.idor.test2@mailinator.com` — Account B for ENG-003's IDOR test. Confirmed, logged in, holds zero real resources. Local database only, does not exist in production.
