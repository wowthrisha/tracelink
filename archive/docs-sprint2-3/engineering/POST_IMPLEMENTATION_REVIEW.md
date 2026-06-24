# Post-Implementation Review — Audit Remediation Sprint 1

**Date:** 2026-06-17

---

## 1. Dead Code Scan

- No new dead code introduced.
- `_downloadBlob` is called 5 times; `buildFeedbackFilters` called 2 times — both used.
- No unreachable branches added.
- `cleanup_orphaned_viewer_profiles` is registered in the beat schedule and exported from `cleanup.py` — fully reachable.

## 2. Duplicate Logic Scan

- Blob-download boilerplate: now 1 definition, 5 usages ✅ (was 5 definitions)
- Feedback filter construction: now 1 definition, 2 usages ✅ (was 2 definitions)
- No new duplication introduced.

## 3. Security Regression Scan

- No auth/permission logic changed.
- No new SQL queries that could introduce injection vectors.
- `cleanup_orphaned_viewer_profiles` uses parameterized `NOT EXISTS` subqueries via SQLAlchemy ORM — no raw SQL.
- Rate limiter change is additive (adds `storage_uri` in production) — does not weaken limits.
- Model `__table_args__` additions are read-only metadata — no schema change.

## 4. Unused Imports Scan

- `billing.py` added `Index` import — used in `__table_args__`. ✅
- No other imports added. No unused imports introduced.

## 5. Broken API Contract Scan

- No routes added, modified, or removed.
- No request/response schema changes.
- Frontend `api.js` deduplication: all 5 export functions still call the same endpoints with the same parameters — only the blob-handling boilerplate was changed. ✅
- `buildFeedbackFilters` returns the same 7-field object shape as before. ✅

## 6. Open Risks and Remaining Work

### Remaining from this sprint's scope
- `_authFetch` centralization (30× duplicated 401 handler in `api.js`) — estimated <1 week, deferred to Sprint 2 because it requires touching all 41 functions in `api.js` and warrants its own focused commit.
- Frontend test framework (vitest + @testing-library/react) — deferred to Sprint 2.

### Known limitations of this sprint's changes
- `cleanup_orphaned_viewer_profiles` only runs daily. A viewer profile created today with no remaining references will persist until tomorrow's cleanup run. This is acceptable — the gap was "never", now it's "at most 24 hours".
- Redis rate limiting only activates when `app_env == "production"`. If an operator sets `app_env` to something other than `"production"` (e.g. `"staging"`) in a horizontally-scaled deployment, they will still get the in-memory limiter. Document in deployment guide.
- `__table_args__` backfill is documentation/tooling only — no migration is generated. If a developer runs `alembic revision --autogenerate` before this is reflected, they must verify the diff carefully. This is a net improvement (previously autogenerate would have generated spurious drops).
