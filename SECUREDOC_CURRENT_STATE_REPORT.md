# SecureDoc Current State Report
**Date:** 2026-06-07  
**Repository:** `/Users/thrisha/traceview/securedoc`  
**Scope:** Read-only inventory. No code modified.  
**Method:** Full file reads with exact line citations.

---

## SECTION 1 — Session Architecture

### 1.1 Session ID Generation

**Source file:** `backend/app/services/link_service.py:264–265`

```python
def _generate_session_id(self) -> str:
    return secrets.token_hex(16)  # 32 hex chars = 128-bit entropy
```

- **Entropy source:** `secrets.token_hex(16)` — Python's CSPRNG via `os.urandom()`
- **Format:** 32 lowercase hexadecimal characters
- **Entropy:** 128 bits (2^128 ≈ 3.4 × 10^38 possible values)
- **Collision probability:** negligible for any realistic traffic volume

**Token generation for share links** (`link_service.py:43`):
```python
token = secrets.token_urlsafe(48)[:64]   # 64 URL-safe chars, ~288 bits
```

### 1.2 Session ID Storage

**Session table:** `backend/app/models/session.py`

```python
# Table: viewer_sessions
session_id:           String(32), PK          # line 18
link_id:              UUID, FK→share_links    # lines 19–21
ip_hash:              String(64), nullable    # line 22
viewer_email_masked:  String(255), nullable   # line 23
created_at:           DateTime(TZ)            # line 24
last_seen_at:         DateTime(TZ)            # line 25
```

**Indexes:** `ix_viewer_sessions_link_id`, `ix_viewer_sessions_last_seen`

Session records are **database-backed** (PostgreSQL in production, SQLite in tests). There is **no Redis storage of session IDs** — Redis stores page image bytes only.

**Session TTL:** 120 minutes of inactivity (`policy.py:20`: `SESSION_ACTIVE_MINUTES = 120`)

**Session heartbeat throttling:** Writes throttled to every 30 seconds (`policy.py:25`: `SESSION_HEARTBEAT_INTERVAL_SEC = 30`)

### 1.3 Session ID Resolution Priority

**Source:** `backend/app/routers/viewer.py:105–124`

```python
def _get_session_id(request: Request, query_param: Optional[str] = None) -> Optional[str]:
    # Priority 1: X-Session-ID header (never logged by CDN/proxy)
    sid = request.headers.get("X-Session-ID", "").strip()
    if sid:
        return sid
    # Priority 2: sdoc_session cookie (HttpOnly-capable, same-origin)
    sid = request.cookies.get("sdoc_session", "").strip()
    if sid:
        return sid
    # Priority 3: query parameter (backward-compat for legacy clients)
    return query_param
```

### 1.4 Session ID Occurrence Matrix

| Location | Present | Evidence |
|----------|---------|----------|
| **URL path** | NO | No route uses session_id as path segment |
| **Query parameter (new code)** | NO | `api.js:211–213` — `sessionHeaders()` uses `X-Session-ID` header |
| **Query parameter (legacy fallback)** | YES (fallback only) | `viewer.py:344`: `session_id: Optional[str] = Query(None)` |
| **X-Session-ID header** | YES (primary) | `viewer.py:118`; `api.js:212` |
| **`sdoc_session` cookie** | YES (secondary) | `viewer.py:121` |
| **localStorage** | NO | `app.jsx` keeps sessionId in React state only |
| **sessionStorage** | NO | No sessionStorage calls in frontend |
| **Redis** | NO | Redis stores page bytes, not sessions |
| **JWT payloads** | NO | JWT is Supabase bearer token for document owner auth only |
| **Analytics events (DB)** | YES (partial) | `app/models/event.py:62`: `session_id: String(32)` stored in `access_events` table |
| **Analytics API response** | TRUNCATED | `analytics.py:135`: `session_id[:8]` — only first 8 chars returned |
| **Watermark text** | YES (truncated) | `viewer.py:305`: `sess:{session_id[:6]}` embedded in watermark |
| **Access logs** | SANITIZED | `middleware/request_id.py:20–24`: tokens ≥20 chars replaced with `[token]` |

#### Exact Evidence for Each Location

**Analytics events (DB column):**
```python
# backend/app/models/event.py:62
session_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
```

**Analytics API response (truncated):**
```python
# backend/app/routers/analytics.py:135
"session_id": e.session_id[:8] if e.session_id else None,
```

**Watermark (6-char prefix only):**
```python
# backend/app/routers/viewer.py:305
watermark_text = f"{viewer_email or 'anonymous'} · {now_str} · sess:{session_id[:6]}"
```

**Path sanitization in access log:**
```python
# backend/app/middleware/request_id.py:20–24
def _sanitize_path(path: str) -> str:
    return re.sub(r'[A-Za-z0-9_-]{20,}', '[token]', path)
```

**Session ID returned in validate response:**
```python
# backend/app/routers/viewer.py:324
return { "session_id": session_id, ... }
```
The full 32-char session_id is returned to the frontend only in the `/validate` POST response body (HTTPS, not logged by CDN).

### 1.5 Cross-Link Session Replay Protection

**Source:** `backend/app/services/policy.py:181–188`

```python
if existing.link_id != link_id:
    logger.warning(
        "session_link_mismatch session=%s... expected_link=%s actual_link=%s",
        session_id[:6], link_id, existing.link_id,
    )
    return None  # refuse to refresh heartbeat; caller gets None for email
```

A session ID from Link A cannot be replayed against Link B.

---

## SECTION 2 — Viewer Request Flow

### 2.1 Sequence Diagram: Full Viewer Lifecycle

