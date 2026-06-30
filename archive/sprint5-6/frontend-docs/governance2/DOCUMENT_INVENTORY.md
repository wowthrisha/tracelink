# Document Inventory
Repository Governance Audit — Phase 1
Date: 2026-06-22
Scope: All documentation across `securedoc/` and `securedoc/frontend/docs/`

---

## Summary

| Scope | File Count | Lines |
|---|---|---|
| Repo root (`securedoc/*.md`) | 61 files | ~18,245 |
| Frontend docs (`frontend/docs/**/*.md`) | 30 files | ~11,000 est |
| **Total** | **91 files** | **~29,000** |

---

## Part 1 — Repo Root (`securedoc/`)

### 1.1 Living / Operational Candidates

| Path | Purpose | Created | Last Updated | Referenced | Useful | Superseded |
|---|---|---|---|---|---|---|
| `README.md` | Project overview, setup, deployment | Unknown | Unknown | Yes (implicit) | Yes | No |
| `IMPLEMENTATION_MASTER_PLAN.md` | Enterprise transformation roadmap (Actions 1–20) | 2026-06-07 | 2026-06-07 | Yes — IMPLEMENTATION_PROGRESS.md references it | Partially — Phase 1–2 complete, Phases 3–5 status unknown | No |
| `IMPLEMENTATION_PROGRESS.md` | Status tracker for Actions 1–20 | 2026-06-07 | 2026-06-07 | Yes — IMPLEMENTATION_MASTER_PLAN.md | Stale — "IN PROGRESS" status 15 days old, uncertain current truth | Partially by CHANGELOG_ENTERPRISE.md |
| `TRACEVIEW_PILOT_DEPLOYMENT_GUIDE.md` | Railway + Cloudflare + Supabase production setup (D2.7) | 2026-06-04 | 2026-06-04 | Yes — deployment runbook | Yes — operational | No |
| `RELEASE_BLOCKERS.md` | P0–P2 blockers from pre-pilot audit | 2026-06-08 | 2026-06-08 | Yes — PRE_PILOT_CERTIFICATION_REPORT.md | Partially — P0-1 marked FIXED; P0-2/P0-3 (credential exposure) UNRESOLVED; P0-4 through P0-8 status unknown | No |
| `RISK_REGISTER.md` | Full-stack risk register (R-001 to R-015) | 2026-06-07 | 2026-06-07 | No external refs | Yes — covers backend/full-stack risks | No |
| `SECRET_ROTATION_RUNBOOK.md` | Runbook for rotating exposed Supabase credentials | 2026-06-08 | 2026-06-08 | Yes — RELEASE_BLOCKERS P0-2/P0-3 | **CRITICAL** — active operational document until credentials confirmed rotated | No |
| `SECRET_SCAN_REPORT.md` | Credential exposure scan results | 2026-06-08 | 2026-06-08 | Yes — SECRET_ROTATION_RUNBOOK.md | Yes — as reference for what was exposed and in which commits | No |
| `TECHNICAL_DEBT_REGISTER.md` | Code-smell findings from architecture reviews | Unknown | Unknown | Yes — FRONTEND_ARCHITECTURE_REVIEW.md, BACKEND_ARCHITECTURE_REVIEW.md | Partially — some items may be resolved by extraction sprints | Partially by frontend DECISION_LOG.md |
| `CHANGELOG_ENTERPRISE.md` | Changelog for Actions 1–5 | 2026-06-07 | 2026-06-07 | Implicit | Partially — only covers 5 of 20 actions | No |
| `ARCHITECTURE_DECISIONS.md` | ADR log for full-stack architecture decisions | Unknown | Unknown | Implicit | Yes — ADRs should be permanent | No |
| `TOP_20_ACTIONS_TO_REACH_ENTERPRISE_GRADE.md` | Action list with status (some IN PROGRESS) | 2026-06-07 | 2026-06-07 | Yes — IMPLEMENTATION_MASTER_PLAN.md | Partially — status may be stale | Partially by IMPLEMENTATION_PROGRESS.md |

### 1.2 Architecture Reference Documents

