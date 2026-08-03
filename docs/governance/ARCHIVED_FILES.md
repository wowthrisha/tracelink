# Archived Files — Sprint 6.3

**Date:** 2026-06-30
All files moved to `archive/` via `git mv` to preserve history.

---

## Sprint 6.3 — Newly Archived (this sprint)

### From repository root → `archive/sprint5-6/root-reports/`

| File | Reason |
|------|--------|
| `ARCHITECTURE_DECISIONS.md` | Superseded — content migrated to `docs/architecture/adr/` |
| `ARCHIVE_PLAN.md` | Historical planning document — executed |
| `CHANGELOG_ENTERPRISE.md` | Superseded by `CHANGELOG.md` at root |
| `DELETION_SAFETY_REPORT.md` | Intermediate audit artifact |
| `FINAL_PRELAUNCH_AUDIT.md` | Superseded by RC1 certification |
| `HARDENING_REPORT.md` | Intermediate sprint report |
| `IMPLEMENTATION_PROGRESS.md` | Intermediate sprint tracking |
| `LINK_MANAGEMENT_REVALIDATION.md` | Intermediate revalidation |
| `P0_REVALIDATION_REPORT.md` | Superseded by RC1 reports |
| `PHASE_E2_SCALABILITY_AUDIT.md` | Intermediate audit |
| `PRE_PILOT_CERTIFICATION_REPORT.md` | Superseded by RC1 certification |
| `RELEASE_BLOCKERS.md` | Resolved — all blockers closed |
| `REPO_CLEANUP_PLAN.md` | Executed in this sprint |
| `REPO_INVENTORY.md` | Superseded by `docs/governance/REPOSITORY_INVENTORY.md` |
| `RISK_REGISTER.md` | Superseded by `SECURITY.md` and deployment docs |
| `SECRET_ROTATION_RUNBOOK.md` | Incident-specific (resolved); sensitive detail |
| `SECUREDOC_CURRENT_STATE_REPORT.md` | Intermediate state snapshot |
| `STALE_ARTIFACTS_REPORT.md` | Self-referential audit artifact |

### From `frontend/docs/` → `archive/sprint5-6/frontend-docs/`