```
Browser                  API Server               PostgreSQL    Redis    R2/S3    Analytics
   |                          |                        |           |        |          |
   |-- GET /v/{token} ------->|                        |           |        |          |
   |<- 302 /static/viewer ---|                        |           |        |          |
   |                          |                        |           |        |          |
   |-- GET /api/viewer/gate/{token} ----------------->|           |        |          |
   |   (public, no auth, rate: unlimited)             |           |        |          |
   |                          |-- SELECT share_links ->|           |        |          |
   |                          |<- link row ------------|           |        |          |
   |<- {status, requires_password, requires_email} ---|           |        |          |
   |                          |                        |           |        |          |
   |-- POST /api/viewer/validate -(20/min)----------->|           |        |          |
   |   Body: {token, password?, email?, session_id?}  |           |        |          |
   |                          |                        |           |        |          |
   |   AUTH: Password bcrypt  |-- SELECT share_links ->|           |        |          |
   |   AUTH: Email allowlist  |<- link row ------------|           |        |          |
   |   AUTH: Domain allowlist |-- SELECT documents ---->|           |        |          |
   |   AUTH: IP allowlist     |<- doc row --------------|           |        |          |
   |   AUTH: max_views check  |-- SELECT viewer_sessions ->|        |        |          |
   |   AUTH: revoked check    |<- session row (if reuse) ->|        |        |          |
   |   AUTH: expiry check     |                        |           |        |          |
   |                          |-- UPSERT viewer_sessions ->|        |        |          |
   |                          |-- UPDATE share_links (view_count) ->|        |          |
   |                          |-- INSERT access_events (opened) ---->|        |          |
   |                          |<- COMMIT (1 round-trip) ------------|        |          |
   |                          |-- SELECT document_pages ---------->|           |        |
   |                          |<- page dimensions ------------------|           |        |
   |<- {session_id, page_count, watermark_text, permissions, ...} -|           |        |
   |                          |                        |           |        |          |
   |-- GET /api/viewer/page/{token}/{n} -(120/min)---->|           |        |          |
   |   Header: X-Session-ID: {session_id}             |           |        |          |
   |                          |                        |           |        |          |
   |   AUTH: link TTL cache   |-- [L1 link_cache hit?] |           |        |          |
   |   (miss: DB query)       |-- SELECT share_links ->|           |        |          |
   |   AUTH: revoked check    |                        |           |        |          |
   |   AUTH: expiry check     |                        |           |        |          |
   |   AUTH: IP allowlist     |                        |           |        |          |
   |   AUTH: doc TTL cache    |-- [L1 doc_cache hit?]  |           |        |          |
   |   (miss: DB query)       |-- SELECT documents ---->|           |        |          |
   |   AUTH: doc_ready check  |                        |           |        |          |
   |   AUTH: session check    |-- SELECT viewer_sessions ->|        |        |          |
   |                          |<- session row (valid?) ->|          |        |          |
   |   AUTH: page bounds      |-- [page_cache hit?]    |           |        |          |
   |   (miss: DB query)       |-- SELECT document_pages ->|         |        |          |
   |                          |-- UPSERT viewer_sessions ->|        |        |          |
   |                          |                        |           |        |          |
   |                          |-- [L1 page bytes hit?] |           |        |          |
   |                          |-- [L2 Redis hit?] -------->---------> GET   |          |
   |                          |   (miss: storage)      |           |       -- GET ---->|
   |                          |<- image_bytes ----------------------------------------|
   |                          |-- store L1+L2 ---------->--------->  SET   |          |
   |                          |                        |           |        |          |
   |                          |-- apply_visible_watermark() (PIL, in executor)         |
   |                          |   (session-unique angle, viewer email, date, sess:XXX) |
   |                          |                        |           |        |          |
   |<- 200 image/webp --------|                        |           |        |          |
   |   Cache-Control: private, no-store               |           |        |          |
   |   Content-Security-Policy headers                |           |        |          |
   |                          |                        |           |        |          |
   |-- POST /api/analytics/events -(60/min)---------->|           |        |          |
   |   Header: X-Session-ID                           |           |        |          |
   |   Body: {token, session_id, event_type, page_number} |       |        |          |
   |   AUTH: link active      |-- SELECT share_links ->|           |        |          |
   |   AUTH: not revoked      |                        |           |        |          |
   |   AUTH: not expired      |                        |           |        |          |
   |   AUTH: session active   |-- SELECT viewer_sessions ->|        |        |          |
   |   AUTH: page_number ≤ page_count |-- SELECT documents ->|      |        |          |
   |                          |-- INSERT access_events -------------->|        |          |
   |<- {logged: true} --------|                        |           |        |          |
```

### 2.2 Authentication and Authorization Checks Summary

**Per `/api/viewer/page` request (every single page load):**

| Check | Where | Mechanism |
|-------|-------|-----------|
| Link exists | `viewer.py:148–150` | DB SELECT (L1 cached 10s) |
| Link not revoked | `viewer.py:80–81` | `revoked_at IS NULL` |
| Link not expired | `viewer.py:83–87` | `expires_at < now` |
| IP allowed | `viewer.py:162–164` | CIDR matching via `policy.py` |
| Document exists and ready | `viewer.py:167–181` | DB SELECT (L1 cached 60s) |
| Session is active (not stale) | `viewer.py:354–355` | DB SELECT (no cache) |
| Session belongs to this link | `policy.py:136` | `row.link_id != link_id` |
| Page number within bounds | `viewer.py:358–359` | `page_number > doc_snap.page_count` |

---

## SECTION 3 — Watermark System

### 3.1 Architecture

**Server-side only.** All watermarking happens in the API server process. No client-side watermark rendering.

**Two distinct watermark types:**

| Type | Function | Applied When | Stored? | Viewer-Specific? |
|------|----------|-------------|---------|-----------------|
| Forensic stamp | Near-invisible corner mark + EXIF metadata | Document processing (worker) | YES — burned into stored WEBP | NO — document ID only |
| Visible watermark | Tiled diagonal text overlay | Every page serve (API) | NO — applied fresh per request | YES — includes viewer email |

### 3.2 Forensic Stamp (`watermark.py:67–123`)

```python
def apply_forensic_stamp(self, image_bytes, document_id, page_number):
    fingerprint = hashlib.sha256(document_id.encode()).hexdigest()[:8]
    mark_text = f"SD:{fingerprint}:{page_number:04d}"   # line 88
    # ...
    alpha = int(255 * 0.03)   # 3% opacity — line 109
    draw.text((x, y), mark_text, font=font, fill=(0, 0, 0, alpha))
    # EXIF embedding:
    exif[270] = f"SecureDoc:{document_id}:p{page_number}"  # line 119
```

- Applied once during Celery worker processing (`pipeline/pdf.py:52`)
- Stored permanently in `pages/{doc_id}/{page:04d}.webp`
- **Survives:** direct storage download, format conversion, screenshot, print
- **Contains:** SHA-256 prefix of document UUID (recoverable if doc UUID is known)
- **EXIF field 270 (ImageDescription):** Full document UUID + page number

