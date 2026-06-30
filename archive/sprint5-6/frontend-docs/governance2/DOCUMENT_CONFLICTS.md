# Document Conflicts Report
Repository Governance Audit — Phase 3
Date: 2026-06-22

---

## Summary

11 conflicts identified. Classified by type and severity.

| ID | Type | Severity | Documents Involved |
|---|---|---|---|
| C-001 | Stale State Claim | **CRITICAL** | FRONTEND_ARCHITECTURE_REVIEW.md vs current codebase |
| C-002 | Obsolete Recommendation | **HIGH** | FRONTEND_REFACTOR_PLAN.md vs Sprint 4.2D completion |
| C-003 | ID Namespace Collision | **HIGH** | root/RISK_REGISTER.md vs frontend/docs/risks/RISK_REGISTER.md |
| C-004 | Unresolved Security Blocker | **HIGH** | TRACEVIEW_AUDIT_B.md (live credentials) vs RELEASE_BLOCKERS P0-2/P0-3 |
| C-005 | Duplicate Document | **MEDIUM** | REPOSITORY_CLEANUP_PLAN.md (root) vs this governance audit |
| C-006 | Stale Status | **MEDIUM** | IMPLEMENTATION_MASTER_PLAN.md / IMPLEMENTATION_PROGRESS.md status claims |
| C-007 | Incomplete Record | **MEDIUM** | CHANGELOG_ENTERPRISE.md (Actions 1–5 only) vs IMPLEMENTATION_PROGRESS.md (Phase 1+2 complete) |
| C-008 | Unverified Fix Claim | **MEDIUM** | RELEASE_BLOCKERS P0-1 "FIXED in this commit" — commit status unknown |
| C-009 | Superseded Security Audit | **LOW** | SECURITY_VERIFICATION_AUDIT.md (2026-06-07) vs SECURITY_AUDIT_REPORT.md (2026-06-17) |
| C-010 | Superseded Architecture Claim | **LOW** | Multiple audit docs describing 6,046-line / 2,581-line app.jsx |
| C-011 | Superseded Cleanup Plan | **LOW** | Root REPOSITORY_CLEANUP_PLAN.md still marks some files as "N — needs review" that are now clearly deletable |

---

## C-001 — Stale State Claim (CRITICAL)

**Documents:** `FRONTEND_ARCHITECTURE_REVIEW.md`
**Conflict:** Document states "The entire frontend is two files: `frontend/src/app.jsx` (**6,046 lines**) and `frontend/api.js` (**797 lines**)."
**Current reality:** `app.jsx` is 5 lines (entry point only) following Sprint 4.2D extraction. The 50-file extracted structure renders every finding in FRONTEND_ARCHITECTURE_REVIEW.md invalid — the "god component" ViewerScreen, the "169 useState calls," the "duplicated fetch boilerplate" are all now in separate files with different characteristics.
**Risk:** Any engineer reading FRONTEND_ARCHITECTURE_REVIEW.md to understand the frontend will build a fundamentally wrong mental model. The document is not just stale — it actively misleads.
**Resolution:** Delete FRONTEND_ARCHITECTURE_REVIEW.md. Replace with reference to `docs/architecture/ARCHITECTURE_BASELINE.md` and `docs/architecture/REPOSITORY_INVENTORY.md`.

---

## C-002 — Obsolete Recommendation (HIGH)

**Documents:** `FRONTEND_REFACTOR_PLAN.md`
**Conflict:** Document recommends "Decompose ViewerScreen into ~6–8 focused components" from `app.jsx` lines 1238–2581. Status: "Analysis complete. No code changed yet."
**Current reality:** ViewerScreen was extracted from app.jsx in Sprint 4.2D (A-114). The extraction is complete. The plan describes a problem that no longer exists and a task that has already been done.
**Risk:** If treated as an active plan, an engineer would re-run the extraction on already-extracted code, or be confused about the repository's current state.
**Resolution:** Delete FRONTEND_REFACTOR_PLAN.md. The execution record lives in `docs/reports/SPRINT4_2D_REPORT.md` and `docs/reports/VIEWERSCREEN_FINAL_AUDIT.md`.

---

## C-003 — Risk Register ID Namespace Collision (HIGH)

