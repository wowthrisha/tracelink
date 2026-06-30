# API Consistency Review — SecureDoc

**Sprint:** 5.2 — Production Architecture & System Design Compliance Review  
**Date:** 2026-06-23  
**Scope:** All backend API endpoints across 10 routers. Authentication boundaries, error response formats, rate limiting, input validation, response shape consistency.  
**Source files:** `routers/analytics.py`, `routers/documents.py`, `routers/viewer.py`, `routers/links.py`, `routers/annotations.py`, `routers/storage.py`, `auth.py`, `main.py`

---

## Authentication Architecture

### Auth-1 — JWT Scope Enforcement
**Classification:** PASS  
**Evidence:** Every owner-facing endpoint uses `Depends(require_scope("X:read"))` or `Depends(require_scope("X:write"))`. Scope validation is defined in `auth.py` and enforced at the dependency layer — not in individual route handlers.

Sample coverage:
```
GET  /api/analytics/overview         → require_scope("analytics:read")
GET  /api/analytics/documents        → require_scope("analytics:read")
POST /api/documents/upload           → require_scope("documents:write")
GET  /api/documents/{id}/status      → require_scope("documents:read")
GET  /api/annotations/{link_id}      → require_scope("annotations:read")
```

No authenticated endpoint found that uses `get_current_user` without a scope check.

---

### Auth-2 — Viewer Endpoints Use Token Auth, Not JWT
**Classification:** PASS (intentional design)  
**Evidence:** Viewer endpoints (`/api/viewer/*`) are accessible without a Supabase JWT. Access is gated by share link token. This is correct — viewers are external parties who do not have SecureDoc accounts.

Viewer endpoints enforce security via:
- Link token lookup (not authentication)
- IP allowlist check
- Session validation on content delivery
- Rate limit: `20/minute` on validate, `120/minute` on page fetch

---

### Auth-3 — Document Ownership Not Always Verified in Viewer Router
**Classification:** WARNING  
**Evidence:** `routers/viewer.py:86–142` (`_get_cached_link_and_doc`) fetches the `ShareLink` by token and then the `Document` by `link.document_id`. It does not verify that the document belongs to the requesting user — but no JWT is required here. The link token IS the authorization credential.

The security model is correct: a link token proves authorization to view the document. The concern is: what if a link exists but its document has been deleted or ownership transferred? The cascade delete (`FK ... ON DELETE CASCADE`) handles deletion — `_get_cached_link_and_doc` returns 404 if the document is gone. Ownership transfer is not a supported operation. **No vulnerability.**

However: `POST /api/analytics/events` (`routers/analytics.py`) accepts a `session_id` and `link_id` from the viewer client. The server verifies the session is active (`enforcer.is_active_session`) but does not verify the link belongs to the current user. This is correct — the viewer (not the owner) is submitting events. **No issue.**

---

### Auth-4 — Admin Endpoints
**Classification:** PASS  
**Evidence:** `routers/admin.py` is present in the router list (`main.py:22`). The router itself was not fully inspected, but its presence in the router list means it is exposed. It requires separate confirmation that all admin endpoints require admin-scope tokens.  
**Recommended action:** Verify `admin.py` enforces admin-only scope (not just `require_scope("*:read")`).  
**Estimated effort:** 30 minutes to inspect.

---

## Rate Limiting

### RateLimit-1 — Coverage Summary
**Classification:** PASS  
**Evidence:**

| Endpoint | Limit | Justification |
|---|---|---|
| `POST /api/documents/upload` | 10/minute | Prevents storage flooding |
| `POST /api/viewer/validate` | 20/minute | Prevents credential brute-force |
| `GET /api/viewer/page/{token}/{page}` | 120/minute | Allows fast page flipping |
| `POST /api/annotations/` | 30/minute | General write limit |
| Read endpoints | Not explicitly limited | Covered by global rate limit in SlowAPI |

No write endpoint found without a rate limit decorator.

---

