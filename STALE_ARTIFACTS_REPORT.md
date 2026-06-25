# Stale Artifacts Report — Phase 2
**Date:** 2026-06-24  
**Sprint:** Repository Cleanup (Phase 2 of 7)  
**Source:** REPO_INVENTORY.md Phase 1 classification

---

## Category 1: Generated / Gitignored Artifacts

These files are explicitly in `.gitignore`. They are rebuilt on each test or build run.

| File | Type | Action |
|------|------|--------|
| `.DS_Store` (root) | macOS metadata | DELETE |
| `backend/.coverage` | Coverage binary | DELETE |
| `tests_e2e/.pytest_cache/*` | pytest cache | DELETE |
| `test_identity_thread_part8.db` (root) | SQLite test DB | DELETE |
| `test_link_service.db` (root) | SQLite test DB | DELETE |
| `test_phase5.db` (root) | SQLite test DB | DELETE |
| `test_purge_sessions.db` (root) | SQLite test DB | DELETE |
| `test_securedoc.db` (root) | SQLite test DB | DELETE |
| `test_viewer_identity.db` (root) | SQLite test DB | DELETE |
| `backend/test_identity_thread_part8.db` | SQLite test DB | DELETE |
| `backend/test_link_service.db` | SQLite test DB | DELETE |
| `backend/test_phase5.db` | SQLite test DB | DELETE |
| `backend/test_purge_sessions.db` | SQLite test DB | DELETE |
| `backend/test_requeue.db` | SQLite test DB | DELETE |
| `backend/test_requeue_processing.db` | SQLite test DB | DELETE |
| `backend/test_requeue_skip.db` | SQLite test DB | DELETE |
| `backend/test_securedoc.db` | SQLite test DB | DELETE |
| `backend/test_viewer_identity.db` | SQLite test DB | DELETE |
| `backend/test_vp_cleanup.db` | SQLite test DB | DELETE |
| `backend/test_vp_cleanup_mixed.db` | SQLite test DB | DELETE |
| `backend/test_vp_cleanup_session.db` | SQLite test DB | DELETE |

**Count:** 21 files  
**Risk:** None — all gitignored, all regenerated on next test run

---

## Category 2: Already-Staged Deletions (Pending Commit)

These files were previously deleted from disk; git is tracking the deletions as staged changes. They need a commit to finalize.

| File | Last Action |
|------|-------------|
| `ACTION_1_DESIGN.md` through `ACTION_20_DESIGN.md` (20 files) | Deleted from disk |
| `ALL_ACTION_DESIGNS.md` | Deleted from disk |
| `ENTERPRISE_READINESS_AUDIT.md` | Deleted from disk |
| `ENTERPRISE_REVALIDATION_REPORT.md` | Deleted from disk |
| `FRONTEND_REFACTOR_PLAN.md` | Deleted from disk |
| `IMPLEMENTATION_VERIFICATION_REPORT.md` | Deleted from disk |
| `SECURITY_VERIFICATION_AUDIT.md` | Deleted from disk |

**Count:** 27 files  
**Action:** Include in cleanup commit — these deletions are already staged

---

## Category 3: Prior Project Name — TRACEVIEW_* Files

These 9 files are from when the project was named "TraceView." They contain historical analysis that remains relevant as an audit trail but should not live at the repository root as active documents.

| File | Last Modified | Superseded By |
|------|--------------|--------------|
| `TRACEVIEW_ARCHITECTURE_EXTRACTION_REPORT.md` | Committed 3f69106 | `ARCHITECTURE_DECISIONS.md` |
| `TRACEVIEW_AUDIT_A.md` | Committed cc50838 | `frontend/docs/production/*` |
| `TRACEVIEW_AUDIT_B.md` | Committed cc50838 | `frontend/docs/production/*` |
| `TRACEVIEW_AUDIT_C.md` | Modified (M) | `frontend/docs/production/*` |
| `TRACEVIEW_AUDIT_D.md` | Modified (M) | `frontend/docs/production/*` |
| `TRACEVIEW_D25_VALIDATION_REPORT.md` | Modified (M) | `frontend/docs/production/*` |
| `TRACEVIEW_D2_DECISION_REPORT.md` | Modified (M) | `frontend/docs/production/*` |
| `TRACEVIEW_LAUNCH_READINESS_REPORT.md` | Modified (M) | `PRE_PILOT_CERTIFICATION_REPORT.md` |
| `TRACEVIEW_PILOT_DEPLOYMENT_GUIDE.md` | Committed | `README.md` + `start.sh` |

**Action:** Move to `archive/legacy-traceview/`

---

## Category 4: Superseded Root-Level Reports

These reports were generated at a specific point in time. Their content has been superseded by Sprint 5.x production/ docs, but they represent historical evidence.

