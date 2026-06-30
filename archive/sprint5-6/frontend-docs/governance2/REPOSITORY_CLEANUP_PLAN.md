# Repository Cleanup Plan
Repository Governance Audit — Phase 4
Date: 2026-06-22

**STOP — Do not execute without user approval.**
This is a plan only. No files have been deleted or moved.

---

## Safe To Delete

These files contain no unique information. Deletion is zero-risk.

### Root Level (`securedoc/`)

| File | Reason |
|---|---|
| `].md` | 31,909-byte exact duplicate of `TRACEVIEW_PILOT_DEPLOYMENT_GUIDE.md`. Accidental shell artifact. Confirmed identical byte-for-byte. |
| `ALL_ACTION_DESIGNS.md` | 0 bytes. Empty file. |
| `FRONTEND_ARCHITECTURE_REVIEW.md` | **Critically stale.** Describes app.jsx as 6,046 lines. Current reality: 5 lines. Actively misleads any reader about the frontend codebase. Unique content: none — all concerns have been resolved and documented in sprint reports. |
| `FRONTEND_REFACTOR_PLAN.md` | **Fully executed plan.** Recommends extracting ViewerScreen from app.jsx — done in Sprint 4.2D. The plan describes a task that is complete. No unrealized content. |
| `REPOSITORY_CLEANUP_PLAN.md` | **Superseded** by this governance cleanup plan. The prior plan identified a subset of what this plan identifies and was never actioned. |
| `ENTERPRISE_READINESS_AUDIT.md` | Superseded by `PRODUCTION_READINESS_AUDIT.md`. Same audit, earlier generation, lower confidence. |
| `IMPLEMENTATION_VERIFICATION_REPORT.md` | Historical one-time audit. Superseded by `SECURITY_AUDIT_REPORT.md` (2026-06-17). |
| `SECURITY_VERIFICATION_AUDIT.md` | Superseded by `SECURITY_AUDIT_REPORT.md` (2026-06-17). Covers same surface, 10 days older, less evidence-based. |
| `ENTERPRISE_REVALIDATION_REPORT.md` | One-time revalidation pass. Historical only. Superseded by later audits. |
| `ALL_ACTION_DESIGNS.md` | 0 bytes (empty). |

### Root Level — ACTION Design Docs (19 files)

These are per-action implementation design documents for Actions 1–20. All actions with status "APPROVED" or "COMPLETE" have been implemented and the designs are historical artifacts only. Actions with status "IN PROGRESS" should be reviewed before deletion — however, the actual implementation plans are in the code, not these docs.

| File | Status | Safe to Delete? |
|---|---|---|
| `ACTION_1_DESIGN.md` | APPROVED (HSTS) | Yes — implemented |
| `ACTION_2_DESIGN.md` | APPROVED (max_views race) | Yes — implemented |
| `ACTION_3_DESIGN.md` | APPROVED (forensic stamp) | Yes — implemented |
| `ACTION_4_DESIGN.md` | APPROVED (session cache) | Yes — implemented |
| `ACTION_5_DESIGN.md` | APPROVED (structured logging) | Yes — implemented |
| `ACTION_6_DESIGN.md` | Appears complete (streaming) | Yes — implemented |
| `ACTION_7_DESIGN.md` | Appears complete (Prometheus) | Yes — implemented |
| `ACTION_8_DESIGN.md` | Appears complete (OTel) | Yes — implemented |
| `ACTION_9_DESIGN.md` | Appears complete (CDN thumbnails) | Yes — implemented |
| `ACTION_10_DESIGN.md` | Appears complete (PPTX) | Yes — implemented |
| `ACTION_11_DESIGN.md` | Appears complete (XLSX) | Yes — implemented |
| `ACTION_12_DESIGN.md` | COMPLETE (time-on-page analytics) | Yes |
| `ACTION_13_DESIGN.md` | IN PROGRESS (Webhooks) | **Review before delete — may still be active design** |
| `ACTION_14_DESIGN.md` | IN PROGRESS (Public API/API Keys) | **Review before delete** |
| `ACTION_15_DESIGN.md` | IN PROGRESS (Organizations/SSO) | **Review before delete** |
| `ACTION_17_DESIGN.md` | IN PROGRESS (Admin Audit Log) | **Review before delete** |
| `ACTION_18_DESIGN.md` | IN PROGRESS (Document Version History) | **Review before delete** |
| `ACTION_19_DESIGN.md` | IN PROGRESS (SSE Notifications) | **Review before delete** |
| `ACTION_20_DESIGN.md` | IN PROGRESS (Custom Domains) | **Review before delete** |

