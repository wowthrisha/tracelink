# SecureDoc Enterprise Transformation — Changelog

All enterprise transformation changes are documented here.  
Format: `[Action N] Description | Files | Date`

---

## Phase 1 — Security Critical (2026-06-07)

### [Action 1] Enable HSTS by Default
- `backend/app/config.py`: `hsts_max_age` default changed `0 → 31536000`
- `backend/app/middleware/security_headers.py`: Added `; preload` to HSTS header
- `backend/app/main.py`: Production startup HSTS check changed from warning to error
- `backend/tests/integration/test_enterprise_security.py`: HSTS tests added

### [Action 2] Fix max_views Race Condition (Atomic Check-and-Increment)
- `backend/app/services/link_service.py`: Replaced 2-query pattern with atomic `UPDATE ... RETURNING`; removed `increment_view_count()` method
- `backend/app/routers/viewer.py`: Removed explicit `increment_view_count()` call from validate
- `backend/tests/integration/test_enterprise_security.py`: Concurrency and edge case tests added

### [Action 3] Viewer Identity Forensic Stamp
- `backend/app/services/watermark.py`: Added `apply_viewer_forensic_stamp()` method
- `backend/app/routers/viewer.py`: Chain viewer forensic stamp after visible watermark
- `backend/tests/unit/test_watermark.py`: Viewer stamp unit tests added
- `backend/tests/integration/test_enterprise_security.py`: End-to-end stamp tests added

### [Action 4] Session Validation Cache (5-second TTL)
- `backend/app/services/viewer_cache.py`: Added `session_cache` and `invalidate_sessions_for_link()`
- `backend/app/services/policy.py`: `is_active_session()` and `upsert_session()` now use cache
- `backend/tests/unit/test_policy.py`: Cache behavior and revocation propagation tests
- `backend/tests/integration/test_enterprise_security.py`: Performance and security tests

### [Action 5] Structured JSON Logging — Enabled by Default
- `backend/app/config.py`: `enable_json_logging` default changed `False → True`
- `backend/app/middleware/json_logging.py`: Enhanced with request fields: user_id, doc_id, link_id, event, status_code, path, method, duration_ms, cache_hit
- `backend/app/middleware/request_id.py`: Emits structured JSON access log per request
- `backend/app/workers/celery_app.py`: Worker startup configures JSON logging
- `backend/tests/unit/test_json_logging.py`: Formatter and field tests added
