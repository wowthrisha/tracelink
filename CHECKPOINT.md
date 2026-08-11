# Checkpoint — V14.0 Owner Mode Sprint

Running state snapshot, updated after every closed backlog item. See `PROGRESS.md` for the narrative log and `ENGINEERING_BACKLOG.md` for full issue detail.

**Last updated**: 2026-08-11 (V23.0 live browser-reported backlog — BUG-001 through BUG-008 + OBS-001 resolved; see below).

## V23.0 live browser-reported backlog — resolved (2026-08-11)

A separate, freshly-filed backlog (BUG-001..008, OBS-001 — distinct from this file's ENG-XXX numbering) reported live from actual product usage. Full detail in the new **`BUG_REMEDIATION_REPORT.md`** and **`PRODUCTION_REGRESSION_CERTIFICATION.md`** at repo root — not duplicated here, only the pointer and what a resuming session needs:

- **7 of 9 fixed and committed** (`7c5e7eb`..`b71185d`, 9 commits, local `main` only — **not pushed to `origin/main`**). One (BUG-001, TOC/Search navigation) investigated exhaustively — source review, live API reproduction, and live browser click-through all succeeded correctly — and could not be reproduced; classified UNCONFIRMED/NOT REPRODUCIBLE, no code changed. One (OBS-001, sign-in flash) was explicitly filed as *unconfirmed* but was actually reproduced live (network log showed 3 authenticated API calls firing and 401ing after the shell had already mounted, from a stale localStorage token) and fixed.
- **BUG-004 is the one worth flagging to any resuming session**: a real security gap — document retention expiry was never enforced in the viewer access path, only via the once-daily cleanup job's eventual deletion. Now enforced immediately at `_get_cached_link_and_doc`, `LinkService.validate_link`, and `/gate`.
- **Environment note**: `claude-in-chrome` browser automation **was** connected and usable this session (contradicts the stale "not connected" note further down this file from an earlier sprint) — `get_page_text`/`find`/`javascript_tool`/`browser_batch` all worked reliably; `computer` screenshot/zoom actions were intermittently flaky (CDP timeouts) but not blocking. Public share-link viewer pages need no login at all and were used extensively for BUG-001/BUG-005 verification without ever touching credentials.
- **Still open**: BUG-006, BUG-007, BUG-008 (all Low severity, cosmetic/a11y) are fixed and unit-tested but need an owner-authenticated session (Access Control, Webhooks, Analytics screens) for live visual re-verification — the assistant does not enter credentials into login forms under any circumstances, so this needs the user to sign in themselves in the already-open browser tab. Exact next action: sign in, then re-open Access Control → Feedback → Export dropdown, Webhooks → New Webhook checkboxes, and Analytics → Overview help icons to confirm the fixes render correctly.
- **Not pushed to `origin/main`** — per this repo's standing policy, since that auto-deploys to live production Railway. Do not push without separate explicit confirmation.
- Regression baseline after this sprint: backend **1763 passed, 1 skipped, 0 failed**; frontend **56 passed, 0 failed** (10 files, +18 net new test files this sprint).

## V24.0 continuation, Phase 3: ENG-050 found and fixed (2026-08-09)

Live end-to-end Upload→Access Control walkthrough (a genuinely fresh document, not a memorized re-check) found every never-shared document mislabeled "Revoked" with a "NO ACTIVE LINKS" banner — a binary `activeLinks.length === 0` check in `AccessScreen.jsx` that couldn't distinguish "never shared" from "had a link, now revoked." Fixed with a proper 3-way state (`Unshared`/`Active`/`Revoked`), all 3 states live-verified in sequence on a real document. Full record: `ENGINEERING_BACKLOG.md` ENG-050, `docs/engineering/FIX_LOG.md`/`ACTION_LOG.md` Entry 47.

## V24.0 continuation: ENG-046 fully closed, ENG-049 found (2026-08-09)

Picked back up per explicit instruction not to assume ENG-048's closure meant the product was finished. Phase 1 reconciliation confirmed ENG-046 was the only genuinely OPEN AND FIXABLE item among the 5 remaining open ones (no external blocker, just previously deferred as large). Individually categorized and fixed all 206 remaining `backend/tests` lint violations (not blind `--fix`) — `ruff check backend/app backend/tests`, the literal CI command, now passes cleanly. While reviewing them, found 2 tests that assert less than their own docstrings promise (a computed-but-never-checked rate-limit flag, a captured-but-never-asserted mock) — filed as **ENG-049** rather than silently fixing test behavior outside this task's lint-cleanup scope. Full record: `ENGINEERING_BACKLOG.md` ENG-046/ENG-049, `docs/engineering/FIX_LOG.md`/`ACTION_LOG.md` Entry 46.

## V24.0 reconciliation (2026-08-08)

Per V24.0's Step 1 mandate, cross-checked every open/closed claim in this file against `ENGINEERING_BACKLOG.md`'s own per-item detail entries (the canonical source) rather than trusting prior summaries. Found and fixed one real, pre-existing contradiction that had survived V22.0 and V23.0 unnoticed: **ENG-037's detail entry has said "Closed" since 2026-08-05 (V22.0)**, but its backlog summary-table row and every rollup table in this file and `PROGRESS.md` kept labeling it "Open" — `PROGRESS.md` even had a footnote explicitly acknowledging the mismatch as deliberate ("its backlog status label reads 'Open'... to reflect the tripwire's intentionally-permanent nature") rather than resolving it. V24.0 resolves it unambiguously: the canonical detail status (Closed) wins, and every summary table now says so.

This file's older dual-layer table (a stale 44-item V22.0 table left sitting next to a V23.0 prose correction, itself the kind of contradiction this reconciliation pass exists to catch) is replaced below with one single, arithmetically-verified table.

## V24.0 follow-up: ENG-048 closed (2026-08-09)

ENG-048 (Reading Intelligence's active-time counter resetting instead of pausing on window blur, found earlier this same sprint) is **now closed**. Root cause proven via runtime instrumentation (not guessed): a `useEffect` dependency-array race in `useReadingAnalytics.js` — the "handle page changes" effect guarded on a non-reactive ref read and never re-fired once the session actually became ready, so `currentPage` stayed `null` for the entire session and `_accumulate()` permanently no-opped (which also meant nothing was ever flushed to the backend for a session that never left page 1 — a finding beyond what was known when this was filed). Fixed with a 3-line change, 2 new regression tests added (proven to fail pre-fix via `git stash`), and 9 of 10 mandated browser tests directly passing against the local Docker stack (the 10th indeterminate due to a documented headless-automation limitation, not an app defect). Full record: `ENGINEERING_BACKLOG.md` ENG-048, `docs/engineering/FIX_LOG.md`/`ACTION_LOG.md` Entry 45, `REGRESSION_REPORT.md`.

## Burndown (50 items, fully reconciled V24.0 continuation, post-ENG-050 — see `ENGINEERING_BACKLOG.md`'s "Reconciled totals" note for the item-by-item recount)

| Priority | Total | Closed | Deferred (reasoned) | Reviewed/Justified | Open (blocked on external input / low-risk) |
|---|---|---|---|---|---|
| Critical | 0 | 0 | 0 | 0 | 0 |
| High | 5 | 4 | 0 | 0 | 1 |
| Medium | 15 | 11 | 3 | 0 | 1 |
| Low | 21 | 12 | 3 | 3 | 3 |
| Enhancement | 8 | 6 | 1 | 1 | 0 |
| Verification-only (no severity) | 1 | 1 | 0 | 0 | 0 |
| **Total** | **50** | **34** | **7** | **4** | **5** |

`34 + 7 + 4 + 5 = 50`. Overall completion: **68.0%** (34/50 closed). **Zero unresolved High or Critical defects, zero partially-fixed items.** The 5 remaining open items: **ENG-033** (new profile screen — product/design direction, decision record in `docs/governance/ENG-033_DECISION.md`), **ENG-034** (CD/deploy job — deployment-target decision, decision record in `docs/governance/ENG-034_DECISION.md`), **ENG-038** (TOCTOU race, reclassified low-risk-inference after 2 clean live reproduction attempts found no race), **ENG-044** (Celery worker metrics invisible cross-process — ops/infra multiprocess-registry decision), **ENG-049** (2 tests assert less than their own docstrings promise — found while closing ENG-046, correctly scoped out as a separate low-priority test-quality item). ENG-019/045 (V23.0), ENG-037/039/017/040 (V22.0), ENG-046/047/048/050 (V24.0) are all closed; AUTH-006 (tracked as ENG-026) remains a documented, unimplemented architectural risk (severity revised Medium-High→Medium after a new CSP mitigation finding) — a deferred item, not an open one, since a full migration plan already exists and is simply pending an approval decision rather than lacking a plan.

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

**ENG-046 is now fully closed (2026-08-09) — zero partially-fixed items remain anywhere in the backlog.** The `backend/tests` remainder (206 lint violations) was individually categorized and fixed; the literal CI command (`ruff check backend/app backend/tests`) now passes cleanly.

Continuing the V24.0 mandate's remaining phases: Phase 3 (full end-to-end workflow regression via live browser), Phase 4 (Reading Intelligence deep re-verification now that ENG-048 is fixed), Phase 5 (UI/endpoint contract spot-check), Phase 6 (bounded security re-verification), Phase 7/8 (code quality sweep + repository structure), then the 5 mandated final reports (`FINAL_ENGINEERING_STATUS.md`, `FINAL_REGRESSION_CERTIFICATION.md`, `FINAL_OPEN_RISKS.md`, `FINAL_REPOSITORY_HEALTH.md`, `FINAL_RELEASE_CERTIFICATION.md`).

The 5 remaining open items (ENG-033, 034, 038, 044, 049) are each blocked on a named external input or are a newly-filed, correctly-scoped-out low-priority test-quality finding — none are unilaterally engineering-actionable this session.

Commits are local on `main`, not pushed to `origin/main` per this repo's standing policy (`origin/main` auto-deploys to the live Railway production instance). **The live Railway app has NOT received any of V23.0's or V24.0's fixes** (ENG-045, ENG-046, ENG-048) — it still runs pre-V23.0 behavior until a push+deploy happens; only the local Docker stack currently serves the fully corrected build.

Commits this sprint (`main`, none pushed to `origin/main` per standing policy — `origin/main` auto-deploys to the live Railway production instance): `eedaf24` (Step 1 reconciliation), `c02ce76` (backfill FIX_LOG/ACTION_LOG), `28ca812`+`3088797` (ENG-046 fix+docs), `809095c` (ENG-048 filed), `7d82ff8` (Step 8/9), `94b35c1` (docs/release archival), `da9cb2e` (final certification). **The live Railway app has NOT received V23.0's ENG-045 fix or any V24.0 work** — it still runs pre-V23.0 behavior until a push+deploy happens; only the local Docker stack currently serves the corrected build.

## Environment note — browser automation now available (V23.0 correction)

Prior sprints' claim ("no browser-automation tool installed") only ever checked for Claude-Code-native browser tools (`claude-in-chrome`, which is not connected in this environment) and never checked the host's own Python environment. **A working Playwright+Chromium install exists in the host's miniconda3 environment** (`playwright==1.58.0`, confirmed via `python3 -c "import playwright"` and a real headless launch). V23.0 used it directly via Python scripts (not pytest-playwright) against both the live Railway app and the local Docker stack — this unblocks genuine Browser Verified evidence for future UI/workflow verification steps that previously had to be down-classified to Source or API Verified. ENG-030/ENG-031 (closed in earlier sprints as Source/API-verified only) remain correctly classified as-is — not retroactively reclassified, since re-verifying already-closed items isn't this sprint's mandate — but any *future* sprint citing "no browser tool available" should check for this first.

## Disposable/dev environment state

- `frontend/package-lock.json` now correctly reconciles **both** macOS/arm64 and Linux/Alpine optional platform dependencies (verified via isolated `npm ci` checks on each) — fixed twice this sprint (ENG-013, then again ENG-014 after adding `jscpd`). Both platforms confirmed working independently before each commit.

## Disposable test accounts created this sprint (local stack only)

- `eng003.idor.test2@mailinator.com` — Account B for ENG-003's IDOR test. Confirmed, logged in, holds zero real resources. Local database only, does not exist in production.
