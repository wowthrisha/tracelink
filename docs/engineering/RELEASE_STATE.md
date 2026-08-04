# Release State — V21.0 Production Release Closure

Live control file for this sprint. Overwritten on each meaningful update — history lives in `ACTION_LOG.md`/`FIX_LOG.md`/`PROGRESS.md`. Read this first to resume.

**Last updated**: 2026-08-04 — sprint complete.

| Field | Value |
|---|---|
| Current phase | Complete — all 20 phases executed |
| Last completed phase | Phase 19: final repository tree review |
| Current issue | None in progress |
| Last completed issue | ENG-035/ENG-036 (Reading Insights UI toggle + self-inclusive average fix) |
| Open issues | ENG-017, ENG-019, ENG-033, ENG-034, ENG-037, ENG-038, ENG-039 — each blocked on a named external input, not stalled (see `ENGINEERING_BACKLOG.md`) |
| Blocked issues | Same 7 as above |
| Tests status | Backend 1706 passed / 1 skipped / 0 failed. Frontend 13/13 passed. Both re-confirmed after the sprint's final commit. |
| Build status | PASS — `npm run build` succeeds, 309.1kb |
| Migration status | PASS — `alembic upgrade head` clean against the local Docker DB, single linear chain through revision 027, already at head |
| Browser status | No browser-automation tool available in this environment (checked repeatedly across V18/V20/V21). All UI-facing verification this sprint is Integration/API-verified against the real local Docker stack or Source-verified — never mislabeled as Browser Verified. |
| Current commit | `d607216` |
| Uncommitted changes | None — `git status` clean |
| Release blockers | None Critical/High/Medium/Low remain open — all 7 open items are documented, blocked on named external inputs, not release-blocking |
| Overall verified completion | Backlog: 21/39 closed, 11 deferred/reviewed/justified, 7 blocked-on-external-input. Repository: fully committed, root reduced to 9 `.md` files, one consolidated `docs/release/FINAL_RELEASE_CERTIFICATION.md`. |

## Sprint summary

1. **State recovery**: committed 62 files (~1000 lines) of previously-implemented-but-never-committed work spanning multiple earlier sprints (Sprint V6.0 governance fixes, JWKS-outage resilience, V10.0-era Viewer/Reading-Intelligence work, dashboard-screen fixes, doc corrections, QA evidence) in 8 logically-grouped commits, after verifying the whole body coherent (full test suite passed against it as a unit before touching anything). Working tree went from 62-files-dirty to fully clean.
2. **Targeted re-verification** of the newly-committed Reading-Insights and authorization-consolidation code found and fixed 2 real defects (ENG-035: feature-complete backend with no UI toggle to reach it; ENG-036: a self-inclusive "average" query) and surfaced 3 more for the backlog with honest reasoning for not fixing them same-sprint (ENG-037, ENG-038, ENG-039).
3. **Documentation consolidation**: archived V18.0's 6 certification deliverables to `archive/sprint18-certification/`, relocated the still-live `SECURITY_HARDENING_PLAN.md` to `docs/security/`, corrected every cross-reference, corrected an inflated README claim (unbacked "Supabase SAML integration"), corrected 3 stale numbers, added a documentation index.
4. **One consolidated `docs/release/FINAL_RELEASE_CERTIFICATION.md`** produced, classifying every claim VERIFIED/INFERRED/NOT VERIFIED/BLOCKED, plus a companion `KNOWN_LIMITATIONS.md`.
5. Final regression re-run clean at every stage; Docker `api`+`migrate` rebuilt and healthy at the final commit.
