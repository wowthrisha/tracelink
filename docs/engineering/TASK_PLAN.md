# Task Plan — Audit Remediation Sprint 1

**Date:** 2026-06-17  
**Scope:** P1 and P3 quick-win items from Enterprise Production Audit  
**Risk Level:** Low–Medium (no schema changes, no API changes, backwards-compatible)

---

## Goal

Close the highest-impact open findings from the audit without breaking any existing tests or API contracts. Four independent work streams, each independently committable.

---

## Tasks

### T1 — viewer_profiles compliance cleanup (P1)
**Goal:** Add a daily Celery task that deletes `viewer_profiles` rows with no remaining `viewer_sessions` or `viewer_annotations` referencing them, closing the GDPR/CCPA retention gap.

**Files impacted:**
- `backend/app/workers/cleanup.py` — add `cleanup_orphaned_viewer_profiles()` task
- `backend/app/workers/celery_app.py` — register in beat schedule
- `backend/tests/unit/test_cleanup_tasks.py` — new test file

**Risk:** Low. New Celery task, additive only. No schema change.

**Rollback:** Remove the task from `cleanup.py` and `celery_app.py`, delete the test file.

**Acceptance criteria:**
- Task deletes profiles not referenced by any session/annotation
- Task preserves profiles still referenced  
- Task returns `{"deleted": N}` result dict
- All tests pass

---

### T2 — requeue_orphaned_uploads test (P1)
**Goal:** Add a direct unit test for `_requeue_orphaned_uploads_async`, closing the "untested recovery path" gap.

**Files impacted:**
- `backend/tests/unit/test_cleanup_tasks.py` — included in same new file as T1

**Risk:** None. Test-only.

---

### T3 — Production startup guard regression test (P1)
**Goal:** Add tests ensuring the guard sentinels in `app/main.py` stay in sync with `app/config.py` defaults, so a future refactor cannot silently remove the protection.

**Files impacted:**
- `backend/tests/unit/test_config.py` — append `TestProductionStartupGuard` class

**Risk:** None. Test-only.

---

### T4 — Redis-backed rate limiting (P1)
**Goal:** Switch slowapi Limiter to Redis storage in production so rate limits are globally enforced across all `api` replicas, not per-process.

**Files impacted:**
- `backend/app/middleware/rate_limit.py` — add `storage_uri` when `app_env == "production"`

**Risk:** Low. In-memory fallback retained for dev/test. Only activates in production.

**Rollback:** Revert `rate_limit.py` to single-line Limiter construction.

**Acceptance criteria:**
- Test suite passes (in-memory still used in test/dev)
- Code inspection confirms Redis URI is passed in production env

---

### T5 — __table_args__ index backfill (P3)
**Goal:** Declare the 8 indexes that exist in Alembic migrations but are absent from SQLAlchemy models, preventing spurious `DROP INDEX` proposals from autogenerate.

**Files impacted:**
- `backend/app/models/document.py` — 4 indexes
- `backend/app/models/event.py` — 1 composite index
- `backend/app/models/billing.py` — 2 indexes (+ add __table_args__)
- `backend/app/models/annotation.py` — 1 index
- `backend/app/models/session.py` — 1 composite index

**Risk:** None. Pure model metadata — no migrations generated, no DB changes.

**Rollback:** Revert model files.

**Acceptance criteria:**
- All 8 indexes declared in `__table_args__`
- Tests pass

---

### T6 — Frontend blob-download deduplication (P3)
**Goal:** Extract `_downloadBlob(blob, filename)` helper in `api.js`, replacing 5 identical copy-paste implementations.

**Files impacted:**
- `frontend/api.js` — add helper, replace 5 call sites
- `frontend/dist/app.bundle.js` — rebuilt

**Risk:** Low. Pure refactor, no behaviour change.

**Rollback:** Revert `api.js`.

**Acceptance criteria:**
- Frontend builds without errors
- No duplicate blob-download boilerplate remains

---

### T7 — Frontend buildFeedbackFilters extraction (P3)
**Goal:** Extract `buildFeedbackFilters(params)` pure function in `app.jsx`, replacing 2 identical filter-object construction blocks.

**Files impacted:**
- `frontend/src/app.jsx` — add helper function, replace 2 call sites

**Risk:** Low. Pure refactor.

**Acceptance criteria:**
- Frontend builds
- No duplicate filter-object construction

---

## Rollback Strategy (global)

All changes are in non-migration files. Full rollback = `git revert <commit>` for each commit. No database migrations are introduced — existing schema is unchanged.
