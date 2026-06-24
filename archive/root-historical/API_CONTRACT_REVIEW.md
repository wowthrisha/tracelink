# API Contract Review

14 router files, ~80 routes, ~5,821 lines, all registered in `app/main.py:223-237` (no dead router files, no unregistered-but-present routers).

## Full Endpoint Inventory

### admin.py (78 lines, 1 route)
| Method | Path | Auth | Body | Note |
|---|---|---|---|---|
| GET | `/api/admin/audit-log` | `get_current_user` (+ in-body role check if `org_id` passed) | — | Audit log, paginated (`total`, `offset`, `limit`) |

### analytics.py (325 lines, 6 routes)
| Method | Path | Auth | Body |
|---|---|---|---|
| GET | `/api/analytics/overview` | `require_scope("analytics:read")` | — |
| GET | `/api/analytics/documents` | `require_scope("analytics:read")` | query: group_id |
| GET | `/api/analytics/groups` | `require_scope("analytics:read")` | — |
| GET | `/api/analytics/page-heatmap` | `require_scope("analytics:read")` | query: document_id |
| GET | `/api/analytics/events` | `require_scope("analytics:read")` | query: document_id, group_id, limit, offset |
| POST | `/api/analytics/events` | none (share-link token + active session validated in-body) | token, session_id, event_type, page_number, metadata, time_spent_ms |

### annotations.py (1,285 lines, 16 routes — largest router)
| Method | Path | Auth | Body |
|---|---|---|---|
| GET | `/api/viewer/annotations/{token}/{page_number}` | session validation | — |
| POST | `/api/viewer/annotations/{token}` | session validation | AnnotationCreate |
| PUT | `/api/viewer/annotations/{token}/{annotation_id}` | session validation, own-row only | AnnotationUpdate |
| DELETE | `/api/viewer/annotations/{token}/{annotation_id}` | session validation, own-row only | — |
| GET | `/api/viewer/bookmarks/{token}` | session validation | — |
| POST | `/api/viewer/bookmarks/{token}/{page_number}` | session validation | BookmarkCreate |
| PATCH | `/api/viewer/annotations/{token}/{annotation_id}/resolve` | session validation | — |
| GET | `/api/documents/{doc_id}/annotations` | `get_current_user`, owner-only | query: annotation_type, resolved |
| GET | `/api/documents/{doc_id}/annotations/export` | `get_current_user`, owner-only | — |
| GET | `/api/viewer/annotations/{token}/{annotation_id}/thread` | session validation | — |
| POST | `/api/documents/{doc_id}/feedback/{annotation_id}/reply` | `get_current_user`, owner-only | AnnotationReplyCreate |
| GET | `/api/documents/{doc_id}/feedback` | `get_current_user`, owner-only | query: resolved, search, date_from, date_to, page_number, author_role, reviewer |
| GET | `/api/documents/{doc_id}/feedback/reviewers` | `get_current_user`, owner-only | — |
| GET | `/api/documents/{doc_id}/feedback/export` | `get_current_user`, owner-only | same query params as list |
| GET | `/api/documents/{doc_id}/feedback/export-reviewer-activity` | `get_current_user`, owner-only | — |
| GET | `/api/documents/{doc_id}/annotations-visual` | `get_current_user`, owner-only | query: annotation_type |
| GET | `/api/documents/{doc_id}/annotations-visual/export` | `get_current_user`, owner-only | — |

### api_keys.py (215 lines, 5 routes)
POST/GET/GET/PATCH/DELETE on `/api/api-keys[/{key_id}]`, all `get_current_user`. Full key returned once on create only.

### auth.py (133 lines, 1 route)
POST `/api/auth/register` — rate-limited (5/min), no auth (creates account).

### billing.py (247 lines, 4 routes)
GET `/api/billing/status`, POST `/api/billing/checkout`, POST `/api/billing/portal` — all `get_current_user`. POST `/api/billing/webhook` — Stripe HMAC-verified, no JWT.

### documents.py (705 lines, 8 routes)
Upload, reprocess, extract-sidecars, list, status, get, delete, versions — all `require_scope("documents:read|write")`.

### groups.py (253 lines, 7 routes)
Full CRUD + batch document assignment, all `get_current_user`.

### links.py (252 lines, 4 routes)
Create/list/revoke/update, all `require_scope("links:read|write")`.

### notifications.py (131 lines, 1 route)
GET `/api/notifications/stream` (SSE), `get_current_user`, capped at 5 concurrent connections/user.

### orgs.py (503 lines, 12 routes)
Org CRUD, membership CRUD, custom-domain verification — all `get_current_user` + in-body role checks (owner/admin/viewer hierarchy).

### storage.py (241 lines, 3 routes)
Dashboard, forecast (`require_scope("documents:read")`), retention PATCH (`require_scope("documents:write")`).

