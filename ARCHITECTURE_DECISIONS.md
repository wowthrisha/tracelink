# Architecture Decision Records

**Project:** SecureDoc Enterprise Transformation  
**Format:** [ADR-NNN] Title / Status / Context / Decision / Consequences

---

## ADR-001: HSTS Default Enable with Preload
**Status:** Accepted  
**Date:** 2026-06-07

**Context:**  
HSTS was disabled by default (`hsts_max_age=0`) to avoid locking out operators who hadn't confirmed HTTPS. However, in practice every deployment that didn't explicitly set this was vulnerable to SSL strip.

**Decision:**  
Change default to `hsts_max_age=31536000` (1 year). Add `; preload` to the header value. This enables browser HSTS preload list submission. Add a production startup **error** (not warning) if HSTS is disabled.

**Consequences:**  
+ Positive: All new deployments are protected against SSL strip immediately  
+ Positive: Meets NIST SP 800-52, PCI DSS 4.0 requirement 6.5.1  
- Risk: If an operator runs behind HTTP-only proxy without setting `HTTPS_REDIRECT=false`, HSTS won't be injected (the middleware checks X-Forwarded-Proto). This is safe behavior.  
- Rollback: `HSTS_MAX_AGE=0` in env disables it immediately

---

## ADR-002: Atomic max_views Check-and-Increment
**Status:** Accepted  
**Date:** 2026-06-07

**Context:**  
The original validate flow checked `view_count < max_views` in one SELECT and incremented in a separate UPDATE. Under concurrent requests, both SELECTs could read the same `view_count`, both pass the check, and both increment, exceeding `max_views` by the number of concurrent racing requests.

**Decision:**  
Replace the two-query pattern with a single atomic PostgreSQL/SQLite UPDATE:
```sql
UPDATE share_links
SET view_count = view_count + 1
WHERE id = :link_id
  AND (max_views IS NULL OR view_count < max_views)
RETURNING view_count, max_views
```
If 0 rows are returned, `max_views` was hit. The separate `increment_view_count()` method is removed from `link_service.py` and the explicit `increment_view_count()` call removed from `viewer.py:validate_link`.

**Consequences:**  
+ Positive: Race condition eliminated with no locks; PostgreSQL row-level locking handles atomicity  
+ Positive: One fewer DB round-trip on validate  
- Risk: SQLite behavior for `UPDATE ... RETURNING` requires SQLite 3.35.0+. Python 3.9+ ships SQLite 3.35.0+. Tests use aiosqlite which wraps system SQLite. Verified compatible.

---

## ADR-003: Viewer Identity Forensic Stamp at Serve Time
**Status:** Accepted  
**Date:** 2026-06-07

**Context:**  
The existing forensic stamp (`apply_forensic_stamp()`) identifies the document but not the viewer. An insider who obtains R2 credentials can download pages with no viewer identity evidence. Applying a per-viewer stamp at serve time (not storage time) adds this identity without increasing storage costs.

**Decision:**  
Add `apply_viewer_forensic_stamp(image_bytes, session_id, page_number)` to `WatermarkService`. Applied AFTER the visible watermark in the same thread pool executor call. Stamp: `VS:{sha256(session_id)[:8]}:{page:04d}` at 1.5% opacity (different corner than document stamp). Session ID is hashed before embedding — the stamp proves session identity to someone with DB access, not to a random observer.

**Consequences:**  
+ Positive: Viewer identity burned into every served byte  
+ Positive: No storage increase (applied at serve time, not stored)  
+ Positive: Two different corners: document stamp (lower-right), viewer stamp (lower-left)  
- Risk: Marginal latency increase (~2ms additional PIL pass). Acceptable given existing 20-80ms watermark time.

---

## ADR-004: Session Cache with 5-Second TTL
**Status:** Accepted  
**Date:** 2026-06-07

**Context:**  
`is_active_session()` does a DB `SELECT` on every `/api/viewer/page` call. At 100 concurrent viewers × 1 page/2s = 50 DB reads/sec on `viewer_sessions`. The connection pool (10 + 20 = 30 max connections) becomes the bottleneck before anything else.

**Decision:**  
Add `session_cache: _TTLCache(maxsize=50000, ttl_seconds=5.0)` to `viewer_cache.py`. Cache key: `session_id`. Value: `tuple(link_id, last_seen_at, viewer_email_masked)`. On `is_active_session()`: check cache first (O(1) dict lookup); populate on miss. On `upsert_session()`: update cache entry. On `invalidate_link()`: scan and evict all sessions for that link_id.

5-second TTL chosen because:
- Revocation propagation must be < 10 seconds (current link cache TTL)  
- 5s gives acceptable security while eliminating 95%+ of session DB reads under load

**Consequences:**  
+ Positive: ~95% reduction in viewer_sessions DB reads  
+ Positive: ~50 MB memory for 50,000 concurrent sessions  
- Risk: Revoked session may serve 1 more page within the 5-second window. Acceptable given revocation also invalidates the link cache (10s TTL). Maximum exposure: 15 seconds total.  
- Note: If `invalidate_link()` is called, sessions for that link are purged from session_cache immediately, making revocation propagation < 1 second.

---

## ADR-005: JSON Logging Enabled by Default
**Status:** Accepted  
**Date:** 2026-06-07

**Context:**  
`enable_json_logging` defaulted to `False`, meaning all production deployments that didn't explicitly enable it got plaintext logs with no structured fields. This made log aggregation, alerting, and incident response difficult.

