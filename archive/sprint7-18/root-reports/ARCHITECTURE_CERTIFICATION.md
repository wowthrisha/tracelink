# Architecture Certification — TraceLink / SecureDoc

**Method**: source-code inspection of the backend (FastAPI + async SQLAlchemy + PostgreSQL), frontend (hand-rolled React 18, no build framework), background job system (Celery + Redis), and storage layer (Cloudflare R2/S3-compatible) — cross-referenced against `SCALABILITY_CERTIFICATION.md` and `SECURITY_CERTIFICATION.md`, both produced earlier this sprint with the same evidence discipline. No new live testing was performed for this document; every claim is Source-code verified unless marked otherwise.

Every finding is classified as exactly one of **Browser-verified / Source-code verified / Engineering inference / Not enough evidence**. Categories are never mixed within one finding.

---

## 1. Service topology

**Source-code verified**: single FastAPI application (`backend/app/main.py`) serving both the API and the static frontend bundle, backed by PostgreSQL (async SQLAlchemy), Redis (Celery broker + rate-limiter storage + cache in production), and Cloudflare R2 for object storage. Background work (PDF rasterization, watermarking, retention sweeps) runs in a separate Celery worker process, not inline in request handlers. Deployment is on Railway, auto-deploying from `origin/main`.

This is a conventional, well-understood topology for a document-processing SaaS at this scale — no exotic or over-engineered infrastructure, no premature microservices split. **Engineering inference**: appropriately simple for the current stage; splitting further (e.g., a separate rasterization service) would add operational overhead without a demonstrated need.

## 2. Data model & authorization pattern

**Source-code verified** (re-confirmed this sprint, `SECURITY_CERTIFICATION.md` §2): every resource-scoped router filters by `WHERE {Resource}.user_id == current_user_id` (or an org-membership join) directly in the query. This is authorization-by-construction, not a bolt-on permission-check layer — the query itself cannot return another tenant's row. It is also why unauthorized access returns `404` rather than `403` (the resource is invisible, not merely forbidden), which is the more conservative choice and avoids resource-existence leakage.

**Not enough evidence**: this pattern's correctness under cross-account access was not independently re-verified with a second live account this sprint (see `SECURITY_CERTIFICATION.md` §2 for the full disclosure) — the architectural pattern is sound by inspection, but live cross-tenant proof remains an open gap.

## 3. Caching strategy — `viewer_cache.py`

**Source-code verified**: a process-local, in-memory TTL cache (`_TTLCache`, FIFO eviction) sits on the viewer hot path — `LINK_TTL_SEC=10.0`, `SESSION_TTL_SEC=5.0`, `DOC_TTL_SEC=60.0`, `PAGE_TTL_SEC=300.0`. The module's own docstring documents that this is deliberately process-local ("uvicorn runs workers=N as forked *processes*, not threads") and accepts bounded staleness (≤10s) for permission/link changes as a tradeoff, while revocation specifically bypasses the TTL and is checked against wall-clock time on every cache hit (re-confirmed by browser test in `SECURITY_CERTIFICATION.md` §3).

This is an honestly-documented, deliberate tradeoff rather than an accidental bug — the authors clearly understood the process-local limitation and scoped its blast radius (link/permission propagation only, not revocation, not auth). **Engineering inference**: this becomes a real problem only if the deployment moves to multiple concurrently-running API replicas *and* a customer has a hard requirement for instant (not ≤10s) permission propagation — flagged with the same "Before 10,000 users" priority in `SCALABILITY_CERTIFICATION.md` §6.

## 4. Background job design

**Source-code verified**: Celery configured with `task_acks_late=True` + `task_reject_on_worker_lost=True` (a task is only marked complete after it finishes, and is safely redelivered if its worker dies mid-task) and `worker_prefetch_multiplier=1` (a worker doesn't hoard tasks it can't yet process). `WORKER_CONCURRENCY` defaults to 2, sized conservatively against PDF rasterization's documented 800MB–4GB RAM footprint per worker (per `.env.example`'s own sizing guidance).

This is sound failure-recovery design — a crashed worker does not silently drop or duplicate-process a job. **Engineering inference**: the concurrency default trades throughput for memory safety, which is the right default for a self-hosted/Railway deployment without dedicated infra tuning, but will need revisiting as real upload volume grows (already flagged in `SCALABILITY_CERTIFICATION.md` §3, "Before 10,000 users").

