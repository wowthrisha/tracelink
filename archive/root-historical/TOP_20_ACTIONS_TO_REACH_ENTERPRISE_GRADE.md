# Top 20 Actions to Reach Enterprise Grade
**Date:** 2026-06-07  
**Baseline:** SECUREDOC_CURRENT_STATE_REPORT.md (same date)  
**Overall Score:** 5.2/10 C+ → Target: 8.5/10 A-

## Scoring Rubric

Each action is scored across four dimensions, each 1–5:

| Dimension | 1 | 3 | 5 |
|-----------|---|---|---|
| **Impact** | Nice-to-have | Meaningfully improves product | Blocks enterprise deals / critical vulnerability |
| **Complexity** | 1 = Easy | 3 = Moderate | 5 = Very Hard |
| **Risk Reduction** | 1 = Cosmetic | 3 = Eliminates real attack surface | 5 = Fixes critical P0 issue |
| **Cost** | 1 = Expensive | 3 = Moderate | 5 = Cheap / free |

**ROI Score** = `(Impact + Risk Reduction + Cost) / Complexity`  
Higher ROI = should do first.

---

## Quick Reference Table

| Rank | Action | Impact | Complexity | Risk Reduction | Cost | ROI |
|------|--------|--------|-----------|----------------|------|-----|
| 1 | Enable HSTS | 4 | 1 | 5 | 5 | **14.0** |
| 2 | Session validation Redis cache | 5 | 2 | 2 | 4 | **5.5** |
| 3 | PPTX / XLSX format support | 5 | 3 | 1 | 3 | **3.0** |
| 4 | Prometheus + Grafana metrics | 4 | 2 | 2 | 4 | **5.0** |
| 5 | Time-on-page analytics | 5 | 2 | 1 | 4 | **5.0** |
| 6 | SSO / SAML via WorkOS | 5 | 3 | 3 | 2 | **3.3** |
| 7 | Webhooks for view events | 4 | 2 | 1 | 4 | **4.5** |
| 8 | CDN for page images (R2 public + token) | 5 | 3 | 2 | 3 | **3.3** |
| 9 | JSON structured logging → Loki | 3 | 1 | 2 | 5 | **10.0** |
| 10 | Public API + API keys | 5 | 3 | 2 | 3 | **3.3** |
| 11 | Forensic stamp with viewer identity | 4 | 2 | 5 | 4 | **6.5** |
| 12 | Download uses streaming multi-part | 4 | 2 | 2 | 4 | **5.0** |
| 13 | Admin audit log UI | 4 | 3 | 3 | 3 | **3.3** |
| 14 | Fix max_views race condition | 3 | 1 | 4 | 5 | **12.0** |
| 15 | Document version history | 4 | 3 | 1 | 3 | **2.7** |
| 16 | Real-time viewer notifications | 4 | 3 | 1 | 2 | **2.3** |
| 17 | Role-based access (team members) | 5 | 4 | 2 | 2 | **2.3** |
| 18 | OpenTelemetry distributed tracing | 3 | 2 | 2 | 3 | **4.0** |
| 19 | Custom domain per workspace | 4 | 3 | 1 | 2 | **2.3** |
| 20 | SOC 2 Type II preparation | 5 | 5 | 4 | 2 | **2.2** |

---

## Priority Tier: Highest ROI (Do First)

These five actions have the highest ROI score — they close critical gaps for a low implementation cost and maximize security posture before investing in features.

---

### Action 1 — Enable HSTS by Default
**ROI: 14.0 | Impact: 4 | Complexity: 1 | Risk Reduction: 5 | Cost: 5**

**Problem:**
```python
# backend/app/config.py:96
hsts_max_age: int = 0   # Set to 31536000 once HTTPS confirmed stable
```
`hsts_max_age = 0` means HSTS is disabled in every deployment. Any deployment that omits this config is vulnerable to SSL strip attacks (MITM attacker downgrades HTTPS → HTTP). For a document security product, HTTPS enforcement is a baseline requirement.

