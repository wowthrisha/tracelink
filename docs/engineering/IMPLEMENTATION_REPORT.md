# Implementation Report — Audit Remediation Sprint 1

**Date:** 2026-06-17  
**Tests:** 1624 passed, 1 skipped (baseline was 1614 passed — +10 new tests)  
**Build:** frontend 199.2 KB ✅

---

## What Changed

### T1 — viewer_profiles compliance cleanup
Added a new daily Celery task `cleanup_orphaned_viewer_profiles` that deletes `viewer_profiles` rows no longer referenced by any `viewer_sessions` or `viewer_annotations` row. Closes the GDPR/CCPA retention gap identified in DATABASE_REVIEW.md Finding 2 and SECURITY_AUDIT_REPORT.md Finding 8.

### T2 — requeue_orphaned_uploads direct tests
Added 3 direct unit tests for `_requeue_orphaned_uploads_async`: stale-upload re-queue, fresh-upload skip, stuck-processing reset-then-re-queue. Also surfaced and fixed a pre-existing bug (T2b below).

### T2b (Bug fix) — UUID type handling in requeue_orphaned_uploads
`tasks.py` was converting UUID document IDs to strings immediately on query, then passing those strings back to a SQLAlchemy `IN` clause backed by a UUID column — which fails under SQLite's type processor (`.hex` error). Fixed by keeping IDs as UUID objects until passed to Celery (which requires strings). PostgreSQL was silently tolerant of this; SQLite was not.

### T3 — Production startup guard regression tests
Added `TestProductionStartupGuard` class (4 tests) to `test_config.py` verifying:
- `_IP_SALT_DEFAULT` in `main.py` matches the `ip_hash_salt` field default in `config.py`
- `_DOMAIN_SALT_DEFAULT` matches `domain_verify_salt` default
- Guard code block still present in source
- Guard logic collects errors for both default values

### T4 — Redis-backed rate limiting for production
`rate_limit.py` now passes `storage_uri=settings.redis_url` to the slowapi `Limiter` when `settings.app_env == "production"`. In dev/test, in-memory storage is retained (no Redis dependency for local iteration or test runs).

### T5 — __table_args__ index declaration backfill
8 indexes that existed in Alembic migrations but were absent from SQLAlchemy model `__table_args__` are now declared:

| Model file | Indexes added |
|---|---|
| `models/document.py` | ix_documents_file_type, ix_documents_org_id, ix_documents_parent_id, ix_documents_status_updated |
| `models/event.py` | ix_access_events_link_id_created |
| `models/billing.py` | __table_args__ added + ix_user_billing_stripe_customer, ix_user_billing_stripe_sub |
| `models/annotation.py` | ix_viewer_annotations_parent |
| `models/session.py` | ix_viewer_sessions_link_session |

### T6 — Frontend blob-download deduplication
Extracted `_downloadBlob(blob, filename)` helper in `api.js`. Replaced 5 identical 7-line copy-paste implementations in `downloadDocument`, `exportAnnotations`, `exportFeedback`, `exportReviewerActivity`, `exportVisualAnnotations`.

### T7 — Frontend buildFeedbackFilters extraction
Extracted `buildFeedbackFilters({...})` pure function in `app.jsx`. Replaced 2 identical 7-field filter-object construction blocks in `fetchFeedback` callback and the export `onChange` handler.

---

## Files Changed

```
backend/app/workers/cleanup.py         — new task added
backend/app/workers/celery_app.py      — beat schedule updated
backend/app/workers/tasks.py           — UUID type bug fix
backend/app/middleware/rate_limit.py   — Redis backend for production
backend/app/models/document.py         — __table_args__ backfill
backend/app/models/event.py            — __table_args__ backfill
backend/app/models/billing.py          — __table_args__ added + Index import
backend/app/models/annotation.py       — __table_args__ backfill
backend/app/models/session.py          — __table_args__ backfill
backend/tests/unit/test_cleanup_tasks.py   — NEW test file
backend/tests/unit/test_config.py      — TestProductionStartupGuard appended
frontend/api.js                        — _downloadBlob helper + 5 replacements
frontend/src/app.jsx                   — buildFeedbackFilters + 2 replacements
frontend/dist/app.bundle.js            — rebuilt (199.2 KB)
docs/engineering/TASK_PLAN.md          — NEW
docs/engineering/EXECUTION_LOG.md      — NEW
```

---

## Database Changes

None. No migrations. The `__table_args__` additions declare existing indexes for tooling purposes only — they do not create new indexes or modify the schema.

---

## API Changes

None. All changes are internal (Celery tasks, middleware, models, tests, frontend helpers).

---

## Security Impact

**Positive:**
- `viewer_profiles.email` will now be purged daily once all referencing sessions/annotations are gone — closes PII retention gap (GDPR/CCPA)
- Production rate limiting now uses Redis globally, preventing per-process limit bypass under horizontal scaling
- Production startup guard is now covered by regression tests, making it harder to accidentally remove

**Neutral:** All other changes are refactors or documentation — no security surface change.

---

## Performance Impact

**Neutral.** The new `cleanup_orphaned_viewer_profiles` task runs once daily. The `NOT EXISTS` query uses indexed columns (`viewer_profile_id` on both `viewer_sessions` and `viewer_annotations`). The model `__table_args__` additions are metadata-only. The frontend changes reduce bundle parse work marginally (deduplication).

---

## Technical Debt Impact

Closed 4 items from TECHNICAL_DEBT_REGISTER.md:
- ✅ Blob-download boilerplate duplicated 5× → extracted to `_downloadBlob`
- ✅ Feedback filter-object duplicated 2× → extracted to `buildFeedbackFilters`
- ✅ Model/migration index drift (8 indexes, 5 models) → backfilled
- ✅ `viewer_profiles` has no retention path → daily cleanup task added

Partially closed:
- ⚠ `requeue_orphaned_uploads` untested → 3 tests added (bug in same function also fixed)
- ⚠ Production startup guard untested → 4 regression tests added
