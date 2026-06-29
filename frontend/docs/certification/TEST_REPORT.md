# TEST REPORT — Sprint 5.5 Engineering Investigation
**Date:** 2026-06-29  
**Sprint:** 5.5 Phase 2

---

## Test Suite Status

| Metric | Value |
|--------|-------|
| Total tests collected | 1625 |
| Passing | 1624 |
| Skipped | 1 |
| Failing | 0 |
| Warnings | 20 (pre-existing, non-application) |
| Run time | ~66 seconds |
| Test runner | pytest 8.3.0 + pytest-asyncio 0.24.0 |
| Python version | 3.13.9 |

---

## Test Directory Structure

```
tests/
├── unit/
│   ├── test_adapters.py          — file type adapters
│   ├── test_annotation_refactor.py
│   ├── test_auth.py              — JWT + API key auth
│   ├── test_billing.py           — Stripe billing logic
│   ├── test_cleanup_tasks.py
│   ├── test_config.py            — settings validation
│   ├── test_crypto.py            — hash utilities
│   ├── test_docx_toc_merger.py
│   ├── test_hardening.py         — rate limit, validation
│   ├── test_identity_thread_part8.py
│   ├── test_libreoffice_converter.py
│   ├── test_link_service.py      — link CRUD + cache invalidation
│   ├── test_migrate.py           — migration verification
│   ├── test_migration_url.py
│   ├── test_rasterizer.py
│   ├── test_retention.py
│   ├── test_storage.py
│   ├── test_viewer_features.py
│   ├── test_viewer_identity.py
│   ├── test_watermark.py
│   └── test_worker_tasks.py
├── integration/
│   ├── test_access.py            — link access flows
│   ├── test_analytics.py         — analytics endpoints (20 tests)
│   ├── test_audit_remediation.py — audit log endpoint
│   ├── test_cleanup_pass.py
│   ├── test_document_processing.py
│   ├── test_enterprise_phase4.py
│   ├── test_enterprise_product.py — end-to-end enterprise
│   ├── test_enterprise_scalability.py
│   ├── test_enterprise_security.py
│   ├── test_phase1.py through test_phase8.py — cumulative sprint tests
│   ├── test_phase_a_cleanup.py
│   ├── test_phase_b_security.py  — security hardening (audit logging, rate limits)
│   ├── test_phase_c1_hardening.py
│   ├── test_phase_d1.py          — viewer pipeline
│   ├── test_phase_d2.py
│   ├── test_phase_e1_security.py
│   ├── test_phase_e2_stability.py
│   ├── test_stability.py
│   ├── test_toc_engine.py
│   ├── test_upload.py
│   ├── test_v31_v32.py           — V3.1 streaming, V3.2 parallel uploads
│   ├── test_viewer.py
│   └── test_viewer_pipeline.py
└── regression/
    ├── test_auth_enforcement.py  — auth regression
    ├── test_group_ownership.py
    ├── test_link_lifecycle.py    — link create/revoke/delete lifecycle
    └── test_security_invariants.py — security invariant regression
```

---

## Coverage Assessment

### Well-covered areas
| Area | Evidence |
|------|---------|
| Authentication | `test_auth.py`, `test_auth_enforcement.py` |
| Analytics endpoints | `test_analytics.py` — 20 tests including `completed` event |
| Link lifecycle | `test_link_lifecycle.py`, `test_access.py`, `test_link_service.py` |
| Viewer pipeline | `test_viewer.py`, `test_viewer_pipeline.py`, `test_phase_d1.py` |
| Security | `test_enterprise_security.py`, `test_phase_b_security.py`, `test_security_invariants.py` |
| Document processing | `test_document_processing.py`, `test_upload.py` |
| Migrations | `test_migrate.py` — verifies schema consistency |
| Watermark | `test_watermark.py` |

### Coverage gaps identified

| Gap | Description |
|-----|-------------|
| GAP-001 | `analytics.py` webhook failure path: the `except Exception` block at line 342 (where logger.warning is called) is not tested with an actual webhook registered. Tests cover the `completed` event succeeding, not the webhook dispatch failing. FIX-001 addressed the crash but the path remains untested. |
| GAP-002 | `orgs.py` list_orgs with multiple orgs: existing tests may not test the N+1 query with multiple orgs. FIX-002 changed the query pattern. |
| GAP-003 | `billing.py` Stripe webhook handler: tested only for correct signature structure. Actual Stripe event types (subscription.created, invoice.payment_failed) depend on Stripe integration. |

---

## Warnings Analysis

All 20 warnings are from test infrastructure, not application code:

1. **botocore DeprecationWarning** (1): `datetime.utcnow()` used internally in botocore. Not our code.
2. **pytest-asyncio** (19): `asyncio_default_fixture_loop_scope` not set. Harmless infrastructure warning.

**No application warnings.**

---

## Test Health

- Tests are fully async (`asyncio: mode=AUTO`)
- Using pytest-asyncio with class-level fixtures (`conftest.py`)
- Integration tests use SQLite in-memory DB (no external dependencies required)
- Tests run in ~66 seconds total — fast enough for CI pre-merge gates