**What to do:**
1. Change `config.py` default: `hsts_max_age: int = 31536000` (1 year)
2. Add `includeSubDomains` to the Strict-Transport-Security header in `security_headers.py`
3. Test HTTPS redirect with `HTTPS_REDIRECT=true` in staging before enabling `preload`

**Files:** `backend/app/config.py:96`, `backend/app/middleware/security_headers.py`

**Estimated effort:** 30 minutes  
**Estimated impact:** Eliminates SSL strip vulnerability; required for PCI-DSS, HIPAA, and most enterprise security reviews.

---

### Action 2 — Cache Session Validation in Redis (5-Second TTL)
**ROI: 5.5 | Impact: 5 | Complexity: 2 | Risk Reduction: 2 | Cost: 4**

**Problem:**
```python
# backend/app/services/policy.py:125–142
async def is_active_session(self, db, link_id, session_id) -> bool:
    result = await db.execute(
        select(ViewerSession).where(...)
    )
    ...
```
Every call to `GET /api/viewer/page` triggers a `SELECT` on `viewer_sessions`. At 100 concurrent viewers each refreshing every 3 seconds = 33 DB reads/second on `viewer_sessions` alone. This is the primary scalability bottleneck and will cause connection pool exhaustion before other components fail.

**What to do:**
1. Add `session_cache: _TTLCache[str, tuple[str, datetime]]` to `viewer_cache.py` (key: `session_id`, value: `(link_id, last_seen_at)`)
2. TTL: 5 seconds — ensures revocation propagates within 5 seconds
3. In `policy.py:is_active_session()`: check cache first; on miss, do DB SELECT and cache result
4. In `policy.py:upsert_session()`: invalidate or update cache entry after DB write
5. On revocation: call `session_cache.remove(session_id)` alongside `invalidate_link(token)`

**Files:** `backend/app/services/policy.py`, `backend/app/services/viewer_cache.py`

**Estimated effort:** 4 hours (including tests)  
**Estimated impact:** Reduces DB load per page request by ~95% at moderate concurrency. Enables 10× more concurrent viewers on the same DB instance.

---

### Action 14 — Fix max_views Race Condition (Atomic Check-and-Increment)
**ROI: 12.0 | Impact: 3 | Complexity: 1 | Risk Reduction: 4 | Cost: 5**

**Problem:**
The validate flow reads `view_count` and compares it to `max_views` in one query, then increments `view_count` in a second query. Under concurrent validation requests:

```
Session A: SELECT view_count = 9, max_views = 10  → PASSES
Session B: SELECT view_count = 9, max_views = 10  → PASSES (race)
Session A: UPDATE view_count = 10
Session B: UPDATE view_count = 11                  → max_views VIOLATED
```

**What to do:**
1. In `link_service.py:increment_view_count()`, use a single atomic `UPDATE ... WHERE view_count < max_views RETURNING id`
2. If `RETURNING` returns no rows, the limit was hit — raise `HTTPException(429, "Maximum views reached")`
3. PostgreSQL handles this atomically; no lock needed
4. Remove the separate `view_count` SELECT in `validate_link()`

**Files:** `backend/app/services/link_service.py`, `backend/app/routers/viewer.py:204`

**SQL change:**
```sql
-- Atomic check-and-increment
UPDATE share_links
SET view_count = view_count + 1
WHERE id = :link_id
  AND (max_views IS NULL OR view_count < max_views)
RETURNING view_count;
-- If 0 rows returned: max_views exceeded
```

**Estimated effort:** 2 hours  
**Estimated impact:** Eliminates view count bypass; required for accurate billing per view and enforceable access limits.

---

### Action 9 — JSON Structured Logging to Loki / Datadog
**ROI: 10.0 | Impact: 3 | Complexity: 1 | Risk Reduction: 2 | Cost: 5**

