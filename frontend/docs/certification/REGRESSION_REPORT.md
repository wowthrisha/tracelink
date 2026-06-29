# REGRESSION REPORT — Sprint 5.5 Engineering Investigation
**Date:** 2026-06-29  
**Sprint:** 5.5 Phase 2

---

## Test Run Summary

| Run | After | Result | Duration |
|-----|-------|--------|----------|
| Baseline | Session start (before any changes) | 1624 passed, 1 skipped, 20 warnings | 66.59s |
| After FIX-001 | `710ff78` — analytics.py logger fix | 1624 passed, 1 skipped, 20 warnings | 66.54s |
| After FIX-002/003/004 | `3290a00` — orgs N+1, admin count, webhooks import | 1624 passed, 1 skipped, 20 warnings | 66.23s |

**Zero regressions across all 3 test runs.**

---

## Test Coverage by Area

| Test File | Tests | Area |
|-----------|-------|------|
| tests/integration/test_analytics.py | 20 | Analytics endpoints including `completed` event |
| tests/integration/test_phase_b_security.py | — | Security, rate limiting, auth |
| tests/integration/test_phase_d1.py | — | Viewer pipeline |
| tests/integration/test_phase_d2.py | — | Document processing |
| tests/integration/test_enterprise_product.py | — | End-to-end enterprise flows |
| tests/integration/test_audit_remediation.py | — | Audit log |
| tests/unit/test_hardening.py | — | Unit: validation, security |
| tests/regression/test_auth_enforcement.py | — | Auth regression |
| tests/regression/test_security_invariants.py | — | Security invariant regression |
| (25 more test files) | — | All areas |

**Total: 1625 tests collected, 1624 passing, 1 skipped.**

---

## Skipped Test

1 test is skipped throughout (present in all 3 runs). This is a pre-existing skip, not caused by any fix in this sprint. It is unrelated to the changes made.

---

## Warnings (20, all pre-existing)

All 20 warnings are:
1. `botocore` DeprecationWarning about `datetime.datetime.utcnow()` (botocore internal, not our code)
2. `pytest-asyncio` warning about unset `asyncio_default_fixture_loop_scope` (test infrastructure, not application code)

Neither warning category was introduced by any Sprint 5.5 fix.

---

## Regression Risk Assessment

| Fix | Regression Risk | Assessment |
|-----|-----------------|------------|
| FIX-001 (analytics logger) | LOW | Added imports at module level; no logic changed. Existing tests hit the completed event path and still pass. |
| FIX-002 (orgs N+1) | LOW | Same output (list of orgs with member counts). Restructured to batch query. Tests verify org listing works. |
| FIX-003 (admin count) | LOW | Same output (total count integer). Changed from len(all_ids) to func.count() subquery. |
| FIX-004 (webhooks import) | NONE | Removed dead code (duplicate import). datetime/timezone still available from module-level import. |

**VERDICT: PASS — No regressions introduced in Sprint 5.5.**
