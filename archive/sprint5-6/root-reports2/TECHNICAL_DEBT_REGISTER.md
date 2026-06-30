# Technical Debt Register

Consolidates code-smell findings from FRONTEND_ARCHITECTURE_REVIEW.md and BACKEND_ARCHITECTURE_REVIEW.md into a single prioritized register. Severity = impact on future development velocity/risk, not current correctness — none of these are bugs.

| Item | File:Line | Severity | Estimated Fix Effort | Priority |
|---|---|---|---|---|
| `annotations.py` has no service layer — 6 helper functions + 3 inline CSV generators live in the router | `app/routers/annotations.py` (1,285 lines total) | High — highest-churn file in the repo, every feedback feature change pays this tax | 1-2 days (extract `annotation_service.py`) | **P1** |
| `viewer.py` has no service layer — cache/permission/streaming logic inlined per-route | `app/routers/viewer.py` (1,203 lines total) | High | 1-2 days (extract `viewer_service.py`) | **P1** |
| `ViewerScreen` god component — 53 `useState`, 1,348 lines | `frontend/src/app.jsx:1238-2586` | High — hardest component to safely modify | 3-5 days (decompose into ~6-8 components) | **P1** |
| `AccessScreen` god component — 35 `useState`, 720 lines, 4 unrelated tabs merged | `frontend/src/app.jsx:4010-4730` | Medium-High | 2-3 days (split along existing tab boundaries) | **P1** |
| 10 route handlers exceed 100 lines (3 exceed 150) | `viewer.py`, `documents.py`, `analytics.py`, `annotations.py` (full table in BACKEND_ARCHITECTURE_REVIEW.md) | Medium | Resolves naturally once the two service-layer extractions above land | **P2** |
| 401-handler duplicated ~30× | `frontend/api.js` (all 41 exported functions) | Medium — every fetch call is a copy-paste site for auth bugs | <1 day (extract `_authFetch` wrapper) | **P2** |
| Blob-download boilerplate duplicated 5× | `frontend/api.js:401-409,621-629,730-740,749-757,777-785` | Low-Medium | <1 day (extract `_downloadBlob`) | **P3 (quick win)** |
| Feedback filter-object construction duplicated 2× | `frontend/app.jsx:4076-4084,4414-4420` | Low-Medium — already bit us once (grew in lockstep when `reviewer` field was added to both call sites during the CSV redesign) | <1 day (extract `buildFeedbackFilters`) | **P3 (quick win)** |
| Model/migration index declaration drift — 8 indexes exist in DB but undeclared in SQLAlchemy models | `app/models/document.py`, `event.py`, `billing.py`, `annotation.py`, `session.py` (full list in DATABASE_REVIEW.md Finding 1) | Low (no runtime impact) but blocks safe use of Alembic autogenerate | 30 min | **P3 (quick win)** |
| Hardcoded magic strings for status/role/annotation-type/screen-name | `frontend/app.jsx` (20+ sites for annotation type alone) | Low — typo-shaped outage risk, no compile-time check | 1 day (introduce 4 const objects, find/replace) | **P3** |
| Admin/org-role authorization checks live in function bodies, not `Depends` | `app/routers/admin.py:15-78`, `app/routers/orgs.py` | Low (functionally correct) — auditability/contract-clarity gap | 1 day (`require_org_role()` dependency factory) | **P3** |
| List-endpoint response shape inconsistency (6 different wrapper/pagination conventions) | 8 endpoints across `documents.py`, `groups.py`, `links.py`, `webhooks.py`, `analytics.py`, `admin.py`, `annotations.py` | Low today, compounds with every new endpoint that copies an inconsistent precedent | Ongoing — standardize new endpoints now, backfill opportunistically | **P3** |
| Constraint-naming fragility (auto-generated Postgres constraint name hardcoded in a later migration) | `backend/alembic/versions/002`, `005` | Low — only affects fresh-install migration runs | N/A — fix forward only (always name new constraints) | **P3** |
| Frontend has zero test framework/files | `frontend/package.json`, entire `frontend/` tree | High (risk, not "debt" in the refactor sense) — see PRODUCTION_READINESS_AUDIT.md Testability score | 2-3 days to stand up vitest + first critical-path suite | **P1** |
| `tests_e2e/` orphaned — not wired into Makefile/CI | repo root, 23 files | Medium — either dead investment or a silent coverage gap | 0.5-1 day to triage (wire in or delete) | **P2** |
| `requeue_orphaned_uploads()` and `deliver_webhook()` lack direct/real-payload tests | `app/workers/tasks.py`, `app/workers/webhook_tasks.py` | Medium — both are recovery/retry paths, exactly the code that's hardest to debug live if untested | 1-2 days | **P2** |

## Net Refactor Estimate

Per the backend architecture agent's analysis: extracting `annotation_service.py` and `viewer_service.py` is estimated at **~1,000 LOC reduction in routers, +600 LOC in services = net -400 LOC** with significantly improved testability (services become unit-testable without the HTTP layer). This is the single highest-leverage structural change in the repository.
