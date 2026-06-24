# Executive Summary — Enterprise Production Audit

Synthesizes: PRODUCTION_READINESS_AUDIT.md, REPOSITORY_CLEANUP_PLAN.md, FEATURE_VERIFICATION_CHECKLIST.md, TECHNICAL_DEBT_REGISTER.md, SECURITY_AUDIT_REPORT.md, SYSTEM_DESIGN_REVIEW.md, DATABASE_REVIEW.md, API_CONTRACT_REVIEW.md, FRONTEND_ARCHITECTURE_REVIEW.md, BACKEND_ARCHITECTURE_REVIEW.md.

**Bottom line:** No critical security vulnerabilities, no broken features, no data-loss risks were found. The codebase is in materially better shape than a typical "stop and audit" trigger implies — this is a hardening and debt-reduction pass, not a firefight. The two real risk items (PII retention gap, in-process rate limiting that breaks under horizontal scaling) are both well-understood, narrowly scoped fixes.

## Top 10 P0 (Critical) Issues

None found. No P0 issues were identified anywhere across all 10 deep-dive reports — no critical RCE, SQL injection, auth bypass, plaintext secrets in the repo, data corruption, or broken core feature. This is itself a notable finding and should be stated plainly to stakeholders rather than manufacturing severity where none exists.

## Top 20 P1 (High) Issues

1. **`viewer_profiles.email` has no retention/cleanup path** — global PII persists indefinitely after document/link deletion. (DATABASE_REVIEW.md Finding 2, SECURITY_AUDIT_REPORT.md Finding 8)
2. **In-process rate limiting breaks at horizontal scale** — `N × limit` instead of a true global limit once `api` has >1 replica. (SECURITY_AUDIT_REPORT.md Finding 6, SYSTEM_DESIGN_REVIEW.md)
3. **`viewer_cache.py` is in-process, not Redis-backed** — same multi-replica correctness gap as #2, affects session/link cache consistency. (SYSTEM_DESIGN_REVIEW.md)
4. **`annotations.py` (1,285 lines) has no service layer** — highest-churn file in the repo with all business logic inlined in route handlers. (BACKEND_ARCHITECTURE_REVIEW.md Finding 1)
5. **`viewer.py` (1,203 lines) has no service layer** — same pattern, `download_document` alone is 179 lines. (BACKEND_ARCHITECTURE_REVIEW.md Finding 2)
6. **Frontend has zero test framework and zero test files** — security-relevant permission enforcement (`can_download`/`can_print`/`can_copy`) has no regression coverage. (FRONTEND_ARCHITECTURE_REVIEW.md)
7. **`ViewerScreen` god component** — 53 `useState` hooks, 1,348 lines, hardest component in the app to safely change. (FRONTEND_ARCHITECTURE_REVIEW.md)
8. **`AccessScreen` god component** — 35 `useState` hooks, 4 unrelated features merged into one component. (FRONTEND_ARCHITECTURE_REVIEW.md)
9. **No container/seccomp sandbox for the LibreOffice conversion subprocess** — env/macro hardening present but no isolation if LibreOffice itself has an exploitable bug. (SECURITY_AUDIT_REPORT.md §4)
10. **`sdoc_session` cookie `SameSite` attribute unverified** — needs direct confirmation in the `Set-Cookie` issuance path. (SECURITY_AUDIT_REPORT.md Finding 7)
11. **Prod-default-secret-rejection startup check is itself untested** — a future refactor of `main.py` could silently drop it. (SECURITY_AUDIT_REPORT.md Finding 5)
12. **`requeue_orphaned_uploads()` has zero test coverage** — the recovery path for stuck uploads, silent failure mode if broken. (FEATURE_VERIFICATION_CHECKLIST.md)
13. **`deliver_webhook()` only ever tested via mocks** — retry/backoff/dead-letter logic has no real end-to-end coverage. (FEATURE_VERIFICATION_CHECKLIST.md)
14. **`api_keys.py` has no dedicated test file** — user-facing CRUD with real security implications. (FEATURE_VERIFICATION_CHECKLIST.md)
15. **`groups.py` has no dedicated test file.** (FEATURE_VERIFICATION_CHECKLIST.md)
16. **Single Celery Beat instance with no liveness alerting** — silent stop of `purge_stale_sessions`/`requeue_orphaned_uploads` if Beat dies and doesn't restart promptly. (SYSTEM_DESIGN_REVIEW.md)
17. **`tests_e2e/` (23 files) orphaned, not wired into Makefile/CI** — either dead investment or a silent coverage gap; needs triage either direction. (REPOSITORY_CLEANUP_PLAN.md)
18. **Watermark feature only has visual-text assertions, no snapshot test.** (FEATURE_VERIFICATION_CHECKLIST.md)
19. **`admin.py` and audit-log feature have no dedicated test file**, covered only incidentally. (FEATURE_VERIFICATION_CHECKLIST.md)
20. **Admin/org role checks live in function bodies, not declarative `Depends`** — correct today, invisible to API-contract tooling, fragile to future refactors. (SECURITY_AUDIT_REPORT.md Finding 1, API_CONTRACT_REVIEW.md §3)