**Problem:**
```python
# backend/app/config.py:84
enable_json_logging: bool = False
```
All log output is unstructured plaintext. In production, this means:
- No searchable log fields (cannot filter by `session_id`, `link_id`, `document_id`)
- No alerting on error rate by route
- No Grafana/Datadog integration possible
- Incident investigation requires grepping raw log files

**What to do:**
1. Enable `enable_json_logging: bool = True` as default
2. In `main.py`, when JSON logging is enabled, configure `python-json-logger` with fields: `timestamp`, `level`, `logger`, `request_id`, `user_id`, `path`, `method`, `status_code`, `duration_ms`
3. In access log middleware, emit a single JSON line per request instead of formatted string
4. Add `document_id`, `link_id`, `session_id[:8]` as context fields in key log statements
5. Mount a Docker logging driver (JSON-file or Loki plugin) in `docker-compose.yml`

**Files:** `backend/app/config.py:84`, `backend/app/main.py`, `backend/app/middleware/request_id.py`

**Estimated effort:** 3 hours  
**Estimated impact:** Enables Grafana dashboards, Datadog integration, and incident response in minutes instead of hours.

---

### Action 11 — Forensic Stamp Must Contain Viewer Identity
**ROI: 6.5 | Impact: 4 | Complexity: 2 | Risk Reduction: 5 | Cost: 4**

**Problem:**
The current forensic stamp identifies only the document and page:
```python
# backend/app/services/watermark.py:88
mark_text = f"SD:{fingerprint}:{page_number:04d}"
```
The stamp is applied once during processing (`pipeline/pdf.py:52`) before any viewer is known. If someone downloads the raw WEBP from R2, the stamp proves "this came from SecureDoc document X, page N" but does NOT identify who downloaded it.

**This means:** An insider who obtains R2 credentials can download clean pages without leaving their identity in the file, using the forensic stamp as zero evidence against them.

**What to do:**

Two-phase approach that maintains O(1) storage:

**Phase A** (Quick win — applies to existing architecture):
Keep the document-level forensic stamp as-is. Add a second "viewer stamp" applied at serve time alongside the visible watermark, at minimal opacity (1–2%):
```python
# viewer.py:get_page() — after applying visible watermark
viewer_stamp = f"VS:{hash_value(session_id)}:{page_number:04d}"
stamped_bytes = watermark.apply_viewer_forensic_stamp(
    watermarked_bytes, viewer_stamp, opacity=0.01
)
```
This stamp is invisible but recoverable with image tools, contains the session ID hash, and enables viewer identification even if visible watermark is removed.

**Phase B** (Permanent solution — 2 pages storage per viewer):
Store session-specific page variants in R2 (`pages/{doc_id}/{page}/{session_id[:8]}.webp`). Each variant is pre-stamped with viewer identity. This enables instant forensic identification without real-time image processing per request.

**Recommended:** Phase A immediately; Phase B after CDN (Action 8) is in place.

**Files:** `backend/app/services/watermark.py`, `backend/app/routers/viewer.py`

**Estimated effort:** Phase A: 4 hours. Phase B: 2–3 days.  
**Estimated impact:** Closes the critical gap where direct R2 access bypasses viewer identity tracking.

---

## Tier 2: High Business Impact (Do Next)

---

### Action 4 — Prometheus Metrics + Grafana Dashboard
**ROI: 5.0 | Impact: 4 | Complexity: 2 | Risk Reduction: 2 | Cost: 4**

**Problem:** No metrics endpoint. Operators cannot observe:
- Page request rate and latency by document
- Cache hit rate (L1/L2)
- Queue depth and processing backlog
- Error rate by route
- Active viewer sessions