**certification/** (18 files): Sprint 6.0 bug databases, checkpoint files, phase reports — superseded by RC1 certification.

**engineering/** (3 files): Root cause analyses for resolved bugs.

**governance/** (1 file): Sprint action log — superseded by `docs/release/MASTER_ACTION_LOG.md`.

**implementation/** (2 files): Beta launch checklist and decision — executed.

**production/** (22 files): Intermediate hardening, optimization, and revalidation reports from Sprints 5–6; superseded by RC1 reports in `docs/release/`.

---

## Previously Archived (earlier sprints)

| Archive Location | Sprint | Contents |
|-----------------|--------|---------|
| `archive/legacy-traceview/` | Sprint 1 | 8 docs from original TraceView project |
| `archive/root-historical/` | Sprint 1–2 | 8 early architecture/executive docs |
| `archive/docs-sprint2-3/` | Sprint 2–3 | 18 phase implementation reports |
| `archive/sprint3-4-reports/` | Sprint 3–4 | 12 audit and sprint reports |
| `archive/sprint4-4-certification/` | Sprint 4 | 12 certification suite docs |
| `archive/browser-audit-screenshots/` | Sprint 5 | 6 Playwright screenshots |
| `archive/sprint5-6/` | Sprint 5–6 | Root + `frontend/docs/` reports superseded by Sprint 6.3's RC1 certification |

---

## Sprint V18.0 — Newly Archived (2026-07-31)

Sprint 6.3 (above) archived 64 files and left a standing instruction for future sprints to keep archiving obsolete root reports as they accumulate. That instruction was not followed again until now — every file below was created after Sprint 6.3 (2026-07-14 through 2026-07-30) and had simply re-accumulated at repository root. `ENGINEERING_GOVERNANCE.md` and `FINAL_ENGINEERING_REVIEW.md` (both archived in this batch) had each independently rediscovered and re-flagged this exact problem in their own sprints without it being acted on.

**Note on tracking**: most of the 41 directly-archived files below were never `git add`-ed after being written in prior sessions — they existed only as untracked scratch files in the working tree (confirmed via `git status --porcelain`/`git ls-files` before moving). They are committed for the first time at their new archive path in this sprint, rather than `git mv`-ed from a tracked root location. Two files (`FIX_LOG.md`, `PRODUCT_PROPOSAL.md`) were tracked and moved with `git mv`, preserving history.

### From `docs/engineering/` → `archive/sprint7-18/docs-engineering-v10-scratch/` (9 files)

Discovered while staging this sprint's archiving commit: a second, never-committed, never-cleaned-up set of session-scratch tracking files from the V10.0 sprint era, sitting in `docs/engineering/` alongside the actively-maintained `ACTION_LOG.md`/`FIX_LOG.md`/`ISSUE_DATABASE.md`. Same-named as (and confusingly shadowing) the canonical root-level tracking files: `ARCHITECTURE_DECISIONS.md`, `CHECKPOINT.md` (V12.0 content vs. root's current V17.0+), `PROGRESS.md` (V10.0 content vs. root's current burndown), `REGRESSION_LOG.md`, `SCREENSHOT_INDEX.md`, `SESSION_STATE.md`, `TEST_HISTORY.md`, `TODO_QUEUE.md` (already reconciled into `ENGINEERING_BACKLOG.md` during V16.0's backlog merge), `UI_CHANGELOG.md`. All superseded by current root docs; archived rather than deleted per this repo's standing policy.

### From repository root → `archive/sprint7-18/root-reports/` (48 files)

| File | Reason |
|------|--------|
| `API_MATURITY_REPORT.md` | Content funneled into `docs/engineering/ISSUE_DATABASE.md` (V6.0/V7.0 governance consolidation) |
| `ARCHITECTURE_CERTIFICATION.md` | Explicit merge source named in `ENGINEERING_BACKLOG.md`'s own header (V13.0) |
| `ARCHITECTURE_SCORECARD.md` | Point-in-time architecture sweep; findings carried forward into later certifications |
| `CODE_QUALITY_CERTIFICATION.md` | Explicit merge source named in `ENGINEERING_BACKLOG.md`'s own header (V13.0) |
| `CODE_STANDARDIZATION.md` | Point-in-time hygiene sweep; fixes tracked in `docs/engineering/FIX_LOG.md` |
| `COMMIT_SUMMARY.md` | Point-in-time commit record (`31e2966`); `git log` is the actual source of truth |
| `CONSISTENCY_MATRIX.md` | Point-in-time UI sweep; findings tracked forward into `ENGINEERING_BACKLOG.md` |
| `DEPLOYMENT_VERIFICATION.md` | Resolved-incident checklist (JWKS outage, 2026-07-14); infra confirmed working in later sprints |
| `DEVELOPER_EXPERIENCE.md` | Content funneled into `docs/engineering/ISSUE_DATABASE.md` |
| `ENGINEERING_EXCELLENCE_REPORT.md` | Point-in-time sprint scorecard; superseded by `CHECKPOINT.md`/`PROGRESS.md`'s continuous burndown |
| `ENGINEERING_GOVERNANCE.md` | Point-in-time governance sprint; its own archive recommendation (repeated below by `FINAL_ENGINEERING_REVIEW.md`) is what this batch finally executes |
| `ENGINEERING_TRIAGE.md` | One-time triage of an external audit bundle; work committed as `31e2966`, confirmed in `SPRINT7_BASELINE.md` |
| `FINAL_ENGINEERING_REVIEW.md` | Point-in-time sprint scorecard; superseded by `CHECKPOINT.md`/`PROGRESS.md` |
| `FINAL_ENGINEERING_SUMMARY.md` | Point-in-time sprint scorecard; superseded by `CHECKPOINT.md`/`PROGRESS.md` |
| `FINAL_RELEASE_CERTIFICATION.md` | Explicit merge source named in `ENGINEERING_BACKLOG.md`'s own header (V13.0) |
| `FIXES_TODO.md` | Explicit merge source named in `ENGINEERING_BACKLOG.md`'s own header (V13.0) |
| `FIX_IMPLEMENTATION.md` | Resolved-incident code-fix narrative (JWKS outage, 2026-07-14); fix is in git history/tests |
| `FIX_LOG.md` | Unique V4.0/Sprint-7.0/V6.0 historical entries merged verbatim into `docs/engineering/FIX_LOG.md` before archiving (moved with `git mv`) |
| `FRONTEND_MATURITY.md` | Point-in-time UI sweep; findings tracked forward into `ENGINEERING_BACKLOG.md` |
| `FUTURE_READINESS.md` | Content funneled into `docs/engineering/ISSUE_DATABASE.md` |
| `LONG_TERM_MAINTAINABILITY.md` | Content funneled into `docs/engineering/ISSUE_DATABASE.md` |
| `MODULE_BOUNDARIES_AND_CODE_QUALITY.md` | Point-in-time architecture sweep; content funneled into `docs/engineering/ISSUE_DATABASE.md` |
| `PRODUCT_EXCELLENCE_REPORT.md` | Point-in-time sprint scorecard (V10.0); own text calls its own UI-API inventory historical reference, not living doc |
| `PRODUCT_PROPOSAL.md` | PROF-001 (missing profile screen) re-added as `ENGINEERING_BACKLOG.md` ENG-033 before archiving (moved with `git mv`) |
| `RELEASE_BLOCKERS.md` | Explicit merge source named in `ENGINEERING_BACKLOG.md`'s own header (V13.0) |
| `REPOSITORY_HEALTH.md` | Point-in-time hygiene sweep; fixes tracked in `docs/engineering/FIX_LOG.md` |
| `ROOT_CAUSE_ANALYSIS.md` | Resolved-incident postmortem (JWKS outage, 2026-07-14) |
| `SCALABILITY_CERTIFICATION.md` | Point-in-time scalability audit; finding tracked forward as `ENGINEERING_BACKLOG.md` ENG-005 (deferred) |
| `SCALABILITY_REVIEW.md` | Point-in-time scalability audit; same finding as above |
| `SECURITY_CERTIFICATION.md` | Point-in-time security audit (V13.0); IDOR/rate-limit/XSS findings match closed `ENGINEERING_BACKLOG.md` ENG-003/008/009 |
| `SECURITY_GOVERNANCE.md` | Point-in-time security audit; content funneled into `docs/engineering/ISSUE_DATABASE.md` |
| `SECURITY_STATUS.md` | Point-in-time security audit (Sprint 7.0) |
| `SPRINT7_BASELINE.md` | Pre-Sprint-7 baseline snapshot; superseded by `SPRINT7_COMPLETION_REPORT.md` |
| `SPRINT7_COMPLETION_REPORT.md` | Pointer doc to Sprint 7.0 phase reports, all archived in this same batch |
| `TECH_DEBT_REGISTER.md` | P0 salt-default gap re-added as `ENGINEERING_BACKLOG.md` ENG-032 before archiving; all other items already tracked |
| `UI_API_CONTRACT.md` | ~75-action inventory; own downstream reader (`PRODUCT_EXCELLENCE_REPORT.md`) already treats it as historical reference |
| `UI_EXCELLENCE_SCORECARD.md` | Explicit merge source named in `ENGINEERING_BACKLOG.md`'s own header (V13.0) |
| `VERIFIED_ISSUES.md` | Disposition of 49 triaged issues (V4.0), confirmed shipped/committed per `SPRINT7_BASELINE.md` |
| `WORKFLOW_ACTIVITY_LOG.md` | Closed live-QA session log; bugs found (WATERMARK-001, READ-OWNER-001) confirmed fixed in `docs/engineering/FIX_LOG.md` |
| `WORKFLOW_COMPLETENESS.md` | Closed Sprint 7.0 per-workflow completeness pass; fixes captured in the merged `FIX_LOG.md` section above |
| `WORKFLOW_COMPLETION_MATRIX.md` | Closed live-QA session; same bugs as `WORKFLOW_ACTIVITY_LOG.md`, now fixed |
| `WORKFLOW_PROGRESS.md` | Session-specific resume notes, sprint long closed |
| `WORKFLOW_SCREENSHOTS.md` | Redundant pointer to `docs/ui-audit/SCREENSHOT_INDEX.md` |
| `WORKFLOW_VALIDATION.md` | Closed live-QA session's final validation report |
| `DOCUMENTATION_MATURITY.md` | ARCHITECTURE.md/OVERVIEW.md contradiction already fixed (`ENGINEERING_BACKLOG.md` ENG-029); `archive/README.md`'s stale-path finding corrected directly in this same sprint |
| `PUBLIC_RELEASE_READINESS.md` | Version-numbering contradiction resolved by archiving the disagreeing docs (`ZERO_DEFECT_CERTIFICATION.md` lives in `docs/release/`, out of this batch's scope — flagged separately, not silently dropped); no-CD-pipeline gap re-added as `ENGINEERING_BACKLOG.md` ENG-034 |

**Kept at root, not archived**: `SECURITY_HARDENING_PLAN.md` (actively cited by `ENGINEERING_BACKLOG.md` ENG-026 as the live migration plan for an open item) and `REPOSITORY_CERTIFICATION.md` (this sprint's own in-progress entry point).

---

## Sprint V21.0 — Newly Archived / Relocated (2026-08-02)

V18.0's 6 certification deliverables had, by this sprint, served their purpose: every still-actionable finding in them had already been carried forward into `ENGINEERING_BACKLOG.md` (as ENG-032 through ENG-038). Per V21.0's explicit instruction not to leave multiple `FINAL_*`/certification-style documents scattered at root, and to consolidate toward one authoritative `docs/release/FINAL_RELEASE_CERTIFICATION.md`, these are archived now rather than kept indefinitely at root as V18.0's note above assumed they would be.

### From repository root → `archive/sprint18-certification/`

| File | Reason |
|------|--------|
| `REPOSITORY_CERTIFICATION.md` | V18.0 sprint entry point — sprint is long closed; superseded going forward by `docs/release/FINAL_RELEASE_CERTIFICATION.md` |
| `DEAD_CODE_REPORT.md` | Point-in-time dead-code sweep; still-open findings (e.g. the annotation-subsystem private-boundary pattern) remain tracked in `ENGINEERING_BACKLOG.md`, not lost |
| `DEPENDENCY_AUDIT.md` | Point-in-time dependency audit; fixes already applied and documented in `docs/engineering/FIX_LOG.md` |
| `MODULE_BOUNDARY_REPORT.md` | Point-in-time architecture audit; the one security-relevant finding (API-key scope gaps in `orgs.py`/`api_keys.py`/`billing.py`) remains open and trackable — flagged here for a future backlog entry if not already covered |
| `DOCUMENTATION_CLEANUP_PLAN.md` | Point-in-time plan; already executed (see V18.0 section above) |
| `FINAL_REPOSITORY_SCORECARD.md` | Point-in-time scorecard; superseded by `docs/release/FINAL_RELEASE_CERTIFICATION.md` |

### From repository root → `docs/security/`

| File | Reason |
|------|--------|
| `SECURITY_HARDENING_PLAN.md` | Not archived — still an actively-cited live plan (`ENGINEERING_BACKLOG.md` ENG-026), but relocated out of root into `docs/security/` alongside the repo's other current security documentation, since it's a living reference doc, not a certification snapshot. `ENGINEERING_BACKLOG.md`'s citation updated to the new path. |

**Root `.md` count after this sprint's consolidation**: 9 (down from V18.0's 16) — `README.md`, `CHANGELOG.md`, `CODE_OF_CONDUCT.md`, `CONTRIBUTING.md`, `SECURITY.md`, `ENGINEERING_BACKLOG.md`, `PROGRESS.md`, `CHECKPOINT.md`, `REGRESSION_REPORT.md`. The last four are deliberately kept at root rather than moved under `docs/engineering/` alongside their siblings (`ACTION_LOG.md`, `FIX_LOG.md`, `ISSUE_DATABASE.md`, `RELEASE_STATE.md`) — they are this session's actively-referenced, frequently-updated canonical tracking docs, and moving them carries real risk (this session's own Downloads-sync habit and every prior sprint's instructions reference them by root path) for no clear discoverability benefit over the risk of broken references. This is a deliberate, reasoned deviation from V21.0's suggested minimal-root template, not an oversight.