**Decision:**  
Change default to `True`. Operators who need plaintext (local development without log aggregator) can set `ENABLE_JSON_LOGGING=false`. This is a better default for the majority of deployment scenarios (Docker + log aggregator).

**Consequences:**  
+ Positive: All new deployments get structured logs  
+ Positive: Enables Grafana Loki / Datadog / CloudWatch integration out-of-box  
- Risk: Local development logs become harder to read in terminal. Mitigated by: set `ENABLE_JSON_LOGGING=false` in local `.env`; document in README.

---

## ADR-006: Hybrid CDN Strategy (Thumbs Only)
**Status:** Accepted  
**Date:** 2026-06-07

**Context:**  
CDN for full page images would require either pre-generating per-session watermarked variants (storage cost) or moving watermarking to Cloudflare Workers (complexity, LO cost). Neither is acceptable without larger architectural changes.

**Decision:**  
CDN for thumbnails only. Thumbnails have the forensic document stamp but NOT the visible watermark (viewer email). A thumbnail being served by CDN without per-request auth is acceptable because:
1. Thumbnails are low-resolution (200px wide)
2. Thumbnails contain the forensic stamp (document identification)
3. Full-page access still requires validated session

Full pages: keep API-proxy with visible watermark applied per request.

**Consequences:**  
+ Positive: Thumbnail latency reduced 50-80% (CDN edge cache)  
+ Positive: Egress from R2 to API server eliminated for thumbnails  
- Risk: Signed URL can be shared within TTL window (60s). Acceptable for low-res thumbs.

---

## ADR-007: Streaming Download via pypdf PdfWriter
**Status:** Accepted  
**Date:** 2026-06-07

**Context:**  
Current download assembles all pages in a BytesIO buffer before streaming. For 100 pages × ~100KB = ~10 MB RAM per download session. At 50 concurrent downloads = 500 MB. This limits `max_download_pages_pdf` to 100.

**Decision:**  
Use `pypdf.PdfWriter` which already supports incremental writes. Stream page-by-page via an async generator that:
1. Fetches page bytes from cache/R2
2. Appends to PdfWriter
3. Yields serialized PDF chunk when buffer reaches 1 MB

This requires `pypdf >= 5.0` which is already in requirements.

**Consequences:**  
+ Positive: Peak RAM for download = O(1 page) + pypdf overhead (~2 MB)  
+ Positive: First byte latency reduced (client starts receiving sooner)  
- Risk: pypdf streaming API changed in 5.0; test against specific version.

---

## ADR-008: Prometheus Native Client (not Instrumentator)
**Status:** Accepted  
**Date:** 2026-06-07

**Context:**  
`prometheus-fastapi-instrumentator` provides automatic route metrics but with limited customization. `prometheus-client` directly gives full control over metric names, labels, and bucketing.

**Decision:**  
Use `prometheus-client` directly. Define custom metrics:
- `securedoc_requests_total{method, route, status}` — Counter
- `securedoc_request_duration_seconds{method, route}` — Histogram  
- `securedoc_page_cache_hits_total{level}` — Counter (l1/l2/miss)
- `securedoc_active_sessions_gauge` — Gauge (updated by periodic task)
- `securedoc_documents_by_status{status}` — Gauge

Expose at `/metrics` (internal only; not proxied through Cloudflare).

**Consequences:**  
+ Positive: Full control over metric definitions  
- Risk: Manual instrumentation is more work than auto-instrumentation. Mitigated by centralizing in middleware.

---

## ADR-009: PPTX via LibreOffice (same as DOCX pipeline)
**Status:** Accepted  
**Date:** 2026-06-07

**Context:**  
PPTX rendering has two options: LibreOffice headless conversion to PDF, or python-pptx + custom renderer. python-pptx can extract text but cannot render slides with full fidelity (custom fonts, SmartArt, embedded charts).

**Decision:**  
Use LibreOffice headless `--convert-to pdf` for PPTX, same as DOCX pipeline. The existing `LibreOfficeConverter.convert_to_pdf(bytes, suffix=".pptx")` already handles this — only the file detection and adapter registration need to be added.

**Consequences:**  
+ Positive: Reuses proven pipeline; PPTX support is ~1 day of work  
- Risk: LibreOffice PPTX rendering quality varies (custom fonts, transitions). Enterprise customers should test with their specific templates.

---

## ADR-010: SSO via Supabase SAML (not WorkOS)
**Status:** Accepted  
**Date:** 2026-06-07

**Context:**  
Two options evaluated:
1. WorkOS SDK — turnkey SAML/OIDC; ~$0.10/user/month for enterprise tier
2. Supabase SAML — Supabase Auth natively supports SAML 2.0 since 2023; free up to certain limits

**Decision:**  
Implement SSO via Supabase Auth SAML. The existing JWT validation in `auth.py` already validates Supabase JWTs. Supabase handles the SAML SP/IdP integration; our application only needs to:
1. Add `Organization` model
2. Add org membership resolution in `auth.py:get_current_user()`
3. Expose SSO-initiation endpoint

This avoids introducing a new vendor dependency and billing relationship.

**Consequences:**  
+ Positive: No new vendor; stays within existing Supabase contract  
+ Positive: Supabase SAML supports Google Workspace, Azure AD, Okta out of box  
- Risk: Supabase SAML is less battle-tested than WorkOS for edge cases (attribute mapping, JIT provisioning). Mitigation: thorough testing before GA.