| Path | Purpose | Created | Last Updated | Referenced | Useful | Superseded |
|---|---|---|---|---|---|---|
| `BACKEND_ARCHITECTURE_REVIEW.md` | Backend layering, router/service/model map | Unknown | 2026-06-17 est | Yes — EXECUTIVE_SUMMARY.md | Yes — useful architectural reference | No |
| `API_CONTRACT_REVIEW.md` | 14 router files, 80+ routes, full endpoint inventory | Unknown | 2026-06-17 est | Yes — EXECUTIVE_SUMMARY.md | Yes — architecture reference | No |
| `DATABASE_REVIEW.md` | 14 model files, migration chain (001–024) verification | Unknown | Unknown | Yes — EXECUTIVE_SUMMARY.md | Yes — architecture reference | No |
| `SYSTEM_DESIGN_REVIEW.md` | docker-compose, Celery, config, storage topology | Unknown | Unknown | Yes — EXECUTIVE_SUMMARY.md | Yes — architecture reference | No |
| `EXECUTIVE_SUMMARY.md` | Synthesizes 10 audit reports into one summary | Unknown | Unknown | Implicit | Yes — senior audience summary | No |
| `PRODUCTION_READINESS_AUDIT.md` | Category scores 0-10, P0/P1/P2 findings | Unknown | Unknown | Yes — EXECUTIVE_SUMMARY.md | Yes — reference | No |
| `FEATURE_VERIFICATION_CHECKLIST.md` | Every major feature scored across Frontend/Backend/DB/API | Unknown | Unknown | Yes — EXECUTIVE_SUMMARY.md | Yes — reference, but frontend section describes old app.jsx | Partially (frontend column stale) |
| `SECURITY_AUDIT_REPORT.md` | Full backend security audit, file:line citations | 2026-06-17 | 2026-06-17 | No | Yes — most recent, most evidence-based security doc | Supersedes SECURITY_VERIFICATION_AUDIT.md |
| `PHASE_E2_SCALABILITY_AUDIT.md` | Scalability, large document, worker audit | 2026-06-07 | 2026-06-07 | Implicit | Yes — architecture reference | No |
| `TRACEVIEW_ARCHITECTURE_EXTRACTION_REPORT.md` | Full architecture extraction and distributed systems review | 2026-06-08 | 2026-06-08 | Implicit | Yes — deep architecture reference | No |

### 1.3 Historical Archive — Already Superseded

| Path | Purpose | Created | Last Updated | Referenced | Useful | Superseded By |
|---|---|---|---|---|---|---|
| `TRACEVIEW_AUDIT_A.md` | Phase A structural/design audit | 2026-06-01 | 2026-06-01 | Implicitly by later audits | No — superseded | All later audits |
| `TRACEVIEW_AUDIT_B.md` | Phase B security audit | 2026-06-03 | 2026-06-03 | RELEASE_BLOCKERS P0-2/P0-3 | No — superseded; **CONTAINS LIVE CREDENTIALS** (Supabase anon key + URL) | SECURITY_AUDIT_REPORT.md |
| `TRACEVIEW_AUDIT_C.md` | Phase C performance/scalability audit | 2026-06-04 | 2026-06-04 | Implicit | No — superseded | PHASE_E2_SCALABILITY_AUDIT.md |
| `TRACEVIEW_AUDIT_D.md` | Phase D universal document architecture | 2026-06-04 | 2026-06-04 | Implicit | No — superseded | TRACEVIEW_ARCHITECTURE_EXTRACTION_REPORT.md |
| `TRACEVIEW_D2_DECISION_REPORT.md` | DOCX/PPTX processing strategy decision | 2026-06-04 | 2026-06-04 | Implicit | Historical only | ARCHITECTURE_DECISIONS.md |
| `TRACEVIEW_D25_VALIDATION_REPORT.md` | DOCX visual rendering pipeline validation | 2026-06-04 | 2026-06-04 | Implicit | Historical only | PRE_PILOT_CERTIFICATION_REPORT.md |
| `TRACEVIEW_LAUNCH_READINESS_REPORT.md` | Pre-merge/pre-pilot review (phase-d2-docx) | 2026-06-04 | 2026-06-04 | Implicit | Historical only | PRE_PILOT_CERTIFICATION_REPORT.md |
| `HARDENING_REPORT.md` | 10-phase audit remediation pass | 2026-05-13 | 2026-05-14 | Implicit | Historical only | ENTERPRISE_REVALIDATION_REPORT.md |
| `ENTERPRISE_READINESS_AUDIT.md` | Enterprise audit (Score 5.2/10) | 2026-06-07 | 2026-06-07 | Implicit | No — superseded | PRODUCTION_READINESS_AUDIT.md |
| `ENTERPRISE_REVALIDATION_REPORT.md` | Phase E3 revalidation | 2026-06-07 | 2026-06-07 | Implicit | No — superseded | IMPLEMENTATION_VERIFICATION_REPORT.md |
| `IMPLEMENTATION_VERIFICATION_REPORT.md` | Disprove-completion audit for enterprise sprint | 2026-06-07 | 2026-06-07 | Implicit | No — superseded | SECURITY_AUDIT_REPORT.md (2026-06-17) |
| `SECUREDOC_CURRENT_STATE_REPORT.md` | Read-only state snapshot at sprint start | 2026-06-07 | 2026-06-07 | Implicit | Historical baseline only | Current code |
| `P0_REVALIDATION_REPORT.md` | Revalidation of 8 P0 blockers | 2026-06-08 | 2026-06-08 | Yes — RELEASE_BLOCKERS.md | Historical only | RELEASE_BLOCKERS.md (status column) |
| `PRE_PILOT_CERTIFICATION_REPORT.md` | 9-phase, 18-agent, 689-tool audit | 2026-06-08 | 2026-06-08 | Yes — RELEASE_BLOCKERS.md | Historical milestone | SECURITY_AUDIT_REPORT.md |
| `FINAL_PRELAUNCH_AUDIT.md` | Pre-launch direct code audit | 2026-06-07 | 2026-06-07 | Implicit | Historical only | SECURITY_AUDIT_REPORT.md |
| `SECURITY_VERIFICATION_AUDIT.md` | Security verification (v8.1.0) | 2026-06-07 | 2026-06-07 | Implicit | No — superseded | SECURITY_AUDIT_REPORT.md (2026-06-17) |
| `FRONTEND_ARCHITECTURE_REVIEW.md` | Frontend architecture review | Unknown | Unknown | Yes — TECHNICAL_DEBT_REGISTER.md, EXECUTIVE_SUMMARY.md | **NO — critically stale** (claims app.jsx = 6,046 lines; current reality = 5 lines) | Current source code + frontend/docs/architecture/ |
| `FRONTEND_REFACTOR_PLAN.md` | Plan to decompose ViewerScreen from app.jsx | Unknown | Unknown | Implicit | **NO — fully executed** (Sprint 4.2D completed this) | frontend/docs/reports/VIEWERSCREEN_FINAL_AUDIT.md, SPRINT4_2D_REPORT.md |
| `REPOSITORY_CLEANUP_PLAN.md` | Prior cleanup plan identifying files to delete | Unknown | Unknown | Implicit | **NO — superseded** by this governance audit | This governance report |