| File | Era | Superseded By |
|------|-----|--------------|
| `API_CONTRACT_REVIEW.md` | Pre-Sprint 5 | `frontend/docs/production/API_CONSISTENCY_REVIEW.md` |
| `BACKEND_ARCHITECTURE_REVIEW.md` | Pre-Sprint 5 | `ARCHITECTURE_DECISIONS.md` |
| `DATABASE_REVIEW.md` | Pre-Sprint 5 | `frontend/docs/production/DATABASE_HARDENING_REPORT.md` |
| `EXECUTIVE_SUMMARY.md` | Pre-Sprint 5 | `SECUREDOC_CURRENT_STATE_REPORT.md` |
| `FEATURE_VERIFICATION_CHECKLIST.md` | Pre-Sprint 4.4 | `frontend/docs/certification/FEATURE_CERTIFICATION_MATRIX.md` |
| `IMPLEMENTATION_MASTER_PLAN.md` | Completed | Implementation complete |
| `SECRET_SCAN_REPORT.md` | Point-in-time | Re-scan supersedes any snapshot |
| `TOP_20_ACTIONS_TO_REACH_ENTERPRISE_GRADE.md` | Completed | All 20 actions have been actioned |
| `generate_pdf.py` | One-off | Not referenced in any source, build, or test |

**Action:** Move to `archive/root-historical/`

---

## Category 5: Browser Audit Screenshots

6 PNG screenshots from a specific browser UI audit session. Not referenced in any source, test, or documentation.

| File | Timestamp | Content |
|------|-----------|---------|
| `audit_artifacts/screenshots/000_login_forgot_password_1782228390588.png` | 1782228390 | Login page |
| `audit_artifacts/screenshots/000_login_forgot_password_validation_error_1782228403807.png` | 1782228403 | Login validation |
| `audit_artifacts/screenshots/000_login_signin_1782228309415.png` | 1782228309 | Sign-in page |
| `audit_artifacts/screenshots/000_login_signin_validation_error_1782228373312.png` | 1782228373 | Validation error |
| `audit_artifacts/screenshots/000_login_signup_1782228326352.png` | 1782228326 | Sign-up page |
| `audit_artifacts/screenshots/000_login_signup_validation_error_1782228345538.png` | 1782228345 | Sign-up validation |

**Action:** Move to `archive/browser-audit-screenshots/`

---

## Category 6: docs/ Root Directory (Sprint 2–3 Era)

`docs/audit/` and `docs/engineering/` at the repository root contain Sprint 2–3 era technical notes. All Sprint 5.x work uses `frontend/docs/` as the canonical documentation location. These are historical engineering records.

### docs/audit/ (4 files)
| File | Era |
|------|-----|
| `AUDIT_CHECKPOINT.md` | Sprint 2–3 |
| `BUG_DATABASE.md` | Sprint 2–3 |
| `MASTER_AUDIT_LOG.md` | Sprint 2–3 |
| `VISITED_ROUTES.md` | Sprint 2–3 |

### docs/engineering/ (15 files)
Sprint 2–3 phase extraction reports (`PHASE2_*_REPORT.md`), architecture scorecard, action log, sprint reports:

`ACTION_LOG.md`, `ARCHITECTURE_REFACTOR_REPORT.md`, `ARCHITECTURE_SCORECARD.md`, `CHANGELOG_AUTOGENERATED.md`, `DECISION_LOG.md`, `EXECUTION_LOG.md`, `IMPLEMENTATION_REPORT.md`, `PHASE1_EXTRACTION_REPORT.md`, `PHASE2_1_USE_TEXT_LOADER_REPORT.md`, `PHASE2_2_USE_LINKS_SIDECAR_REPORT.md`, `PHASE2_3_USE_SEARCH_HIGHLIGHTS_REPORT.md`, `PHASE2_4_2_5_HOOK_EXTRACTION_REPORT.md`, `PHASE2_6_USE_PAGE_LOADER_REPORT.md`, `PHASE2_7_EXTRACTION_READINESS_REVIEW.md`, `PHASE2_7_USE_VIEWER_SESSION_REPORT.md`, `POST_IMPLEMENTATION_REVIEW.md`, `SPRINT2_FINAL_ARCHITECTURE_AUDIT.md`, `SPRINT3_3_NEXT_SPRINT.md`, `SPRINT3_3_REPORT.md`, `SPRINT3_PHASE3_1_3_2_REPORT.md`, `TASK_PLAN.md`

**Action:** Move entire `docs/` subtree to `archive/docs-sprint2-3/`

---

## Category 7: frontend/docs/certification/ (Sprint 4.4 Era)

14 files documenting system state as of Sprint 4.4. Superseded by Sprint 5.x production/ reports.

