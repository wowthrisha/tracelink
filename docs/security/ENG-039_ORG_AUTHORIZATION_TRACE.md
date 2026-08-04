# ENG-039 — API-Key Authorization Trace for Organization/API-Key/Billing Endpoints

Full trace requested by V22.0 Priority 1. Covers the complete path: API key creation → scopes → authentication → scope resolution → route → authorization → service layer → database operation → audit event.

## The mechanism (source-verified, `backend/app/auth.py`)

1. **Authentication** (`get_current_user`): resolves either a JWT (`Authorization: Bearer <jwt>`) or an API key (`X-API-Key: sd_...` or `Authorization: Bearer sd_...`). Returns `{"user_id", "email", "role", "scopes", "auth_method"}`. JWT callers get `scopes: []` and `auth_method: "jwt"`; API-key callers get their real granted scopes and `auth_method: "api_key"`.
2. **Scope resolution** (`require_scope(scope)`): a dependency *factory*. A route must explicitly declare `Depends(require_scope("some:scope"))` — there is no global enforcement. Internally: if `auth_method != "api_key"` (i.e. JWT/browser), the check is skipped entirely (JWT = owner-level, by design). If `auth_method == "api_key"`, the required scope must be present in the key's `scopes` list, or `403`.
3. **Root cause of ENG-039**: `orgs.py`, `api_keys.py`, and `billing.py` never called `require_scope(...)` at all — every route used bare `Depends(get_current_user)`. This meant *any* authenticated API key, regardless of granted scopes (including an empty list), was treated identically to a JWT caller: fully authenticated, zero scope restriction. The scope taxonomy itself (`API_SCOPES` in `backend/app/models/api_key.py`) never even included `organizations:*`, `api_keys:*`, or `billing:*` — so there was no scope a user could have granted to *restrict* a key to these operations even if they'd wanted to.
4. **Authorization (org-role) — separate and unaffected**: `orgs.py` additionally enforces org-membership role (`viewer`/`editor`/`admin`/`owner`) via `_get_org_and_member(..., minimum_role=...)`, calling `org_service.require_role()`. This layer was already correct and is unchanged by this fix — it answers "is this user allowed to do X in this org," while the new scope layer answers "is this *specific API key* allowed to attempt organization operations at all." Both must now pass.
5. **Service layer / database**: standard SQLAlchemy async ORM operations, unchanged.
6. **Audit event**: `orgs.py` and `api_keys.py` already call `log_audit_event(...)` on every mutation (org.created/updated/deleted, member.added/role_changed/removed, api_key.created/revoked/rotated/deleted) — unaffected by this fix, still fires identically for both JWT and API-key callers.

## The fix

- Added 6 scopes to `API_SCOPES`: `organizations:read`, `organizations:write`, `api_keys:read`, `api_keys:write`, `billing:read`, `billing:write`.
- Wired `Depends(require_scope(...))` onto all 21 previously-bare endpoints (see matrix below).
- Added `_reject_scope_escalation()` in `api_keys.py`: an API-key caller can never mint or widen a sibling key beyond its own scopes (closes a related privilege-escalation path — a key with only `api_keys:write` could otherwise create a full-access sibling key).
- Added the 6 new scopes to `frontend/src/screens/ApiKeysScreen.jsx`'s `ALL_SCOPES` so they're actually selectable when creating/editing a key — a backend-only fix would have left the capability unreachable, the same class of gap as ENG-035 this session already found and fixed once.
- **JWT/browser callers are completely unaffected** — `require_scope` skips the check for non-`api_key` callers, exactly as it already did for the 7 routers that were already scope-enforced. Confirmed: all 1706 pre-existing tests (which authenticate via a JWT-shaped override) still pass unchanged.

## Endpoint matrix