**Documents:** `securedoc/RISK_REGISTER.md` (root) and `frontend/docs/risks/RISK_REGISTER.md`
**Conflict:** Both registers use the R-001, R-002, ... ID numbering scheme. As of this audit:
- Root register: R-001 = "HSTS locks users out on HTTP-only deployment" (backend/infrastructure risk)
- Frontend register: R-001 = "C/mono token object: 47 C keys used across all components" (frontend extraction risk)
Both are active documents. The same ID maps to completely different risks in each.
**Risk:** Any cross-document reference to "R-001" is ambiguous. If the registers are ever consolidated, duplicate IDs will silently overwrite each other.
**Resolution:** Before consolidation, prefix all root register IDs as `BE-R-001` (backend) and all frontend register IDs as `FE-R-001` (frontend). The new unified governance register should use a `RISK-` prefix to avoid collision with either legacy set.

---

## C-004 — Unresolved Security Blocker — Live Credentials in Tracked File (HIGH)

**Documents:** `TRACEVIEW_AUDIT_B.md`, `RELEASE_BLOCKERS.md` (P0-2, P0-3), `SECRET_ROTATION_RUNBOOK.md`
**Conflict:** RELEASE_BLOCKERS.md identifies two P0 blockers:
- P0-2: "TRACEVIEW_AUDIT_B.md tracked at HEAD in a public repo contains the live Supabase anon key and project URL."
- P0-3: "Same Supabase credentials appear in 3 historical commits (ffac077, 704ca80, cc50838) in the public repo."
A `SECRET_ROTATION_RUNBOOK.md` was created to address this. However, as of this audit, `TRACEVIEW_AUDIT_B.md` still exists at `securedoc/TRACEVIEW_AUDIT_B.md` and still contains:
```
content="https://zznenaqcvzxtqxzilpyh.supabase.co"
content="sb_publishable_uTcTOZC9FjEP0VrGQefMkQ_j2XFe1Rc"
```
**Risk:** If the repo is or was ever public, these credentials were exposed. The `sb_publishable_` prefix suggests this is a Supabase anon/publishable key (intended to be public). However, the SECRET_ROTATION_RUNBOOK.md treats it as compromised and requires rotation. The runbook execution status is unknown.
**Resolution:** (1) Verify whether SECRET_ROTATION_RUNBOOK.md steps have been completed. (2) Delete TRACEVIEW_AUDIT_B.md immediately. (3) Verify git history scrub was completed per P0-3.
**NOTE:** This is a documentation governance report only. Do not resolve the credential issue here — it requires separate user action.

---

## C-005 — Duplicate Cleanup Plan (MEDIUM)

**Documents:** `securedoc/REPOSITORY_CLEANUP_PLAN.md` (root, prior audit) vs `securedoc/frontend/docs/governance/REPOSITORY_CLEANUP_PLAN.md` (this governance audit)
**Conflict:** The root-level plan already identified many of the same deletion candidates (TRACEVIEW_AUDIT_A–D, ACTION_*_DESIGN.md files, ].md, ALL_ACTION_DESIGNS.md). However, it was never actioned. Now a more comprehensive governance plan supersedes it.
**Resolution:** Delete the root `REPOSITORY_CLEANUP_PLAN.md` after this governance audit is approved and actioned. The governance plan is the authoritative version.

---

## C-006 — Stale Status in Living Planning Docs (MEDIUM)

**Documents:** `IMPLEMENTATION_MASTER_PLAN.md`, `IMPLEMENTATION_PROGRESS.md`
**Conflict:** Both documents show:
- Phase 3 (Product Completeness, Actions 11–15): "🔄 In Progress"
- Phase 4 (Enterprise, Actions 16–19): "⏳ Pending"
- Phase 5 (SOC2): "⏳ Pending"
Last updated: 2026-06-07 (15 days stale as of this audit on 2026-06-22).
Individual ACTION_*_DESIGN.md files show:
- Actions 10–11 (PPTX/XLSX): appear complete per ALL_ACTION_DESIGNS.md aggregate
- Action 12 (Time-on-Page Analytics): "COMPLETE"
- Actions 13–15, 17–20: "IN PROGRESS"
**Risk:** Planning documents claiming "in progress" state for items that may now be complete, or complete items not reflected, makes sprint planning unreliable.
**Resolution:** Update IMPLEMENTATION_PROGRESS.md before using it for any future sprint planning. Flag as stale pending update.

---

## C-007 — Incomplete Changelog (MEDIUM)