## Quick Wins (<1 day each)

- Extract `_downloadBlob()` helper, collapse 5 duplicate copies in `api.js`. (TECHNICAL_DEBT_REGISTER.md)
- Extract `buildFeedbackFilters()` helper, collapse 2 duplicate copies in `app.jsx`. (TECHNICAL_DEBT_REGISTER.md)
- Backfill 8 missing `__table_args__` index declarations across 5 model files (no runtime change, fixes Alembic-autogenerate safety). (DATABASE_REVIEW.md Finding 1)
- Archive 26 stale root-level markdown files into `archive/`; delete 4 empty/junk files (`200`, `404`, `ALL_ACTION_DESIGNS.md`, `].md`). (REPOSITORY_CLEANUP_PLAN.md)
- Add a regression test asserting the app fails to boot under `ENV=production` with default secrets. (SECURITY_AUDIT_REPORT.md Finding 5)
- Add a test for `requeue_orphaned_uploads()`.

## Medium Wins (<1 week each)

- Extract `_authFetch()` wrapper in `api.js`, collapsing the 30× duplicated 401-handling pattern.
- Add `viewer_profiles` cleanup pass to `app/workers/cleanup.py`.
- Add `require_org_role()` dependency factory; migrate `admin.py`/`orgs.py` checks to it.
- Stand up vitest + @testing-library/react; cover the access-gate flow and `can_*` permission enforcement first.
- Add dedicated test files for `api_keys.py` and `groups.py`.
- Move rate limiting to a Redis-backed store.
- Triage `tests_e2e/`: wire into CI or delete.
- Replace magic strings (status/role/annotation-type/screen-name) with shared const objects in `app.jsx`.

## Major Refactors (>1 week each)

- Extract `annotation_service.py` from `annotations.py` (estimated net -400 LOC across both routers once paired with the viewer-service extraction, +significant unit-testability).
- Extract `viewer_service.py` from `viewer.py`.
- Decompose `ViewerScreen` into ~6-8 focused components.
- Decompose `AccessScreen` along its 4 existing tab boundaries.
- Move `viewer_cache.py` to a Redis-backed implementation ahead of any horizontal `api` scaling.
- Container/seccomp isolation for the LibreOffice conversion subprocess.

## Roadmap

**Phase 1 — Stabilize (now, ~1-2 weeks):** All Quick Wins + the highest-risk Medium Wins: `viewer_profiles` cleanup (compliance exposure), regression test for the prod-secret-rejection check, tests for `requeue_orphaned_uploads()` and the access-gate/permission flows. Goal: close every gap that has a real (even if low-likelihood) compliance or silent-failure consequence.

**Phase 2 — Harden (~2-4 weeks):** Remaining Medium Wins — Redis-backed rate limiting, `require_org_role()` dependency, dedicated test files for `api_keys.py`/`groups.py`/`webhooks.py` real-delivery tests, `tests_e2e/` triage, vitest rollout beyond the first suite. Goal: every router and every critical frontend flow has direct test coverage; every authz check is declarative.

**Phase 3 — Scale (~4-8 weeks, only if/when approaching the 10,000-user tier per SYSTEM_DESIGN_REVIEW.md):** Move `viewer_cache.py` to Redis, add Celery Beat liveness alerting, evaluate read-replica/connection-pooling needs, separate LibreOffice conversion into its own worker queue. Goal: the architecture survives horizontal `api`/`worker` scaling without correctness regressions.

**Phase 4 — Enterprise (ongoing, as headcount/roadmap allows):** Both major service-layer extractions (`annotation_service.py`, `viewer_service.py`), both god-component decompositions (`ViewerScreen`, `AccessScreen`), LibreOffice container/seccomp sandboxing, standardized list-response shape across all endpoints. Goal: the two largest files in each tier (backend routers, frontend components) no longer dominate the maintenance burden, and new features stop having to pay the "edit a 1,000+ line file" tax.

## What NOT To Do

Per the audit's mandate, this is explicitly not a feature backlog. Nothing in this document should be read as "build X" — every item above is risk/debt removal. Resist scope creep: e.g. don't use the `ViewerScreen` decomposition as an opportunity to redesign the viewer UX; don't use the service-layer extraction as an opportunity to change API contracts beyond what API_CONTRACT_REVIEW.md already flags as worth standardizing.