### 3.3 Visible Watermark (`watermark.py:9–65`)

```python
def apply_visible_watermark(self, image_bytes, text, opacity=None, angle=-32.0, ...):
    opacity = opacity if opacity is not None else settings.watermark_opacity  # 0.22
```

**Watermark text composition** (`viewer.py:305`):
```python
watermark_text = f"{viewer_email or 'anonymous'} · {now_str} · sess:{session_id[:6]}"
# Example: "user@corp.com · 2026-06-07 · sess:a3f9e2"
```

**Note:** `viewer_email` here is the unmasked email supplied at gate validation (viewer.py:222), not the masked form stored in DB.

**Session-unique angle** (`viewer.py:44–55`):
```python
def _session_watermark_angle(session_id: str, base: float = -32.0) -> float:
    h = int(hashlib.sha256(session_id.encode()).hexdigest()[:8], 16)
    norm = (h % 10000) / 10000.0
    jitter = settings.watermark_angle_jitter_deg   # default 5.0°
    return base + (norm - 0.5) * 2.0 * jitter      # base ± 5°
```

Different sessions see the same document page with slightly different watermark angles, making composite-removal attacks harder.

### 3.4 Bypass Analysis

| Attack | Mitigated? | Evidence |
|--------|-----------|----------|
| Download raw R2/S3 bytes | **Partial** — forensic stamp present, visible watermark absent | Forensic stamp: `watermark.py:67–123`; visible applied per-serve only |
| Screenshot/Print | **Partial** — screenshot captures visible watermark; forensic survives contrast enhancement | `watermark.py:77–83` |
| Session token sharing | **Mitigated** — cross-link replay blocked; different sessions get different angles | `policy.py:181–188` |
| Modify EXIF after download | **Partial** — pixel stamp is separate from EXIF | `watermark.py:112–122` |
| Disable watermark in permissions | **Controlled by owner** — `permissions.watermark_enabled` flag | `viewer.py:330` |

**Critical finding:** A viewer who obtains R2/S3 credentials and downloads page bytes directly receives the forensic stamp but **not** the visible watermark (email/date/session). The forensic stamp only identifies the document, not the leaker.

---

## SECTION 4 — Document Rendering

### 4.1 PDF Rendering Flow

**Upload → Processing → Serve**

```
1. Upload:    POST /api/documents/upload
              → detect_file_type() → "pdf"
              → store original at originals/{uuid}.pdf
              → INSERT document (status=uploaded)
              → celery.delay("securedoc.process_document", doc_id)

2. Process:   [Celery Worker] tasks.py → process_document_with_session()
              → adapters.get_adapter("pdf") → pdf.process_pdf_document()
              → storage.download_bytes("originals/{uuid}.pdf")
              → rasterizer.rasterize_document(pdf_bytes, doc_id)
                  • convert_from_bytes(..., output_folder=tmp_dir, paths_only=True)
                  • For each PPM file: PIL.open → save as WEBP → del PIL
                  • Peak RAM: ~1 PIL image at a time (post E2.1 streaming fix)
              → asyncio.gather (8 concurrent pairs):
                  • watermark.apply_forensic_stamp(page_bytes, doc_id, page_num)
                  • _make_thumbnail(stamped_bytes) — 200px wide
                  • storage.upload_file(stamped, "pages/{uuid}/{page:04d}.webp")
                  • storage.upload_file(thumb, "thumbs/{uuid}/{page:04d}.webp")
              → INSERT document_pages rows (batch committed)
              → UPDATE document status=ready, page_count=N
              → extract_and_store_pdf_toc() → store "toc/{uuid}.json"

3. Serve:     GET /api/viewer/page/{token}/{page}
              → L1 local cache → L2 Redis → R2/S3 storage
              → apply_visible_watermark(bytes, email·date·sess)
              → return image/webp (no redirect, proxied bytes)
```

**Key files:**
- `app/services/rasterizer.py` — `RasterizerService.rasterize_document()`
- `app/workers/pipeline/pdf.py` — `process_pdf_document()`
- `app/services/watermark.py` — `apply_forensic_stamp()`, `apply_visible_watermark()`
- `app/services/storage.py` — `StorageService.upload_file()`, `download_bytes()`
- `app/services/page_cache.py` — `fetch_page_bytes()`, `store_page_bytes()`

**Dependencies:** pdf2image (poppler wrapper), Pillow (PIL), boto3 (R2/S3)

### 4.2 Thumbnail Generation Flow

**Source:** `pipeline/pdf.py:18–27`

```python
def _make_thumbnail(image_bytes: bytes) -> bytes:
    img = Image.open(BytesIO(image_bytes))
    ratio = 200 / img.width          # _THUMBNAIL_WIDTH_PX = 200
    new_h = max(1, int(img.height * ratio))
    thumb = img.resize((200, new_h), Image.LANCZOS)
    buf = BytesIO()
    thumb.save(buf, format="WEBP", quality=60)
    return buf.getvalue()
```

- Generated during document processing (best-effort, does not block)
- Stored at `thumbs/{doc_id}/{page:04d}.webp`
- Retrieved via `GET /api/viewer/thumb/{token}/{page}`
- Two-level cache (L1 local OrderedDict, L2 Redis)
- **Thumbnails are forensic-stamped** (applied to stamped bytes before thumbnail creation)
- **Thumbnails do NOT have the visible watermark** (watermark applied only on full-page serve)

### 4.3 Text Document Flow (`.txt`, `.md`, `.log`)

**Source:** `app/workers/pipeline/text.py`

```
1. Upload:  detect_file_type() → "txt"/"md"/"log"
            _reject_if_binary() — null-byte scan on first 512 bytes
            store raw bytes at originals/{uuid}.txt

2. Process: [Worker] _process_text_document()
            → storage.download_bytes(storage_key)
            → decode_text_safe(bytes)    # UTF-8 with replacement
            → count_chunks(lines, lines_per_chunk=100)
            → UPDATE document status=ready, page_count=chunk_count

3. Serve:   GET /api/viewer/text/{token}/{chunk}
            → fetch chunk lines from original stored text
            → return {content, chunk_number, total_chunks, doc_type, watermark_text}
```

