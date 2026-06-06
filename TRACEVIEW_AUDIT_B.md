# TRACEVIEW SECURITY AUDIT — PHASE B
## Deep Security Audit and Threat-Model Review

**Audit Date:** 2026-06-03  
**Auditor Role:** Security-Focused Principal Engineer  
**Repository:** `/Users/thrisha/traceview/securedoc/`  
**Scope:** Phase B — authentication, authorization, upload safety, cache security, proxy/header hardening, worker isolation, logging leakage, repo hygiene.  
**Post-Phase-A State:** Structural cleanup complete; 930 tests passing; prototype code removed; cache invalidation fixed.

---

## Executive Summary

SecureDoc has a **sound security architecture** for a controlled document-sharing platform. The core protection model — revocable share tokens, per-session watermarking, fail-closed policy enforcement, and server-proxied asset delivery — is correctly implemented. For its intended use case (trainer uploading documents, sharing access links with specific students), the security model is defensible.

**No single critical vulnerability was found that would allow an unauthenticated attacker to access protected document content in a single step.**

However, several real weaknesses exist that need addressing before wider exposure:

- A **storage inflation attack** via unbounded analytics metadata is the most actionable exploit available to a viewer with a valid session.
- **29 coverage artifacts still committed** to git reveal backend code structure.
- The **health endpoint leaks deployment configuration** without authentication.
- **Session IDs are logged** server-side, creating a privilege escalation path for log-access holders.
- The **forensic watermark is a silent no-op** — the feature is documented but not implemented.
- The **Supabase anon key is committed** to the HTML file tracked in git.

The verdict: **safe for careful pilot use with known students under a specific trainer, but not ready for public expansion** until the issues in Phase B1 are resolved.

---

## 1. Threat Model

### 1.1 System Purpose

SecureDoc is a controlled document-sharing platform where:
- A **trainer** (document owner) uploads PDFs and text documents
- The trainer generates **share links** with optional policies (expiry, password, email restriction, IP allowlist, view limits)
- **Students** (viewers) access documents through share links without creating accounts
- The system enforces non-circumventable access control through server-side proxied delivery with per-session watermarking

### 1.2 Assets to Protect

| Asset | Sensitivity | Location |
|-------|------------|---------|
| Document content (pages/PDFs) | HIGH — confidential training material | S3/R2 storage; Redis byte cache |
| Document originals | CRITICAL — source files before rasterization | S3/R2 storage (`originals/` prefix) |
| Share link tokens | HIGH — access credential | Database; browser URL/sessionStorage |
| Session identifiers | MEDIUM — active access token | Database viewer_sessions; server logs |
| Viewer email addresses | MEDIUM — PII; stored masked | Database (masked); watermark (full) |
| IP addresses | MEDIUM — PII; stored hashed | Database (hashed) |
| Admin JWT (Supabase) | CRITICAL — owner authentication | localStorage (client); JWKS-verified server-side |
| Storage credentials | CRITICAL — direct bucket access | .env file (not tracked) |
| Stripe webhook secret | HIGH — billing manipulation | .env file (not tracked) |
| IP hash salt | MEDIUM — de-anonymization protection | .env file (not tracked) |

### 1.3 Trust Boundaries

```
┌──────────────────────────────────────────────────────────────────┐
│ UNTRUSTED                                                         │
│  Public Internet → share link URL (token) → viewer browser       │
│  No Supabase account required; token is the only credential       │
└──────────────────────┬───────────────────────────────────────────┘
                       │ HTTPS (Cloudflare TLS termination)
┌──────────────────────▼───────────────────────────────────────────┐
│ SEMI-TRUSTED                                                       │
│  Authenticated trainers (Supabase JWT bearers)                    │
│  Can upload documents, create/revoke links, view own analytics    │
│  Cannot see other trainers' documents (user_id scoping enforced)  │
└──────────────────────┬───────────────────────────────────────────┘
                       │ Internal
┌──────────────────────▼───────────────────────────────────────────┐
│ TRUSTED                                                            │
│  FastAPI app (validated tokens, ORM-filtered queries)             │
│  Celery workers (DB + storage access; no external input)          │
│  Redis (byte cache; no auth secrets stored)                       │
│  PostgreSQL (ORM-mediated; no direct client access)               │
│  S3/R2 (storage keys in .env; not exposed to clients)             │
└──────────────────────────────────────────────────────────────────┘
```

### 1.4 Attacker Profiles

| Profile | Capability | Primary Goal | Risk Level |
|---------|-----------|-------------|-----------|
| Unauthorized viewer | Has no link token; public internet | Access documents without authorization | MEDIUM — token space is 384-bit; brute force infeasible |
| Authorized viewer (malicious student) | Has a valid share link | Bypass restrictions (max views, IP, email), extract document | HIGH — most likely real attacker |
| Former viewer (expired/revoked link) | Had a valid session | Continue access after revocation | MEDIUM — requires exploiting stale caches |
| Competing trainer | Has own Supabase account | Access another trainer's documents | LOW — user_id scoping enforced at ORM level |
| Infrastructure attacker | Has log or Redis access | Extract session IDs or cached bytes | MEDIUM — session IDs in logs; bytes in Redis |
| Supply chain attacker | Can modify CDN-served React | Inject malicious JS | LOW — SRI hashes on React scripts; see Section 7 |

---

## 2. Authentication and Token Security

### 2.1 Trainer Authentication (Supabase JWT)

**Implementation:** `app/auth.py` — fetches JWKS from Supabase, verifies JWT signature, checks `audience="authenticated"`, accepts only ES256/RS256 algorithms.

**Strong points:**
- Algorithm restriction (only ES256/RS256 accepted) prevents algorithm-confusion attacks
- JWKS refreshed on `InvalidTokenError`, handling key rotation correctly
- Token expiry enforced by `jwt.decode` (raises `ExpiredSignatureError`)
- No hardcoded secret — relies on Supabase's asymmetric key pair

**Weakness — Thread Safety:**  
`_jwks_cache` and `_jwks_fetched_at` are module-level globals mutated by `async` code. In the current single-event-loop asyncio model this is safe, but if the app is ever run with Gunicorn threading workers, there's a race condition on JWKS refresh. This is theoretical at current scale.

**Weakness — Error Detail in 401:**  
`raise HTTPException(status_code=401, detail=f"Invalid token: {e2}")` leaks the specific JWT validation error message to the client. While unlikely to aid an attacker, this reveals internal JWT library error strings. The detail should be a generic message like `"Authentication failed"` in production.