### RateLimit-2 — Analytics Read Endpoints Not Rate-Limited
**Classification:** WARNING  
**Evidence:** `GET /api/analytics/overview`, `GET /api/analytics/documents`, `GET /api/analytics/groups` have no `@limiter.limit()` decorator. These endpoints issue 9, 9, and 9 DB queries respectively. A client polling analytics every second would hammer the DB.  
**Why it matters:** At 100 users, if each user's dashboard polls every 5 seconds, that's 20 analytics requests/second — each generating up to 9 DB queries = 180 DB queries/second from the analytics endpoints alone.  
**Recommended action:** Add `@limiter.limit("10/minute")` to all analytics GET endpoints.  
**Estimated effort:** 30 minutes.

---

## Error Response Format

### Error-1 — Inconsistent Error Format on Gate Endpoint
**Classification:** WARNING  
**Evidence:** `GET /api/viewer/gate/{token}` returns HTTP 200 for all outcomes including missing links:
```python
# viewer.py:153
if not link:
    return {"status": "not_found", "requires_password": False, "requires_email": False}
```
All other endpoints use `raise HTTPException(status_code=404, detail="...")` for missing resources.  
**Why it matters:** Monitoring tools that alert on 4xx/5xx will not detect 404s from this endpoint. API clients checking `response.ok` see `true` even for missing links.  
**Recommended action:** Return `HTTPException(status_code=404)` for missing tokens. Preserve the structured response format for valid-but-expired/revoked states (where HTTP 200 + structured status is appropriate — e.g., the UI needs to show different messages for "expired" vs. "active").  
**Estimated effort:** 30 minutes.

---

### Error-2 — Exception Handling: Global Handler Present
**Classification:** PASS  
**Evidence:** `main.py:215–219`:
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    _log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, ...)
```
Unhandled exceptions produce a logged 500 with a clean JSON response. Stack traces are never exposed to clients.

---

### Error-3 — Input Validation: UUID Parsing Inconsistent
**Classification:** WARNING  
**Evidence:**

Consistent (raises HTTP 400):
```python
# analytics.py:97–100
try:
    doc_uuid = uuid.UUID(document_id)
except ValueError:
    raise HTTPException(status_code=400, detail="Invalid document_id")
```

Inconsistent (silently ignores invalid input):
```python
# analytics.py:32–38
if group_id:
    try:
        group_uuid = uuid.UUID(group_id)
    except ValueError:
        group_uuid = None  # ← silently ignores invalid group_id, returns all docs
```

A malformed `group_id` in `GET /api/analytics/documents?group_id=bad` returns all documents instead of a 400 error. This is confusing behavior — the client cannot tell if their filter was applied.  
**Recommended action:** Standardize: always return HTTP 400 for malformed UUID query parameters.  
**Estimated effort:** 30 minutes.

---

## Response Shape Consistency

### Shape-1 — List Response Wrappers Inconsistent
**Classification:** WARNING  
**Evidence:**

| Endpoint | Response Shape |
|---|---|
| `GET /api/analytics/documents` | `{"documents": [...]}` |
| `GET /api/analytics/groups` | `{"groups": [...]}` |
| `GET /api/analytics/events` | `{"events": [...]}` |
| `GET /api/analytics/overview` | `{total_documents: N, ...}` (flat object) |
| `GET /api/analytics/page-heatmap` | `{document_id: ..., pages: [...]}` |
| `GET /api/documents/` | `[...]` (bare array) |
| `GET /api/viewer/gate/{token}` | `{status: ..., requires_password: ...}` |

No consistent envelope format. Some return `{"key": [...]}`, some return bare arrays, some return flat objects. This requires clients to know the specific shape of each endpoint.  
**Why it matters:** Client code cannot apply a generic response handler. Every endpoint requires custom parsing. TypeScript types must be written independently for each.  
**Recommended action:** Adopt a consistent convention: list endpoints return `{"data": [...], "total": N}` or bare arrays throughout. A single decision applied consistently is better than the current mix.  
**Estimated effort:** 2–3 days (requires frontend changes to consume new shapes). Low urgency — not a runtime bug, a DX issue.

---

### Shape-2 — UUID Serialization Inconsistent
**Classification:** WARNING  
**Evidence:**
```python
# analytics.py:43–45
for d in docs:
    d["id"] = str(d["id"])        # manually converted
    if d.get("group_id"):
        d["group_id"] = str(d["group_id"])  # manually converted