### 1.4 Deletion Candidates

| Path | Reason |
|---|---|
| `].md` | 31,909-byte exact duplicate of `TRACEVIEW_PILOT_DEPLOYMENT_GUIDE.md`; accidental shell artifact (`echo [...] > ].md`); confirmed identical byte count |
| `ALL_ACTION_DESIGNS.md` | 0 bytes — empty file |

---

## Part 2 — Frontend Docs (`frontend/docs/`)

### 2.1 Permanent Operational (Category A)

| Path | Purpose | Created | Last Updated | Referenced | Useful | Superseded |
|---|---|---|---|---|---|---|
| `docs/engineering/ACTION_LOG.md` | Append-only log of every file change (A-001–A-143) | 2026-06-17 | 2026-06-22 | Yes — all sprint plans reference it | **Yes — primary source of truth for what changed** | No |
| `docs/risks/RISK_REGISTER.md` | Frontend extraction risks (R-001–R-063) | 2026-06-15 | 2026-06-22 | Yes — all sprint plans reference it | Yes | No |
| `docs/decisions/DECISION_LOG.md` | Architectural decisions (D-001–D-031) | 2026-06-17 | 2026-06-22 | Yes — sprint plans reference it | Yes | No |

### 2.2 Architecture Reference (Category B)

| Path | Purpose | Created | Last Updated | Referenced | Useful | Superseded |
|---|---|---|---|---|---|---|
| `docs/architecture/ARCHITECTURE_BASELINE.md` | Baseline architecture state before extraction | 2026-06-15 est | 2026-06-22 | Yes — ARCHITECTURE_SCORECARD.md | Yes — baseline for comparison | No |
| `docs/architecture/ARCHITECTURE_SCORECARD.md` | Quality scores across all sprints (Sprint 3.3–4.2E) | 2026-06-17 | 2026-06-22 | Yes — sprint reports | Yes — shows progression | No |
| `docs/architecture/DEPENDENCY_AUDIT.md` | esbuild dependency audit | 2026-06-22 | 2026-06-22 | Yes — REPOSITORY_STABILIZATION_AUDIT.md | Yes | No |
| `docs/architecture/REPOSITORY_INVENTORY.md` | 50-file source inventory | 2026-06-22 | 2026-06-22 | Yes — multiple sprint reports | Yes | No |
| `docs/security/SECURITY_BASELINE.md` | Frontend security surface baseline (DRM, sessions, etc.) | 2026-06-17 est | 2026-06-22 | Yes — SPRINT4_3_SECURITY_HARDENING_PLAN.md | Yes | No |

### 2.3 Historical Archive (Category C)