**What to do:**
1. Add `prometheus_fastapi_instrumentator` (or `starlette-prometheus`) to `requirements.txt`
2. Mount `/metrics` endpoint (internal, not proxied through Cloudflare)
3. Define custom gauges/counters:
   - `securedoc_page_requests_total{route, status}` (auto from instrumentator)
   - `securedoc_page_cache_hits_total{level}` (L1/L2)
   - `securedoc_active_sessions_gauge` (from periodic Celery task)
   - `securedoc_processing_queue_depth_gauge` (from `redis.llen("celery")`)
4. Add Docker Compose service: `prometheus` + `grafana`
5. Pre-built dashboard for: request latency p50/p95/p99, cache hit rate, processing queue depth

**Files:** `backend/requirements.txt`, `backend/app/main.py`, `docker-compose.yml`

**Estimated effort:** 1 day  
**Estimated impact:** Required for on-call response; enables auto-scaling decisions; demonstrates operational maturity in enterprise sales.

---

### Action 5 — Time-on-Page Analytics
**ROI: 5.0 | Impact: 5 | Complexity: 2 | Risk Reduction: 1 | Cost: 4**

**Problem:** SecureDoc tracks page_viewed events but not dwell time. DocSend's #1 selling feature is "see which slides prospects spent the most time on." Without time-on-page data, SecureDoc cannot compete on analytics.

**What to do:**
1. Frontend: Track `page_enter_time` when a page is navigated to; send `time_spent_ms` when navigating away or on heartbeat
2. API: Add optional `time_spent_ms: int` field to `POST /api/analytics/events` (existing endpoint)
3. DB migration: Add `time_spent_ms INTEGER` column to `access_events` table
4. Analytics response: Include `avg_time_per_page` in the aggregate view
5. UI: Add a simple "time heatmap" in Access Log tab — bar chart of pages with average dwell time

**Files:** `frontend/src/app.jsx`, `backend/app/routers/analytics.py`, new migration `012_add_time_spent_ms.py`

**Estimated effort:** 2 days (frontend-heavy)  
**Estimated impact:** Primary competitive differentiator vs. Google Drive; key feature in DocSend competitor comparison. Often the deciding factor for sales enablement teams.

---

### Action 7 — Webhooks for Document View Events
**ROI: 4.5 | Impact: 4 | Complexity: 2 | Risk Reduction: 1 | Cost: 4**

**Problem:** Document owners must check the Access Log in the UI to know if someone viewed a document. There is no push notification to external systems.

**What to do:**
1. DB: `webhook_endpoints` table: `(id, user_id, url, secret, events[])` — events = ["link.opened", "link.completed", "link.expired"]
2. `POST /api/webhooks` — register a webhook; `GET /api/webhooks` — list; `DELETE /api/webhooks/{id}` — deactivate
3. Celery task `securedoc.deliver_webhook(endpoint_id, event_type, payload)` — HMAC-SHA256 signed POST to target URL; retry on failure (3 retries, exponential backoff)
4. Trigger in `link_service.py` after session open and after `view_count >= max_views`
5. Send `X-SecureDoc-Signature: sha256=<HMAC>` header — standard pattern (Stripe, GitHub)

**Files:** New `backend/app/models/webhook.py`, `backend/app/routers/webhooks.py`, `backend/app/workers/tasks.py`

**Estimated effort:** 2 days  
**Estimated impact:** Enables Zapier/Make integrations and CRM automation ("fire when investor views pitch deck"). Frequently requested by enterprise customers.

---

### Action 12 — Streaming Download (Page-by-Page, No Full-RAM Assembly)
**ROI: 5.0 | Impact: 4 | Complexity: 2 | Risk Reduction: 2 | Cost: 4**

**Problem:**
```python
# backend/app/routers/viewer.py:680–750
# Downloads all pages, assembles into a single PDF bytes object in memory
pdf_buffer = io.BytesIO()
# ... assembles pages in memory
return StreamingResponse(io.BytesIO(pdf_buffer.getvalue()), ...)
```