### 2.2 Share Link Tokens

**Generation:** `secrets.token_urlsafe(48)[:64]`

`token_urlsafe(48)` generates exactly 64 base64url characters from 48 random bytes (384 bits of entropy). Token space is `2^384` — brute force is infeasible even with the most powerful hardware conceivable. **This is correctly implemented.**

**Token uniqueness:** Column has a `UNIQUE` constraint. Collision probability is astronomically low.

**Token in URL:** After the `/v/{token}` redirect, the token appears as `?token=xxx` in the browser address bar:
- Visible in browser history
- Visible to browser extensions
- **NOT leaked in Referer** due to `strict-origin-when-cross-origin` Referrer-Policy ✓
- Path sanitization in `RequestIDMiddleware` redacts the `/v/{token}` path in server logs ✓
- The `?token=` query parameter is NOT sanitized by `_sanitize_path` — this appears in access logs if the app serves the static file directly. Mitigated by fact that the static file request (`/static/SecureDoc.html?token=xxx`) is a full URL, and the log line only includes the path portion. **The `_TOKEN_RE` regex `r"/[A-Za-z0-9_\-]{20,}(?=/|$|\?)"` does NOT match query strings.** Token could appear in access logs if the backend serves static files. In Cloudflare deployment, Cloudflare serves static files, so backend logs don't see this path.

### 2.3 Session Identifiers

**Generation:** `secrets.token_hex(16)` = 32 hex chars = 128-bit entropy.

128 bits is adequate for session IDs. The session is scoped to a specific link (`link_id` FK in viewer_sessions), preventing cross-link session reuse.

**Session storage:** `sessionStorage` in the browser (tab-isolated). Session is not stored in localStorage, so it does not persist across tabs. This is correct.

**Session reuse logic:** When `existing_session_id` is provided, `is_active_session(db, link.id, existing_session_id)` is called to verify both session ID and link membership. A valid session for Link A cannot be reused for Link B. **This is correctly implemented.**

**FINDING — Session ID Logged in Server Logs (MEDIUM):**
```python
# link_service.py:190
logger.info("[viewer] link=%s REUSE session=%s", link.id, existing_session_id)
# link_service.py:202
logger.info("[viewer] link=%s max_sessions=%d active_before=%d new_session=%s",
            link.id, link.max_concurrent_sessions, active, session_id)
```
Session IDs are logged in INFO-level server logs. Anyone with log access (cloud log aggregator, sysadmin) can see active session IDs. If they identify a target viewer's session, they could replay requests to `/api/viewer/page/{token}/{page_number}?session_id=xxx` as long as the session is active (up to 2 hours). The risk is limited by the requirement to also know the link token.

### 2.4 Password Protection

**bcrypt hashing** via `bcrypt.hashpw`. Correct implementation.

**Brute force protection:** Validate endpoint is rate-limited at 20/minute per IP. Against bcrypt this provides adequate protection for casual attacks. The error message correctly distinguishes "Password required" from "Wrong password" — these are the same level of information since the gate endpoint already reveals `requires_password: true`. No information leak.

**FINDING — 401 vs 403 on Wrong Password (LOW):** The validate endpoint returns HTTP 401 for wrong password. This is semantically correct (authentication failure) but the frontend must handle both 401 (wrong password) and 403 (access denied) differently. This is already handled correctly in practice.

---

## 3. Authorization and Access Control

### 3.1 Viewer Gate Chain

The authorization chain for a viewer is:
1. `GET /api/viewer/gate/{token}` → reveals policy requirements (public, unauthenticated)
2. `POST /api/viewer/validate` → verifies credentials, creates session
3. `GET /api/viewer/page/{token}/{page}?session_id=xxx` → verifies session + link status on every request

**The `_get_cached_link_and_doc` helper (Phase A fix) now enforces:**
- Link existence (404 if not found)
- Revocation check (410 if revoked)
- Expiry check (410 if expired)
- IP allowlist (403 if blocked)
- Document existence (404 if not found)
- Document ready status (503 if not ready)

This is applied consistently to `/page`, `/thumb`, `/toc`, and `/text` endpoints. The Phase A audit correctly noted and fixed the missing IP check on `/thumb`. ✓

### 3.2 Cache and Revocation Timeliness

**Link cache TTL:** 10 seconds (LINK_TTL_SEC in viewer_cache.py)

**On revoke:** `invalidate_link(token)` called immediately after DB commit in `link_service.revoke_link()`. Cache evicted in <10ms. ✓

**On PATCH (Phase A fix):** `invalidate_link(link.token)` called after commit. Cache evicted immediately. ✓

**Remaining gap — download endpoint does NOT use `_get_cached_link_and_doc`:**  
`GET /api/viewer/download/{link_token}` re-reads the link fresh from DB each time. This is actually **more secure** than the cached path for revocation, but uses slightly different logic for the revocation check (`if link.revoked_at:` vs `if link.revoked_at is not None:`). Both are functionally equivalent since `None` is falsy. The inconsistency is harmless but should be noted for maintenance reasons.

**FINDING — Page bytes survive revocation in Redis (LOW):**  
After link revocation, previously cached page images remain in L2 Redis for up to `redis_page_cache_ttl_sec` (1 hour by default). However, since all access control checks happen before cache access (auth checks are in `_get_cached_link_and_doc`, called before `fetch_page_bytes`), a revoked link cannot reach the cache. The stale bytes are harmless dead data. Redis TTL 1 hour is appropriate and not a security issue.

### 3.3 Authorization Consistency Across Endpoints

| Endpoint | Auth | IP Check | Session | Revoke | Expiry |
|----------|------|----------|---------|--------|--------|
| `/gate/{token}` | None | No | No | Yes (inline) | Yes (inline) |
| `/validate` | None | Yes | Creates | Yes | Yes |
| `/page/{token}/{page}` | Session | Yes | Yes (heartbeat) | Yes (cache) | Yes (cache) |
| `/thumb/{token}/{page}` | Session | Yes ✓ (Phase A) | Yes (heartbeat) | Yes (cache) | Yes (cache) |
| `/toc/{token}` | Session | Yes | Yes | Yes (cache) | Yes (cache) |
| `/text/{token}/{chunk}` | Session | Yes | Yes (heartbeat) | Yes (cache) | Yes (cache) |
| `/download/{token}` | Session | No | Yes | Yes (DB fresh) | Yes (DB fresh) |