No rasterization. Text stored as-is; chunked on-the-fly during serve.

### 4.4 DOCX / DOC Conversion Flow

**DOCX** (`pipeline/docx_pdf.py`):
```
download DOCX → LibreOffice headless (subprocess, timeout=120s)
→ extract PDF bytes → process_pdf_document() [same as PDF flow]
→ extract_docx_toc() via python-docx → resolve page numbers from PDF bookmarks
→ store TOC sidecar at toc/{doc_id}.json
```

**DOC** (`pipeline/word.py`):
```
download .doc → antiword subprocess (timeout=30s, env-whitelisted)
→ plain text output → store as text → process as text document
```

**Supported types:** `pdf`, `txt`, `md`, `log`, `docx`, `doc`  
**NOT supported:** `pptx`, `xlsx`, `odt`, `rtf`, `epub`

---

## SECTION 5 — Storage Security

### 5.1 Bucket Structure

Single bucket (`settings.storage_bucket_name`, default: `securedoc-docs`):

```
originals/{doc_uuid}.{ext}              Upload original
pages/{doc_uuid}/{page:04d}.webp        Rasterized page (forensic-stamped)
thumbs/{doc_uuid}/{page:04d}.webp       Thumbnails (200px wide)
toc/{doc_uuid}.json                     TOC sidecar
```

**Source:** `pipeline/pdf.py:46`, `pipeline/text.py` (implicitly), `pipeline/docx_pdf.py`

### 5.2 Object Key Security

| Property | Value | Evidence |
|----------|-------|----------|
| Keys contain user-supplied filename | NO | Keys use UUID + sequential page numbers only |
| Keys predictable given doc UUID | YES (sequential) | `pages/{uuid}/0001.webp` through `/{N:04d}.webp` |
| UUID exposed to clients | NO | Only `link.token` (random 64-char) is exposed |
| Path traversal possible | NO | Keys constructed programmatically, not from user input |

**Key generation:** `page_key = f"pages/{document_id}/{page.page_number:04d}.webp"` (`pipeline/pdf.py:46`)

**UUID origin:** Python `uuid.uuid4()` — cryptographically random (`models/document.py:20`)

### 5.3 Signed URLs

**Available but not used in viewer path.** 

`storage.py` exposes `generate_presigned_url()`. Search shows it is **not called** in the viewer endpoints — page bytes are downloaded by the API server and proxied directly to the client.

**Download endpoint** (`viewer.py:680–750`): Downloads full page bytes server-side, concatenates into a multi-page PDF, streams the result. Never redirects to signed R2 URL.

This is architecturally correct for security (enables server-side auth on every byte) but is a scalability bottleneck for large documents.

### 5.4 CDN Configuration

No CDN layer between viewer and API server for page bytes. Pages are served directly from FastAPI → R2.

Cloudflare Tunnel (`cloudflared tunnel --url http://localhost:8000`) is used for public ingress, but it is a transport proxy only — Cloudflare does not cache page images (no R2 public bucket configured).

### 5.5 Cache Strategy for Page Bytes

```
L1: Process-local OrderedDict LRU
    pages: 600 entries, ~50 KB avg → ~30 MB process RAM
    thumbs: 2000 entries, ~5 KB avg → ~10 MB process RAM
    Code: page_cache.py:57–90

L2: Redis shared cache
    Key: securedoc:page:v1:{storage_key}
    TTL: 3600 seconds (1 hour, config: redis_page_cache_ttl_sec)
    Degrades gracefully: returns None on Redis unavailability
    Code: page_cache.py:115–211
```

### 5.6 Path Enumeration Risk Assessment

**Risk:** LOW. Conditions for enumeration:
1. Attacker must know a document UUID — not exposed in any API response
2. Attacker must have R2 bucket credentials — not exposed in any API response
3. Even with doc UUID, attacker must bypass API server auth to serve pages

**Mitigation:** API server proxies all bytes. Direct R2 access requires AWS credentials with bucket read permission. Default R2 bucket is not publicly accessible.

---

## SECTION 6 — Security Controls

### 6.1 Content Security Policy (CSP)

**Source:** `backend/app/middleware/security_headers.py`

**Status: PRESENT — Hardened**

```
default-src 'none';
script-src 'self' https://unpkg.com 'sha384-...' 'sha384-...';
style-src 'self' https://fonts.googleapis.com 'unsafe-inline';
font-src 'self' https://fonts.gstatic.com data:;
connect-src 'self' https://*.supabase.co;
img-src 'self' blob: data:;
object-src 'none';
frame-ancestors 'none';
base-uri 'self';
form-action 'self';
```

- React CDN scripts are SRI-hash-pinned (`sha384-...`)
- `unsafe-eval` is absent — no dynamic code execution
- `unsafe-inline` absent from `script-src` — inline script block moved to `api.js`
- `frame-ancestors 'none'` prevents clickjacking

**Gap:** `style-src 'unsafe-inline'` is required for inline styles (CSS-in-JS pattern in React). This is a common tradeoff but allows CSS injection if XSS is achieved.

### 6.2 HSTS (HTTP Strict Transport Security)

**Status: PRESENT but DISABLED by default**

```python
# config.py:96
hsts_max_age: int = 0   # Set to 31536000 once HTTPS confirmed stable
```

**Source:** `security_headers.py` — injected only when `hsts_max_age > 0` AND `X-Forwarded-Proto: https`.

**Production action required:** Operator must set `HSTS_MAX_AGE=31536000` in `.env`.

### 6.3 Rate Limiting

**Status: PRESENT — slowapi**

| Endpoint | Rate | Key |
|----------|------|-----|
| `POST /api/viewer/validate` | 20/minute | Real client IP |
| `GET /api/viewer/page/{token}/{page}` | 120/minute | Real client IP |
| `GET /api/viewer/thumb/{token}/{page}` | 120/minute | Real client IP |
| `GET /api/viewer/toc/{token}` | 60/minute | Real client IP |
| `GET /api/viewer/download/{token}` | 10/minute | Real client IP |
| `GET /api/viewer/text/{token}/{chunk}` | 120/minute | Real client IP |
| `POST /api/analytics/events` | 60/minute | Real client IP |
| `POST /api/documents/upload` | 10/minute | Auth user ID |