### viewer.py (1,203 lines, 10 routes — 2nd largest router)
Gate, validate, page, thumb, toc, download, text, search, links, words — all use `link_token` + `session_id` (header/cookie), not JWT. This is correct by design (viewers don't have dashboard accounts) but means none of these 10 routes show a `Depends(get_current_user)` in their signature, which makes naive API-contract tooling flag them as "unauthenticated" — they are not; auth is just a different scheme.

### webhooks.py (250 lines, 7 routes)
Full CRUD + deliveries + test-ping, all `require_scope("webhooks:read|write")`. URL SSRF-validated on create/update (see SECURITY_AUDIT_REPORT.md).

## Contract Inconsistencies

### 1. Response-shape drift across list endpoints
| Endpoint | Shape |
|---|---|
| `GET /api/documents` | `{"documents": [...]}` (no `total`) |
| `GET /api/groups` | `{"groups": [...]}` (no `total`) |
| `GET /api/links` | `{"links": [...]}` (no `total`) |
| `GET /api/webhooks` | `{"webhooks": [...]}` (no `total`) |
| `GET /api/analytics/events` | `{"events": [...], "total": n}` |
| `GET /api/admin/audit-log` | `{"events": [...], "total", "offset", "limit"}` (full pagination) |
| `GET /api/documents/{id}/feedback` | `{"feedback": [...], "total": len(...)}` (in-memory count, no offset) |
| `GET /api/documents/{id}/annotations` | `{"annotations": [...], "total": len(...)}` |

**Impact:** every client integration has to special-case each endpoint's wrapper key and whether `total` reflects a real DB count vs. a post-filter Python `len()`. **Recommendation (P2):** standardize on `{"items": [...], "total": int, "offset": int, "limit": int}` for any new endpoint; backfill existing ones opportunistically (breaking change, needs a frontend `api.js` update in lockstep).

### 2. Export-as-separate-path instead of format negotiation
Three places duplicate a list endpoint as a CSV-export sibling instead of using a query param:
- `/api/documents/{id}/annotations` vs `/api/documents/{id}/annotations/export`
- `/api/documents/{id}/annotations-visual` vs `/api/documents/{id}/annotations-visual/export`
- `/api/documents/{id}/feedback` vs `/api/documents/{id}/feedback/export`

**Recommendation (P3, cosmetic):** Not worth breaking working clients to "fix" — but any *new* export should be `?format=csv` on the existing list route rather than a fourth sibling path.

### 3. Authorization not expressed as a `Depends`
`admin.py:15-78` — the `org_id`-scoped admin-role check lives inside the function body, not in the dependency graph. Functionally correct (verified by tests), but it means OpenAPI-generated docs and any automated contract scanner will not surface "requires admin org role" as part of the route's declared auth. **Recommendation (P2):** extract to a `require_org_role("admin")` dependency, mirroring the existing `require_scope()` pattern used everywhere else.

### 4. Viewer routes show no `Depends` in their signature
All 10 `viewer.py` routes and 7 of the 16 `annotations.py` routes authenticate via `link_token` + `session_id` resolved manually inside the function body (`_get_session_id()`, policy enforcer calls) rather than via a FastAPI dependency. This is consistent across the codebase (not a one-off mistake) but means the auth model isn't visible from the route decorator. **Recommendation (P3):** wrap the existing session-resolution logic in a `Depends(get_viewer_session)` for documentation value; not a security issue since the checks do happen, just an API-contract clarity issue.

## Unused / Duplicate Endpoints
None found — `git grep` against the frontend `api.js` confirms every backend route has at least one caller, and `app/main.py` registers all 14 router files with no orphaned imports.

## Validation & Error Handling
- Pydantic request models (`AnnotationCreate`, `AnnotationUpdate`, `BookmarkCreate`, `LinkCreateRequest`, `GroupCreateRequest`, `RetentionUpdate`, etc.) handle body validation consistently — 422 on schema mismatch is uniform across routers (FastAPI default).
- Manual validation (file type/size in `documents.py`, metadata byte-cap in `analytics.py:log_viewer_event`, date-range parsing in `annotations.py:_parse_filter_date`) raises `HTTPException` with specific status codes (400/404/403/422) consistently — no bare `500` leak points found in the reviewed routers.
- One past production bug (fixed in commit `9505370`): `annotations.py`'s `doc_id` path params were declared as plain `str` (not `uuid.UUID`) and compared directly against a UUID-typed column without parsing first, crashing under SQLite with a raw `AttributeError` instead of a clean 400. Verified this is **not** a repo-wide pattern: `links.py:127,158,202` and `groups.py:85,109,155,183,223-224` correctly type their path params as `uuid.UUID`, so FastAPI parses/validates them before the route body runs. `annotations.py` is the only router using bare `str` for what should be UUID path params — worth a follow-up pass to retype those for consistency, though the crash itself is already patched at each call site.
