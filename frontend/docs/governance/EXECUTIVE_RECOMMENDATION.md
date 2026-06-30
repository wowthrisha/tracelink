# Executive Recommendation
Repository Governance Audit — Phase 6
Date: 2026-06-22

Audience: Principal Engineer / Staff Architect / TPM

---

## Bottom Line

The codebase is structurally sound after Sprint 4.2D–E. The frontend extraction is complete, the import graph is clean, and there is no dead code. **The primary governance risk is documentation sprawl, not code quality.** 91 markdown files across the repository, many describing superseded or incorrect state, create a significant risk of future decisions being made on stale information.

One security item requires immediate non-code action by the user (credential file still tracked — see Question 1 note).

---

## 1. What Should Remain Permanently?

**Source of truth for what happened:**
- `docs/governance/ACTION_LOG.md` (migrate from `docs/engineering/ACTION_LOG.md`) — every file change since Sprint 3.3, append-only
- `docs/governance/RISK_REGISTER.md` (unified, namespace-prefixed) — every identified risk

**Active operational documents:**
- `docs/decisions/DECISION_LOG.md` — architectural decision record
- `docs/architecture/ARCHITECTURE_SCORECARD.md` — quality progression
- `docs/security/SECURITY_BASELINE.md` — frontend security surface

**Full-stack references (root level):**
- `README.md`
- `TRACEVIEW_PILOT_DEPLOYMENT_GUIDE.md` — operational runbook
- `SECRET_ROTATION_RUNBOOK.md` — **security critical until credentials confirmed rotated**
- `SECRET_SCAN_REPORT.md` — credential exposure history
- `SECURITY_AUDIT_REPORT.md` (2026-06-17) — most recent security audit
- `RELEASE_BLOCKERS.md` — some P0/P1 items may still be open
- `BACKEND_ARCHITECTURE_REVIEW.md`, `API_CONTRACT_REVIEW.md`, `DATABASE_REVIEW.md`, `SYSTEM_DESIGN_REVIEW.md` — full-stack architecture references
- `ARCHITECTURE_DECISIONS.md` — ADRs
- `TECHNICAL_DEBT_REGISTER.md` — active debt tracking
- `IMPLEMENTATION_MASTER_PLAN.md` — enterprise transformation roadmap (needs status update)
- `TOP_20_ACTIONS_TO_REACH_ENTERPRISE_GRADE.md` — action register

**Active sprint plan:**
- `docs/engineering/SPRINT4_3_SECURITY_HARDENING_PLAN.md`

---

## 2. What Should Be Archived?

**Archive = keep for reference but mark clearly as historical, not current state.**

Root level (13 files):
- `HARDENING_REPORT.md` — earliest security milestone
- `TRACEVIEW_AUDIT_A.md`, `TRACEVIEW_AUDIT_C.md`, `TRACEVIEW_AUDIT_D.md` — Phase A/C/D audit series
- `TRACEVIEW_D2_DECISION_REPORT.md`, `TRACEVIEW_D25_VALIDATION_REPORT.md`, `TRACEVIEW_LAUNCH_READINESS_REPORT.md` — decision and validation history
- `SECUREDOC_CURRENT_STATE_REPORT.md` — pre-transformation baseline
- `PHASE_E2_SCALABILITY_AUDIT.md` — scalability audit snapshot
- `P0_REVALIDATION_REPORT.md`, `PRE_PILOT_CERTIFICATION_REPORT.md`, `FINAL_PRELAUNCH_AUDIT.md` — launch certification history
- `IMPLEMENTATION_PROGRESS.md` — stale status tracker (archive, replace with updated version)

Frontend docs (12 files):
- All `docs/reports/*.md` (10 files) — sprint reports and historical audits
- `docs/engineering/REPOSITORY_STABILIZATION_AUDIT.md` — Phase 0 audit, superseded by this governance audit
- `docs/engineering/REPOSITORY_HEALTH_SCORE.md` — 97/100 snapshot at Sprint 4.2E close

---

## 3. What Should Be Deleted?

**Delete = no unique information. Safe to remove immediately upon approval.**