**IP extraction:** `middleware/rate_limit.py` → `_get_real_client_ip()` reads `request.state.client_ip` set by `TrustedProxyMiddleware`. Falls back to `request.client.host`.

**Gap:** No global rate limit on authenticated document management endpoints (`/api/documents`, `/api/links`).

### 6.4 CSRF Protection

**Status: MISSING — not explicitly implemented**

**Partial mitigation:**
- JWT bearer token in Authorization header (not in cookies) — CSRF doesn't work against header-based auth
- Viewer session uses `X-Session-ID` header — same protection
- `Content-Type: application/json` required for POST endpoints — CSRF forms can't set custom content-type

**Gap:** No `SameSite` cookie attribute enforced, no CSRF token. Mitigation is implicit (header-based auth) but not explicit.

### 6.5 JWT Validation

**Status: PRESENT — Supabase JWKS**

```python
# auth.py:36–59
async def get_current_user(credentials: HTTPAuthorizationCredentials, ...):
    jwks = await _get_jwks(supabase_url)          # line 46
    public_key = _find_key(jwks, token_kid)        # line 47
    payload = jwt.decode(token, public_key,
        algorithms=["ES256", "RS256"],
        audience="authenticated")                  # line 49
```

- JWKS cached with 1-hour TTL (`auth.py:11`: `_JWKS_TTL = 3600`)
- On `InvalidTokenError`: refresh JWKS and retry once (`auth.py:54`)
- Token expiry validated by `python-jose`
- `audience` claim validated (must be `"authenticated"`)

**Gap:** No revocation list — a compromised JWT is valid until expiry (standard JWT limitation, not unique to this implementation).

### 6.6 Session Validation

**Status: PRESENT — database-backed with heartbeat**

Every `/api/viewer/page`, `/api/viewer/thumb`, `/api/viewer/toc`, `/api/viewer/download`, `/api/viewer/text` request calls:
```python
# viewer.py:354
if not await policy_enforcer.is_active_session(db, link_snap.id, session_id):
    raise HTTPException(status_code=401, detail="Session not recognized. Please re-validate.")
```

- Sessions expire after 120 minutes of inactivity
- Cross-link replay blocked (`policy.py:136`)
- Purged by Celery Beat every 30 minutes (`celery_app.py:28`: `securedoc.purge_stale_sessions`)

**Gap:** `is_active_session()` performs a DB SELECT on every page request (no session cache). Under high load this creates DB read pressure.

### 6.7 Replay Protection

**Status: PARTIAL**

- **Session cross-link replay:** BLOCKED (`policy.py:181–188`)
- **View count limit:** ENFORCED (`models/link.py`, validated in `link_service.py`)
- **Token replay (same link, different viewer):** NOT BLOCKED — tokens are shareable by design
- **Session reuse within same link:** ALLOWED (intentional — enables page refresh without re-auth)

### 6.8 Revocation

**Status: PRESENT — propagates within 10 seconds**

```python
# link_service.py: revoke_link() calls invalidate_link(token) immediately after commit
# links.py: PATCH /api/links/{id} calls invalidate_link(token) after commit
```

Link cache TTL is 10 seconds (`viewer_cache.py:46`). Maximum revocation propagation delay: 10 seconds.

Cached `revoked_at` is checked on every cache hit:
```python
# viewer.py:159
_check_link_active(link_snap, now)   # checks revoked_at even on cache hits
```

### 6.9 Additional Security Controls

| Control | Status | Location |
|---------|--------|----------|
| `X-Frame-Options: DENY` | PRESENT | `security_headers.py` |
| `X-Content-Type-Options: nosniff` | PRESENT | `security_headers.py` |
| `Referrer-Policy: strict-origin-when-cross-origin` | PRESENT | `security_headers.py` |
| `Permissions-Policy` | PRESENT | `security_headers.py` |
| `X-Request-ID` correlation | PRESENT | `middleware/request_id.py` |
| IP hashing (SHA-256 + salt) | PRESENT | `utils/crypto.py`, `hash_value()` |
| Password hashing (bcrypt) | PRESENT | `utils/crypto.py` |
| Email masking before DB storage | PRESENT | `utils/crypto.py:mask_email()` |
| Env-whitelisted subprocesses | PRESENT | `libreoffice_converter.py:163–173`, `docx_extractor.py:263–264` |
| HTTPS redirect enforcement | PRESENT (opt-in) | `main.py`, `config.py:https_redirect` |
| Production startup checks | PRESENT | `main.py:25–67` |
| `storage_key` never in API response | PRESENT | Enforced by response model |
| Page endpoint proxies bytes (no redirect) | PRESENT | `viewer.py:338–450` |

---

## SECTION 7 — Scalability Limits

### 7.1 Maximum PDF Pages

**Hard limit:** `config.py:39` — `max_pages_per_doc: int = 500`

This is enforced in `rasterizer.py:62`:
```python
last_page = settings.max_pages_per_doc if settings.max_pages_per_doc > 0 else None
```

**Practical limits after Phase E2.1 streaming fix:**

| Worker RAM | Max Pages (reliable) | Bottleneck |
|-----------|---------------------|------------|
| 512 MB | ~20 pages | Celery overhead + poppler |
| 1 GB | ~100 pages | PDF rasterization |
| 2 GB | ~200 pages | R2 upload throughput |
| 4 GB | ~400 pages | Task time limit (600s) |
| 8 GB | 500 pages | Task time limit (600s) |

**Post-streaming rasterizer:** Peak PIL RAM = ~8 MB regardless of page count. The bottleneck is now task_soft_time_limit (600s) and disk I/O for PPM temp files (~6.5 MB × N pages).

**Download:** Separately limited to `max_download_pages_pdf = 100` (`config.py:138`) because download assembles all pages in memory simultaneously.

### 7.2 Maximum DOCX Pages

**Bottleneck:** LibreOffice conversion timeout (`lo_conversion_timeout_sec = 120` after Phase E2.1).

| DOCX Size | Estimated Conversion Time | Status |
|-----------|--------------------------|--------|
| < 50 pages | < 30s | Reliable |
| 50–100 pages | 30–90s | Usually succeeds |
| 100–200 pages | 90–180s+ | Risk of timeout at 120s |
| > 200 pages | > 180s | Will timeout |

