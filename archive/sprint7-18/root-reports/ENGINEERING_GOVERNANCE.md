# Engineering Governance — Sprint V6.0

Repo-wide directory review: for every directory, why it exists, whether it should, whether it's placed correctly, and whether it can be simplified. Includes Phase 8 (documentation canonicalization) since the two problems overlap almost entirely — most of the repo's directory-hygiene debt *is* duplicate/stale documentation.

## Repo root

| Path | Why it exists | Should it exist | Belongs here | Simplify |
|---|---|---|---|---|
| `.claude/`, `.github/` | Tooling config, CI workflow | Yes | Yes | No |
| `backend/`, `frontend/` | Service + client source | Yes | Yes | No |
| `docs/` | Long-term documentation | Yes, but bloated — see §Documentation below | Yes | Consolidate (below) |
| `scripts/` | `backup.sh`/`restore.sh`, referenced by `docs/operations/BACKUP_RESTORE.md` | Yes | Yes | No — documented, just not CI-wired; not dead |
| `tests_e2e/` | Cross-stack API/UI/service e2e tests, distinct from `backend/tests/`'s unit/integration/regression | Yes | Yes | Minor: `test_link_service.py` exists in both trees — confirm it isn't literal duplicate coverage before next touching either |
| `archive/` | Historical sprint reports/screenshots | Yes, as a dead-storage bucket | Yes | `sprint5-6/` holds 149 of 226 archived files with internal near-duplicate nesting (`frontend-docs/production/production/...`) — worth a cleanup pass, low urgency |
| `audit_artifacts/` | Current-cycle QA reports (20 files) + empty `screenshots/{before,after}/` | Reports: yes. Screenshot subdirs: no, empty | Borderline — conceptually overlaps `archive/browser-audit-screenshots/` (which holds the real screenshots) | Delete the empty `screenshots/` subtree; `reports/` has internal `V34`-suffixed duplicates (`CHANGELOG.md`/`CHANGELOG_V34.md`, `FIX_DATABASE.md`/`FIX_DATABASE_V34.md`, etc.) worth consolidating |
| **17 loose sprint-report `.md` files at root** (`ENGINEERING_TRIAGE.md`, `VERIFIED_ISSUES.md`, `FIX_LOG.md`, `SECURITY_HARDENING_PLAN.md`, `PRODUCT_PROPOSAL.md`, `COMMIT_SUMMARY.md`, `SPRINT7_*.md`, `ARCHITECTURE_SCORECARD.md`, `WORKFLOW_COMPLETENESS.md`, `SECURITY_STATUS.md`, `REPOSITORY_HEALTH.md`, plus `DEPLOYMENT_VERIFICATION.md`/`FIX_IMPLEMENTATION.md`/`REGRESSION_REPORT.md`/`ROOT_CAUSE_ANALYSIS.md` from an unrelated in-progress task) | Active work product from recent sprints | Temporarily, yes — while the work they document is still in-flight/uncommitted | **No** — root should hold only perennial files (README, LICENSE, CONTRIBUTING, SECURITY, CHANGELOG) | **Recommended standing rule**: once a sprint's changes are committed, move its point-in-time reports into `archive/` (or fold durable decisions into the matching `docs/` canonical doc) rather than leaving them at root indefinitely. Not done this sprint — these are still active/referenced. |
| `frontend/dist/app.bundle.js` (git-tracked) | `.gitignore` has `dist/` ignored, then explicitly re-included via `!frontend/dist/` | **No** — built artifacts shouldn't be committed | N/A | Recommend removing the `!frontend/dist/` override and untracking the bundle, with CI building it on deploy instead. **Not done this sprint** — this is a build/deploy-pipeline change outside "fix only low-risk architectural issues," and untracking a file the deploy process may currently depend on needs a deliberate decision, not a silent removal. |
| 5 untracked `test_*.db` files, `frontend/.pytest_cache`, `frontend/docs/` (empty) | Local dev/test leftovers (`.db` files are `.gitignore`d and confirmed untracked; `frontend/.pytest_cache` is evidence `pytest` was once run from inside `frontend/` by mistake; `frontend/docs/` is a stray empty directory) | No | No | Low-risk cleanup, but these are local/untracked — nothing to fix in the repo itself. `frontend/docs/` empty directory removed this sprint (see below). |
| Binary/exported artifacts check | Confirmed via repo-wide search: no `.zip`/`.pdf`/`.pages`/`.har` files exist inside the repo (the ones the team was tracking — `tracelink.pdf`, `traceview.zip`, etc. — live only in `~/Downloads`, outside git). `DATABASE_TRACE_MATRIX.md`/`STORAGE_RUNTIME_TRACE.md` do exist in-repo but are already correctly archived at `archive/sprint4-4-certification/`. | N/A | N/A | Clean — no action needed |

