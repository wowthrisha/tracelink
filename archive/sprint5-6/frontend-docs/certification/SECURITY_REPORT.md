# SECURITY REPORT — Sprint 6.0 Engineering Excellence
**Date:** 2026-06-29  
**Sprint:** 6.0 (supersedes Sprint 5.5)  
**Method:** Full source code review of all backend routers, middleware, services, security utilities, worker delivery chain

---

## Summary

| Category | Score | Finding |
|----------|-------|---------|
| Authentication | PASS | JWT JWKS validation with key rotation, API key SHA-256 hashing |
| Authorization | PASS | Scope enforcement per endpoint, viewer session validation at every content endpoint |
| SSRF Protection | PASS | RFC 1918 + loopback + link-local + IPv6 ULA + DNS rebinding; TOCTOU re-check on delivery |
| Input Validation | PASS | Pydantic models, coordinate bounds checking, UUID coercion, page_number range validation |
| Security Headers | PASS | CSP with SRI hashes, X-Frame-Options: DENY, HSTS opt-in, COOP, X-Permitted-Cross-Domain-Policies |
| CORS | PASS | Explicit origins in production, no credentials with wildcard |
| Rate Limiting | PASS | slowapi on all write and viewer endpoints; Redis-backed in production |
| Injection Prevention | PASS | No raw SQL; parameterized SQLAlchemy ORM throughout |
| Webhook Security | PASS | SSRF validation at registration + re-validation immediately before HTTP delivery |
| Storage Lifecycle | PASS | All 4 sidecar types (toc, text, links, words) deleted on document removal (FIX-011) |
| Analytics Poisoning | PASS | `page_number`, `time_spent_ms`, `event_type` range-validated; metadata size capped at 1 KB |
| Production Hardening | PASS | Startup refuses unsafe salt/URL config |

**No critical or high security vulnerabilities found.**

---

## Detailed Findings

### AUTH-001 — JWT validation is correct and robust

**File:** `backend/app/auth.py`

- JWKS loaded from Supabase at startup; cached for 1 hour (`_JWKS_TTL = 3600`)
- Algorithm whitelist: `ES256` and `RS256` only — rejects `none` and other weak algorithms
- Audience validation: `audience="authenticated"` — rejects tokens not issued for the app
- Expiry enforced: `jwt.ExpiredSignatureError` → 401
- Key rotation: on `InvalidTokenError`, JWKS is refreshed and decode retried once
- API key auth: SHA-256 hash verified against stored hash; never stored in cleartext
- API key expiry enforced inline with timezone-aware comparison

**Result: CLEAN**

---

### AUTH-002 — Scope enforcement is correctly applied

**File:** `backend/app/auth.py` → `require_scope()`

- JWT users: all scopes granted (owner-level access)
- API key users: must include the required scope or 403 is returned with structured log
- Applied to: all write endpoints, analytics:read, documents:write, webhooks:write, etc.

**Result: CLEAN**

---

### SSRF-001 — Webhook URL SSRF protection is comprehensive

**File:** `backend/app/utils/ssrf_guard.py`

Blocked ranges:
- RFC 1918: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
- Loopback: 127.0.0.0/8, ::1/128
- Link-local / AWS IMDS: 169.254.0.0/16
- Shared address space: 100.64.0.0/10
- IPv6 ULA: fc00::/7
- IPv6 link-local: fe80::/10
- TEST-NET-1/2/3: 192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24
- Class E reserved: 240.0.0.0/4
- 0.0.0.0/8 (this network)
- IPv6 unspecified: ::/128

Hostname blocklist: `localhost`, `metadata.google.internal`, `metadata`, `169.254.169.254`, `fd00::ec2`, `instance-data`

DNS rebinding protection: resolves hostname via `socket.getaddrinfo` and validates **all** returned IPs.

Re-validated at delivery time (`webhook_tasks.py:86`) to prevent DNS rebinding attacks where hostname resolves to private IP after registration.

**Observation:** `allow_http=True` is the default, so webhook URLs can use HTTP instead of HTTPS. This is intentional (comment in code: "webhooks may legitimately use http for internal test servers in dev"). Webhook payloads could be intercepted over HTTP in non-TLS environments.  
**Risk:** LOW for beta (acceptable with documentation). Recommend `allow_http=False` for production deployment.

---

### SEC-HEADERS-001 — Security headers are correctly set

**File:** `backend/app/middleware/security_headers.py`

```
Content-Security-Policy: default-src 'none'; 
  script-src 'self' 'sha384-...' 'sha384-...';
  style-src 'self' https://fonts.googleapis.com 'unsafe-inline';
  font-src 'self' https://fonts.gstatic.com data:;
  connect-src 'self' https://*.supabase.co;
  img-src 'self' blob: data:;
  object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
Cross-Origin-Opener-Policy: same-origin
X-Permitted-Cross-Domain-Policies: none
```

React CDN scripts use SRI (Subresource Integrity) SHA-384 hashes — a CDN compromise delivering different bytes is blocked by CSP.

HSTS: opt-in via `HSTS_MAX_AGE` config. Correctly only sent over HTTPS (checks `x-forwarded-proto`).

**Result: CLEAN**

---

### SEC-CORS-001 — CORS is correctly configured

**File:** `backend/app/main.py`

- Development: `allow_origins=["*"]`, `allow_credentials=False` — no cookies sent cross-origin with wildcard
- Production: `allow_origins=settings.allowed_origins_list`, `allow_credentials=True` — explicit origins required when credentials are enabled

**Result: CLEAN**

---

### SEC-VIEWER-001 — Viewer session security is enforced at every content endpoint

**File:** `backend/app/routers/viewer.py`

Every content endpoint (`/page`, `/thumb`, `/download`, `/search`) validates:
1. `session_id` header present
2. Link not revoked (timestamp check)
3. Link not expired (timestamp check)
4. IP allowlist (if configured on link)
5. `policy_enforcer.is_active_session()` — verifies session exists in DB for this specific link
6. Permission check for download (`can_download`)

Page bounds validated against `doc.page_count` to prevent analytics poisoning.

**Result: CLEAN**

---

### SEC-PROD-001 — Production startup guard prevents unsafe deployment

**File:** `backend/app/main.py`

Refuses to start in production if:
- `SUPABASE_URL` not set
- `APP_PUBLIC_BASE_URL` is localhost or HTTP
- `IP_HASH_SALT` is the default placeholder value
- `DOMAIN_VERIFY_SALT` is the default placeholder value
- `HSTS_MAX_AGE == 0` (HSTS disabled)

**Result: CLEAN**

---

## Observations (Not Bugs)

| ID | Observation | Risk | Recommendation |
|----|-------------|------|----------------|
| OBS-001 | Webhook URLs allow HTTP (not HTTPS-only by default) | LOW | Set `allow_http=False` in `validate_ssrf_url()` for production |
| OBS-002 | JWT stored in `localStorage` | ACCEPTED | Documented risk; acceptable for beta. Mitigated by HTTPS-only in production and short-lived tokens. |
| OBS-003 | `'unsafe-inline'` in CSP `style-src` | LOW | Only inline styles allowed, not inline scripts. Acceptable trade-off for current UI approach. |