## 5. Frontend architecture

**Source-code verified**: hand-rolled React 18 via CDN UMD scripts + esbuild IIFE bundling — no Next.js/Vite/CRA framework layer, no client-side router framework, no state-management library (component state + a handful of custom hooks, e.g. `useLinksSidecar.js`, `useReadingAnalytics.js`). Screens are organized one-file-per-screen under `frontend/src/screens/`, shared UI primitives under `frontend/src/components/`.

**Engineering inference**: this is a deliberately minimal, dependency-light choice — it avoids an entire category of build-tool/framework-upgrade churn, at the cost of some ergonomics (no fast-refresh dev loop, no framework-provided code-splitting). For a product this size (≈10-15 screens, no deep component nesting) the tradeoff is defensible. It would stop being defensible if the frontend's screen count or shared-state complexity grew substantially — there is no currently-observed evidence that it has.

**Known, previously-documented debt** (not re-litigated this sprint, cited for completeness):
- `AccessScreen.jsx` (~900 lines) is oversized by conventional component-size norms — tracked as `ISSUE_DATABASE.md` M-13, a deliberate refactor deferral from an earlier sprint.
- A 7-key `permissions` dict is duplicated across `AccessScreen.jsx` and `viewer_session_service.py` — tracked as `ARCHITECTURE_DECISIONS.md` AD-7, deliberately extended rather than consolidated in V11.0, with that sprint's reasoning already on record.
- A CSS responsive breakpoint (640px) is unreachable — tracked as `ARCHITECTURE_DECISIONS.md` AD-6, a deliberate non-fix pending a product decision about mobile support scope.

These are documented, intentional tradeoffs with recorded rationale — not silently-accumulated drift. Re-confirmed present (not re-litigated) via the Phase 1 repository cleanup sweep this sprint (`docs/engineering/FIX_LOG.md`, "What this cleanup did NOT cover").

## 6. Security headers & transport

**Source-code verified** (re-confirmed in `SECURITY_CERTIFICATION.md` §7): strict CSP (`default-src 'none'`, hash-pinned inline scripts), HSTS with preload, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, restrictive `Permissions-Policy`, and no `Set-Cookie` header anywhere (Bearer-token-only auth). This is an architecturally strong default posture, not a checklist afterthought — the no-cookie design structurally removes an entire CSRF attack surface rather than mitigating it with tokens.

## 7. Observability

**Source-code verified**: real Prometheus instrumentation exists (`app/metrics.py` — `http_requests_total`, `page_requests_total`, `document_uploads_total`, `share_links_created_total`, `webhook_deliveries_total`, etc.) plus structured JSON logging in both the API and worker processes. `SCALABILITY_CERTIFICATION.md` §13 covers this in more depth.

**Not enough evidence**: whether these metrics are actually wired into a running dashboard/alerting stack (vs. only exposed and un-scraped) was not verified this sprint — the instrumentation exists in code, but its operational use is unconfirmed.

## 8. What this certification does not cover

- No new live testing — this document synthesizes source-code findings, cross-referenced with the browser evidence already gathered for `SECURITY_CERTIFICATION.md` and `SCALABILITY_CERTIFICATION.md`.
- No infrastructure-as-code / deployment-pipeline review (Railway configuration itself was not audited beyond what's referenced in `.env.example` and observed auto-deploy behavior).
- No dependency-vulnerability scan (`pip-audit`/`npm audit` or equivalent) was run this sprint.

---

## Score: 8/10

**Why not higher**: two structural risks are flagged but unresolved — (1) no cluster-wide DB connection budget if horizontally scaled (`SCALABILITY_CERTIFICATION.md` §2, §11), and (2) the process-local cache's bounded-staleness tradeoff, while deliberate and documented, has no cross-process invalidation broadcast if a customer ever needs provably-instant permission propagation. Both are "safe today, latent risk at scale" rather than active defects, which keeps this out of "reject" territory but short of full marks.

**Why not lower**: the authorization pattern is sound by construction (not bolt-on), background-job failure recovery is correct, security headers/transport are strong defaults, and every piece of known architectural debt (AD-6, AD-7, M-13) is deliberately made and documented with recorded rationale rather than silently accumulated. This is a codebase that understands its own tradeoffs.