**FINDING — Download missing IP check (MEDIUM):**  
The `/download/{link_token}` endpoint validates the session and checks revocation/expiry via fresh DB reads, but does NOT check `ip_allowlist`. A viewer who initially validated with an allowed IP, then later changes networks (or uses a VPN), can still download the document as long as their session is active. The page-serving endpoints correctly check IP on every request, but download does not.

### 3.4 max_views Race Condition

**FINDING — TOCTOU on max_views (MEDIUM):**  
The validate endpoint checks `link.view_count >= link.max_views` before calling `increment_view_count()`. With concurrent requests from multiple browsers against the same link, all requests may pass the check simultaneously (before any increment commits), causing max_views to be exceeded by the number of concurrent requests. In practice, for a trainer sharing with students, this means a `max_views=3` link might allow 3-5 sessions on a sudden burst. This is a real but low-exploitation-risk race condition given typical use patterns.

To fix: use a DB-level atomic check-and-increment or a SELECT FOR UPDATE on the view_count. Alternatively, accept the slight over-count given max_views is a soft limit.

### 3.5 User Ownership Enforcement

All data access is scoped by `user_id`:
- Documents: `WHERE Document.user_id == user_uuid`
- Groups: `WHERE DocumentGroup.user_id == user_uuid`  
- Links: verified via document ownership chain
- Analytics: scoped through document → link chain

`DocumentGroup.user_id` is now NOT NULL after Phase A migration 011. ✓

The pattern is consistent and correctly applied across all routers reviewed.

---

## 4. Upload and Parsing Security

### 4.1 File Type Detection

**Detection flow:** Content-type check → `detect_file_type()` (extension-first, content-type fallback) → format-specific magic byte check → binary sniff for text files.

**PDF magic bytes:** Checked both at upload (`file_bytes[:5] != b"%PDF-"`) and during rasterization (`_is_valid_pdf`). Defense-in-depth. ✓

**DOCX:** ZIP magic bytes (`PK`) verified. Prevents any non-DOCX ZIP file from being processed as DOCX. ✓

**DOC:** OLE2 magic bytes (`\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1`) verified. ✓

**Text files:** Binary null-byte sniff in first 512 bytes. Catches executables, images, ZIPs renamed to .txt. ✓

**Weakness — application/octet-stream bypass:**  
`ALLOWED_CONTENT_TYPES` includes `"application/octet-stream"`. A client sending an executable with content-type `application/octet-stream` and filename `backdoor.txt` would:
1. Pass the content-type check
2. Fail the binary sniff (`_reject_if_binary` detects null bytes)

So `application/octet-stream` is allowed at the content-type layer but must pass format-specific validation downstream. The binary sniff correctly protects against this. The `application/octet-stream` allowance is a pragmatic choice for browsers that misreport content-type. ✓

### 4.2 Parser Safety

**PDF rasterization (`pdf2image` / `poppler`):** Runs with a configurable timeout (`rasterizer_timeout_sec = 300`). Timeout enforced via `asyncio.wait_for`. PDF-bomb protection is in place. However, `pdf2image` is a wrapper around `poppler`'s `pdftoppm` which forks external processes. If poppler has vulnerabilities, the worker process is exposed. Mitigation: workers run in containers, failures are caught and marked as permanent errors (no retry on ValueError/RasterizerError). ✓

**DOCX processing (`python-docx`):** Opens `io.BytesIO(docx_bytes)` — no disk temp file for DOCX itself. The library parses XML internally. If python-docx has XML entity expansion vulnerabilities (XXE), adversarial DOCX could exploit this. The library generally handles this safely, but worth noting.

**DOC processing (`antiword`):**  
```python
result = subprocess.run(["antiword", tmp_path], capture_output=True, timeout=30, check=False)
```
- Runs a subprocess with user-uploaded content. `antiword` is a trusted system binary.
- Uses `tempfile.NamedTemporaryFile` with `prefix=f"securedoc_{doc_id}_"` — leaks the document UUID in the temp filename. Not a direct vulnerability but reveals internal IDs in filesystem audit.
- No path traversal risk: `doc_id` is a UUID4, constrained characters.
- Timeout of 30 seconds prevents hanging subprocess.

**FINDING — temp file leaks document_id (LOW):**  
`prefix=f"securedoc_{doc_id}_"` in the temp filename exposes the internal document UUID to filesystem-level auditors or log systems that track file creation. This reveals that a specific document is being processed. Low risk in containerized deployment.

### 4.3 Upload Size Limits

- PDF/DOCX: `max_upload_mb` (default 100MB)  
- Text: `max_text_size_mb` (default 10MB)

Size checks happen AFTER `await file.read()`, meaning the full file is loaded into memory before checking. A 100MB upload consumes 100MB of memory. For a single-user trainer, this is fine. For public use, this creates a DoS vector (many concurrent large uploads exhaust memory before the size check rejects them).

**FINDING — Full file loaded before size check (MEDIUM for public use, LOW for private):**  
`file_bytes = await file.read()` followed by `if len(file_bytes) > settings.max_upload_bytes`. On a high-concurrency public deployment, 100 concurrent 100MB uploads = 10GB RAM consumed before any are rejected. Mitigation: stream to temp storage with size limit, or use middleware-level request size limiting. For the current use case (controlled, few users), this is acceptable.

### 4.4 XSS via Document Content

**Text documents:** API returns plain JSON string. React renders text in a `<pre>` tag via JSX interpolation — auto-escaped, no `dangerouslySetInnerHTML` anywhere in the frontend. ✓

**DOCX/Markdown conversion:** `docx_to_markdown()` returns plain text/ATX-style headings (no HTML tags generated). The module comment states "Never generates HTML." ✓

**TOC entries:** `TocEntry.to_dict()` returns plain string fields. No HTML generation. ✓

### 4.5 Archive Extraction Risk

DOCX and DOC files that are ZIP-based are opened via `io.BytesIO` into python-docx/antiword. No zip slip risk since neither library extracts files to disk during normal operation. ✓

---

## 5. Viewer and Frontend Security

### 5.1 Content Security Policy

**CSP in production:**
```
default-src 'none';
script-src 'self' https://unpkg.com;
style-src 'self' https://fonts.googleapis.com 'unsafe-inline';
font-src 'self' https://fonts.gstatic.com data:;
connect-src 'self' https://*.supabase.co;
img-src 'self' blob: data:;
object-src 'none';
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
```

