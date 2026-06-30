# Production Readiness Audit

Each category scored 0-10. Evidence cites the relevant deep-dive report. P0 = Critical, P1 = High, P2 = Medium, P3 = Low.

## Security — 8/10

**Evidence:** No critical RCE/SQLi/auth-bypass found (SECURITY_AUDIT_REPORT.md). Deliberate hardening present: JWT algorithm whitelist (`app/auth.py:43-74`), SSRF TOCTOU re-validation (`app/workers/webhook_tasks.py:80-106`), env-whitelisted LibreOffice subprocess (`app/services/libreoffice_converter.py:172-187`), startup-time secret rejection (`app/main.py:29-82`).
**Risk Level:** Medium (open items, none critical).
**Recommended Actions:**
- P1: Confirm `sdoc_session` cookie `SameSite` attribute (`viewer.py:105-119`) — unverified in this pass.
- P1: Container/seccomp isolation for LibreOffice subprocess.
- P1: Add cleanup path for `viewer_profiles.email` (PII retention gap).
- P2: Move admin-role check to a `Depends` (`admin.py:15-78`); rotate session ID after re-validation.

## Scalability — 6/10

**Evidence:** SYSTEM_DESIGN_REVIEW.md — single Postgres/Redis instances, in-process rate limiting and viewer cache both break correctness (not just performance) once `api` scales past 1 replica.
**Risk Level:** Medium — fine today, becomes a real gate at ~10,000 concurrent users.
**Recommended Actions:**
- P1: Move rate limiting (`app/middleware/rate_limit.py`) and `viewer_cache.py` to Redis-backed before any horizontal `api` scaling.
- P2: Plan a read replica / connection pooling path ahead of the 10,000-user tier.

## Reliability — 7/10

**Evidence:** Migration advisory-lock pattern prevents multi-replica migration races (`migrate.py`, `docker-compose.yml`). `requeue_orphaned_uploads()` exists as a recovery mechanism but has zero test coverage (FEATURE_VERIFICATION_CHECKLIST.md). Single Celery Beat instance is a documented hard constraint with no liveness alerting found.
**Risk Level:** Medium.
**Recommended Actions:**
- P1: Add a test for `requeue_orphaned_uploads()`.
- P2: Add Beat liveness alerting/monitoring.

## Availability — 7/10

**Evidence:** Healthchecks present for `db`, `redis`, `api`, `worker` (`docker-compose.yml`). `restart: unless-stopped` on all long-running services. No multi-region/failover design (acceptable at current scale).
**Risk Level:** Low-Medium at current scale.
**Recommended Actions:** P3 — revisit only when approaching the 10,000+ user tier (SYSTEM_DESIGN_REVIEW.md).

## Maintainability — 5/10

**Evidence:** `annotations.py` (1,285 lines) and `viewer.py` (1,203 lines) have no service layer, business logic inlined in route handlers (BACKEND_ARCHITECTURE_REVIEW.md Findings 1-2). Frontend `app.jsx` (6,046 lines) contains two god components (`ViewerScreen` 53 useState, `AccessScreen` 35 useState). 10 backend functions exceed 100 lines.
**Risk Level:** Medium — not blocking today, compounds with every future feature touching these files.
**Recommended Actions:**
- P1: Extract `annotation_service.py` and `viewer_service.py` (estimated net -400 LOC, +testability).
- P1: Decompose `ViewerScreen` and `AccessScreen` along existing feature/tab boundaries.

## Testability — 5/10

**Evidence:** 1,614 backend tests, strong coverage on most routers (FEATURE_VERIFICATION_CHECKLIST.md). But: zero frontend tests/framework (FRONTEND_ARCHITECTURE_REVIEW.md), 3 routers with no dedicated test file (`api_keys.py`, `notifications.py`, `groups.py`), `webhooks.py` only mock-tested, `requeue_orphaned_uploads()` and `deliver_webhook()` lack real end-to-end coverage.
**Risk Level:** Medium-High on the frontend specifically (security-relevant `can_download`/`can_print`/`can_copy` enforcement has zero regression coverage).
**Recommended Actions:**
- P1: Stand up vitest + @testing-library/react, starting with the access-gate and permission-enforcement flows.
- P2: Add dedicated test files for `api_keys.py` and `groups.py`.