| File | Superseded By |
|------|--------------|
| `ACTION_LOG.md` | `frontend/docs/production/ACTION_LOG.md` |
| `API_CERTIFICATION.md` | Sprint 5.3 hardening reports |
| `COMPETITIVE_FEATURE_GAPS.md` | Ongoing product strategy |
| `DATABASE_TRACE_MATRIX.md` | Sprint 5.3 database reports |
| `DEPLOYMENT_FORENSICS.md` | N/A (resolved) |
| `FEATURE_CERTIFICATION_MATRIX.md` | Sprint 5.4 verification |
| `PRODUCTION_WALKTHROUGH_MATRIX.md` | Sprint 5.3 revalidation matrix |
| `PRODUCT_REALITY_AUDIT.md` | Current product docs |
| `REMAINING_BUG_BACKLOG.md` | Items actioned |
| `SECURITY_CERTIFICATION.md` | Sprint 5.3 security revalidation |
| `SPRINT4_4_CERTIFICATION_REPORT.md` | Sprint 5.3A certification |
| `STORAGE_RUNTIME_TRACE.md` | Storage architecture stable |
| `TOP_20_FIXES_BEFORE_BETA.md` | Items actioned |
| `UI_CERTIFICATION.md` | Sprint 5.3 frontend hardening |

**Action:** Move to `archive/sprint4-4-certification/`

---

## Category 8: Scattered Historical Sprint Reports

Individual report files across `frontend/docs/` subdirectories that are from Sprint 3–4 era:

| File | Era | Action |
|------|-----|--------|
| `frontend/docs/engineering/BUILD_HYGIENE_AUDIT.md` | Sprint 3-4 | ARCHIVE |
| `frontend/docs/engineering/QUICK_SHARE_IMPLEMENTATION_PLAN.md` | Sprint 4.x completed | ARCHIVE |
| `frontend/docs/engineering/REPOSITORY_HEALTH_SCORE.md` | Point-in-time | ARCHIVE |
| `frontend/docs/engineering/REPOSITORY_STABILIZATION_AUDIT.md` | Completed | ARCHIVE |
| `frontend/docs/engineering/SPRINT4_3_SECURITY_HARDENING_PLAN.md` | Sprint 4.3 completed | ARCHIVE |
| `frontend/docs/implementation/SPRINT4_8A_IMPLEMENTATION_REPORT.md` | Sprint 4.8A completed | ARCHIVE |
| `frontend/docs/product/SPRINT4_8_RECOMMENDATION.md` | Sprint 4.8 completed | ARCHIVE |
| `frontend/docs/reports/BUILD_HYGIENE_AUDIT.md` | Historical | ARCHIVE |
| `frontend/docs/reports/POST_SCREEN_EXTRACTION_AUDIT.md` | Completed | ARCHIVE |
| `frontend/docs/reports/SCREEN_EXTRACTION_READINESS_REVIEW.md` | Completed | ARCHIVE |
| `frontend/docs/reports/SPRINT3_4_REPORT.md` | Sprint 3.4 completed | ARCHIVE |
| `frontend/docs/reports/SPRINT3_5_REPORT.md` | Sprint 3.5 completed | ARCHIVE |
| `frontend/docs/reports/SPRINT4_0_REPORT.md` | Sprint 4.0 completed | ARCHIVE |
| `frontend/docs/reports/SPRINT4_2D_REPORT.md` | Sprint 4.2D completed | ARCHIVE |
| `frontend/docs/validation/SPRINT4_6_PRODUCT_EXPERIENCE_PROPOSAL.md` | Sprint 4.6 completed | ARCHIVE |

**Action:** Move to `archive/sprint3-4-reports/`

---

## Category 9: Duplicate Files (Same Name, Multiple Locations)

These files exist under multiple paths. None are identical — each has different content for different purposes. Keeping all; noting duplication for awareness.

| Filename | Locations | Note |
|----------|-----------|------|
| `RISK_REGISTER.md` | Root, governance, production, risks | Each covers a different scope; KEEP all |
| `ACTION_LOG.md` | docs/engineering, frontend/docs/engineering, governance, production | Each covers a different sprint; KEEP all |

---

## Summary

| Category | Files | Recommended Action |
|----------|-------|-------------------|
| Generated/gitignored artifacts | 21 | DELETE |
| Staged deletions (pending commit) | 27 | COMMIT (already deleted) |
| TRACEVIEW_* legacy files | 9 | ARCHIVE → archive/legacy-traceview/ |
| Superseded root reports | 9 | ARCHIVE → archive/root-historical/ |
| Browser audit screenshots | 6 | ARCHIVE → archive/browser-audit-screenshots/ |
| docs/ Sprint 2–3 subtree | 25 | ARCHIVE → archive/docs-sprint2-3/ |
| frontend/docs/certification/ Sprint 4.4 | 14 | ARCHIVE → archive/sprint4-4-certification/ |
| Scattered Sprint 3–4 reports | 15 | ARCHIVE → archive/sprint3-4-reports/ |
| Duplicates (multi-location same name) | 8 | KEEP all (different content) |

**Total proposed ARCHIVE moves:** 78 files  
**Total proposed DELETEs:** 21 files  
**Total staged commits:** 27 files  
**No source code, migrations, tests, or active production docs affected.**
