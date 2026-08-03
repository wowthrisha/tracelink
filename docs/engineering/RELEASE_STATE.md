# Release State — V21.0 Production Release Closure

Live control file for this sprint. Overwritten on each meaningful update — history lives in `ACTION_LOG.md`/`FIX_LOG.md`/`PROGRESS.md`. Read this first to resume.

**Last updated**: 2026-08-02, mid-sprint (repository-consolidation commits done; product/security/repo-cleanup phases in progress).

| Field | Value |
|---|---|
| Current phase | Phase 4-9: Product correctness / UI-API contract / Reading Intelligence / Security / Scalability / Code Quality passes |
| Last completed phase | Phase 1-2: state recovery + committing 62 files (~1000 lines) of previously-verified, never-committed work from earlier sprints — working tree now fully clean |
| Current issue | None in progress |
| Last completed issue | Committed the full pre-existing uncommitted body of work in 8 grouped commits (governance fixes, JWKS resilience, annotation/reading consolidation, Viewer UI, dashboard screens, docs, QA evidence, bundle rebuild) |
| Open issues | ENG-017 (observability wiring — needs infra access), ENG-019 (dashboard toggle sweep — 2/N verified, needs browser tooling for the rest), ENG-033 (profile screen — needs product/design input), ENG-034 (CD pipeline — needs deployment-target decision) |
| Blocked issues | Same 4 as above — each has a named, non-engineering blocker, not stalled |
| Tests status | Backend 1705 passed / 1 skipped / 0 failed. Frontend 13/13 passed. Both re-confirmed after the commit batch. |
| Build status | PASS — `npm run build` succeeds, 309.0kb, bundle rebuilt fresh and committed to match source |
| Migration status | PASS — `alembic upgrade head` clean against the local Docker DB, single linear chain through revision 027, already at head |
| Browser status | No browser-automation tool available in this environment (Playwright/chromium-cli absent, checked repeatedly across V18/V20/V21). All UI-facing verification this sprint is Integration/API-verified against the real local Docker stack or Source-verified — never mislabeled as Browser Verified. |
| Current commit | `8ccf594` |
| Uncommitted changes | None — `git status` clean |
| Release blockers | None Critical/High/Medium/Low remain open — the 4 open backlog items are Enhancement/High-needing-product-input tier, documented, not release-blocking per this session's established stop-condition criteria |
| Overall verified completion | Backlog: 19/34 closed, 11 deferred-with-reasoning, 4 blocked-on-external-input (see `ENGINEERING_BACKLOG.md`). Repository: working tree fully committed and clean for the first time this session. |

## What changed in this phase (state recovery)

`git status` at the start of this sprint showed 62 modified/new files with zero uncommitted-change history — leftover implemented-but-never-committed work from sprints predating this session's mega-prompt-driven atomic-commit discipline (roughly V6.0 through the JWKS-outage incident and V10.0-era Viewer/Reading-Intelligence work). Before committing any of it: ran the full backend suite (1705 passed), frontend suite (13/13), lint, and build against the complete as-found working tree to confirm it was internally coherent as a whole, not half-finished. Spot-checked ~15 of the 62 files' diffs against `docs/engineering/FIX_LOG.md`'s historical sprint sections (which already documented most of this work's root cause and verification when it was originally done) and against a live database check confirming migration 027 was already applied (`alembic_version=027` in the running Postgres instance) — no discrepancies found. Committed in 8 logically-grouped commits rather than one bulk commit, each with a commit message describing what the change is and pointing to its historical documentation, and explicitly labeled as "previously verified, now committed" rather than implying it was written fresh this turn.

## Next steps

1. Product-correctness / UI-API-contract / Reading-Intelligence / Security / Scalability / Code-quality passes (Phases 4-9) — confirm no NEW actionable defect exists on top of this now-fully-committed baseline, leaning on the extensive verification already on record in `ENGINEERING_BACKLOG.md`/`docs/engineering/FIX_LOG.md` rather than re-deriving it from zero.
2. Repository cleanup + documentation consolidation (Phases 10-13) — root is already down to 16 `.md` files (from 55, via V18.0's archival); assess whether further consolidation into a `docs/` hierarchy is warranted, and correct README.md's remaining accuracy per a fresh read.
3. Full regression re-run after any structural moves (Phase 14).
4. ONE consolidated `docs/release/FINAL_RELEASE_CERTIFICATION.md` (Phase 18), superseding the scattered `FINAL_*`/certification docs still at root.