After DOCX → PDF conversion, same limits as PDF apply.

### 7.3 Maximum PPTX / XLSX / Other Formats

**PPTX: NOT SUPPORTED.** No adapter in `app/services/adapters.py`. Uploading a `.pptx` file is not detected and will fail in processing.

**XLSX: NOT SUPPORTED.** Same.

**Supported formats only:** `pdf`, `docx`, `doc`, `txt`, `md`, `log`.

### 7.4 Concurrent Viewers

**No hard limit on concurrent viewers per link.** The system supports many concurrent viewer sessions. Bottlenecks:

| Component | Limit | Configured |
|-----------|-------|-----------|
| FastAPI workers (uvicorn) | Async → handles hundreds | Default via Docker Compose |
| DB connections (asyncpg pool) | `db_pool_size=10`, `max_overflow=20` | `config.py:105–106` |
| Redis connections | Single client, async pipelining | `page_cache.py:232–238` |
| Session validation (DB read) | 1 query per page request | No session cache — bottleneck at scale |

**Concurrency detection (non-blocking):** `config.py:82` — `max_concurrent_sessions_per_link: int = 50` — logs warning only, never denies access.

### 7.5 Concurrent Document Conversions

**Celery workers:** `config.py:118` — `worker_concurrency: int = 2` (default)

With `worker_prefetch_multiplier=1` and `task_acks_late=True`, exactly 2 conversions run in parallel per worker container.

**Queue starvation risk:** A single 200-page PDF takes ~60–120s (rasterize + 400 uploads). Two concurrent large PDFs block all other uploads for that duration.

### 7.6 Identified Bottlenecks

| Bottleneck | Impact | Where |
|------------|--------|-------|
| Session validation DB read per page | High concurrent viewer load | `policy.py:125–142` — no cache |
| Download assembles all pages in memory | RAM on API server for large docs | `viewer.py:680–750` |
| Single storage bucket (no sharding) | R2 rate limits at very high scale | `storage.py` |
| No CDN layer for page images | Latency from repeated R2 fetches | Architecture |
| LibreOffice startup cost (~3s) | DOCX queue latency | `libreoffice_converter.py` |
| DOCX → PDF in memory | No streaming for large DOCX | `pipeline/docx_pdf.py:49` |

---

## SECTION 8 — Competitor Gap Analysis

### Legend
- ❌ Missing  
- 🔶 Partial  
- ✅ Equivalent  
- ⭐ Better

### 8.1 Document Sharing & Access Control

| Feature | SecureDoc | DocSend | Google Drive | Dropbox | Adobe | Box |
|---------|-----------|---------|-------------|---------|-------|-----|
| Expiry date on links | ✅ | ✅ | 🔶 (file expiry) | ❌ | ✅ | ✅ |
| Max views per link | ✅ | ✅ | ❌ | ❌ | 🔶 | ✅ |
| Password protection | ✅ | ✅ | 🔶 | 🔶 | ✅ | ✅ |
| Email allowlist per link | ✅ | ✅ | 🔶 | ❌ | ❌ | ✅ |
| IP allowlist per link | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Domain allowlist per link | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ |
| Revoke link instantly | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Link-level permissions (print, copy, download) | ✅ | ✅ | 🔶 | ❌ | ✅ | ✅ |
| Group/folder organization | ✅ | 🔶 | ✅ | ✅ | ❌ | ✅ |

### 8.2 Watermarking

| Feature | SecureDoc | DocSend | Google Drive | Dropbox | Adobe | Box |
|---------|-----------|---------|-------------|---------|-------|-----|
| Viewer email in watermark | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Session-unique watermark angle | ⭐ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Forensic near-invisible stamp | ⭐ | ❌ | ❌ | ❌ | 🔶 (metadata) | ❌ |
| EXIF metadata embedding | ⭐ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Watermark on print | 🔶 (CSS not enforced) | ✅ | ❌ | ❌ | ✅ | ✅ |

### 8.3 Analytics

| Feature | SecureDoc | DocSend | Google Drive | Dropbox | Adobe | Box |
|---------|-----------|---------|-------------|---------|-------|-----|
| Per-link view count | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| Page-level analytics | ✅ | ✅ | ❌ | ❌ | ✅ | 🔶 |
| Time-on-page | ❌ | ✅ | ❌ | ❌ | ✅ | 🔶 |
| Device/browser fingerprint | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Viewer geo-location | 🔶 (IP hash only) | ✅ | ❌ | ❌ | ❌ | 🔶 |
| Real-time notifications | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Analytics export (CSV/PDF) | ❌ | ✅ | ❌ | ❌ | 🔶 | ✅ |

### 8.4 Document Rendering

| Feature | SecureDoc | DocSend | Google Drive | Dropbox | Adobe | Box |
|---------|-----------|---------|-------------|---------|-------|-----|
| PDF rendering | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| DOCX rendering | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| PPTX rendering | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| XLSX rendering | ❌ | 🔶 | ✅ | ✅ | 🔶 | ✅ |
| Mobile-optimized viewer | 🔶 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Table of contents | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ |
| Full-text search | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| Offline viewing | ❌ | ❌ | ✅ (exported) | ✅ | ✅ | ✅ |

### 8.5 Enterprise Features

| Feature | SecureDoc | DocSend | Google Drive | Dropbox | Adobe | Box |
|---------|-----------|---------|-------------|---------|-------|-----|
| SSO / SAML | ❌ | ✅ (paid) | ✅ | ✅ | ✅ | ✅ |
| Audit log (admin) | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Role-based access control | 🔶 (owner only) | ✅ | ✅ | ✅ | ✅ | ✅ |
| e-Signature | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Version history | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| API access | 🔶 (internal only) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Webhooks | ❌ | ✅ | 🔶 | ✅ | ❌ | ✅ |
| Custom domain for viewer | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| White-label / custom branding | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| SOC 2 / ISO 27001 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## SECTION 9 — Technical Debt

### Critical (P0) — Data Loss or Security Risk