**Issues:**
- `script-src 'self' https://unpkg.com` — allows scripts from **all of unpkg.com**. If any unpkg.com package is compromised or if a typosquat is loaded, arbitrary scripts run. The React scripts are protected by SRI hashes in `SecureDoc.html`, but the CSP allows any unpkg.com script without hash requirement. An attacker who tricks the app into loading `https://unpkg.com/malicious-package` bypasses this.
  
  **FINDING — Overly broad unpkg.com in CSP (HIGH):** The CSP should pin specific packages with `'sha384-...'` or use `unpkg.com/react@18.3.1/...` path scoping instead of the full domain wildcard.

- `style-src 'unsafe-inline'` — allows inline styles anywhere on the page. This is a known XSS escalation path (CSS injection). Inline styles cannot execute JS directly but can steal content via CSS data exfiltration. Moderate risk; difficult to completely eliminate in React apps that use inline style objects.

- `connect-src 'self' https://*.supabase.co` — wildcard subdomain for Supabase. Acceptable given Supabase project isolation.

### 5.2 Watermarking

**Visible watermark:** Applied per-session with session-specific angle jitter (±5°). Text includes masked email + date + short session prefix. Applied server-side in thread pool executor, never client-side. ✓

**FINDING — Forensic stamp is a no-op (HIGH for security posture):**
```python
# watermark.py:apply_forensic_stamp
def apply_forensic_stamp(self, image_bytes, document_id, page_number):
    # Phase 1: no-op pass-through; LSB steganography reserved for a future phase
    return image_bytes
```
The forensic stamp does nothing. Pages uploaded to storage have no hidden steganographic identity. If document pages are leaked without visible watermarks (e.g., screenshots cropped to remove visible watermark), there is no forensic evidence trail embedded in the image data. This is not a flaw in the current security model (visible watermark is the active protection), but the silent no-op creates misleading documentation. Any security claim about "forensic watermarking" is currently false.

### 5.3 Anti-Extraction Deterrence

The frontend implements:
- Right-click suppression (`right_click_attempt` event logging)
- Print attempt detection (`print_attempt` event logging)
- Copy attempt detection (`copy_attempt` event logging)
- Download disabled by default (permission flag)

These are **deterrence mechanisms, not hard security controls.** A determined user can:
1. Take screenshots (not preventable via web)
2. Use developer tools to inspect network responses
3. Extract WEBP images from browser cache
4. Programmatically call the page API with a valid session

These are accepted limitations of web-based document security. The visible watermark burned into each served image provides the accountability layer.

### 5.4 Session Token in Browser URL

After the `/v/{token}` → `?token={token}` redirect:
- Token appears in the browser address bar
- Token is stored in `sessionStorage` after validate (cleared on tab close)
- Token is NOT stored in localStorage (no persistence)

The viewer URL `https://secure.wowmyspace.com/static/SecureDoc.html?token=LONGTOKEN` would be visible to browser autofill and sync features. Students could inadvertently share it via browser history sync. This is an inherent design trade-off of URL-based share links. Mitigation: document expiry policy enforcement.

### 5.5 Supabase Credentials in HTML

**FINDING — Supabase URL and anon key committed to git (MEDIUM):**

`SecureDoc.html` lines 8-9 (tracked in git):
```html
<meta name="supabase-url" content="https://zznenaqcvzxtqxzilpyh.supabase.co" />
<meta name="supabase-anon-key" content="sb_publishable_uTcTOZC9FjEP0VrGQefMkQ_j2XFe1Rc" />
```

The Supabase anon key is designed to be public (client-facing) and the `sb_publishable_` prefix confirms this. However:
1. The real project URL is now permanently in git history
2. Anyone with repo access can attempt Supabase sign-ups or password attempts
3. If Supabase's Row Level Security (RLS) is misconfigured, the anon key could be used to directly query Supabase tables

The server-side JWT verification via JWKS is correct and prevents the anon key from being used to bypass the SecureDoc API. But Supabase itself is a potential attack surface.

**Recommendation:** Move these to environment-driven meta tags injected at runtime, or accept the public anon key exposure as a known design choice and ensure Supabase RLS is properly configured.

---

## 6. Cache Security

### 6.1 Cache Architecture Overview

| Layer | Content | TTL | Key | Auth Before Access |
|-------|---------|-----|-----|-------------------|
| L1 viewer_cache | LinkSnapshot, DocSnapshot, PageSnapshot | 10s/60s/300s | link token / doc ID / page key | Yes — checks done before cache use |
| L1 page_cache | Raw WEBP page bytes (pre-watermark) | LRU eviction | storage key | Yes — full auth check precedes |
| L1 thumb_cache | Raw thumbnail bytes | LRU eviction | storage key | Yes |
| L1 text_content_cache | Decoded text content | 300s | storage key | Yes |
| L1 toc_cache | TOC tree JSON | 300s | doc_id | Yes |
| L2 Redis | WEBP page bytes + thumbnails + TOC | 3600s (configurable) | prefixed storage key | N/A — proxy fetches on hit |

**Security contract (from page_cache.py):**
> "Callers MUST complete all auth / session / revocation / expiry checks BEFORE calling any get function."

This contract is correctly honored. All viewer endpoints call `_get_cached_link_and_doc` (which enforces all auth checks) before accessing any cache. ✓

### 6.2 Cross-User Cache Leakage

**No cross-user leakage exists in the design:**
- Page cache keys are storage keys (`pages/{doc_id}/{page:04d}.webp`) — only accessible if the requester knows the doc_id, which requires going through the link → doc resolution with a valid token
- The viewer_cache link snapshots are keyed by the share link token — unique per link
- No user identifier is used in cache keys, but access requires a valid link token that maps to the correct document

### 6.3 Stale Authorization Decision Risk