| File | Reason |
|---|---|
| `].md` | Zero-information duplicate of TRACEVIEW_PILOT_DEPLOYMENT_GUIDE.md |
| `ALL_ACTION_DESIGNS.md` | 0 bytes — empty file |
| `FRONTEND_ARCHITECTURE_REVIEW.md` | **Critically stale.** Claims app.jsx = 6,046 lines. Reality = 5 lines. Actively misleads. |
| `FRONTEND_REFACTOR_PLAN.md` | **Obsolete plan.** Describes a task completed in Sprint 4.2D. |
| `REPOSITORY_CLEANUP_PLAN.md` (root) | Superseded by this governance cleanup plan |
| `ENTERPRISE_READINESS_AUDIT.md` | Superseded by PRODUCTION_READINESS_AUDIT.md |
| `IMPLEMENTATION_VERIFICATION_REPORT.md` | Superseded by SECURITY_AUDIT_REPORT.md (2026-06-17) |
| `SECURITY_VERIFICATION_AUDIT.md` | Superseded by SECURITY_AUDIT_REPORT.md (2026-06-17) |
| `ENTERPRISE_REVALIDATION_REPORT.md` | One-time pass, no unique content |
| `ACTION_1_DESIGN.md` through `ACTION_12_DESIGN.md` | Implemented features — designs are historical artifacts with zero active use |
| `docs/engineering/DOCS_MIGRATION_LOG.md` | Migration complete — captured in ACTION_LOG entries A-131–A-136 |
| 8 completed sprint plan files in `docs/engineering/` | Sprint execution is recorded in ACTION_LOG |

**Pending user verification before deletion:**
| File | Required Action |
|---|---|
| `TRACEVIEW_AUDIT_B.md` | Verify SECRET_ROTATION_RUNBOOK.md was executed + git history scrubbed, then delete |
| `ACTION_13_DESIGN.md` through `ACTION_20_DESIGN.md` | Verify each feature's implementation status, then delete if complete |

---

## 4. What Creates Future Maintenance Risk?

**Risk 1 (HIGH): RISK_REGISTER ID namespace collision**
Two separate RISK_REGISTER documents use R-001...R-NNN numbering with different scopes. Any cross-document reference to "R-001" is ambiguous. Before the governance migration, all root register IDs must be prefixed `BE-R-` and all frontend IDs prefixed `FE-R-`. Without this, the unified governance register will silently have duplicate IDs.

**Risk 2 (HIGH): Documentation written about current state that will become stale**
The current ARCHITECTURE_BASELINE.md, SECURITY_BASELINE.md, and REPOSITORY_INVENTORY.md describe the state as of Sprint 4.2E. As future sprints add files or change structure, these documents will drift from reality unless they are explicitly updated each sprint. The governance standard should require: any sprint that adds/removes/renames a source file updates REPOSITORY_INVENTORY.md as part of its Phase 7 (log) step.

**Risk 3 (MEDIUM): `IMPLEMENTATION_MASTER_PLAN.md` / `IMPLEMENTATION_PROGRESS.md` status is stale**
These root-level documents show Phases 3–5 of the enterprise transformation as "In Progress" / "Pending" as of 2026-06-07. If any future sprint starts from these documents without first verifying current action statuses, it will plan against an incorrect baseline. These need a single dedicated update session before the next enterprise transformation sprint.

**Risk 4 (MEDIUM): `api.js` decomposition is deferred but unscheduled**
`api.js` at 769 lines is the last large undecomposed frontend file. The technical debt items (30 duplicated 401 handlers, 5 blob-download sequences, duplicate `buildFeedbackFilters`) are documented but unscheduled. As new API methods are added, this file will grow. Recommend scheduling the decomposition sprint before `api.js` exceeds 1,000 lines.

**Risk 5 (LOW): Completed sprint plans remaining in `docs/engineering/`**
Eight completed sprint plans still exist in `docs/engineering/`. They are never referenced by active documents. They create cognitive overhead — a new team member reading the docs folder would not immediately distinguish active from historical plans.

---

## 5. What Would a Senior Staff Engineer Remove Immediately?

Without hesitation, in this order:

1. **`TRACEVIEW_AUDIT_B.md`** — a tracked file containing live credentials in a public repository is a P0 security incident. The file should have been deleted when RELEASE_BLOCKERS.md was written. The SECRET_ROTATION_RUNBOOK.md exists to remediate this. Remove immediately after confirming the runbook was executed.

2. **`FRONTEND_ARCHITECTURE_REVIEW.md`** — the most dangerous documentation in the repo. It describes a codebase that no longer exists. A new engineer reading it would believe `app.jsx` has 6,046 lines, 169 useState calls, and 3 "god components." Every line is wrong. This document will cause bad decisions.