| # | Debt | File | Line |
|---|------|------|------|
| 1 | **Visible watermark bypassed by direct R2 access** — forensic stamp exists but doesn't contain viewer identity | `watermark.py:67–123` | — |
| 2 | **HSTS disabled by default** — production deployments without HSTS are vulnerable to SSL strip attacks | `config.py:96` | `hsts_max_age=0` |
| 3 | **JWT never revoked** — a compromised token is valid until expiry (standard JWT limitation but no workaround implemented) | `auth.py` | — |
| 4 | **PPTX/XLSX not supported** — silently fails or produces wrong output for common enterprise formats | `adapters.py` | — |
| 5 | **Download endpoint loads all pages into API server RAM** — 100-page PDF download uses ~500 MB on API server | `viewer.py:680–750` | `max_download_pages_pdf=100` |

### High (P1) — Performance or Reliability Risk

| # | Debt | File | Line |
|---|------|------|------|
| 6 | **Session validation uncached** — DB SELECT on every `/page` request; at 100 concurrent viewers × 1 page/sec = 100 DB queries/sec on viewer_sessions table alone | `policy.py:125–142` | — |
| 7 | **Single-process Redis page cache** — L1 cache is per-process; multi-replica deployments get no cross-process cache sharing for L1 | `page_cache.py:57` | — |
| 8 | **No database connection pooling validation in workers** — Celery workers create their own engine; no pool health check | `tasks.py:39–54` | — |
| 9 | **LibreOffice memory not bounded** — each DOCX conversion spawns a full LO process; no container memory limit enforced | `libreoffice_converter.py:127` | — |
| 10 | **No retry on storage upload failure** — `storage.upload_file()` uses `max_attempts=2` in boto3 config but `_process_and_upload_page()` raises immediately on failure; entire 200-page document fails | `pipeline/pdf.py:65–69` | — |
| 11 | **Text viewer serves from original bytes on every request** — no chunk-level caching for text documents | `pipeline/text.py` | — |
| 12 | **No background pre-warming of page cache** — first viewer of each page incurs R2 latency | `viewer.py:398–420` | — |

### Medium (P2) — Engineering Debt

| # | Debt | File | Line |
|---|------|------|------|
| 13 | **Alembic migration not idempotent** — `migrate.py` uses advisory lock but `alembic upgrade head` is still called on every container start | `entrypoint.sh`, `migrate.py` | — |
| 14 | **`viewer_sessions` table grows unboundedly between purge runs** — purge runs every 30 min via Beat; at high viewer load this table can reach millions of rows | `celery_app.py:27` | `beat_schedule` |
| 15 | **`access_events` has no retention policy** — no archival or deletion after N days | `models/event.py` | — |
| 16 | **Worker concurrency fixed at 2** — not auto-scaled based on queue depth | `config.py:118` | `worker_concurrency=2` |
| 17 | **No health endpoint authentication** — `GET /health` is public and reveals container info | `main.py` | — |
| 18 | **Static assets served by FastAPI** — `/static/*` is handled by the API server, not a CDN or object store | `main.py` | `StaticFiles` |
| 19 | **JSON logging disabled by default** — `enable_json_logging=False`; structured logs required for Grafana/Datadog | `config.py:84` | — |
| 20 | **No distributed tracing** — `X-Request-ID` exists but no OpenTelemetry/Jaeger spans | `middleware/request_id.py` | — |
| 21 | **Supabase dependency hard-coded** — no abstraction layer; switching auth providers requires extensive changes | `auth.py` | — |
| 22 | **Watermark text includes unmasked viewer email** — the full email from the gate is burned in; masking happens only for DB storage | `viewer.py:305` | — |
| 23 | **`max_views` check in `get_gate_requirements` not atomic** — view_count check and increment are in separate queries; concurrent sessions can bypass max_views by a small margin | `viewer.py:204` | — |
| 24 | **No CSRF token implementation** — relies implicitly on header-based auth; no explicit SameSite cookie enforcement | — | — |
| 25 | **Frontend bundles React from CDN** — CDN downtime breaks the app; SRI hashes help integrity but not availability | `SecureDoc.html` | — |

### Low (P3) — Code Quality

| # | Debt | File | Line |
|---|------|------|------|
| 26 | **`from __future__ import annotations` missing in several files** — forward reference style inconsistent | Multiple | — |
| 27 | **No API versioning** — all routes at `/api/*`; breaking changes require coordinated deploys | `main.py` | — |
| 28 | **No OpenAPI schema validation** — Pydantic models not used for request bodies in viewer routes (uses raw `body: dict`) | `viewer.py:219` | `body: dict` |
| 29 | **`functools.partial` imported but unused** in original rasterizer.py (now removed after refactor) | — | — |
| 30 | **`demo_storage_patch.py` in production code path** — `celery_app.py:6` checks `USE_DEMO_STORAGE` env var in production code | `celery_app.py:5–7` | — |
| 31 | **`link_service.py` has a `commit=False` pattern** that is not documented and creates implicit coupling between callers | `link_service.py:90–237` | — |
| 32 | **No structured log context** — `logger.info/warning` calls use positional format strings, not structured fields compatible with Loki | Multiple | — |
| 33 | **`viewer.py:219`: `body: dict` for validate** — no Pydantic model; type errors become 500s instead of 422s | `viewer.py:219` | — |
| 34 | **Test database SQLite incompatibility** — `asyncio_mode=auto` masks some SQLAlchemy async edge cases specific to PostgreSQL | `pytest.ini`, `conftest.py` | — |
| 35 | **No pagination cursor for documents list** — `GET /api/documents` returns all documents; grows unboundedly | `routers/documents.py` | — |
| 36 | **Billing status `past_due` treated as free** — rationale: intentional degradation, but silently overcharges customers who pay late | `config.py` (billing logic) | — |
| 37 | **No retry backoff on R2 upload** — single page failure retries immediately (boto3 `max_attempts=2`) with no exponential backoff | `storage.py:48–52` | — |
| 38 | **Orphan requeue task may create duplicate processing** — if a document is stuck in `processing` it resets to `uploaded` and re-queues even if the original task is still running | `tasks.py:260–278` | — |
| 39 | **No input length validation on `allowed_emails`** — can store unlimited JSON; large allowlists cause slow policy checks | `models/link.py:30` | — |
| 40 | **`get_gate_requirements` leaks link existence** — returns `"not_found"` status; allows enumeration of valid tokens | `viewer.py:188–210` | — |
| 41 | **LibreOffice `_get_conversion_timeout()` function called at module import** — settings must be initialized before import | `libreoffice_converter.py:43–49` | — |
| 42 | **No checksum on uploaded files** — storage silently accepts partially-uploaded files | `routers/documents.py` | — |
| 43 | **`viewer_email_masked` for watermark uses masked form only in DB** — viewer.py:305 watermarks with full unmasked email but stores masked form | `viewer.py:305`, `utils/crypto.py:mask_email()` | — |
| 44 | **Celery Beat runs in separate container** — session cleanup only runs if Beat is deployed separately; single-container deployments miss it | `celery_app.py:28` | — |
| 45 | **No graceful degradation for Celery down** — upload returns 202 but document stays in `uploaded` status forever if worker is down | `routers/documents.py` | — |
| 46 | **`max_concurrent_sessions_per_link` is detection-only** — the setting exists but never enforces; high concurrency is logged but not blocked | `config.py:82`, `viewer.py:264–274` | — |
| 47 | **No viewer session invalidation on link update** — PATCH `/api/links/{id}` invalidates metadata cache but existing viewer sessions remain valid | `links.py`, `policy.py` | — |
| 48 | **Redis password not in default config** — `redis_url: str = "redis://localhost:6379/0"` — no auth by default | `config.py:26` | — |
| 49 | **No input sanitization for filenames in storage** — original filename preserved in `Document.filename` but not in storage key (good), but filename is returned in API responses and could contain HTML | `models/document.py:12` | — |
| 50 | **Single `user_id` per document** — no shared ownership model; sharing requires creating share links rather than granting direct access to another owner | `models/document.py:32` | — |