**Recommendation:** Delete Actions 1–12 immediately. For Actions 13–20 IN PROGRESS: if implementation is complete (verify against codebase), delete. If implementation is incomplete, retain until the feature ships.

### Frontend Docs

| File | Reason |
|---|---|
| `docs/engineering/DOCS_MIGRATION_LOG.md` | Migration is complete. Content captured in ACTION_LOG entries A-131–A-136. No unique content. |
| `docs/engineering/SPRINT3_5_NEXT_SPRINT.md` | Completed sprint plan. ACTION_LOG records the execution. |
| `docs/engineering/SPRINT4_2_EXECUTION_PLAN.md` | Completed sprint plan. |
| `docs/engineering/SPRINT4_2B_EXECUTION_PLAN.md` | Completed sprint plan. |
| `docs/engineering/SPRINT4_2C_EXECUTION_PLAN.md` | Completed sprint plan. |
| `docs/engineering/SPRINT4_2D_VIEWER_FINAL_PLAN.md` | Completed sprint plan. Superseded by SPRINT4_2D_REPORT.md. |
| `docs/engineering/SPRINT4_2D_IMPLEMENTATION_PROMPT.md` | Execution prompt for completed sprint. Historical only. |
| `docs/engineering/SPRINT4_2E_REPOSITORY_STABILIZATION_PLAN.md` | Completed sprint plan. Sprint 4.2E is done. |
| `docs/engineering/SPRINT4_EXECUTION_PLAN.md` | Completed sprint plan. All 4.x sprints executed. |

---

## Archive Only

These files have historical value and should be retained in an archive location (e.g., `docs/archive/` or simply left in place and clearly marked HISTORICAL). Do not delete.

### Root Level (`securedoc/`)

| File | Archive Reason |
|---|---|
| `HARDENING_REPORT.md` | Earliest security hardening milestone (2026-05-13). Shows baseline state before audit series. |
| `TRACEVIEW_AUDIT_A.md` | Phase A structural audit (2026-06-01). Earliest comprehensive audit. Historical baseline. |
| `TRACEVIEW_AUDIT_C.md` | Phase C performance audit (2026-06-04). Historical performance baseline. |
| `TRACEVIEW_AUDIT_D.md` | Phase D universal document architecture (2026-06-04). Historical architecture decision record. |
| `TRACEVIEW_D2_DECISION_REPORT.md` | DOCX/PPTX processing decision (2026-06-04). Historical ADR. |
| `TRACEVIEW_D25_VALIDATION_REPORT.md` | DOCX rendering pipeline validation (2026-06-04). Historical milestone. |
| `TRACEVIEW_LAUNCH_READINESS_REPORT.md` | Pre-pilot launch readiness (2026-06-04). Historical milestone. |
| `TRACEVIEW_ARCHITECTURE_EXTRACTION_REPORT.md` | Architecture extraction deep-dive (2026-06-08). Historical architecture reference. |
| `SECUREDOC_CURRENT_STATE_REPORT.md` | State snapshot before enterprise sprint (2026-06-07). Historical baseline. |
| `IMPLEMENTATION_PROGRESS.md` | Status tracker (stale at 2026-06-07). Historical record of transformation phases. |
| `PHASE_E2_SCALABILITY_AUDIT.md` | Scalability audit (2026-06-07). Historical reference. |
| `P0_REVALIDATION_REPORT.md` | P0 blocker revalidation (2026-06-08). Historical milestone. |
| `PRE_PILOT_CERTIFICATION_REPORT.md` | 9-phase pre-pilot certification (2026-06-08). Historical milestone — documents audit methodology. |
| `FINAL_PRELAUNCH_AUDIT.md` | Pre-launch code audit (2026-06-07). Historical milestone. |
| `SECURITY_VERIFICATION_AUDIT.md` | Security audit v8.1.0 (2026-06-07). Historical — superseded but useful for regression reference. |