**Documents:** `CHANGELOG_ENTERPRISE.md`, `IMPLEMENTATION_PROGRESS.md`
**Conflict:** CHANGELOG_ENTERPRISE.md records only Actions 1–5 (Phase 1 Security Critical). IMPLEMENTATION_PROGRESS.md claims Phase 2 (Actions 6–9: Prometheus, OpenTelemetry, CDN offload, streaming downloads) is also "✅ Complete." No CHANGELOG entries exist for Actions 6–9.
**Risk:** CHANGELOG_ENTERPRISE.md is incomplete and cannot be used as a reliable audit trail for what was changed in the backend transformation sprint.
**Resolution:** Either complete CHANGELOG_ENTERPRISE.md with Actions 6–9 entries, or explicitly mark it as "Phase 1 only — see git log for Phases 2–5."

---

## C-008 — Unverified Fix Claim (MEDIUM)

**Documents:** `RELEASE_BLOCKERS.md`
**Conflict:** P0-1 reads: "Migration 020 re-creates `ix_organizations_slug`... **FIXED in this commit.**" However, as of this audit, nothing has been committed. The git status from the Sprint 4.2E audit (2026-06-22) shows substantial unstaged changes and untracked files. The phrase "in this commit" is ambiguous — it may mean the commit that generated the RELEASE_BLOCKERS.md report, which may or may not be the current HEAD.
**Risk:** P0-1 may appear resolved when it actually requires verification against the current deployed migration chain.
**Resolution:** Run `alembic heads` or inspect `alembic/versions/020_add_performance_indexes.py` to verify the fix is present.

---

## C-009 — Superseded Security Audit (LOW)

**Documents:** `SECURITY_VERIFICATION_AUDIT.md` (2026-06-07) vs `SECURITY_AUDIT_REPORT.md` (2026-06-17)
**Conflict:** Two security audit documents covering overlapping scope, 10 days apart. The 2026-06-17 audit is more recent, more evidence-based (every finding cites file:line), and covers the same authentication, session, SSRF, and injection surface areas.
**Resolution:** SECURITY_VERIFICATION_AUDIT.md is superseded. Archive only; use SECURITY_AUDIT_REPORT.md as the active security reference.

---

## C-010 — Superseded Architecture Claims (LOW)

**Documents:** Multiple audit docs reference `app.jsx` line counts that no longer exist.
**Affected:**
- `TRACEVIEW_AUDIT_A.md`: references app.jsx state as of 2026-06-01
- `PRE_PILOT_CERTIFICATION_REPORT.md`: references app.jsx state at 2026-06-08 (pre-extraction, ~882 lines)
- `FRONTEND_ARCHITECTURE_REVIEW.md`: claims 6,046 lines (C-001, more severe)
- `FEATURE_VERIFICATION_CHECKLIST.md`: frontend column describes old monolithic app.jsx
**Risk:** These are low risk because they are historical reports and should be read as such. Risk elevates if treated as current state.
**Resolution:** Archive these docs with a clear "HISTORICAL — reflects state before Sprint 3.3–4.2D extraction" header.

---

## C-011 — Prior Cleanup Plan Left Incomplete (LOW)

**Documents:** `securedoc/REPOSITORY_CLEANUP_PLAN.md`
**Conflict:** The prior cleanup plan recommended deleting TRACEVIEW_AUDIT_A–D, ACTION_*_DESIGN.md files, ].md, and ALL_ACTION_DESIGNS.md. Some files it marked as "N — needs review" (ARCHITECTURE_DECISIONS.md, RISK_REGISTER.md, etc.) have now been reviewed. The plan was never executed.
**Risk:** Prior cleanup plan creates the impression that cleanup was planned and actioned when it was not.
**Resolution:** This governance audit supersedes it. Delete root REPOSITORY_CLEANUP_PLAN.md after this audit is approved.

---

## Conflicts Requiring User Action (Not Auto-Resolvable)

| Conflict | Required Action | Owner |
|---|---|---|
| C-004 | Verify SECRET_ROTATION_RUNBOOK.md was executed; delete TRACEVIEW_AUDIT_B.md; confirm git history scrub | User |
| C-008 | Verify P0-1 migration fix is present in deployed code | User |
| C-006 | Update IMPLEMENTATION_PROGRESS.md with current action statuses | User |
| C-007 | Complete CHANGELOG_ENTERPRISE.md for Actions 6–20 | User |