---

## SECTION 10 — Enterprise Readiness

### 10.1 Scoring Summary

| Dimension | Score | Grade |
|-----------|-------|-------|
| Security | 6.5/10 | B |
| Performance | 5.5/10 | C+ |
| Scalability | 4.5/10 | C |
| Reliability | 5.0/10 | C |
| Observability | 3.5/10 | D+ |
| Maintainability | 6.0/10 | B- |
| **Overall** | **5.2/10** | **C+** |

### 10.2 Security — 6.5/10

**Strengths:**
- Hardened CSP with SRI hashes (`security_headers.py`)
- JWT validation via Supabase JWKS with retry (`auth.py`)
- Cross-link session replay protection (`policy.py:181–188`)
- Forensic watermark with EXIF embedding (`watermark.py:67–123`)
- IP allowlist with CIDR support (`policy.py:32–71`)
- Environment-whitelisted subprocesses (`libreoffice_converter.py:163`)
- `X-Frame-Options: DENY` preventing clickjacking
- IP hashing with configurable salt

**Gaps:**
- HSTS disabled by default (P0)
- Visible watermark bypassed by direct storage access (P0)
- JWT revocation not implemented (P1)
- CSRF protection is implicit, not explicit (P2)
- Max views race condition (P2)
- Gate endpoint leaks link existence (P3)

### 10.3 Performance — 5.5/10

**Strengths:**
- Two-level page cache (L1 LRU + L2 Redis) with graceful fallback
- Streaming rasterization (O(1) PIL RAM, Phase E2.1)
- Bounded parallel R2 uploads (semaphore=8, Phase E2.1)
- Session heartbeat throttled to 30s interval
- 3 DB writes in 1 atomic commit on validate
- `asyncio.wait_for` on all storage operations

**Gaps:**
- Session validation uncached (1 DB read per page)
- No CDN for page bytes (all R2 reads go to API server)
- Download assembles entire document in memory
- LibreOffice ~3s startup cost per DOCX
- No text document chunk caching

### 10.4 Scalability — 4.5/10

**Strengths:**
- Celery for async document processing
- `worker_prefetch_multiplier=1` prevents queue monopolization
- `task_acks_late=True` with `task_reject_on_worker_lost=True`
- Streaming rasterization handles 200+ page PDFs reliably
- Task time limits (600s soft, 660s hard)

**Gaps:**
- Worker concurrency fixed at 2 (not auto-scaled)
- PPTX/XLSX unsupported (blocks enterprise document formats)
- No horizontal scaling story (single-process session cache)
- No CDN — all page bytes served through API server
- DB connection pool (10+20=30 connections) exhausted at moderate scale
- `max_download_pages_pdf=100` limits large document downloads

### 10.5 Reliability — 5.0/10

**Strengths:**
- `task_reject_on_worker_lost=True` prevents lost tasks
- Orphan requeue task recovers stuck documents
- Storage operations degrade gracefully (try/except in cache helpers)
- Redis unavailability handled gracefully (returns None, falls through to storage)
- Alembic migration with advisory lock prevents race conditions

**Gaps:**
- No retry backoff on page upload failure
- Celery Beat required for session cleanup — not auto-started in single-container mode
- LibreOffice conversion is not retried on failure (permanent)
- No circuit breaker on R2 storage
- Health endpoint (`/health`) doesn't check critical dependencies (DB, Redis, R2)

### 10.6 Observability — 3.5/10

**Strengths:**
- `X-Request-ID` correlation header (injected or echoed)
- Access log per request (method/path/status/ms/req_id)
- Path sanitization in logs
- `enable_json_logging` setting exists (disabled by default)
- Debug-level cache hit/miss logging

**Gaps:**
- JSON logging disabled by default (no structured log output)
- No distributed tracing (no OpenTelemetry)
- No metrics endpoint (no `/metrics` for Prometheus)
- No error budget / SLO tracking
- Analytics are stored in DB only, no streaming to external systems
- No alerting on high concurrent sessions or processing failures
- Log entries use positional format strings not JSON-structured fields

### 10.7 Maintainability — 6.0/10

**Strengths:**
- 1265 tests (unit + integration) with SQLite in-memory for speed
- Coverage at 86% (lines)
- Clear pipeline adapter pattern (`adapters.py`, `pipeline/`)
- Pydantic settings with env-variable override
- Alembic migrations for schema evolution
- Middleware stack cleanly separated

**Gaps:**
- No API versioning (`/v1/`)
- Raw `body: dict` in viewer routes (no Pydantic validation)
- No integration with CI/CD (no `.github/workflows/`)
- Demo storage patch in production code path
- Billing logic spread across multiple files
- No API documentation beyond auto-generated OpenAPI