With `max_download_pages_pdf=100` and an average page at ~100 KB, a 100-page download requires ~10 MB of API server RAM. At 50 concurrent downloads, that is 500 MB RAM solely for downloads. This limits `max_download_pages_pdf` to 100 and creates memory pressure.

**What to do:**
1. Use `reportlab` or `pypdf` with a streaming writer that emits PDF chunks page-by-page
2. Replace `io.BytesIO` accumulation with a generator that yields bytes as each page is processed
3. Use `StreamingResponse` with a generator function: `yield from _page_generator(pages)`
4. Remove the in-memory `pdf_buffer.getvalue()` call — data flows directly to client socket
5. Raise `max_download_pages_pdf` to 500 once streaming is confirmed working

**Files:** `backend/app/routers/viewer.py:680–750`

**Estimated effort:** 1 day  
**Estimated impact:** Enables full 500-page document downloads; reduces API server peak RAM by ~10× during downloads.

---

### Action 18 — OpenTelemetry Distributed Tracing
**ROI: 4.0 | Impact: 3 | Complexity: 2 | Risk Reduction: 2 | Cost: 3**

**Problem:** `X-Request-ID` exists but spans only the single HTTP request. There is no visibility into:
- Which page requests are slow due to R2 vs. Redis vs. watermark
- Celery task duration breakdown (download vs. rasterize vs. upload)
- DB query count per request

**What to do:**
1. Add `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-sqlalchemy` to `requirements.txt`
2. Initialize tracer in `main.py` with OTLP exporter pointing to Tempo or Jaeger
3. Add `opentelemetry-instrumentation-celery` for worker spans
4. Add Docker Compose service: `grafana-tempo` (or Jaeger)
5. Propagate `X-Request-ID` as parent span ID

**Files:** `backend/app/main.py`, `backend/requirements.txt`, `docker-compose.yml`

**Estimated effort:** 1 day  
**Estimated impact:** Enables root-cause analysis in under 5 minutes for latency incidents.

---

## Tier 3: Enterprise Features (Do After Tier 1 and 2)

---

### Action 3 — PPTX and XLSX Format Support
**ROI: 3.0 | Impact: 5 | Complexity: 3 | Risk Reduction: 1 | Cost: 3**

**Problem:** The two most common enterprise presentation formats are unsupported. An enterprise team with a PowerPoint pitch deck or Excel financial model cannot use SecureDoc.

**What to do:**
1. **PPTX:** LibreOffice already converts PPTX → PDF headlessly. Add `"pptx"` to `detect_file_type()` and `get_adapter()`. The existing DOCX → PDF pipeline handles PPTX with minimal changes.
2. **XLSX:** Add `"xlsx"` to `detect_file_type()`. LibreOffice converts XLSX → PDF but output quality varies. Consider using `openpyxl` + a PDF writer for better fidelity.
3. DB migration: Extend `file_type VARCHAR(10)` to `VARCHAR(20)` and add enum values
4. Add upload validation for XLSX binary structure (magic bytes: `PK\x03\x04`)
5. Test with common templates: investor model (multi-sheet), pitch deck (with images)

**Files:** `backend/app/services/text_processor.py` (detection), `backend/app/services/adapters.py`, `backend/app/workers/pipeline/`

**Estimated effort:** 3 days (PPTX 1 day, XLSX 2 days)  
**Estimated impact:** Unlocks the majority of enterprise document types. DocSend supports both.

---

### Action 6 — SSO via WorkOS or Auth0 (SAML / OIDC)
**ROI: 3.3 | Impact: 5 | Complexity: 3 | Risk Reduction: 3 | Cost: 2**

**Problem:** Enterprise IT teams will not approve a SaaS product that requires employees to create separate credentials. SSO is table-stakes for enterprise procurement, appearing in >90% of enterprise security reviews.