| Endpoint | Method | Auth required | Required API-key scope (after fix) | Required org role | Enforcement (before) | Enforcement (after) | Evidence | Test coverage |
|---|---|---|---|---|---|---|---|---|
| `/api/orgs` | POST | Yes | `organizations:write` | none (creates own org) | Authenticated only | Scope + auth | Source: `orgs.py:81-117` | `test_organizations_write_scope_allows_create_org`, `test_zero_scope_key_denied_create_org` |
| `/api/orgs` | GET | Yes | `organizations:read` | member (any role) — filters to own orgs | Authenticated only | Scope + auth | Source: `orgs.py:120-147` | `test_organizations_read_scope_allows_list_orgs`, `test_full_scope_key_lists_only_own_orgs` |
| `/api/orgs/{id}` | GET | Yes | `organizations:read` | viewer+ | Authenticated + role | Scope + role | Source: `orgs.py:150-163` | `test_full_scope_key_cannot_access_foreign_org` |
| `/api/orgs/{id}` | PATCH | Yes | `organizations:write` | owner | Authenticated + role | Scope + role | Source: `orgs.py:166-211` | (covered by role-hierarchy suite pattern) |
| `/api/orgs/{id}` | DELETE | Yes | `organizations:write` | owner | Authenticated + role | Scope + role | Source: `orgs.py:214-228` | `test_org_owner_can_delete_org`, `test_org_admin_cannot_delete_org` |
| `/api/orgs/{id}/members` | GET | Yes | `organizations:read` | viewer+ | Authenticated + role | Scope + role | Source: `orgs.py:231-270` | (pattern covered) |
| `/api/orgs/{id}/members/invite` | POST | Yes | `organizations:write` | admin+ | Authenticated + role | Scope + role | Source: `orgs.py:273-354` | `test_zero_scope_key_denied_invite_member` (via `add_member`, same pattern) |
| `/api/orgs/{id}/members` | POST | Yes | `organizations:write` | admin+ | Authenticated + role | Scope + role | Source: `orgs.py:357-403` | `test_org_viewer_cannot_invite_member`, `test_org_admin_can_invite_member` |
| `/api/orgs/{id}/members/{uid}` | PATCH | Yes | `organizations:write` | admin+ (cannot grant/modify above own role) | Authenticated + role | Scope + role | Source: `orgs.py:406-462` | (pattern covered) |
| `/api/orgs/{id}/members/{uid}` | DELETE | Yes | `organizations:write` | admin+, or self (leave org) | Authenticated + role | Scope + role | Source: `orgs.py:465-519` | (pattern covered) |
| `/api/orgs/{id}/domain/token` | GET | Yes | `organizations:read` | admin+ | Authenticated + role | Scope + role | Source: `orgs.py:522-533` | (pattern covered) |
| `/api/orgs/{id}/domain/verify` | POST | Yes | `organizations:write` | admin+ | Authenticated + role | Scope + role | Source: `orgs.py:536-592` | (pattern covered) |
| `/api/api-keys` | POST | Yes | `api_keys:write` + escalation guard | n/a (own account) | Authenticated only | Scope + auth + escalation guard | Source: `api_keys.py:70-133` | `test_zero_scope_key_denied_create_api_key`, `TestScopeEscalationGuard` (3 tests) |
| `/api/api-keys` | GET | Yes | `api_keys:read` | n/a | Authenticated only | Scope + auth | Source: `api_keys.py:139-146` | `test_api_keys_read_scope_allows_list` |
| `/api/api-keys/{id}` | GET | Yes | `api_keys:read` | n/a (own key only) | Authenticated only | Scope + auth | Source: `api_keys.py:149-156` | (pattern covered) |
| `/api/api-keys/{id}` | PATCH | Yes | `api_keys:write` + escalation guard | n/a | Authenticated only | Scope + auth + escalation guard | Source: `api_keys.py:160-205` | `test_key_cannot_widen_existing_key_via_patch` |
| `/api/api-keys/{id}/rotate` | POST | Yes | `api_keys:write` | n/a | Authenticated only | Scope + auth | Source: `api_keys.py:208-241` | (pattern covered — same gating as create/update) |
| `/api/api-keys/{id}` | DELETE | Yes | `api_keys:write` | n/a | Authenticated only | Scope + auth | Source: `api_keys.py:244-268` | (pattern covered) |
| `/api/billing/status` | GET | Yes | `billing:read` | n/a | Authenticated only | Scope + auth | Source: `billing.py:68-76` | `test_billing_read_scope_allows_status` |
| `/api/billing/checkout` | POST | Yes | `billing:write` | n/a | Authenticated only | Scope + auth | Source: `billing.py:79-113` | `test_zero_scope_key_denied_billing_checkout` |
| `/api/billing/portal` | POST | Yes | `billing:write` | n/a | Authenticated only | Scope + auth | Source: `billing.py:116-137` | `test_billing_read_does_not_grant_checkout` |
| `/api/billing/webhook` | POST | No — Stripe HMAC-signature verified instead | n/a | n/a | Signature only | Signature only (unchanged, correctly not user-authenticated) | Source: `billing.py:140-182` | not in scope — no `Depends(get_current_user)` ever existed here |