## Observability — 6/10

**Evidence:** Healthchecks exist per-service. `admin_audit_log` table captures admin actions. No centralized structured logging or metrics/tracing tooling identified in the reviewed code (no APM/Prometheus/OpenTelemetry references found in dependency or config files reviewed).
**Risk Level:** Medium — incident diagnosis today relies on container logs and the audit log table, not metrics.
**Recommended Actions:** P2 — add basic request/task metrics (Celery queue depth, request latency percentiles) before the 10,000-user tier; this is also what would have surfaced a silent Beat outage (Reliability finding above).

## Developer Experience — 6/10

**Evidence:** Clean Makefile/docker-compose, advisory-locked migrations, well-commented deployment config (REPOSITORY_CLEANUP_PLAN.md confirms no dead Makefile/compose targets). Counterweight: two 1,000+ line backend files and one 6,000+ line frontend file make onboarding and safe changes slower than necessary (TECHNICAL_DEBT_REGISTER.md).
**Risk Level:** Low-Medium.
**Recommended Actions:** P2 — same service-layer/component-decomposition work as the Maintainability score; this category and Maintainability share root causes and fixes.

## User Experience — not independently scored

Out of scope for this audit (no frontend UX/usability review was performed — this audit is a code/architecture/security review, not a design review). Feature completeness from a user-facing-functionality perspective is covered in FEATURE_VERIFICATION_CHECKLIST.md, where 17/20 features score ✅ Complete.

## Compliance — 6/10

**Evidence:** `viewer_profiles.email` has no retention/deletion path (DATABASE_REVIEW.md Finding 2, SECURITY_AUDIT_REPORT.md Finding 8) — a real exposure under GDPR/CCPA-style "right to erasure" obligations, since a viewer's email persists indefinitely even after every document/link they touched is deleted. Per-link PII (`access_events`, `viewer_sessions`, `viewer_annotations`) correctly cascades on deletion.
**Risk Level:** Medium-High if the product has EU/CA users and any compliance commitments.
**Recommended Actions:**
- P1: Add `viewer_profiles` cleanup pass to `app/workers/cleanup.py`, deleting profiles with no remaining referencing sessions/annotations.

## Performance — 7/10

**Evidence:** Hot-path queries (document_id, user_id, link_id, session_id filters) are all indexed (DATABASE_REVIEW.md). 5s/10s in-process caching reduces DB load for session/link lookups. No N+1 query patterns or missing indexes found in the reviewed routes.
**Risk Level:** Low at current scale.
**Recommended Actions:** P3 — the only performance-relevant change needed soon is moving caching to Redis ahead of horizontal scaling (already captured under Scalability).

---

## Score Summary

| Category | Score | Risk Level |
|---|---|---|
| Security | 8/10 | Medium |
| Scalability | 6/10 | Medium |
| Reliability | 7/10 | Medium |
| Availability | 7/10 | Low-Medium |
| Maintainability | 5/10 | Medium |
| Testability | 5/10 | Medium-High |
| Observability | 6/10 | Medium |
| Developer Experience | 6/10 | Low-Medium |
| Compliance | 6/10 | Medium-High |
| Performance | 7/10 | Low |

**Overall:** This is a well-hardened codebase from a pure security standpoint (no critical vulnerabilities found) that is carrying real but bounded maintainability and testability debt concentrated in a small number of files (2 backend routers, 2 frontend components, 1 missing test framework). Nothing here blocks current production operation; the highest-value near-term work is the PII retention gap (Compliance) and the service-layer extraction (Maintainability/Testability), both well-scoped and independent of each other.
