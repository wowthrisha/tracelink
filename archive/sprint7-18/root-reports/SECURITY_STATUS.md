# Security Status — Sprint 7.0

## Phase 4 scope: low-risk hardening only, no partial migrations

Per this sprint's explicit instruction ("implement ONLY low-risk hardening that does not require API redesign... never implement partial security migrations"), `SECURITY_HARDENING_PLAN.md`'s subject — moving the session token from `localStorage` to an httpOnly cookie (AUTH-006) — was re-evaluated for any safely separable low-risk slice.

**Conclusion: no code was implemented against that plan this sprint.** Every phase in the plan (including "Phase 0," which the plan itself describes as non-breaking) is a step *of* the token-storage migration — implementing even the first step would be exactly the "partial security migration" this sprint was told not to do, since it changes CORS credential semantics and adds a cookie-reading code path ahead of the frontend cutover that depends on it. AUTH-006 remains fully deferred, with `SECURITY_HARDENING_PLAN.md` (produced last sprint) standing as the complete implementation plan, unchanged.

## Security-relevant fixes made this sprint (via Phases 2/3, not Phase 4)

These weren't part of the AUTH-006 migration — they're independent, contained fixes that surfaced during the workflow-completeness and architecture reviews and happened to have security or integrity implications:

| Fix | Why it's security-relevant |
|---|---|
| `groups.py` now enforces `require_scope("documents:read"/"documents:write")` on all 7 endpoints, matching `documents.py`/`links.py` | Closes a real permission-boundary gap: an API key scoped only to `documents:read` could previously still mutate document-group membership. Zero impact on browser/JWT users. |
| Org member self-removal ("leave org") fixed for viewer/editor roles | Not itself a vulnerability, but a legitimate access-control *availability* bug — members were unintentionally trapped in organizations. Two regression tests added. |
| Org member removal now requires confirmation | Was the one destructive action in the entire app with zero "are you sure" step. |
| "Revoke All Access" now accurately reports partial/total failure instead of unconditionally claiming success | This was a false-positive security claim — a user could believe all access was revoked when some links silently remained active. This is the most security-significant fix in this sprint's non-AUTH-006 set. |
| `resolve_annotation` misleading "uploader-facing" comment corrected | Documentation-only fix; the underlying permission question (should any viewer session be able to resolve any other viewer's annotation on a shared link?) is flagged for a product/security decision in `ARCHITECTURE_SCORECARD.md`, not silently resolved by changing behavior. |
| Document upload now writes an audit log entry (`document.uploaded`) | Closes an asymmetry where document *deletion* was audited but creation wasn't — relevant for any compliance/forensics use of the audit log. |

## Known gaps carried forward, not addressed this sprint

- **AUTH-006** (session token in `localStorage`) — unchanged, full plan in `SECURITY_HARDENING_PLAN.md`.
- **AUTH-004** (no ToS/Privacy links) — unchanged, blocked on missing legal content.
- Audit logging gaps on `annotations.py`, `groups.py`, `webhooks.py` mutations, `storage.py:update_retention`, `orgs.py:verify_custom_domain` — see `ARCHITECTURE_SCORECARD.md` for the full list and priority order (webhooks — external URL exposure — ranked highest).
- `annotations.py`'s document-owner endpoints still use bare `get_current_user` rather than `require_scope` — same class of fix as the `groups.py` one made this sprint, not yet applied there.

## Validation

All security-relevant changes ran through the full backend regression suite (`pytest tests/unit tests/integration tests/regression`) — 1701 passed, 1 skipped, 0 failed, including the pre-existing `tests/regression/test_auth_enforcement.py` and `tests/regression/test_security_invariants.py` suites and 2 new tests added for the org self-removal fix.