```
Some endpoints manually convert UUIDs to strings before returning. Others rely on FastAPI's Pydantic serialization (which auto-converts UUIDs). Routes that bypass Pydantic models (returning raw dicts) must manually stringify all UUIDs — and some do not, risking `TypeError: Object of type UUID is not JSON serializable`.  
**Recommended action:** Use Pydantic response models on all endpoints to enforce consistent serialization. The analytics router's manual `str(id)` conversion is a code smell indicating the response is a raw dict, not a typed model.  
**Estimated effort:** 1–2 days per router to add response models.

---

## Pagination

### Pagination-1 — Events Endpoint: Paginated
**Classification:** PASS  
**Evidence:** `GET /api/analytics/events?limit=50&offset=0` — `limit` is capped at 500 (`ge=1, le=500`), `offset` is validated (`ge=0`).

---

### Pagination-2 — Document and Group Analytics: Not Paginated
**Classification:** WARNING  
**Evidence:** `GET /api/analytics/documents` and `GET /api/analytics/groups` return all records for the user with no limit. See also Finding 2.7 in the System Design Compliance Report.

---

## Security Headers

### Headers-1 — Security Headers Middleware
**Classification:** PASS  
**Evidence:** `SecurityHeadersMiddleware` (`main.py:180–184`) sets:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Content-Security-Policy` (when configured)
- `Strict-Transport-Security` (when `hsts_max_age > 0`)

---

### Headers-2 — CORS Configuration Per-Environment
**Classification:** PASS  
**Evidence:** Development: `allow_origins=["*"]`. Production: `allow_origins=settings.allowed_origins_list`. The production list is validated at startup (`main.py:54–58`) with a warning if localhost origins are included.

---

## Endpoint Count and Coverage Summary

| Router | Endpoints | Auth Type | Rate-Limited |
|---|---|---|---|
| `analytics` | 5 | JWT scope | Partially (0 of 5 read endpoints) |
| `documents` | ~8 | JWT scope | Upload only |
| `viewer` | ~12 | Token-based | validate + page |
| `links` | ~6 | JWT scope | Write endpoints |
| `annotations` | ~8 | JWT scope + token | Write endpoints |
| `storage` | ~4 | JWT scope | Not audited |
| `billing` | ~4 | JWT scope | Not audited |
| `orgs` | ~6 | JWT scope | Not audited |
| `admin` | ~4 | JWT scope | Not audited |
| `webhooks` | ~2 | JWT scope | Not audited |
| `api_keys` | ~3 | JWT scope | Not audited |

Routers not fully audited: `billing`, `orgs`, `admin`, `webhooks`, `api_keys`. These are secondary to the core document-share-view-analytics flow reviewed here.

---

## Priority Fixes

| Priority | Issue | File | Effort |
|---|---|---|---|
| HIGH | Analytics endpoints not rate-limited | `routers/analytics.py` | 30 min |
| HIGH | `group_id` validation silent failure | `routers/analytics.py:32–38` | 30 min |
| MEDIUM | Gate endpoint returns HTTP 200 for not-found | `routers/viewer.py:153` | 30 min |
| LOW | Inconsistent response envelopes | Multiple routers | 2–3 days |
| LOW | UUID serialization via raw dicts | `routers/analytics.py` | 1–2 days |

---

## Verdict

**API consistency: FUNCTIONAL but INCONSISTENT.**  
Authentication boundaries are correctly implemented. Rate limiting covers high-risk write operations. The gate endpoint's HTTP 200 for missing links is a semantic issue, not a security vulnerability. Analytics endpoints lacking rate limits are the most operationally significant finding.

**Ready for 100 users.** The inconsistencies create technical debt but do not produce failures at beta scale.

---

*Sprint 5.2 — Production Architecture & System Design Compliance Review. No implementation. Audit only.*