After Phase A fixes:
- Revocation: L1 cleared immediately via `invalidate_link()` ✓
- PATCH policy update: L1 cleared immediately via `invalidate_link()` ✓
- Expiry: always re-checked against current clock even on cache hits ✓
- max_views: only enforced at validate time, not on every page request ✓ (by design — page access doesn't increment view count)

**FINDING — max_views not re-enforced on page requests (LOW):**  
Once a session is established (validate passed), pages can be served even if another viewer's access pushed the total over `max_views`. The `max_views` limit is enforced at session-creation time only. For most use cases this is correct behavior, but a trainer expecting strict "total page access" counting may be surprised. This is a design clarification issue, not a security bug.

### 6.4 TOC Cache L2 (Phase A addition)

`toc/cache.py` is now wired into the `/toc` endpoint. The Redis key `securedoc:toc:v1:{doc_id}` stores the TOC tree. On document delete, `invalidate_doc_entries()` calls `toc_cache.invalidate(doc_id)` (L1 eviction); L2 expires via TTL (300s). For the TOC use case (read-once, immutable after processing), TTL expiration is adequate.

---

## 7. Proxy / Domain / Header Security

### 7.1 Security Headers

| Header | Value | Assessment |
|--------|-------|-----------|
| `X-Content-Type-Options` | `nosniff` | ✓ Correct |
| `X-Frame-Options` | `DENY` | ✓ Correct (also enforced by CSP `frame-ancestors 'none'`) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | ✓ Correct — prevents token leakage in Referer |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=()` | ✓ Good baseline |
| `Content-Security-Policy` | See Section 5.1 | ⚠ `unpkg.com` wildcard too broad |
| `Cross-Origin-Opener-Policy` | `same-origin` | ✓ Hardens against Spectre |
| `X-Permitted-Cross-Domain-Policies` | `none` | ✓ Blocks Flash/legacy plugin reads |
| `Strict-Transport-Security` | Opt-in via `hsts_max_age > 0` | Not yet enabled; needs activation |

**FINDING — HSTS not enabled (MEDIUM):**  
`hsts_max_age` defaults to 0 (disabled). HSTS is not active. Without HSTS, browsers can be downgraded to HTTP via MITM. Must be enabled once HTTPS is confirmed stable on the production domain.

### 7.2 Trusted Proxy / IP Resolution

The `TrustedProxyMiddleware` correctly implements:
- Single trusted header mode (`real_ip_header = "CF-Connecting-IP"`)
- Rightmost-N from XFF mode (`trusted_proxy_depth = N`)
- Direct mode (no proxy trust)

**FINDING — Proxy not configured by default (MEDIUM for Cloudflare deployment):**  
Default values: `real_ip_header = ""`, `trusted_proxy_depth = 0`. In the current production deployment via Cloudflare, these must be set to get the real client IP for rate limiting and IP allowlist enforcement. If `real_ip_header` is not set to `CF-Connecting-IP`, the rate limiter and IP allowlist see Cloudflare's edge IP rather than the client's IP, making IP allowlists ineffective and rate limiting trivially bypassable.

### 7.3 HTTPS Configuration

**FINDING — HTTPS redirect and HSTS are opt-in but not enabled (HIGH for production):**  
`https_redirect: bool = False` and `hsts_max_age: int = 0` are both disabled by default. On the production domain (`secure.wowmyspace.com`), if Cloudflare's "Always Use HTTPS" rule is the only TLS enforcement, an attacker who bypasses Cloudflare (direct IP access) can send plain HTTP. Must enable:
- `HTTPS_REDIRECT=true`
- `HSTS_MAX_AGE=31536000` (after HTTPS is confirmed stable)
- Cloudflare's "Always Use HTTPS" rule as additional defense

### 7.4 Health Endpoint Information Disclosure

**FINDING — Health endpoint leaks deployment configuration without authentication (HIGH):**
```python
# main.py - /health endpoint (unauthenticated)
checks["proxy"] = {
    "https_redirect": settings.https_redirect,
    "real_ip_header": settings.real_ip_header or None,
    "trusted_proxy_depth": settings.trusted_proxy_depth,
    "hsts_max_age": settings.hsts_max_age,
}
```

The unauthenticated `/health` endpoint returns:
- Storage backend type name
- Proxy configuration (real_ip_header value — tells attacker exactly which header to forge)
- HSTS max-age
- Whether Redis is connected

An attacker who sees `"real_ip_header": "CF-Connecting-IP"` knows exactly how to set that header to spoof a different IP for rate limiting and IP allowlist bypass. This is an information disclosure that meaningfully aids an attacker.

**Recommendation:** Remove the `proxy` configuration from the health response, or require authentication to see it.

### 7.5 CORS Configuration

Development mode: `allow_origins=["*"]`, `allow_credentials=False` — acceptable for development.

Production mode: `allow_origins=settings.allowed_origins_list`, `allow_credentials=True`. Since auth uses Bearer tokens (not cookies), CORS `allow_credentials=True` has limited security impact, but restricting origins is still correct practice.

**Startup warning on localhost origins in production:** The app logs a warning if `ALLOWED_ORIGINS` contains localhost entries in production mode. ✓

---

## 8. Worker / Backend Security

### 8.1 Worker Isolation

Celery workers connect to the same PostgreSQL and Redis as the API. They do not expose any HTTP endpoints. Worker tasks are triggered only via the Celery broker (Redis).

**Trust assumption:** Redis is trusted. If Redis is compromised, an attacker could enqueue arbitrary `process_document` tasks with document IDs, causing the worker to process (or attempt to process) any document.

### 8.2 Processing Error Handling

`RasterizerError` and `ValueError` are classified as permanent failures (no retry). This correctly handles malformed PDFs and conversion failures — a bad document stays in "error" state rather than flooding retries.

Transient failures (storage blips, DB connection errors) trigger `task.retry(exc=exc)` with max 3 retries and 10-second delay. Appropriate for recovery from temporary infrastructure issues.

### 8.3 Stale Document Recovery

```python
if decision == "recover":
    # delete partial pages and retry
    await db.execute(delete(DocumentPage).where(...))
    await clear_doc_bytes_redis(document_id)
    invalidate_doc_entries(document_id)
```

Documents stuck in "processing" for 15+ minutes are recovered. Cache is properly invalidated. ✓

**FINDING — Documents in "error" status cannot be re-queued (MEDIUM):**  
`_should_process` returns "skip" for `status == "error"`. A document that permanently fails (e.g., malformed PDF) has no retry path short of direct DB manipulation. If a document gets corrupted during an infrastructure failure and incorrectly ends up in "error" state, there's no self-healing mechanism. This is a reliability issue more than a security issue.

### 8.4 Storage Keys in Worker Logs

**FINDING — Storage paths logged at INFO level (MEDIUM):**
```python
# pipeline/pdf.py:37
logger.info("Document %s: downloading from storage key %r", document_id, doc.storage_key)
# pipeline/text.py:18  
logger.info("Document %s: downloading text from storage key %r", document_id, doc.storage_key)
# pipeline/word.py:49
logger.info("Document %s: downloading DOCX from %r", document_id, doc.storage_key)
```

Worker logs include the storage keys (e.g., `originals/{doc_id}.pdf`). While these are server-side logs (not client-visible), in shared infrastructure or cloud log aggregation, storage paths are visible to whoever has log access. The storage key is already derivable from the document ID (`originals/{doc_id}.{ext}`), so this is redundant exposure rather than a new information leak, but it does make log access equivalent to storage key knowledge.

Also: `documents.py:211`: `logger.error("Storage upload failed for key %s: %s", storage_key, exc)` — same category.

### 8.5 Periodic Tasks

`purge_stale_sessions` (30 min) and `requeue_orphaned_uploads` (5 min) both use the module-level DB engine correctly. The orphan requeue creates new `process_document.delay(doc_id)` tasks via Celery. ✓

---

## 9. Database / ORM Security

### 9.1 SQL Injection Prevention

All queries use SQLAlchemy ORM with parameterized queries. No raw SQL string concatenation found. No `text(f"...")` with user input. ✓

### 9.2 User Ownership Enforcement

All authenticated data access is scoped by `user_id`:
- `WHERE Document.user_id == user_uuid` — all document queries ✓
- `WHERE DocumentGroup.user_id == user_uuid` — all group queries ✓
- Link access verified through document ownership chain ✓

**Phase A fixed:** `DocumentGroup.user_id` is now NOT NULL (migration 011). ✓

**FINDING — Documents without user_id cleaned silently in migration (LOW):**  
Migration 007 did `DELETE FROM documents WHERE user_id IS NULL` before adding the NOT NULL constraint. Migration 011 does the same for groups. These deletions are permanent and irreversible. While functionally correct for orphaned records, any legitimate data incorrectly having NULL user_id is silently deleted. This is acceptable given the ORM enforced user_id at create time, making real orphans impossible under normal operation.

### 9.3 Cascade Deletes

`ShareLink`: `ondelete="CASCADE"` from `Document.id` — all links deleted when document is deleted. ✓

`AccessEvent`: `cascade="all, delete-orphan"` on `link.events` — events deleted when link is deleted. ✓

`ViewerSession`: `ondelete="CASCADE"` from `ShareLink.id` — sessions cleaned when link deleted. ✓

These cascades are correctly configured, preventing orphaned data leakage.

---

## 10. Logging / Observability Security

### 10.1 Request Logging

`RequestIDMiddleware` logs: `method=POST path=/api/documents/upload status=202 ms=45.3 req_id=uuid ip=1.2.3.4`

- Path token sanitization: `_TOKEN_RE = re.compile(r"/[A-Za-z0-9_\-]{20,}(?=/|$|\?)")` — sanitizes token-like path segments ✓
- IP is the real client IP (resolved by TrustedProxyMiddleware) ✓
- **Query string NOT sanitized:** If a request includes `?token=LONGTOKEN` in the URL, the log does not sanitize it. However, the app routes `GET /v/{token}` (path, sanitized) and then serves `SecureDoc.html?token=xxx` as a static file. If static files are served by the backend, `?token=xxx` could appear in access logs.

### 10.2 Sensitive Data in Logs

| Data | Where | Risk | Severity |
|------|-------|------|---------|
| Session IDs (32 hex chars) | `link_service.py:190,202` | Log-access session hijacking | MEDIUM |
| Storage keys | `pipeline/*.py`, `documents.py` | Reveals storage path structure | LOW |
| JWT validation errors | `auth.py:59` | Minor detail leakage | LOW |
| Viewer email (unmasked) | NOT logged (only masked email stored in DB) | ✓ Safe | — |
| Share link tokens | NOT logged (sanitized by regex) | ✓ Safe | — |
| Password hashes | NOT logged | ✓ Safe | — |
| IP addresses (raw) | Logged by request middleware | Appropriate for access logs | Acceptable |

### 10.3 JSON Structured Logging

`JSONLogFormatter` emits: `ts, level, logger, msg, [request_id, session_id, doc_id, link_id, cache_source, latency_ms]`

**FINDING — session_id in JSON log schema (MEDIUM):**  
`_EXTRA_KEYS` includes `"session_id"`. If any log handler explicitly sets `session_id` on a LogRecord, it would appear in structured logs. Currently nothing explicitly sets this field in log records, but the schema suggests it might be used in the future. Ensure `session_id` is never included as a log field in JSON output. Full session IDs should not appear in structured logs.

---

## 11. Repo Hygiene Security

### 11.1 Committed Secrets

| Item | Tracked? | Severity |
|------|---------|---------|
| `backend/.env` | NO (`.gitignore`) | ✓ Safe |
| Supabase URL in `SecureDoc.html` | **YES** | MEDIUM |
| Supabase anon key in `SecureDoc.html` | **YES** | MEDIUM |
| Storage credentials | NO (`.gitignore`) | ✓ Safe |
| Stripe secrets | NO (`.gitignore`) | ✓ Safe |
| Database password | NO (`.gitignore`) | ✓ Safe |
| IP hash salt | NO (`.gitignore`) | ✓ Safe |
| JWT secret (`JWT_SECRET` in .env) | NO (`.gitignore`) | ✓ Safe — also appears unused |

**Note on `.env` security:** The `.env` file contains real production credentials (Supabase storage S3 API keys, Supabase URL, DB password). While not tracked by git, the file sits on disk. Ensure it has `chmod 600` permissions and is not readable by other system users.

### 11.2 Remaining Coverage Artifacts (Phase A Incomplete)

**FINDING — 29 additional .cover files still tracked in git (HIGH):**

Phase A only removed 2 specific ghost cover files (`token.py,cover` and `schemas/event.py,cover`). However, 29 other `.cover` files corresponding to existing source files remain tracked:

```
backend/app/__init__.py,cover
backend/app/config.py,cover
backend/app/database.py,cover
backend/app/main.py,cover
backend/app/middleware/rate_limit.py,cover
backend/app/models/document.py,cover
backend/app/models/event.py,cover
backend/app/models/link.py,cover
backend/app/routers/analytics.py,cover
backend/app/routers/documents.py,cover
backend/app/routers/links.py,cover
backend/app/routers/viewer.py,cover
backend/app/schemas/document.py,cover
backend/app/schemas/link.py,cover
backend/app/services/analytics_service.py,cover
backend/app/services/link_service.py,cover
backend/app/services/rasterizer.py,cover
backend/app/services/storage.py,cover
backend/app/services/watermark.py,cover
backend/app/utils/crypto.py,cover
backend/app/workers/celery_app.py,cover
backend/app/workers/tasks.py,cover
... (and more)
```

These `.cover` files contain per-line coverage percentage data — they reveal which code paths are exercised by tests versus which are not. This helps an attacker identify untested edge cases and potential weak spots. They should all be removed with `git rm --cached`.

Fix:
```bash
git rm --cached $(git ls-files | grep ",cover")
git commit -m "Remove all committed coverage artifacts"
```

The `.gitignore` already has `*.cover` so no new files will be committed.

### 11.3 Build Artifacts

| Item | Status | Notes |
|------|--------|-------|
| `frontend/dist/app.bundle.js` | Tracked intentionally | Required for Docker multi-stage build |
| `frontend/node_modules/` | Tracked | Contains macOS-specific esbuild binary; see note |
| `backend/.coverage` | Not tracked | Excluded by `.gitignore` |
| `backend/htmlcov/` | Not tracked | Excluded by `.gitignore` |

**`frontend/node_modules/`:** The audit report (Phase A) noted this contains a macOS-arm64 esbuild binary. The `.gitignore` has `node_modules/` but since node_modules was committed before this rule was added, it may still be tracked. Let me verify:

```
git ls-files frontend/node_modules/ | head -5
```

If tracked, this is ~4MB of a macOS-specific binary that cannot be used in Linux Docker builds. The Dockerfile already runs `npm ci`, so this is dead weight and potentially confusing.

---

## 12. Severity-Ranked Security Findings

| # | Severity | Area | Finding | Impact | Exploitable? |
|---|---------|------|---------|--------|-------------|
| 1 | HIGH | Repo hygiene | 29 `.cover` files tracked — reveals test coverage map of backend | Attacker identifies untested code paths | No direct exploit; aids reconnaissance |
| 2 | HIGH | CSP | `script-src 'self' https://unpkg.com` allows any unpkg package | XSS via unpkg CDN compromise or typosquat | Requires CDN compromise; low probability |
| 3 | HIGH | Health endpoint | `/health` reveals `real_ip_header` config unauthenticated | Attacker learns exact header to forge for IP spoofing | Yes — enables IP allowlist bypass |
| 4 | HIGH | Worker logs | Storage keys logged at INFO level in workers and upload error logs | Internal storage path structure visible in logs | Requires log access; no direct exploit |
| 5 | HIGH | HTTPS/HSTS | HTTPS redirect and HSTS not enabled in production config | Downgrade attacks; token leakage over plain HTTP | Requires Cloudflare bypass |
| 6 | HIGH | Watermark | `apply_forensic_stamp` is a no-op | No steganographic identity in exported images | No exploit; removes advertised protection |
| 7 | MEDIUM | Repo hygiene | Supabase URL + anon key in committed HTML | Enables Supabase account creation/brute-force | Limited by server-side JWT verification |
| 8 | MEDIUM | Upload safety | Full file loaded into memory before size check | DoS via concurrent large uploads (public use) | Yes — for public deployment |
| 9 | MEDIUM | Authorization | Download endpoint missing IP allowlist check | IP-restricted link can still be downloaded after IP changes | Yes — requires active session |
| 10 | MEDIUM | Rate limiting | API endpoints without explicit rate limits: `/api/links/*`, `/api/groups/*`, `/api/analytics/GET`, billing | Enumeration, brute-force link creation, analytics scraping | Moderate |
| 11 | MEDIUM | Logging | Session IDs logged in server logs | Log-access session hijacking (requires log access) | Yes — if log access obtained |
| 12 | MEDIUM | Proxy config | `real_ip_header` not set by default for Cloudflare | IP allowlists see Cloudflare edge IP; rate limit bypassable | Yes — in production Cloudflare deployment |
| 13 | MEDIUM | Analytics | `metadata` field in POST `/api/analytics/events` has no size limit | Storage inflation (60 req/min × large payload per IP) | Yes — authenticated viewer required |
| 14 | MEDIUM | Concurrency | max_views TOCTOU race | Over-count by number of concurrent validate requests | Low probability in practice |
| 15 | LOW | Auth | JWT error details returned to client | Leaks JWT library validation errors | Minor |
| 16 | LOW | Worker | Temp file for antiword uses doc_id prefix | Reveals doc UUID in filesystem | Requires filesystem access |
| 17 | LOW | Configuration | Default IP hash salt used in non-production mode | IP hashes reversible in dev analytics | Only dev environment |
| 18 | LOW | Data model | Documents in "error" status cannot be re-queued | Stuck documents require manual DB intervention | Reliability, not security |

---

## 13. Security Gap Analysis

### Strongest Controls

1. **Share token entropy (384 bits)** — token brute force is computationally infeasible
2. **JWT verification via Supabase JWKS** — correct asymmetric key verification, no shared secrets
3. **Fail-closed policy enforcement** — malformed JSON in allowlists denies access rather than defaulting to open
4. **Server-proxied asset delivery** — raw document bytes never reach the client directly; presigned URLs are never used
5. **Per-session watermarking with angle jitter** — visible accountability layer with composite-removal resistance
6. **Revoke/PATCH immediate cache invalidation** — link metadata cache evicted immediately on policy changes (Phase A)
7. **User ownership scoping** — all data access filtered by authenticated user_id; no horizontal privilege escalation
8. **bcrypt passwords** — link passwords correctly hashed
9. **Email masking** — viewer emails stored masked (u***@domain) in DB, not raw
10. **IP stored as salted SHA-256 hash** — no raw IP addresses in DB

### Weakest Links

1. **Health endpoint exposes proxy config** — tells attackers exactly which header to forge for IP spoofing
2. **Real IP header not configured for Cloudflare by default** — IP allowlists and rate limiting ineffective without configuration
3. **HTTPS/HSTS not enabled by default** — must be explicitly configured
4. **Unlimited metadata in analytics events** — storage inflation attack path for authenticated viewers
5. **CSP unpkg.com wildcard** — CDN compromise scenario (low probability but high impact)

### Where a Real Attacker Tries First

1. **Reconnaissance via `/health`** — reveal proxy configuration, then craft `CF-Connecting-IP` header to bypass IP allowlists
2. **Analytics metadata inflation** — with a valid viewer session, spam large metadata payloads to inflate storage
3. **Screenshot exfiltration** — watermark is visible but screenshots sidestep server-side controls entirely
4. **Session persistence** — if the token is shared beyond intended audience (forwarded link), viewer sessions are established per-browser but the link remains accessible

### Must Fix Before Public Expansion

1. Remove proxy config from `/health` response
2. Set `REAL_IP_HEADER=CF-Connecting-IP` in production .env
3. Enable `HTTPS_REDIRECT=true` and `HSTS_MAX_AGE=31536000`
4. Add `metadata` size validation in analytics events (e.g., max 1KB JSON)
5. Remove all 29 remaining `.cover` files from git
6. Add rate limits to links, groups, and analytics GET endpoints
7. Fix download endpoint to check IP allowlist

---

## 14. Phased Security Fix Plan

### Phase B1 — Critical Fixes (Before Any Public Expansion)

**Objective:** Close gaps that allow an attacker to actively bypass access controls or exploit the running system.

| Fix | File(s) | Risk | Urgency |
|-----|---------|------|---------|
| Remove proxy config from `/health` | `app/main.py` | IP allowlist bypass vector | IMMEDIATE |
| Set `REAL_IP_HEADER` in production .env | `backend/.env` | IP allowlists currently see Cloudflare edge IP | IMMEDIATE |
| Enable HTTPS redirect and HSTS | `backend/.env` | Credential exposure over HTTP | IMMEDIATE |
| Add `metadata` size limit (≤ 1024 bytes JSON) | `app/routers/analytics.py` | Storage inflation attack | HIGH |
| Fix download endpoint: add IP allowlist check | `app/routers/viewer.py` | IP restriction bypass on download | HIGH |
| Remove session IDs from server logs | `app/services/link_service.py` | Session hijacking via log access | HIGH |

**Dependency:** None — all are independent.

### Phase B2 — High-Priority Hardening

**Objective:** Close gaps that reduce effective security posture without being immediately exploitable.

| Fix | File(s) | Risk | Urgency |
|-----|---------|------|---------|
| Remove 29 .cover files from git | `.gitignore` + `git rm --cached` | Reconnaissance aid | SOON |
| CSP: pin unpkg.com to specific hashes or paths | `app/middleware/security_headers.py` | CDN compromise XSS | HIGH (dep: React version lock) |
| Add rate limits to links PATCH/POST, groups, analytics GET | `app/routers/*.py` | Enumeration and bulk operations | HIGH |
| Move Supabase keys from HTML to server-injected meta | `SecureDoc.html`, `app/main.py` | Anon key permanently in git history | MEDIUM |
| Restrict JWT error detail to client | `app/auth.py` | Minor detail leakage | LOW |
| Add max_views DB-level atomic enforcement | `app/services/link_service.py` | Race condition over-count | LOW |

### Phase B3 — Medium-Priority Cleanup

**Objective:** Remove information leakage and maintenance debt that could aid attackers.

| Fix | File(s) | Risk | Urgency |
|-----|---------|------|---------|
| Remove storage keys from worker INFO logs | `app/workers/pipeline/*.py` | Internal path exposure in logs | MEDIUM |
| Remove storage key from upload error log | `app/routers/documents.py` | Internal path in error logs | LOW |
| Fix `apply_forensic_stamp` or document as not implemented | `app/services/watermark.py` | Misleading security claim | MEDIUM |
| Add size check before `await file.read()` | `app/routers/documents.py` | DoS on public deployment | LOW (current use) |
| Remove temp file doc_id prefix in antiword call | `app/services/toc/docx_extractor.py` | Minor path information | LOW |
| Add startup check: warn if real_ip_header not set in production | `app/main.py` | Ops visibility | LOW |

### Phase B4 — Future Hardening (For Billing / Custom Domain / DOCX/PPTX)

**Objective:** Prepare the security model for expanded attack surface.

| Area | Action | Trigger |
|------|--------|---------|
| Billing webhook | Current Stripe HMAC verification is correct. Add webhook event replay protection (check event ID uniqueness). | Before billing goes live |
| Custom domain | When custom domain is added, ensure `APP_PUBLIC_BASE_URL` correctly reflects the domain. Add subdomain isolation if multiple tenants share one deployment. | Before custom domain |
| DOCX/PPTX upload | PPTX files use ZIP format (same magic bytes as DOCX). Add explicit PPTX magic byte check. Review python-pptx for XXE/zip-slip vulnerabilities. | Before DOCX/PPTX support |
| Session management | Consider shorter session TTL for high-security links (currently 2 hours). Allow trainers to configure session TTL per link. | Future feature |
| Presigned URL removal | `generate_presigned_url` exists in storage.py but is unused. Remove to reduce attack surface. | Next code review |
| Concurrent validation locking | Use `SELECT FOR UPDATE` on ShareLink in `validate_link` to prevent max_views race. | Before high-concurrency public use |
| Worker Redis auth | Ensure Redis has a password set in production. The Celery/Redis connection uses `redis://` (no auth). | Before production at scale |
| Database connection pool | Reduce `db_max_overflow=20` for limited-resource deployments to prevent connection exhaustion under attack. | Before high-concurrency use |

---

## 15. Final Verdict

### Is the current repo secure enough for pilot use by the trainer and students?

**Yes, with immediate configuration fixes.**

The fundamental security model is sound:
- Share links cannot be guessed
- Revoked links stop serving content immediately
- Per-session watermarking provides accountability
- User data is correctly isolated
- No SQL injection paths exist

For a closed pilot with known participants (trainer + specific students), the main risk is misconfiguration:
1. `REAL_IP_HEADER` must be set for Cloudflare deployment
2. HTTPS must be properly enforced
3. The health endpoint should not expose proxy config

These are configuration changes, not code changes. Fix them in `.env` and `main.py` before sharing any links.

### What must be fixed before any public expansion?

In order of urgency:

1. **Health endpoint configuration disclosure** — closes IP spoofing reconnaissance
2. **REAL_IP_HEADER configuration** — makes IP allowlists and rate limiting effective
3. **HTTPS redirect + HSTS** — protects credentials in transit
4. **Analytics metadata size limit** — prevents storage inflation
5. **Download endpoint IP check** — closes IP restriction bypass
6. **Session IDs out of logs** — prevents privilege escalation via log access
7. **Rate limits on all mutation endpoints** — prevents bulk operations and enumeration

### Is the security model strong enough to proceed to the next phase?

**Yes for Phase C (scalability analysis) and Phase D (competitor research).**  
**Conditional for Phase E (DOCX/PPTX expansion)** — the B1 fixes should be completed first, and PPTX file handling needs security review before adding PPTX upload support.

The architecture is well-structured for secure document sharing. The gaps identified are fixable in a day of targeted work. None of the findings represent fundamental design flaws — they are implementation gaps and configuration issues that are common at this stage of development.

---

*End of Phase B Security Audit. Phase C (scalability) and Phase D (competitive analysis) to follow.*