**What to do:**
1. Integrate [WorkOS](https://workos.com) SDK — adds SAML, OIDC, Google Workspace, Microsoft 365 SSO with 3 days of implementation vs. 3 months
2. Replace Supabase JWT validation in `auth.py` with WorkOS token verification
3. Add `Organization` model: `(id, name, sso_connection_id, allowed_domains[])`
4. Add `User.organization_id` FK; SCIM provisioning for user sync
5. Billing: SSO is typically an enterprise tier feature — wire to plan gating

**Alternative:** Supabase Auth supports SAML/OIDC natively. If staying on Supabase, configure SAML there rather than adding WorkOS.

**Files:** `backend/app/routers/auth.py`, `backend/app/models/` (new Organization model), `backend/app/config.py`

**Estimated effort:** 1 week  
**Estimated impact:** Required for Fortune 500 procurement approval; enables team-level sharing and provisioning.

---

### Action 8 — CDN for Page Images with Signed Cloudflare Tokens
**ROI: 3.3 | Impact: 5 | Complexity: 3 | Risk Reduction: 2 | Cost: 3**

**Problem:** Every page request (`/api/viewer/page/{token}/{page}`) downloads image bytes from R2 to the API server, then streams them to the browser. This path:
- Adds ~50–200ms latency (R2 round-trip + server processing)
- Consumes API server bandwidth (outbound egress on every page)
- Prevents geographic distribution (all requests route through single region)
- Cannot use browser caching (response is `Cache-Control: private, no-store`)

**What to do:**
1. Configure R2 bucket as a Cloudflare-proxied public origin (pages and thumbs only — NOT originals)
2. In `viewer.py:get_page()`, generate a Cloudflare signed URL with 60-second expiry instead of streaming bytes
3. Return a 302 redirect (or `{url: "..."}` JSON) pointing to the signed CDN URL
4. Cloudflare edge caches the page image; the signed token prevents unauthorized direct access
5. Visible watermark must now be pre-generated or moved to Cloudflare Workers (complexity trade-off)

**Security trade-off:**
- Current: API server applies visible watermark per request — full viewer identity in every served image
- CDN approach: Visible watermark must be pre-generated per session (adds storage) or applied at Cloudflare Worker edge (adds LO to Workers budget)

**Recommended approach:** CDN for thumbnails (no watermark required). Keep API-proxied path for full-page images. Hybrid model: CDN latency benefit for thumbnail strip; security model unchanged for full pages.

**Files:** `backend/app/routers/viewer.py:338–450`, `backend/app/services/storage.py`

**Estimated effort:** 3 days (hybrid approach)  
**Estimated impact:** Reduces page load latency by 50–80% via edge caching; removes egress bandwidth cost for thumbs.

---

### Action 10 — Public API with API Keys
**ROI: 3.3 | Impact: 5 | Complexity: 3 | Risk Reduction: 2 | Cost: 3**

**Problem:** SecureDoc has no public API for integrations. Enterprise customers cannot:
- Programmatically upload documents from their CRM/ERP
- Auto-revoke links on deal close
- Query analytics from their BI tools
- Build custom workflows (Zapier, Workato, etc.)

**What to do:**
1. DB: `api_keys` table: `(id, user_id, key_hash, name, created_at, last_used_at, revoked_at)`
2. `POST /api/v1/keys` — generate a new API key; returns key once (stored as bcrypt hash)
3. API key auth middleware: validates `Authorization: Bearer sdoc_sk_...` header
4. Version all routes: `/api/v1/documents`, `/api/v1/links`, `/api/v1/analytics`
5. Rate limiting per API key (separate limit from UI sessions)
6. OpenAPI spec with `servers` pointing to `https://secure.wowmyspace.com`

**Files:** New `backend/app/models/api_key.py`, `backend/app/middleware/api_key_auth.py`, versioned routers

**Estimated effort:** 3 days  
**Estimated impact:** Unlocks Zapier integration, CRM automation, and headless document workflows. Required for enterprise self-service.

---

### Action 13 — Admin Audit Log UI
**ROI: 3.3 | Impact: 4 | Complexity: 3 | Risk Reduction: 3 | Cost: 3**

**Problem:** Access events are stored in `access_events` DB table but the Access Log tab in the UI shows only current document events. There is no organization-wide audit log showing:
- All link activations across all documents
- Failed validation attempts (wrong password, IP denied)
- Admin actions (link revocation, document deletion)

This is required for SOC 2 audit evidence and enterprise security reviews.

**What to do:**
1. Add `event_type` values: `"ip_denied"`, `"password_failed"`, `"link_revoked"`, `"document_deleted"` — log these in the relevant code paths
2. New `GET /api/admin/audit-log` endpoint: paginated, filterable by event_type, date range, document, user
3. New "Audit Log" tab in the Access Control section of the UI (admin-only, gated by plan)
4. CSV export from the UI
5. DB index: `CREATE INDEX ix_access_events_user_created ON access_events(user_id, created_at DESC)` (for org-wide queries)

**Files:** `backend/app/routers/analytics.py`, `backend/app/models/event.py`, `frontend/src/app.jsx`

**Estimated effort:** 3 days  
**Estimated impact:** Required for SOC 2 CC6.1, CC7.2; frequently cited in enterprise security questionnaires.

---

## Tier 4: Competitive Completeness

---

### Action 15 — Document Version History
**ROI: 2.7 | Impact: 4 | Complexity: 3 | Risk Reduction: 1 | Cost: 3**

Allow uploading a new version of an existing document without changing its share links.

**What to do:**
1. Add `Document.version: int` and `Document.parent_id FK → Document.id` (allows version chain)
2. `POST /api/documents/{id}/version` — upload new version; marks old as `superseded`, creates new with same `group_id`
3. Share links point to `document_id` of the latest active version (resolved at serve time)
4. UI: "Upload new version" button; version history panel showing v1, v2, v3 with upload date and view count

**Estimated effort:** 3 days

---

### Action 16 — Real-Time View Notifications (WebSocket or SSE)
**ROI: 2.3 | Impact: 4 | Complexity: 3 | Risk Reduction: 1 | Cost: 2**

DocSend sends push notifications when a prospect opens a document. This is a key engagement feature for sales teams.

**What to do:**
1. Add `GET /api/events` (Server-Sent Events) — authenticated stream for the document owner
2. When `access_events` INSERT occurs in the viewer path, publish to Redis pub/sub channel `user:{user_id}:events`
3. SSE endpoint subscribes to that channel and forwards events to connected owner
4. UI: Toast notification "John@corp.com just opened your pitch deck"

**Estimated effort:** 3 days (Redis pub/sub + SSE)

---

### Action 17 — Role-Based Access (Team Members)
**ROI: 2.3 | Impact: 5 | Complexity: 4 | Risk Reduction: 2 | Cost: 2**

Enterprise teams need multiple users to manage documents. Currently all documents are single-owner.

**What to do:**
1. `Organization` model (from Action 6 SSO)
2. `OrgMembership` table: `(org_id, user_id, role)` — roles: `owner`, `admin`, `editor`, `viewer`
3. Ownership model: Documents belong to organizations, not individuals
4. Access control: `admin+` can manage all documents; `editor` can upload/create links; `viewer` sees analytics only
5. Invitation flow: `POST /api/org/invite` sends email via Supabase

**Estimated effort:** 5 days (requires SSO infrastructure from Action 6)

---

### Action 19 — Custom Domain per Workspace
**ROI: 2.3 | Impact: 4 | Complexity: 3 | Risk Reduction: 1 | Cost: 2**

Enable enterprise customers to serve documents at `docs.theircompany.com` instead of `secure.wowmyspace.com`.

**What to do:**
1. `Workspace.custom_domain` column + DNS verification flow (TXT record challenge)
2. Cloudflare API to add custom hostname to the tunnel/zone
3. `APP_PUBLIC_BASE_URL` becomes per-workspace: read from DB at link generation time
4. SSL: Cloudflare handles cert provisioning via its custom hostname feature

**Estimated effort:** 3 days (Cloudflare custom hostnames API + DB changes)

---

### Action 20 — SOC 2 Type II Preparation
**ROI: 2.2 | Impact: 5 | Complexity: 5 | Risk Reduction: 4 | Cost: 2**

SOC 2 Type II is the primary certification requested in enterprise security reviews. It requires 6+ months of evidence collection demonstrating security controls were operating continuously.

**SOC 2 readiness gaps today:**
| Control | Gap | Fix |
|---------|-----|-----|
| CC6.1 Logical access control | Admin audit log incomplete | Action 13 |
| CC6.2 Authentication | SSO not available | Action 6 |
| CC6.7 Transmission security | HSTS disabled by default | Action 1 |
| CC7.2 Monitoring | No metrics/alerts | Action 4 |
| CC7.3 Security incidents | No incident response playbook | Document policy |
| CC8.1 Change management | No CI/CD pipeline | Add GitHub Actions |
| A1.1 System availability | No uptime SLA or monitoring | Add UptimeRobot + PagerDuty |

**Recommended sequence:**
1. Complete Actions 1, 4, 9, 13 (fills CC6.7, CC7.2, CC7.3, CC6.1)
2. Engage a SOC 2 audit firm to identify gaps for your specific trust service criteria
3. Begin 6-month observation period (evidence collection)
4. Annual audit certification

**Estimated effort:** 3–6 months of preparation + audit engagement cost ($15–40K)  
**Estimated impact:** Required for Fortune 500 and financial services enterprise sales.

---

## Implementation Roadmap

### Month 1 (Security and Observability Foundation)
- **Week 1:** Actions 1 (HSTS), 14 (max_views race), 9 (JSON logs)
- **Week 2:** Action 2 (session cache), Action 11 Phase A (viewer forensic stamp)
- **Week 3:** Action 4 (Prometheus + Grafana)
- **Week 4:** Action 12 (streaming download), Action 7 (webhooks skeleton)

### Month 2 (Enterprise Feature Gap)
- **Week 1–2:** Action 3 (PPTX/XLSX support)
- **Week 3:** Action 5 (time-on-page analytics), Action 7 (webhooks complete)
- **Week 4:** Action 10 (public API v1), Action 13 (audit log)

### Month 3 (Enterprise Platform)
- **Week 1–2:** Action 6 (SSO)
- **Week 3:** Action 17 (RBAC, requires SSO)
- **Week 4:** Action 8 (CDN for thumbnails), Action 18 (tracing)

### Month 4–6 (Market Expansion)
- Action 15 (version history)
- Action 16 (real-time notifications)
- Action 19 (custom domains)
- Action 20 (SOC 2 preparation — ongoing)

---

## Resulting Score After Top 5 Actions

| Dimension | Before | After Top 5 | Change |
|-----------|--------|-------------|--------|
| Security | 6.5/10 | 8.5/10 | +2.0 |
| Performance | 5.5/10 | 7.0/10 | +1.5 |
| Scalability | 4.5/10 | 6.5/10 | +2.0 |
| Reliability | 5.0/10 | 5.5/10 | +0.5 |
| Observability | 3.5/10 | 7.5/10 | +4.0 |
| Maintainability | 6.0/10 | 6.5/10 | +0.5 |
| **Overall** | **5.2/10** | **7.0/10** | **+1.8** |

After all 20 actions:

| Dimension | Score |
|-----------|-------|
| Security | 9.0/10 |
| Performance | 8.0/10 |
| Scalability | 8.0/10 |
| Reliability | 8.0/10 |
| Observability | 8.5/10 |
| Maintainability | 8.0/10 |
| **Overall** | **8.3/10 A-** |
