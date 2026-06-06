# TraceView — Launch Readiness Audit Report
## Pre-Merge / Pre-Pilot Review

**Audit date:** 2026-06-04  
**Branch:** `phase-d2-docx-pipeline`  
**Test suite:** 1202 / 1202 passing  
**Reviewer:** Phase D2.5 → Launch audit pass  

---

## Table of Contents

1. [Architecture Score](#1-architecture-score)
2. [Security Score](#2-security-score)
3. [Scalability Score](#3-scalability-score)
4. [Maintainability Score](#4-maintainability-score)
5. [Deployment Score](#5-deployment-score)
6. [Git Hygiene Score](#6-git-hygiene-score)
7. [Launch Blockers](#7-launch-blockers)
8. [Recommended Next Steps](#8-recommended-next-steps)
9. [Pilot Readiness Verdict](#9-pilot-readiness-verdict)

---

## 1. Architecture Score

**9 / 10**

### What is excellent

**Document adapter pattern (Phase D1):** Format dispatch is cleanly centralised in `app/services/adapters/`. Adding a new format (PPTX, HTML, EPUB) requires exactly one new file and one registry line — no if/elif chains in four scattered locations.

**Pipeline separation:** PDF, text, and DOCX pipelines are fully independent. `process_pdf_document` accepts pre-loaded bytes (`pdf_bytes=`) for the DOCX conversion path — a clean, backward-compatible seam.

**Caching layering:** L1 (process-local LRU) → L2 (Redis) → Storage is implemented consistently across pages, thumbnails, TOC, and text chunks. Cache security contract is clear: only pre-watermark bytes are cached; the session-specific visible watermark is applied after every cache hit.

**Worker architecture:** Module-level persistent async event loop and DB engine in the Celery worker correctly prevents asyncpg connection-bound-to-closed-loop errors. `task_acks_late=True` + `task_reject_on_worker_lost=True` prevents documents from being silently dropped if a worker process is killed mid-job.

**DOCX pipeline (Phase D2–D2.7):** LibreOffice conversion → existing PDF pipeline is the correct industry approach. Phase D2.7's PDF bookmark extraction via pypdf for TOC page numbers is zero-overhead (PDF bytes already in memory).

**Migration safety:** `migrate.py` wraps Alembic under `pg_advisory_lock(7325613)`, preventing concurrent container startup races. The docker-compose `migrate` service with `service_completed_successfully` dependency is belt-and-suspenders.

### Minor architectural concern

`storage.py` line 128 contains `client.create_bucket(Bucket=self._bucket)` triggered by `NoSuchBucket`. This Moto-testing artifact would silently attempt bucket creation on a production credentials mismatch. Not a real risk (R2/S3 credential scopes would deny creation) but conceptually the wrong response to a misconfigured deployment.

---

## 2. Security Score

**8 / 10**

### What is excellent

**JWT verification:** Supabase EC-256 JWT verified via JWKS with automatic key rotation handling. Algorithm is constrained to `{"ES256", "RS256"}`. No symmetric secret (HS256) auth surface.

**No secrets in source control:** Confirmed by `git ls-files` scan — `.env`, `.db`, `htmlcov/`, `.coverage` are all gitignored and have never been committed.

**Watermark security:** Forensic stamp (0.03 opacity pixel layer + EXIF ImageDescription) burned into stored pages at processing time. Visible watermark applied per-session per-request in executor thread. DOCX now gets identical treatment to PDF — no more CSS-overlay watermark that was removable via DevTools.

**IP allowlists:** Fail-CLOSED on malformed JSON. Enforced on every viewer route including download, not just on initial validate.

**Session validation:** Session heartbeat with 30-second write throttle. `is_active_session()` checked on download. `upsert_session()` called on every page/chunk served.

**CSP:** `default-src 'none'` with SRI hashes for React bundles. No `unsafe-eval`. No `unsafe-inline` in `script-src`. `frame-ancestors 'none'`.

**IP hashing:** SHA-256 with env-sourced salt. Default salt triggers `RuntimeError` at startup in production mode.

**File validation:** Magic-byte checks for DOCX (PK), DOC (OLE2), LibreOffice subprocess receives list args (no shell injection), input filename is always `input.docx` (not user-supplied).

**Startup guard (`main.py:25–42`):** In `APP_ENV=production`, refuses to start if `SUPABASE_URL` is missing, `APP_PUBLIC_BASE_URL` is localhost/HTTP, or `IP_HASH_SALT` is the default placeholder. These are hard failures, not warnings.

### Findings

**F1 — Dead config entry: `JWT_SECRET` in `.env`**  
`backend/.env` contains `JWT_SECRET=688e163ae...` and `backend/.env.example` documents `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_LINK_EXPIRE_HOURS`. None of these appear in `config.py` or anywhere in `app/`. Share link tokens are generated with `secrets.token_urlsafe()` (confirmed: `link_service.py` uses `secrets`). This is orphaned config from a previous implementation. It causes confusion for operators who might believe there is an internal JWT they need to rotate.  
**Risk: LOW** — no code reads this value; it can't be exploited. But it creates audit confusion.

**F2 — Supabase anon key injected into HTML**  
`/app` route substitutes `SECUREDOC_SUPABASE_ANON_KEY` from env into `<meta>` tags in the served HTML. This is architecturally correct (anon keys are designed to be public; they only allow unauthenticated DB reads restricted by Row Level Security). No issue.

**F3 — `REAL_IP_HEADER` not set by default**  
When deployed behind Cloudflare, `REAL_IP_HEADER=CF-Connecting-IP` must be set or the rate limiter and IP allowlists use the Cloudflare edge IP (shared by all users). A non-fatal startup warning is issued (`main.py:51–56`) but this should be treated as a pilot blocker since IP allowlists — a core feature — are ineffective without it.

**F4 — `HTTPS_REDIRECT=false` by default**  
The startup non-fatal warning is correct. Without `HTTPS_REDIRECT=true`, the origin port (Railway's internal service URL) is technically accessible over HTTP if someone discovers it. Cloudflare handles TLS termination, so end-users always get HTTPS. Risk is low but should be set for defence-in-depth.

---

## 3. Scalability Score

**7 / 10**

### What is good

- Database connection pool is fully configurable via env vars (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_RECYCLE`).
- Storage I/O uses a dedicated `_STORAGE_EXECUTOR` (16 threads) separate from the default asyncio thread pool.
- L1/L2 caching means hot documents served from memory with no DB or storage I/O.
- Celery `worker_prefetch_multiplier=1` prevents task hoarding.
- `MAX_PAGES_PER_DOC: 500` and `MAX_DOWNLOAD_PAGES_PDF: 100` guard against memory exhaustion.

### Concerns

**S1 — Single Docker image for API + Worker**  
Both the API server and the Celery worker use the same image, which now includes LibreOffice (~700 MB extra). The API server never calls LibreOffice but carries the full worker image weight. On Railway, this means the API container pulls and stores ~1.7 GB instead of ~1.0 GB.

**S2 — Worker concurrency and DOCX RAM**  
`config.py` documents "800MB–4GB RAM per worker for PDF". DOCX adds +400–600 MB during LibreOffice conversion. With `WORKER_CONCURRENCY=2` (default), two simultaneous large DOCX conversions could push worker RAM to 6+ GB. The `.env.example` documents this clearly but the default of `2` is risky for DOCX-heavy workloads on Railway's Hobby plan (512 MB).

**S3 — No horizontal worker scaling documented**  
The architecture supports horizontal worker scaling (multiple Celery workers against shared Redis + Postgres) but Railway deployment guide for adding a second worker service isn't documented.

---

## 4. Maintainability Score

**9 / 10**

**Test suite:** 1202 tests, all passing. Good separation: unit tests (pure Python, no I/O), integration tests (SQLite + mocked storage), regression tests. Coverage is tracked.

**Code organisation:** Clean layering — adapters → pipelines → routers → models. No circular imports. Lazy imports inside pipeline functions prevent import-time side effects.

**Documentation:** Module docstrings explain architecture decisions (subprocess vs unoserver, advisory lock, persistent event loop). `config.py` comments explain every setting. `.env.example` is comprehensive with annotated sections.

**Phase history:** Incremental development is well-tracked in commit history (D1 → D2 → D2.6 → D2.7). Each commit message is specific and informative.

**Minor concerns**

- `README.md` describes frontend as "React + Babel" but Phase 2 migrated to esbuild prebuild. The README hasn't been updated to reflect the pre-compiled bundle.
- 6 audit/decision report `.md` files sit untracked at the repo root (`TRACEVIEW_AUDIT_*.md`, `TRACEVIEW_D2_*.md`, `TRACEVIEW_D25_*.md`). They're analysis artifacts, not application code, but they're messy.

---

## 5. Deployment Score

**8 / 10**

### What is production-ready

**Entrypoint:** `entrypoint.sh` runs `python migrate.py` then `exec "$@"`. Both API and worker containers run migrations on startup; the advisory lock serialises the race correctly.

**Health check:** `GET /health` checks DB (`SELECT 1`), Redis (`PING`), storage instantiation, and worker presence (Kombu binding scan via `SCAN`). Returns structured JSON with degraded/ok status. Correctly wired into `docker-compose.yml` health check and Railway health probe.

**Graceful shutdown:** `@app.on_event("shutdown")` disposes the DB engine cleanly. Worker uses `task_acks_late=True` + `task_reject_on_worker_lost=True`.

**Cloudflare tunnel support:** `start.sh` and `docker-compose.yml` are documented. `REAL_IP_HEADER=CF-Connecting-IP` is the documented production switch.

**DB migrations:** 12 Alembic migrations, properly chained, with idempotent `op.create_table` using `if_exists` / `if_not_exists` guards.

**Frontend delivery:** Pre-compiled JSX bundle (`dist/app.bundle.js` via esbuild in multi-stage Docker build). No Babel runtime in container. `SecureDoc.html` is 246 lines, served with `no-cache` headers.

### Concerns

**D1 — `APP_PUBLIC_BASE_URL` in `.env` points to expired Cloudflare tunnel**  
The dev `.env` currently contains:
```
APP_PUBLIC_BASE_URL=https://realtor-centuries-left-byte.trycloudflare.com
```
This temporary URL is expired/expiring. Any share link created while this value is active will embed a broken base URL. The pilot deployment on Railway must set this to the stable production domain before the first document is uploaded. Since the startup guard only checks for `localhost` and HTTP, an expired trycloudflare URL passes without warning.

**D2 — `WORKER_MAX_TASKS_PER_CHILD=0` in dev `.env`**  
The dev `.env` has `WORKER_MAX_TASKS_PER_CHILD=0` (never recycle). The `.env.example` recommends `50` for production. Pillow and pdf2image accumulate memory across tasks. Libr eOffice adds to this. Leaving this at 0 in production risks gradual OOM over hours.

---

## 6. Git Hygiene Score

**7 / 10**

### What is clean

- `.env`, `.env.*` correctly gitignored; confirmed never committed (`git log -- backend/.env` returns empty).
- Test databases previously committed in early development were explicitly removed in commit `f8e2e29` ("Remove test databases from repository"). `.db` is now properly gitignored.
- `htmlcov/`, `.coverage` are gitignored and untracked in git.
- Commit history is clean, linear, and descriptive. 10 commits with meaningful messages.
- No binary blobs (except `frontend/dist/app.bundle.js` — intentionally committed as pre-compiled asset per Phase 2 decision).

### Concerns

**G1 — 6 untracked analysis documents at repo root**  
The following files are untracked and will show as `??` to any contributor:
```
TRACEVIEW_AUDIT_A.md
TRACEVIEW_AUDIT_B.md
TRACEVIEW_AUDIT_C.md
TRACEVIEW_AUDIT_D.md
TRACEVIEW_D25_VALIDATION_REPORT.md
TRACEVIEW_D2_DECISION_REPORT.md
```
These are valuable architectural decision records but they need a home. Either commit them to `docs/decisions/` or add `*.md` to the root-level gitignore (taking care not to gitignore `README.md`). As-is they create noise in `git status`.

**G2 — Test databases exist on disk but not in git**  
`backend/test_securedoc.db`, `backend/test_phase5.db`, etc. exist on the local filesystem (created by test runs) and are properly gitignored. Not a git problem, but these leftover files suggest `make clean` should include a `rm -f *.db` step in the Makefile.

**G3 — Branch `phase-d2-docx-pipeline` not merged to `main`**  
The audit is being performed on a feature branch. The branch is ahead of `main` by 4 commits. Before pilot, this branch must be merged.

---

## 7. Launch Blockers

There are **4 operational blockers** that must be resolved before pilot. These are all environment variable configuration items — no code changes required.

---

### Blocker 1 (CRITICAL) — Set stable `APP_PUBLIC_BASE_URL`

**Who:** Person setting up Railway environment variables.  
**What:** `APP_PUBLIC_BASE_URL` must be set to the stable Railway or custom domain URL before the first document upload.  
**Why:** Every share link embeds this URL. Links created with the wrong URL break permanently when the URL changes. There is no migration path.  
**How:**
```
APP_PUBLIC_BASE_URL=https://your-app.railway.app   # or your custom domain
ALLOWED_ORIGINS=https://your-app.railway.app
```
The startup guard catches `localhost` and non-HTTPS URLs but not arbitrary stale URLs. Must be set manually.

---

### Blocker 2 (HIGH) — Set `APP_ENV=production` + `IP_HASH_SALT`

**What:** Railway deployment must have `APP_ENV=production` and a randomly generated `IP_HASH_SALT`.  
**Why:** Without `APP_ENV=production`, the startup guards don't run. IP addresses would be hashed with the default placeholder salt (`securedoc_ip_salt_change_in_production`), making all hashes predictable and reversible.  
**How:**
```
APP_ENV=production
IP_HASH_SALT=<output of: python -c "import secrets; print(secrets.token_hex(32))">
```
The startup guard enforces this: the app refuses to start in production with the default salt.

---

### Blocker 3 (HIGH) — Set `REAL_IP_HEADER=CF-Connecting-IP`

**What:** If deploying behind Cloudflare (which is the documented production setup), set the real-IP header.  
**Why:** Without this, the rate limiter and IP allowlists operate on the Cloudflare edge IP address, which is shared across thousands of unrelated users. Rate limits are effectively per-Cloudflare-edge, not per-user. IP allowlists are completely ineffective.  
**How:**
```
REAL_IP_HEADER=CF-Connecting-IP
```

---

### Blocker 4 (MEDIUM) — Set `WORKER_MAX_TASKS_PER_CHILD=50`

**What:** The Celery worker must be configured to recycle after 50 tasks.  
**Why:** pdf2image, Pillow, and LibreOffice accumulate memory across tasks. Without recycling, a worker container will eventually OOM-kill on Railway.  
**How:**
```
WORKER_MAX_TASKS_PER_CHILD=50
WORKER_CONCURRENCY=1   # for Railway Hobby plan; 2 for Pro plan with 4GB+ RAM
```

---

## 8. Recommended Next Steps

### Before merging `phase-d2-docx-pipeline` → `main`

1. **Commit or gitignore the 6 untracked `TRACEVIEW_*.md` files.** Move to `docs/decisions/` and commit. These are valuable architectural decision records.

2. **Remove the dead `JWT_SECRET` / `JWT_ALGORITHM` / `JWT_LINK_EXPIRE_HOURS` entries from `.env.example`.** They are confusing — no code reads them. Add a comment explaining authentication is entirely Supabase JWKS.

3. **Update `README.md`** to reflect the current architecture: esbuild bundle (not Babel), DOCX support (not just PDF), LibreOffice dependency in worker container.

4. **Add `rm -f backend/*.db` to Makefile `clean` target** to keep the working directory tidy after test runs.

### Before pilot first use (operational, not code)

5. **Set the 4 environment variables above on Railway** (Blockers 1–4).

6. **Enable `HTTPS_REDIRECT=true`** on Railway once HTTPS is confirmed stable on the domain.

7. **Set `HSTS_MAX_AGE=31536000`** after HTTPS is stable for at least 24 hours with no issues.

8. **Set `HTTPS_REDIRECT=true` and `ENABLE_JSON_LOGGING=true`** for operational visibility.

### Near-term follow-on

9. **Separate Dockerfile for API vs Worker** — reduces API image by ~700 MB; eliminates LibreOffice from the API container which never uses it.

10. **DOCX TOC page navigation for documents without PDF bookmarks** — For DOCX files where LibreOffice doesn't emit PDF bookmarks (rare, edge case), TOC entries appear in the sidebar as structural headings without navigation. Phase D3+ improvement.

11. **DOC (legacy .doc) migration to LibreOffice** — Currently uses antiword text pipeline. Phase D4 would bring it to the image-based pipeline for layout fidelity.

---

## 9. Pilot Readiness Verdict

### Summary of scores

| Area | Score | Key finding |
|------|-------|-------------|
| Architecture | 9/10 | Clean adapter pattern, well-layered, solid DOCX pipeline |
| Security | 8/10 | Solid fundamentals; dead JWT_SECRET config; REAL_IP_HEADER must be set |
| Scalability | 7/10 | Single Docker image bloat; worker RAM sizing for DOCX |
| Maintainability | 9/10 | 1202 tests, clean structure, good documentation |
| Deployment | 8/10 | Production startup guards in place; APP_PUBLIC_BASE_URL is a pre-flight item |
| Git hygiene | 7/10 | 6 untracked analysis docs; test DBs on disk; branch not yet merged |

### Can Dad start using this tomorrow?

**Yes — with four operational prerequisites.**

The system is architecturally sound, the security model is comprehensive, and 1202 tests validate the core functionality. The DOCX pipeline is production-ready (LibreOffice conversion, watermarked pages, thumbnail navigation, page-aware TOC). All four launch blockers are environment variable configuration items, not code defects.

The platform is ready for real users **as soon as the Railway environment has the four blockers set**. None of them require code changes, commits, or deployments — they are Railway dashboard env var entries that take effect on the next container restart.

**Known limitations for the pilot** (not blockers, but worth communicating to early users):

1. DOCX TOC page navigation requires LibreOffice to emit PDF bookmarks. Most modern DOCX files work correctly. Edge cases (protected documents, unusual custom heading definitions) show headings in the TOC sidebar without click navigation.
2. DOCX layout may differ slightly from Word for documents using non-standard fonts beyond Calibri/Cambria (covered by the carlito/caladea fonts added in D2.6).
3. Legacy `.doc` files are served as plain text (antiword extraction). Layout, tables, and images are not preserved.
4. Free plan is limited to 10 documents per user.
5. PPTX is not yet supported.

---

## SAFE FOR PILOT
