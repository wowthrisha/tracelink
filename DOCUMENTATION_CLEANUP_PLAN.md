# Documentation Cleanup Plan — V18.0 Repository Certification

Most of this plan has already been **executed** this sprint (commit `4862abb`), not just proposed — see `docs/governance/ARCHIVED_FILES.md`'s "Sprint V18.0" section for the full per-file table. This document records the reasoning, the still-open follow-ups, and the parts intentionally left for a future decision.

## What was found

The repository root had accumulated 41 report-style `.md` files spanning sprints from 2026-07-14 through 2026-07-30, plus 9 more inside `docs/engineering/` (a second, never-cleaned-up set of session-scratch files from the V10.0 era, confusingly shadowing the currently-active `CHECKPOINT.md`/`PROGRESS.md` by using the identical filenames). This is not a new problem: `ENGINEERING_GOVERNANCE.md` (Sprint V6.0) and `FINAL_ENGINEERING_REVIEW.md` (Sprint V7.0) each independently rediscovered and flagged this exact same accumulation, and Sprint 6.3 (2026-06-30) executed this exact cleanup once already — archiving 64 files with an explicit recommendation that future sprints repeat it as reports accumulate. That recommendation was not followed for the following 41 days of sprint activity.

**Notable discovery while executing**: the vast majority (39 of 41 root files) were never `git add`-ed in the first place — they existed only as untracked scratch output in the working tree the entire time, confirmed via `git status --porcelain`/`git ls-files` before moving any of them. This means the repository's `git status` output has been cluttered with ~40 untracked files for over a month of sprints, independent of the archival question — every session had to visually filter past them.

## What was executed this sprint

- **48 files** moved to `archive/sprint7-18/root-reports/` and `archive/sprint7-18/docs-engineering-v10-scratch/`, following the exact directory-naming convention already established by `archive/sprint5-6/`. Tracked files moved with `git mv` (history preserved); untracked files moved and committed for the first time at their archive path (nothing was ever silently deleted — see the Evidence Policy note below).
- **Before archiving, 3 genuine content gaps were extracted and preserved**, not lost in the shuffle:
  - `FIX_LOG.md` (root)'s unique V4.0/Sprint-7.0/V6.0 fix history — never previously folded into the canonical `docs/engineering/FIX_LOG.md`, which jumped straight from "Sprint C" to "Sprint V10.0" — was merged in verbatim, in chronological order, before the root copy was archived.
  - `TECH_DEBT_REGISTER.md`'s P0 finding (hardcoded `ip_hash_salt`/`domain_verify_salt` defaults with no production-startup guard) was re-surfaced as `ENGINEERING_BACKLOG.md` **ENG-032**.
  - `PRODUCT_PROPOSAL.md`'s PROF-001 (no profile/account-settings screen exists) was re-surfaced as **ENG-033**.
  - `PUBLIC_RELEASE_READINESS.md`'s "CI has no CD/deploy job" finding was re-surfaced as **ENG-034**.
- **`archive/README.md` corrected**: it referenced `frontend/docs/` (deleted in Sprint V6.0 — confirmed via the now-merged `FIX_LOG.md` history, "a 3-level-deep tree with zero files at any level") and `RISK_REGISTER.md`/`ARCHITECTURE_DECISIONS.md` at root (both themselves archived in Sprint 6.3) as if they were still live. Corrected to point at the real current locations (`docs/`, `SECURITY.md`) and added the two missing directory rows (`sprint5-6/`, `sprint7-18/`) that existed on disk but were never documented.
- **`docs/governance/ARCHIVED_FILES.md` and `CLEANUP_LOG.md`** updated with new dated sections, appended (never overwriting Sprint 6.3's original entries), matching the existing convention exactly.

## What was kept at root, deliberately

| File | Why |
|---|---|
| `SECURITY_HARDENING_PLAN.md` | Actively cited by `ENGINEERING_BACKLOG.md` ENG-026 as the live migration plan for a currently-open item (AUTH-006, session token in `localStorage`). Archiving a plan for work that isn't done yet would orphan the plan from the ticket that needs it. |
| `REPOSITORY_CERTIFICATION.md`, `DEAD_CODE_REPORT.md`, `DEPENDENCY_AUDIT.md`, `MODULE_BOUNDARY_REPORT.md`, `DOCUMENTATION_CLEANUP_PLAN.md` (this file), `FINAL_REPOSITORY_SCORECARD.md` | This sprint's own live deliverables. |
| `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `LICENSE` | Perennial repo-standard files, never in scope for archival. |
| `ENGINEERING_BACKLOG.md`, `PROGRESS.md`, `CHECKPOINT.md`, `REGRESSION_REPORT.md` | This session's actively-maintained canonical tracking docs. |

## Still open — not resolved this sprint, flagged rather than dropped

| Item | Evidence | Recommendation | Owner needed |
|---|---|---|---|
| Version-numbering signals: `frontend/package.json` says `1.0.0`, the git tag is `v1.0.0-beta`, and the live `/health` endpoint self-reports `"version":"8.1.0"` (confirmed live against the local Docker stack this sprint) | Source + runtime verified | Three-way disagreement, not the four-way one `PUBLIC_RELEASE_READINESS.md` originally found (that report's fourth signal, a cert doc claiming `v3.2.2`, lived in `docs/release/` — out of this sprint's root-only archival scope, and wasn't independently re-checked). Pick one source of truth and propagate it everywhere else. | Whoever owns the release-versioning decision — not a unilateral pick for an engineering certification pass |
| `docs/release/`'s 14 files were flagged by the doc audit as one-time "RC-1" point-in-time reports rather than a repeatable release process doc, and weren't in this sprint's root-only scope to inspect further | Insufficient evidence — not independently re-read this sprint, relying on a prior report's characterization | A `docs/` (non-root) documentation audit is a reasonable next-sprint scope, following the same evidence-classification discipline as this one | — |
| `docs/engineering/REMAINING_DECISIONS.md` — currently has pre-existing uncommitted modifications sitting in the working tree, not examined this sprint (out of scope: this sprint audited root + `docs/engineering/`'s untracked stragglers, not every file with pending edits) | Not examined | Flag for whoever owns that in-progress diff to confirm it's still accurate before the next documentation pass | Whoever authored the pending edit |

## Evidence policy applied throughout

Every archived file was checked for one of: (a) explicit supersession stated by a newer canonical doc (`ENGINEERING_BACKLOG.md`'s own header names its 6 direct merge sources), (b) content demonstrably funneled forward into `docs/engineering/ISSUE_DATABASE.md` per that file's own "Consolidated from..." statement, (c) a closed, resolved incident/session with its findings independently confirmed fixed elsewhere (the JWKS-outage trio; the two live-QA "WORKFLOW_*" clusters, whose bugs — WATERMARK-001, READ-OWNER-001 — are confirmed closed in the now-merged `FIX_LOG.md`), or (d) a point-in-time sprint scorecard whose function is now served continuously by `CHECKPOINT.md`/`PROGRESS.md`. Nothing was archived on the basis of "looks old" alone — every row in `docs/governance/ARCHIVED_FILES.md`'s Sprint V18.0 table cites its specific reason. Consistent with this repo's standing policy, nothing was deleted — every file remains fully readable at its new archive path with full git history where it was previously tracked.