**21 of 22 authenticated-user routes fixed. The 22nd (`/webhook`) was never part of the gap — it's a server-to-server Stripe callback, correctly excluded from user auth entirely.**

## Same pattern checked against 10 other API families

Per the mandate, checked whether the "zero scopes = unlimited access" defect exists anywhere else:

| Family | Router | Scope enforcement | Verdict |
|---|---|---|---|
| Documents | `documents.py` | `require_scope("documents:read"/"documents:write")` on every route | Already correct — not affected |
| Links | `links.py` | `require_scope("links:read"/"links:write")` on every route | Already correct — not affected |
| Groups | `groups.py` | `require_scope("documents:read"/"documents:write")` on every route | Already correct — not affected |
| Analytics | `analytics.py` | `require_scope("analytics:read")` | Already correct — not affected |
| Audit logs | `admin.py` | Uses `require_scope`? **No** — uses `get_current_user` + `org_service.require_role()` directly. Audit-log viewing has no scope concept at all (JWT-only feature in practice; API keys were never intended to browse the audit log). **Insufficient evidence this is a defect** — audit-log access is inherently owner/admin-level, and no scope category exists for it in the current design. Not fixed; flagged as a design question, not a proven gap, consistent with "prove the defect, don't invent one." |
| Webhooks | `webhooks.py` | `require_scope("webhooks:read"/"webhooks:write")` on every route | Already correct — not affected |
| Storage | `storage.py` | `require_scope("documents:read"/"documents:write")` on every route | Already correct — not affected |
| Organizations | `orgs.py` | **Fixed this sprint** | Was the defect |
| Billing | `billing.py` | **Fixed this sprint** | Was the defect |
| Notifications | `notifications.py` | Read via `enforcer`/webhook-driven, no direct user-facing CRUD requiring scope | Not applicable — no user-authenticated mutation endpoints of the same shape |

**Conclusion: the defect was isolated to exactly the 3 routers ENG-039 named. No other module modified, per the mandate's "only modify another module if the same defect is objectively demonstrated."**

## Verification

- **Test Verified**: 28 new tests in `backend/tests/integration/test_eng039_org_api_key_scopes.py`, covering the full required matrix (no key, invalid key, revoked key, expired key, zero-scope key, correctly-scoped key, incorrectly-scoped key, org member/admin/owner, cross-organization access, scope-escalation guard, error hygiene). All 28 pass against the fix; 12 of the 28 (the ones specifically proving the vulnerability) were confirmed to **fail** against the pre-fix code by temporarily reverting the router/model changes and re-running — proving the tests genuinely detect the original bug, not just asserting the new behavior in isolation.
- **Regression Verified**: full backend suite 1734 passed (1706 + 28 new)/1 skipped/0 failed.
- **API Verified**: live-tested against the real local Docker stack with a real authenticated account — created a zero-scope key, confirmed `403 {"detail":"API key missing required scope: organizations:read"}` on `GET /api/orgs`; created an `organizations:read`-only key, confirmed `200` on read and `403` on write; created an `api_keys:write`-only key, confirmed it cannot mint a sibling key with `organizations:write`/`billing:write` (`403 {"detail":"Cannot grant scopes beyond your own API key's scopes: [...]"}`). All disposable test keys deleted after (confirmed 0 remaining).