| Path | Purpose | Created | Last Updated | Useful | Superseded |
|---|---|---|---|---|---|
| `docs/reports/SPRINT3_4_REPORT.md` | Sprint 3.4 completion report | 2026-06-17 | 2026-06-17 | Historical only | Sprint 4.2E state |
| `docs/reports/SPRINT3_5_REPORT.md` | Sprint 3.5 completion report | 2026-06-18 | 2026-06-18 | Historical only | Sprint 4.2E state |
| `docs/reports/SPRINT4_0_REPORT.md` | Sprint 4.0 completion report | 2026-06-18 est | 2026-06-22 | Historical only | Sprint 4.2E state |
| `docs/reports/SPRINT4_2D_REPORT.md` | ViewerScreen extraction summary | 2026-06-22 | 2026-06-22 | Historical milestone | No |
| `docs/reports/ANNOTATION_LAYER_READINESS_REVIEW.md` | Pre-extraction safety review | 2026-06-17 | 2026-06-17 | Historical only | Already extracted |
| `docs/reports/SCREEN_EXTRACTION_READINESS_REVIEW.md` | Pre-extraction safety review | 2026-06-18 est | 2026-06-22 | Historical only | Already extracted |
| `docs/reports/POST_SCREEN_EXTRACTION_AUDIT.md` | Post-extraction verification | 2026-06-22 | 2026-06-22 | Historical only | Sprint 4.2E audit |
| `docs/reports/BUILD_HYGIENE_AUDIT.md` | Build hygiene findings | 2026-06-22 | 2026-06-22 | Historical only | REPOSITORY_STABILIZATION_AUDIT.md |
| `docs/reports/DEAD_CODE_AUDIT.md` | Dead code findings (zero dead code) | 2026-06-22 | 2026-06-22 | Historical only | CODEBASE_GOVERNANCE_AUDIT.md |
| `docs/reports/VIEWERSCREEN_FINAL_AUDIT.md` | 62-scenario verification matrix | 2026-06-22 | 2026-06-22 | Historical milestone | No |
| `docs/engineering/REPOSITORY_STABILIZATION_AUDIT.md` | Phase 0 audit for Sprint 4.2E | 2026-06-22 | 2026-06-22 | Historical only | CODEBASE_GOVERNANCE_AUDIT.md |
| `docs/engineering/REPOSITORY_HEALTH_SCORE.md` | 97/100 score at Sprint 4.2E close | 2026-06-22 | 2026-06-22 | Historical only | No |
| `docs/engineering/DOCS_MIGRATION_LOG.md` | Record of 17 files moved to semantic subdirs | 2026-06-22 | 2026-06-22 | Historical only | ACTION_LOG entries A-131–A-136 |

### 2.4 Completed Sprint Plans (Category C — Historical)

| Path | Status | Superseded |
|---|---|---|
| `docs/engineering/SPRINT3_5_NEXT_SPRINT.md` | Completed | Sprint 3.5 executed |
| `docs/engineering/SPRINT4_2_EXECUTION_PLAN.md` | Completed | Sprint 4.2A–E executed |
| `docs/engineering/SPRINT4_2B_EXECUTION_PLAN.md` | Completed | Sprint 4.2B executed |
| `docs/engineering/SPRINT4_2C_EXECUTION_PLAN.md` | Completed | Sprint 4.2C executed |
| `docs/engineering/SPRINT4_2D_VIEWER_FINAL_PLAN.md` | Completed | Sprint 4.2D executed |
| `docs/engineering/SPRINT4_2D_IMPLEMENTATION_PROMPT.md` | Completed | Sprint 4.2D executed |
| `docs/engineering/SPRINT4_2E_REPOSITORY_STABILIZATION_PLAN.md` | Completed | Sprint 4.2E executed |
| `docs/engineering/SPRINT4_EXECUTION_PLAN.md` | Completed | All 4.x sprints executed |

### 2.5 Active Sprint Plans

| Path | Status |
|---|---|
| `docs/engineering/SPRINT4_3_SECURITY_HARDENING_PLAN.md` | **ACTIVE — next sprint** |

---

## Governance Gap

The new governance standard (docs/governance/ as home for ACTION_LOG and RISK_REGISTER) is not yet implemented. Current locations:
- ACTION_LOG → `docs/engineering/ACTION_LOG.md` (should become `docs/governance/ACTION_LOG.md`)
- RISK_REGISTER → `docs/risks/RISK_REGISTER.md` (should become `docs/governance/RISK_REGISTER.md`)
- DECISION_LOG → `docs/decisions/DECISION_LOG.md` (Category B reference; stays in docs/decisions/)

**RISK_REGISTER NAMESPACE COLLISION:** The root-level `securedoc/RISK_REGISTER.md` uses IDs R-001 to R-015 (backend/full-stack risks). The frontend `docs/risks/RISK_REGISTER.md` also starts at R-001 (frontend extraction risks through R-063). These share the same ID namespace — R-001 refers to different risks in each register. This must be resolved before the governance migration.