3. **`FRONTEND_REFACTOR_PLAN.md`** — describes ViewerScreen extraction as a pending task. It was completed weeks ago. Its presence implies there is unfinished work that doesn't exist.

4. **`].md`** — 31KB duplicate file with a broken filename. Noise.

5. **`ALL_ACTION_DESIGNS.md`** — 0 bytes. A zero-byte file in the repo root is pure clutter.

6. **All 8 completed sprint plans** (`SPRINT4_2_EXECUTION_PLAN.md` etc.) — these have zero future value. The ACTION_LOG is the execution record.

---

## 6. What Would Prevent Future Architectural Drift?

**Rule 1: Two living documents maximum.**
Only `docs/governance/ACTION_LOG.md` and `docs/governance/RISK_REGISTER.md` are append-only operational logs. Every other document is either architecture reference (updated when the architecture changes) or historical archive (never updated).

**Rule 2: Sprint completion requires document cleanup.**
Every sprint's Phase 7 (logs) step must:
- Append to ACTION_LOG
- Append to RISK_REGISTER (open or close entries)
- Mark any completed sprint plans as HISTORICAL or delete them
- Update REPOSITORY_INVENTORY.md if file count changed

**Rule 3: New documentation requires a classification statement.**
Every new document created must declare its category in the header: `Category: A (Operational) | B (Architecture Reference) | C (Historical Archive) | D (Sprint Plan — delete on completion)`. This prevents the "accumulation problem" where documents are created without a clear end-of-life plan.

**Rule 4: RISK_REGISTER IDs must be namespaced.**
All risk IDs use the format `{SCOPE}-R-{NNN}`: `BE-R-001` for backend, `FE-R-001` for frontend, `GOV-R-001` for governance. This prevents the current collision between root and frontend registers.

**Rule 5: No documentation describing the current state of source code.**
Architecture baseline documents snapshot the state at a point in time. They should be dated and not updated to track every change — the ACTION_LOG tracks changes. Avoid documents like "REPOSITORY_INVENTORY.md" that will drift from code reality unless you commit to updating them every sprint. A live inventory is better generated by `find src/ -type f | wc -l` than maintained by hand.

---

## Governance Migration Steps (Recommended Order)

| Step | Action | Risk | Prerequisite |
|---|---|---|---|
| 1 | User: execute SECRET_ROTATION_RUNBOOK.md | Security | None |
| 2 | Delete `TRACEVIEW_AUDIT_B.md` after rotation confirmed | Low | Step 1 |
| 3 | Delete zero-risk files: `].md`, `ALL_ACTION_DESIGNS.md` | Zero | None |
| 4 | Delete stale frontend docs: FRONTEND_ARCHITECTURE_REVIEW.md, FRONTEND_REFACTOR_PLAN.md | Zero | None |
| 5 | Delete superseded audit docs (8 files) | Zero | None |
| 6 | Delete completed sprint plans in frontend/docs/engineering/ (8 files) | Zero | None |
| 7 | Prefix RISK_REGISTER IDs: root = `BE-R-`, frontend = `FE-R-` | Low | None |
| 8 | Create `docs/governance/ACTION_LOG.md` — migrate A-001–A-143 from docs/engineering/ | Low | Step 6 |
| 9 | Create `docs/governance/RISK_REGISTER.md` — migrate FE-R-001–FE-R-063 + BE-R-001–BE-R-015 | Low | Step 7 |
| 10 | Update `IMPLEMENTATION_PROGRESS.md` with current action statuses | Medium | User validates action statuses |
| 11 | Archive or label remaining historical docs with HISTORICAL marker | Zero | None |
| 12 | Delete ACTION_13–20_DESIGN.md after verifying each feature's implementation | Low | User validates per-action |

---

## Score After Governance Execution

| Dimension | Current | After Cleanup |
|---|---|---|
| Documentation quality | 60/100 (91 files, many stale) | 85/100 (~35 files, all current) |
| Source code quality | 97/100 | 97/100 (unchanged) |
| Risk register clarity | 60/100 (dual registers, ID collision) | 90/100 (single namespaced register) |
| Security documentation | 75/100 (AUDIT_B with credentials) | 95/100 (after file deletion) |
| Architectural clarity | 70/100 (stale FRONTEND_ARCHITECTURE_REVIEW active) | 95/100 (stale docs removed) |
