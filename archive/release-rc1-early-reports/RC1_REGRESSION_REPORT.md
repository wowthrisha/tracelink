# RC1 REGRESSION REPORT — Sprint 6.2
**Date:** 2026-06-30
**Release:** RC-1 (v8.1.0)

---

## Test Suite Execution

```
Platform:   macOS Darwin 24.3.0, Python 3.13
Backend:    localhost:8000 (FastAPI + SQLAlchemy async)
Database:   PostgreSQL 15 at localhost:5432
Redis:      localhost:6379
Storage:    DemoStorageService (USE_DEMO_STORAGE=1)

Command:    python -m pytest tests/ -x -q --tb=short
Duration:   54.31s
Result:     1624 passed, 1 skipped, 20 warnings
Failures:   0
```

---

## Test Distribution

| Suite | Description |
|-------|-------------|
| `tests/unit/` | Unit tests for services, storage, config |
| `tests/integration/` | Full-stack integration tests (all phases 1–7 + e1 security) |
| `tests/integration/test_phase7.py` | Watermark angle, viewer session, PDF rendering |

---

## FIX-007 Regression Verification

`test_phase7.py` was modified as part of FIX-007: import source changed from `app.routers.viewer` to `app.services.viewer_service`, patch target changed from `app.routers.viewer.settings` to `app.services.viewer_service.settings`.

All `test_phase7.py` tests pass. No regression.

---

## Warnings (Non-Blocking)

| Warning | Source | Impact |
|---------|--------|--------|
| `RuntimeError: Event loop is closed` | `asyncio` teardown in pytest | No test failures; pytest asyncio cleanup artifact |
| `DeprecationWarning: Setting per-request cookies=<...>` | `httpx` v0.2x | No test failures; httpx API evolution |
| `DeprecationWarning: datetime.utcnow()` (×18) | `botocore` | Third-party library; not our code |

All 20 warnings are pre-existing, third-party, or test-harness artifacts. None introduced by Sprint 6.2 changes.

---

## Skipped Tests

1 test skipped — pre-existing skip marker (not introduced in Sprint 6.2).

---

## Verdict

**NO REGRESSIONS.** 1624/1624 tests pass. Sprint 6.2 changes (FIX-007) did not break any existing test.