**Fixed this sprint**: removed `frontend/docs/` — not a single empty directory as initially reported by research, but a 3-level-deep tree (`certification/`, `governance/`, `implementation/` subdirectories) containing zero files at any level. Verified empty with `find -type f` before removal.

## Documentation canonicalization (Phase 8)

Target: exactly one canonical document per category (Architecture, Deployment, Security, API, Database, Runbook, Incident Response, Backup, Release, Developer Guide).

| Category | Verdict | Detail |
|---|---|---|
| Architecture | Needs consolidation | `docs/architecture/ARCHITECTURE.md` and `OVERVIEW.md` both cover system topology/security model with real content differences (OVERVIEW has a date/version stamp and frontend/data-flow detail; ARCHITECTURE has DB-schema/observability detail and no date stamp). Neither is a strict subset of the other. |
| Deployment | Single canonical | `docs/deployment/DEPLOYMENT.md` (dated 2026-06-30, v8.1.0) |
| Security | Mostly fine, but disconnected | `docs/security/SECURITY.md` (architecture-level) is canonical; root `SECURITY.md` (vulnerability-disclosure policy) is a legitimately distinct scope, not a duplicate. `SECURITY_HARDENING_PLAN.md`/`SECURITY_STATUS.md` are point-in-time sprint artifacts, not merged into the canonical doc — should eventually fold their durable conclusions in. |
| API | Single canonical, possibly stale | `docs/api/API.md` is dated 2024-01 — the oldest date found anywhere in the doc tree, next to peers stamped 2026-06/07. Worth a refresh pass to confirm it still matches the current route surface (this sprint added new event types/indexes but no new routes, so no urgent drift, but the date gap itself is a red flag for the next person who touches the API). |
| Database | **Missing** | No canonical full-schema/ERD document exists — only `docs/reading_analytics/DATABASE_SCHEMA.md` (subsystem-scoped) and a 9-row table embedded in `ARCHITECTURE.md`. Given the repo now has 27 migrations, a proper schema reference is overdue. |
| Runbook | Single canonical | `docs/operations/RUNBOOK.md` |
| Incident Response | Single canonical | `docs/operations/INCIDENT_RESPONSE.md` |
| Backup | Single canonical | `docs/operations/BACKUP_RESTORE.md` |
| Release | **Needs consolidation, most severe finding** | 14 overlapping files in `docs/release/` plus two competing CHANGELOGs (root `CHANGELOG.md`, actively maintained, vs. `docs/engineering/CHANGELOG.md`, stuck at v3.2.1). `ZERO_DEFECT_CERTIFICATION.md` is stamped **v3.2.2** sitting alongside `RC1_*`/`FINAL_RELEASE_NOTES.md` peers stamped v8.1.0 — a five-major-version-stale document presented as current release documentation. |
| Developer Guide | Single canonical | `docs/development/DEVELOPER_GUIDE.md` + `CONTRIBUTING.md` (distinct, non-overlapping scopes) |

**Stale self-referential doc found**: `archive/README.md` claims canonical docs live at `frontend/docs/production/`, `frontend/docs/governance/`, `frontend/docs/security/`, `frontend/docs/product/`, plus root `ARCHITECTURE_DECISIONS.md`/`RISK_REGISTER.md` — **none of these exist**; `docs/governance/ARCHIVED_FILES.md` confirms the last two were themselves archived. The archive's own index document is stale.

**Broken/archive-pointing cross-references found**: `CHANGELOG.md:110` links to `archive/sprint5-6/frontend-docs/certification/` from the active root changelog — treating an archived path as a live reference target.

**Not consolidated this sprint** — file moves/merges across `docs/` were judged too broad a change to make safely without the original authors confirming which content in each overlapping pair is authoritative (e.g., merging `ARCHITECTURE.md` + `OVERVIEW.md` risks silently dropping real content from one side). This is exactly the class of "document major refactors instead of implementing them" the mission calls for. **Recommended follow-up, in priority order**:
1. Consolidate `docs/release/`'s 14 files down to one canonical release doc + a changelog; retire `ZERO_DEFECT_CERTIFICATION.md` (5 major versions stale) and `docs/engineering/CHANGELOG.md` (superseded by root).
2. Merge `ARCHITECTURE.md` + `OVERVIEW.md`, keeping the union of both.
3. Write a canonical `docs/architecture/DATABASE.md` (currently missing entirely).
4. Fix `archive/README.md`'s dead pointers or delete the file if the archive doesn't need an index.
5. Refresh `docs/api/API.md`'s date stamp after confirming it against the current route surface.

## Root README accuracy check

`README.md` was spot-checked against current reality: tech stack (FastAPI + async SQLAlchemy, PostgreSQL 16, Redis 7, Celery, React 18) and migration count both still match. No stale references found in it.