### Critical — Pending User Action Before Archiving

| File | Action Required Before Archive |
|---|---|
| `TRACEVIEW_AUDIT_B.md` | **CONTAINS LIVE CREDENTIALS** (Supabase anon key + URL). User must: (1) verify SECRET_ROTATION_RUNBOOK.md was executed, (2) scrub git history per RELEASE_BLOCKERS P0-3, (3) THEN delete this file. Do NOT merely archive — archiving keeps the credentials accessible. |

### Frontend Docs

| File | Archive Reason |
|---|---|
| `docs/reports/SPRINT3_4_REPORT.md` | Historical sprint milestone |
| `docs/reports/SPRINT3_5_REPORT.md` | Historical sprint milestone |
| `docs/reports/SPRINT4_0_REPORT.md` | Historical sprint milestone |
| `docs/reports/SPRINT4_2D_REPORT.md` | Historical sprint milestone |
| `docs/reports/ANNOTATION_LAYER_READINESS_REVIEW.md` | Historical pre-extraction safety review |
| `docs/reports/SCREEN_EXTRACTION_READINESS_REVIEW.md` | Historical pre-extraction safety review |
| `docs/reports/POST_SCREEN_EXTRACTION_AUDIT.md` | Historical verification |
| `docs/reports/BUILD_HYGIENE_AUDIT.md` | Historical hygiene check |
| `docs/reports/DEAD_CODE_AUDIT.md` | Historical dead-code sweep (zero dead code confirmed) |
| `docs/reports/VIEWERSCREEN_FINAL_AUDIT.md` | Historical 62-scenario verification — important milestone |
| `docs/engineering/REPOSITORY_STABILIZATION_AUDIT.md` | Historical Phase 0 audit for Sprint 4.2E |
| `docs/engineering/REPOSITORY_HEALTH_SCORE.md` | Historical 97/100 score snapshot |

---

## Keep (Permanent)

These files should remain in place. They are either operational, actively referenced, or carry unique information not recorded elsewhere.

### Root Level

| File | Reason |
|---|---|
| `README.md` | Project documentation |
| `IMPLEMENTATION_MASTER_PLAN.md` | Living roadmap index — update status before next use |
| `TRACEVIEW_PILOT_DEPLOYMENT_GUIDE.md` | Operational deployment runbook |
| `RELEASE_BLOCKERS.md` | Active blockers — several P0/P1 items may still be open |
| `SECRET_ROTATION_RUNBOOK.md` | **SECURITY CRITICAL** — operational runbook until rotation confirmed complete |
| `SECRET_SCAN_REPORT.md` | Reference for credential exposure history |
| `RISK_REGISTER.md` | Backend/full-stack risk register — **rename IDs to BE-R-xxx before governance merge** |
| `ARCHITECTURE_DECISIONS.md` | ADR log |
| `BACKEND_ARCHITECTURE_REVIEW.md` | Architecture reference |
| `API_CONTRACT_REVIEW.md` | API contract reference (80+ routes) |
| `DATABASE_REVIEW.md` | Database/migration reference |
| `SYSTEM_DESIGN_REVIEW.md` | Deployment topology reference |
| `EXECUTIVE_SUMMARY.md` | Senior audience summary |
| `PRODUCTION_READINESS_AUDIT.md` | Readiness audit reference |
| `SECURITY_AUDIT_REPORT.md` | **Most recent security audit (2026-06-17)** — primary security reference |
| `FEATURE_VERIFICATION_CHECKLIST.md` | Feature coverage reference (note: frontend column stale) |
| `TECHNICAL_DEBT_REGISTER.md` | Active debt tracking |
| `CHANGELOG_ENTERPRISE.md` | Incomplete but valuable — complete through Actions 9 then keep |
| `TOP_20_ACTIONS_TO_REACH_ENTERPRISE_GRADE.md` | Action status register |
| `PHASE_E2_SCALABILITY_AUDIT.md` | Scalability reference |
| `TRACEVIEW_ARCHITECTURE_EXTRACTION_REPORT.md` | Deep architecture reference |

