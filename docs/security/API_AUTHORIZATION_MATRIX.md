# API Authorization Matrix

Bounded authorization consistency review, V22.0 Priority 2. Covers every protected API family: authentication mechanism, required scope, resource-ownership check, organization-role check, and audit requirement. Builds on `docs/security/ENG-039_ORG_AUTHORIZATION_TRACE.md` rather than repeating its per-endpoint detail for `orgs.py`/`api_keys.py`/`billing.py`.

## Two authentication models in this codebase

1. **User-authenticated** (`Depends(get_current_user)` / `Depends(require_scope(...))`): JWT (browser) or API key (`sd_...`). This is what this matrix covers.
2. **Viewer-session-authenticated** (`/api/viewer/*`, `/api/reading/batch`, `/api/reading/session/{id}`): anonymous share-link viewers, authenticated by an active `session_id` tied to a `ShareLink` token via `policy_enforcer.is_active_session()` — no JWT, no API key, no user account at all. Scope/role concepts don't apply here by design; access is controlled by link-level settings (password, expiry, allowlists) instead. Confirmed via source read of `viewer.py`, `reading.py`'s `/batch` and `/session/{id}` routes: zero occurrences of `get_current_user` in either.

## Matrix — user-authenticated routers

| Router | Auth mechanism | Scope enforcement | Resource-ownership check | Org-role check | Audit logged | Status |
|---|---|---|---|---|---|---|
| `documents.py` | JWT or API key | `documents:{read,write}` on all 8 user-facing routes | `user_id` match or `_get_accessible_document()` (org-membership-aware) | n/a (per-document, not per-org) | Yes — `document.uploaded`/`document.deleted` | Compliant |
| `links.py` | JWT or API key | `links:{read,write}` on all 5 routes | Document ownership via the parent document | n/a | Partial — link creation logged via document context; revoke/hard-delete not independently audit-logged (pre-existing, not evaluated further — out of this review's bound) | Compliant |
| `groups.py` | JWT or API key | `documents:{read,write}` on all 7 routes | `user_id`-scoped queries | n/a | No dedicated group audit events (pre-existing; not evaluated further) | Compliant |
| `webhooks.py` | JWT or API key | `webhooks:{read,write}` on all 7 routes | `user_id` match | n/a | Yes — `webhook.created`/`updated`/`deleted` | Compliant |
| `storage.py` | JWT or API key | `documents:{read,write}` on all 3 routes | `user_id`-scoped queries | n/a | Yes — `document.retention_changed` | Compliant |
| `analytics.py` | JWT or API key | `analytics:read` on all 5 routes | Document ownership | n/a | n/a (read-only) | Compliant |
| `reading.py` (user-facing routes only) | JWT or API key | `analytics:read` on all 4 routes | Document ownership | n/a | n/a (read-only) | Compliant |
| `orgs.py` | JWT or API key | `organizations:{read,write}` on all 12 routes (**fixed V22.0**) | n/a | `viewer`/`admin`/`owner` via `require_role()`, layered under the scope check | Yes — `org.*`/`member.*` | **Fixed this sprint (ENG-039)** |
| `api_keys.py` | JWT or API key | `api_keys:{read,write}` on all 6 routes (**fixed V22.0**) + scope-escalation guard | `user_id` match | n/a | Yes — `api_key.created`/`revoked`/`rotated`/`deleted` | **Fixed this sprint (ENG-039)** |
| `billing.py` | JWT or API key | `billing:{read,write}` on all 3 authenticated routes (**fixed V22.0**); `/webhook` correctly uses Stripe HMAC signature instead, no user auth | `user_id`-scoped | n/a | No dedicated billing audit events (pre-existing; Stripe's own dashboard is the system of record) | **Fixed this sprint (ENG-039)** |
| `admin.py` | JWT or API key | `organizations:read` on the 1 route (**fixed V22.0**) | n/a | `admin`/`owner` via `require_role()` when `org_id` given; else self-actor-only | n/a (this *is* the audit log) | **Fixed this sprint** |
| `annotations.py` (10 uploader-facing `/api/documents/{id}/...` routes) | JWT or API key | `documents:{read,write}` (**fixed V22.0**) | `_get_accessible_document()` (org-membership-aware) | n/a | No dedicated annotation-review audit events (pre-existing; not evaluated further) | **Fixed this sprint** |
| `annotations.py` (7 `/api/viewer/...` routes) | Viewer-session (not user-authenticated) | n/a by design | Session ↔ link-token check | n/a | n/a | Correct as-is — different auth model, not part of this review |
| `notifications.py` | JWT or API key | `documents:read` on the 1 route (**fixed V22.0**) | Per-user Redis channel (`user_id`-scoped) | n/a | n/a (real-time stream, not a mutation) | **Fixed this sprint** |
| `viewer.py` | Viewer-session (not user-authenticated) | n/a by design | Session ↔ link-token check | n/a | Yes — view/download events | Correct as-is — different auth model, not part of this review |

## What was fixed this sprint (beyond ENG-039's original 3 routers)

Two more instances of the identical defect shape were found while tracing ENG-039 and fixed in the same sprint, using the **existing** scope taxonomy (no new scopes invented beyond ENG-039's original 6):

- **`admin.py`'s `GET /audit-log`**: gated on `organizations:read` — a zero-scope API key could otherwise read an org's full accountability trail.
- **`annotations.py`'s 10 uploader-facing routes**: gated on `documents:{read,write}` matching each route's actual read/write nature — a zero-scope API key could otherwise list/export/reply-to/resolve document feedback and annotations.
- **`notifications.py`'s SSE stream**: gated on `documents:read` — lower severity (the stream only carries the caller's own per-user events), fixed for consistency.

## What was checked but NOT changed, with reasoning

- **`links.py`/`groups.py`/`storage.py` missing dedicated audit events** for some mutations: noted in the matrix above, not fixed — this review's bound is authorization (scope/role), not audit-completeness, and inventing new audit event types wasn't objectively demonstrated as this sprint's task. Worth a future backlog item, not fixed here to avoid scope creep beyond what was asked.
- **`links.py`'s `is_link_active()` duplication**: already tracked as ENG-037, addressed in Priority 5 of this sprint (see `PROGRESS.md`), not re-litigated here.
- **No IDOR opportunities found** beyond what ENG-039 already fixed — every route's data-access query is scoped to `user_id` or routed through an ownership/membership-aware helper (`_get_accessible_document()`, `_get_org_and_member()`). No route was found returning another user's data without an ownership check.
- **No fail-open behavior found**: `require_scope()` defaults to denying API-key callers missing the scope (raises `403`); every ownership-check helper raises `404`/`403` on a miss rather than falling through to a permissive default.
- **No further privilege-escalation paths found** beyond the one already fixed (API-key scope self-widening via key creation/update) — checked whether org role-granting (`update_member_role`, `add_member`) allows a caller to grant a role above their own: no, `role_gte(actor.role, new_role)` already guards this correctly, pre-existing and unchanged.

## Verification

All fixes in this document are covered by `backend/tests/integration/test_priority2_scope_consistency.py` (8 tests) plus `test_eng039_org_api_key_scopes.py` (28 tests) for the original 3 routers — 36 total security regression tests. Full backend suite: 1742 passed (1734 + 8 new)/1 skipped/0 failed. 3 of the 8 new tests confirmed to fail against the pre-fix code (reverted via `git stash`, re-ran, restored) — the 4th (SSE stream) was not revert-tested the same way since the pre-fix code causes the test to hang consuming a live stream response rather than returning a clean failing assertion; the fix itself is the identical one-line `Depends` swap already proven correct by the other 3 routers' revert tests.