### Frontend Docs

| File | Reason |
|---|---|
| `docs/engineering/ACTION_LOG.md` | **PRIMARY OPERATIONAL LOG** — append-only, never delete |
| `docs/risks/RISK_REGISTER.md` | **PRIMARY RISK LOG** — append-only, never delete; **rename IDs to FE-R-xxx before governance merge** |
| `docs/decisions/DECISION_LOG.md` | Architectural decision record — permanent |
| `docs/architecture/ARCHITECTURE_BASELINE.md` | Architecture reference |
| `docs/architecture/ARCHITECTURE_SCORECARD.md` | Quality progression record |
| `docs/architecture/DEPENDENCY_AUDIT.md` | Dependency reference |
| `docs/architecture/REPOSITORY_INVENTORY.md` | Source inventory reference |
| `docs/security/SECURITY_BASELINE.md` | Frontend security reference — used by SPRINT4_3 |
| `docs/engineering/SPRINT4_3_SECURITY_HARDENING_PLAN.md` | **ACTIVE** next sprint plan |

---

## Consolidate Into Governance ACTION_LOG

The following ACTION_LOG content should be migrated into `docs/governance/ACTION_LOG.md` (the new permanent home):

1. All entries from `docs/engineering/ACTION_LOG.md` (A-001 through A-143) — copy verbatim, append to the governance log
2. Append new governance actions (this audit: A-144 and forward)

Note: Migrate content, then update `docs/engineering/ACTION_LOG.md` to redirect to new location.

---

## Consolidate Into Governance RISK_REGISTER

The new `docs/governance/RISK_REGISTER.md` should unify:

1. Root `RISK_REGISTER.md` (backend/full-stack risks): Rename all IDs to `BE-R-001...BE-R-015` before migration
2. Frontend `docs/risks/RISK_REGISTER.md` (extraction risks): Rename all IDs to `FE-R-001...FE-R-063` before migration
3. New risks from this governance audit: Use `GOV-R-001...` prefix

This prevents the namespace collision documented in C-003.

---

## Execution Order (When Approved)

1. **Immediate** (zero risk): Delete `].md`, `ALL_ACTION_DESIGNS.md`
2. **Security priority**: Verify SECRET_ROTATION_RUNBOOK.md execution → delete `TRACEVIEW_AUDIT_B.md`
3. **High confidence deletions**: FRONTEND_ARCHITECTURE_REVIEW.md, FRONTEND_REFACTOR_PLAN.md, REPOSITORY_CLEANUP_PLAN.md (root), ENTERPRISE_READINESS_AUDIT.md, IMPLEMENTATION_VERIFICATION_REPORT.md, SECURITY_VERIFICATION_AUDIT.md, ENTERPRISE_REVALIDATION_REPORT.md
4. **Completed ACTION_DESIGN docs** (Actions 1–12): Delete after confirming implementation
5. **IN PROGRESS ACTION_DESIGN docs** (Actions 13–20): Review each against codebase, then delete
6. **Frontend completed sprint plans**: Delete 8 completed sprint plan files
7. **Frontend historical reports**: Move to archive or leave in place with HISTORICAL marker
8. **Risk register namespace migration**: Prefix IDs, create unified governance RISK_REGISTER
9. **ACTION_LOG migration**: Migrate A-001–A-143 to docs/governance/ACTION_LOG.md

**Do not execute without explicit user approval per step.**
