# SecureDoc — All Action Design Docs

> Combined from 19 individual `ACTION_*_DESIGN.md` files.  
> Actions are grouped by phase. Action 16 had no standalone design file (RBAC was covered inline in the org/phase4 plan).

---

## Table of Contents

### Phase 1 — Security Critical
- [Action 1: Enable HSTS by Default](#action-1-enable-hsts-by-default)
- [Action 2: Fix max_views Race Condition](#action-2-fix-max_views-race-condition)
- [Action 3: Viewer Identity Forensic Stamp](#action-3-viewer-identity-forensic-stamp)
- [Action 4: Session Validation Cache](#action-4-session-validation-cache)
- [Action 5: Structured JSON Logging](#action-5-structured-json-logging)

### Phase 2 — Scalability
- [Action 6: Streaming PDF Downloads](#action-6-streaming-pdf-downloads)
- [Action 7: Prometheus Metrics](#action-7-prometheus-metrics)
- [Action 8: OpenTelemetry Distributed Tracing](#action-8-opentelemetry-distributed-tracing)
- [Action 9: CDN Offload for Thumbnails](#action-9-cdn-offload-for-thumbnails)

### Phase 3 — Product Completeness
- [Action 10: PPTX Support](#action-10-pptx-support)
- [Action 11: XLSX Support](#action-11-xlsx-support)
- [Action 12: Time-on-Page Analytics](#action-12-time-on-page-analytics)
- [Action 13: Webhooks](#action-13-webhooks)
- [Action 14: Public API + API Keys](#action-14-public-api--api-keys)

### Phase 4 — Enterprise
- [Action 15: Organizations + SSO Foundation](#action-15-organizations--sso-foundation)
- [Action 16: RBAC](#action-16-rbac)
- [Action 17: Admin Audit Log](#action-17-admin-audit-log)
- [Action 18: Document Version History](#action-18-document-version-history)
- [Action 19: Real-Time SSE Notifications](#action-19-real-time-sse-notifications)
- [Action 20: Custom Domains](#action-20-custom-domains)

---

# Phase 1 — Security Critical

---

## Action 1: Enable HSTS by Default

**Status:** COMPLETE | **Risk:** Low (config change only)

### Problem

`config.py` defaulted `hsts_max_age: int = 0`, meaning every deployment without an explicit env var got no HSTS header. HTTP Strict Transport Security prevents SSL strip attacks — a network MITM can silently downgrade HTTPS to HTTP, exposing session tokens, passwords sent to `/validate`, and document bytes.

### Current Architecture

- `config.py:96`: `hsts_max_age: int = 0`
- `security_headers.py`: HSTS only injected when `hsts_max_age > 0` AND `X-Forwarded-Proto: https`
- `main.py`: emitted a WARNING (not error) when HSTS disabled in production

### Alternative Designs

| Option | Verdict |
|--------|---------|
| Keep default=0, add docs | Rejected — insecure by default |
| Default=31536000, opt-out via env | **Chosen** — safe because middleware already checks X-Forwarded-Proto |
| Force-enable, no opt-out | Rejected — too restrictive |

### Chosen Design

Default `hsts_max_age=31536000`. Added `; preload` to enable HSTS preload list submission. Production startup check changed from warning → error when HSTS is disabled.

**Safe because:** The middleware only injects HSTS when the request arrived over HTTPS (`X-Forwarded-Proto: https`). HTTP-only local dev deployments are never affected.

### Files Changed

- `app/config.py` — default 0 → 31536000
- `app/middleware/security_headers.py` — added `; preload`
- `app/main.py` — HSTS warning → error in production startup

### Rollback

Set `HSTS_MAX_AGE=0` in `.env`. HSTS header immediately stops being sent. No redeploy required.

### Test Plan

1. HSTS header present on HTTPS responses (`X-Forwarded-Proto: https`)
2. HSTS header absent on HTTP responses (no X-Forwarded-Proto)
3. max-age = 31536000, includes `includeSubDomains` and `preload`
4. Production startup raises error when HSTS=0
5. `HSTS_MAX_AGE=0` env var disables it (opt-out works)

---

## Action 2: Fix max_views Race Condition

**Status:** COMPLETE | **Risk:** Medium (modifies core validation flow)

### Problem

Two concurrent `/validate` requests could both read `view_count = N-1`, both pass `N-1 < max_views`, and both succeed — allowing a `max_views=1` one-time link to be used twice. This was exploitable both accidentally (two browser tabs) and intentionally (parallel requests).

### Current Architecture

```python
# link_service.py — step 4 (separate read)
if link.max_views is not None and link.view_count >= link.max_views:
    raise HTTPException(410)

# viewer.py — separate write later
await link_svc.increment_view_count(db, str(link.id), commit=False)
```

Two separate DB operations = TOCTOU race.

### Alternative Designs

| Option | Verdict |
|--------|---------|
| SELECT FOR UPDATE | Rejected — row lock held across Python check; low throughput |
| Optimistic locking (version column) | Rejected — requires retry loop, extra roundtrips |
| Atomic UPDATE ... RETURNING | **Chosen** — single atomic operation, no locks |

### Chosen Design

```sql
UPDATE share_links
SET view_count = view_count + 1
WHERE id = :link_id
  AND (max_views IS NULL OR view_count < max_views)
RETURNING id
```

If 0 rows returned → max_views was hit → 410. One fewer DB round-trip per validate call (2 → 1).

### Files Changed

- `app/services/link_service.py` — removed eager max_views check; added atomic UPDATE RETURNING
- `app/routers/viewer.py` — removed separate `increment_view_count()` call

### Test Plan

1. Single validate succeeds when under limit
2. Returns 410 exactly when limit reached
3. 10 concurrent threads: total successes ≤ max_views
4. `max_views=None` → never hits 410
5. Failed validates (wrong password, IP denied) do NOT increment view_count

---

## Action 3: Viewer Identity Forensic Stamp

**Status:** COMPLETE | **Risk:** Low (additive to existing watermark pipeline)

### Problem

Two watermarks existed:
1. **Document forensic stamp** — applied during Celery processing, stored in R2. Identifies document + page. Does NOT identify the viewer.
2. **Visible watermark** — applied at serve time. Contains email + date. Visible to naked eye.

Gap: If someone obtained raw R2 bytes (via stolen credentials), they got pages that proved the document but NOT who viewed it.

### Chosen Design

New serve-time method `apply_viewer_forensic_stamp(image_bytes, session_id, page_number)`:
- Stamp text: `VS:{sha256(session_id)[:8]}:{page:04d}`
- Opacity: 1.5% (half of document stamp's 3%)
- Position: lower-LEFT corner (document stamp = lower-right; different corners = independent recovery)
- Applied AFTER visible watermark in the same executor call (single PIL round-trip)

The 8-char SHA-256 prefix of session_id allows DB lookup to identify viewer without exposing raw session ID in the image.

### Files Changed

- `app/services/watermark.py` — `apply_viewer_forensic_stamp()` method
- `app/routers/viewer.py` — chained in `get_page()` after visible watermark

### Test Plan

1. Returns bytes with pixel changes in lower-left corner
2. Format: `VS:{8 hex chars}:{4-digit page}`
3. Different session_ids → different stamp texts
4. Same session_id → deterministic (stable)
5. Does NOT contain raw session_id

---

## Action 4: Session Validation Cache

**Status:** COMPLETE | **Risk:** Low (additive cache layer)

### Problem

`policy.py:is_active_session()` issued a DB read on EVERY page/thumb/text/toc/download request. At 100 concurrent viewers × 1 page/2s = 50 DB reads/sec on `viewer_sessions`. Pool exhaustion risk above ~200 concurrent page requests/sec.

### Chosen Design

Process-local `session_cache: _TTLCache` in `viewer_cache.py`. TTL=5s, maxsize=50,000.

- Cache key: `session_id` (32 hex chars)
- Cache value: `(link_id, last_seen_at, viewer_email_masked)`
- On revocation: `invalidate_sessions_for_link(link_id)` scans and purges matching entries
- On hit: verifies `link_id` matches AND `last_seen_at >= cutoff` (cross-link replay protection preserved)

**Performance:** ~1 DB read per 5s per unique session instead of per request.  
**Security risk:** ≤5s window between revocation and cache expiry — acceptable per ADR-004.

### Files Changed

- `app/services/viewer_cache.py` — `session_cache`, `invalidate_sessions_for_link()`
- `app/services/policy.py` — cache-first `is_active_session()` and `upsert_session()`

---

## Action 5: Structured JSON Logging

**Status:** COMPLETE | **Risk:** Low (logging format change only)

### Problem

Default `enable_json_logging: bool = False` meant every deployment without explicit opt-in got plaintext logs. No log aggregation (Loki/Datadog/CloudWatch), no field-based alerting, no trace ID correlation.

### Chosen Design

Changed default to `True`. Enhanced `json_logging.py` formatter with:
- `status_code`, `method`, `path`, `duration_ms`, `request_id` for HTTP access log
- `user_id`, `doc_id`, `link_id` correlation fields
- Sensitive field protection: `session_id` logged as `session_id[:8]` only

Celery workers also emit JSON logs on startup.

### Files Changed

- `app/config.py` — default False → True
- `app/middleware/json_logging.py` — extended formatter
- `app/middleware/request_id.py` — structured JSON access log per request
- `app/workers/celery_app.py` — JSON logging in worker startup

### Rollback

Set `ENABLE_JSON_LOGGING=false` in `.env`. No code change needed.

---

# Phase 2 — Scalability

---

## Action 6: Streaming PDF Downloads

**Status:** COMPLETE | **Risk:** Low (streaming replaces buffered assembly)

### Problem

The download endpoint loaded ALL page images from R2 into memory simultaneously. For a 100-page doc at 200KB/page WebP: ~40–80MB buffer before first byte was sent. Under concurrent downloads this could OOM the API container.

### Chosen Design

Generator-based `StreamingResponse`:
- Fetch pages from R2 one at a time (batches of N=5)
- Write each page as a single-page PDF chunk immediately
- Apply watermark per-page before embedding
- `Content-Disposition: attachment` to prevent inline rendering

Peak memory during 100-page download: ~5MB (1 page in flight) vs ~80MB (all-at-once).  
Raised `max_download_pages_pdf` from 100 → 500 (safe now that pages aren't all in memory).

### Files Changed

- `app/routers/viewer.py` — generator-based `_stream_download_pages()`
- `app/config.py` — `max_download_pages_pdf`: 100 → 500

---

## Action 7: Prometheus Metrics

**Status:** COMPLETE | **Risk:** Zero (pure-additive)

### Problem

Zero observability into application-level performance: no way to alert on error rates, no SLO measurement, no Grafana integration. Cannot make enterprise SLA commitments without metrics.

### Metrics Defined

| Metric | Type | Labels |
|--------|------|--------|
| `securedoc_http_requests_total` | Counter | method, path_pattern, status_code |
| `securedoc_http_request_duration_seconds` | Histogram | method, path_pattern |
| `securedoc_viewer_validations_total` | Counter | result |
| `securedoc_page_requests_total` | Counter | cache_hit |
| `securedoc_downloads_total` | Counter | result |
| `securedoc_document_uploads_total` | Counter | status |
| `securedoc_active_sessions` | Gauge | — |

Path normalization prevents cardinality explosion (UUIDs/tokens replaced with `{id}`/`{token}`).

### Files Changed

- `app/metrics.py` — metric singletons + `normalize_path()`
- `app/middleware/metrics.py` — `PrometheusMiddleware` ASGI wrapper
- `app/main.py` — `/metrics` endpoint + middleware wired in
- `requirements.txt` — `prometheus-client>=0.21.0`

### Security Note

`/metrics` is unauthenticated — restrict access at the network/firewall layer. No user data, emails, IPs, or session IDs in metric labels.

---

## Action 8: OpenTelemetry Distributed Tracing

**Status:** COMPLETE | **Risk:** Zero (no-op when endpoint not configured)

### Problem

No distributed tracing. When a document took 8+ seconds to load, impossible to tell if the bottleneck was DB, R2, watermark render, or network without a prod debug session.

### Chosen Design

OpenTelemetry SDK with auto-instrumentation (FastAPI + SQLAlchemy). OTLP export to any compatible backend (Tempo, Jaeger, Honeycomb, Datadog).

- Default: disabled (`OTEL_EXPORTER_OTLP_ENDPOINT=""`) — no overhead when not configured
- Activates only when endpoint is set in `.env`
- No manual span creation needed for common paths

### Files Changed

- `app/telemetry.py` — `setup_tracing()`, `instrument_app()`
- `app/config.py` — `otel_exporter_otlp_endpoint`, `otel_service_name`
- `app/main.py` — called in lifespan startup
- `requirements.txt` — 4 otel packages

---

## Action 9: CDN Offload for Thumbnails

**Status:** COMPLETE | **Risk:** Low (opt-in, default off)

### Problem

Every thumbnail request hit the API: session check + R2 download + PIL watermark + return bytes. For a 50-page doc, first viewer fetched all 50 thumbnails through the API. Subsequent viewers repeated the same work — thumbnails are identical for all viewers (no per-session data).

### Chosen Design

When `cdn_thumbnail_enabled=True`, the thumbnail endpoint returns a **302 redirect** to a presigned R2 URL (TTL=300s) instead of proxying bytes.

**Security invariants preserved:**
- Session validation still runs before the redirect
- Full page endpoint (`/api/viewer/page/{token}/{page}`) NEVER redirects — proxied always (hard rule from security spec)
- Presigned URLs are short-lived (5 minutes), unguessable

### Files Changed

- `app/routers/viewer.py` — presigned redirect in `/thumb/` when CDN enabled
- `app/config.py` — `cdn_thumbnail_enabled`, `cdn_thumbnail_presign_ttl_sec`

---

# Phase 3 — Product Completeness

---

## Action 10: PPTX Support
## Action 11: XLSX Support

**Status:** COMPLETE | **Risk:** Low (same LibreOffice pipeline as DOCX)

### Problem

Enterprise document sharing expects PowerPoint (PPTX) and Excel (XLSX). Without them, every deck or spreadsheet shared with a prospect must be manually converted to PDF by the sender. All major competitors (DocSend, Box, Dropbox, Adobe, Google) support these natively.

### Chosen Design

LibreOffice headless is already deployed for DOCX. It supports PPTX and XLSX with high fidelity. The pipeline is identical:

1. Download original PPTX/XLSX from storage
2. Convert → PDF via `LibreOfficeConverter.convert_to_pdf(bytes, ".pptx")`
3. Pass PDF bytes to existing `process_pdf_document()` pipeline
4. Store page WebP images, apply forensic stamp, write thumbnails

No migration needed — `file_type VARCHAR(10)` already supports `pptx` (4 chars) and `xlsx` (4 chars).

### Files Changed

- `app/services/adapters/presentation.py` — `PPTXAdapter` with ZIP magic validation
- `app/services/adapters/spreadsheet.py` — `XLSXAdapter` with ZIP magic validation
- `app/workers/pipeline/pptx_pdf.py` — PPTX processing pipeline
- `app/workers/pipeline/xlsx_pdf.py` — XLSX processing pipeline
- `app/services/adapters/registry.py` — both adapters registered (8 total)
- `app/services/text_processor.py` — PPTX/XLSX detection by extension + MIME

---

## Action 12: Time-on-Page Analytics

**Status:** COMPLETE | **Risk:** Low (additive nullable column)

### Problem

SecureDoc logged page_viewed events but captured no dwell time. DocSend's core value prop is "see which pages engaged them." Without `time_spent_ms`, the Access Log is a click-stream, not an engagement story.

### Schema Change

```sql
-- Migration 013
ALTER TABLE access_events ADD COLUMN time_spent_ms INTEGER NULL;
```

### Validation Rules

- Must be a non-negative integer (bool subclass rejected)
- Capped server-side at 14,400,000 ms (4 hours) to prevent skewed averages
- Fully optional — historical events have NULL, not 0
- Only accepted for `VIEWER_LOGGABLE_EVENTS` (client-supplied timing on server events blocked)

### API Changes

- `POST /api/analytics/events` — body may include `"time_spent_ms": 12500`
- `GET /api/analytics/events` — response includes `"time_spent_ms": null|<int>`

### Files Changed

- `app/models/event.py` — `time_spent_ms` mapped column
- `alembic/versions/013_add_time_spent_ms.py` — migration
- `app/services/analytics_service.py` — `time_spent_ms` kwarg in `log_event()`
- `app/routers/analytics.py` — extract, validate (cap at 4h), pass, expose in GET

---

## Action 13: Webhooks

**Status:** COMPLETE | **Risk:** Medium (async delivery infrastructure)

### Problem

No programmatic event notification. Enterprise customers need to react to document events (prospect opened doc, viewer finished reading) from their CRM, sales tools, or Zapier workflows.

### Supported Events

| Event | Trigger |
|-------|---------|
| `document.processed` | After pipeline completes (success or error) |
| `link.viewed` | After viewer successfully validates a share link |
| `analytics.completed` | After viewer logs the `completed` event |

### Payload Format

```json
{
  "id": "<delivery_uuid>",
  "event": "document.processed",
  "created_at": "2026-06-07T12:00:00Z",
  "data": { "document_id": "...", "filename": "report.pdf", "status": "ready", "page_count": 12 }
}
```

### HMAC Signing

```
X-SecureDoc-Signature: sha256=<hex(HMAC-SHA256(secret, body_bytes))>
X-SecureDoc-Event: document.processed
X-SecureDoc-Delivery: <delivery_uuid>
```

### Delivery & Retry

- Timeout: 10s per attempt
- Retry on: 5xx, 429, connection error
- No retry on: 4xx (bad endpoint config)
- Schedule: 1m → 5m → 30m → 3h (4 retries max)
- After 4 retries: `status = "failed"`
- `WebhookDelivery` committed before Celery task queued — no orphan tasks on crash

### API

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/webhooks | Create (secret returned once only) |
| GET | /api/webhooks | List (no secret) |
| GET | /api/webhooks/{id} | Get (no secret) |
| PATCH | /api/webhooks/{id} | Update url/events/is_active |
| DELETE | /api/webhooks/{id} | Delete + cascade deliveries |
| GET | /api/webhooks/{id}/deliveries | Delivery history |
| POST | /api/webhooks/{id}/test | Send test ping |

### Files Changed

- `app/models/webhook.py` — `WebhookEndpoint`, `WebhookDelivery`, `WEBHOOK_EVENTS`
- `alembic/versions/014_add_webhooks.py` — tables + indexes
- `app/services/webhook_service.py` — `dispatch_webhook_event()` fan-out
- `app/routers/webhooks.py` — full CRUD + delivery history + test endpoint
- `app/workers/webhook_tasks.py` — `deliver_webhook` Celery task, HMAC, 4-level retry
- `app/workers/tasks.py` — `document.processed` trigger after pipeline
- `app/routers/analytics.py` — `analytics.completed` trigger
- `app/routers/viewer.py` — `link.viewed` trigger after validate

---

## Action 14: Public API + API Keys

**Status:** COMPLETE | **Risk:** Medium (auth path change)

### Problem

Enterprise integrations (Salesforce, HubSpot, scripts) cannot use short-lived JWT tokens. They need stable, revocable API keys for machine-to-machine requests.

### Key Format

```
sd_<48 hex chars>   →   51 chars total, 192-bit entropy
```

- `sd_` prefix: easily grep-able if leaked into logs
- SHA-256 stored in DB; full key shown only once at creation

### Scopes

`documents:read`, `documents:write`, `links:read`, `links:write`, `analytics:read`, `webhooks:read`, `webhooks:write`

### Authentication Flow

1. Request arrives with `Authorization: Bearer sd_...` or `X-API-Key: sd_...`
2. `get_current_user` tries X-API-Key first, then Bearer `sd_` prefix, then JWT
3. API key path: SHA-256 supplied key → lookup by hash → check is_active + expiry
4. On valid: update `last_used_at` asynchronously → return same user dict as JWT

**FastAPI signature note:** `x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None` — the `= None` keeps Python's actual default as `None`; the `Header(...)` is annotation-only metadata. Using `Header(default=None, alias=...)` causes unit tests that call the function directly to receive the Header sentinel object instead of None.

### API

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/api-keys | Create (full key returned once) |
| GET | /api/api-keys | List (no key value) |
| GET | /api/api-keys/{id} | Get metadata |
| PATCH | /api/api-keys/{id} | Update name/scopes/is_active |
| DELETE | /api/api-keys/{id} | Revoke |

### Files Changed

- `app/models/api_key.py` — `APIKey` model, `API_SCOPES`, `generate_api_key()`, `hash_api_key()`
- `alembic/versions/015_add_api_keys.py` — `api_keys` table
- `app/routers/api_keys.py` — CRUD router
- `app/auth.py` — `verify_api_key()` + `sd_` detection in `get_current_user`

---

# Phase 4 — Enterprise

---

## Action 15: Organizations + SSO Foundation

**Status:** COMPLETE | **Risk:** P1 (single-owner model blocks team use)

### Problem

SecureDoc was purely single-user. Teams couldn't share a document library, admins couldn't manage access, and SAML SSO requires an org-scoped identity model. Enterprise procurement requires workspace-level access control.

### Role Hierarchy

| Role | Upload | Share | Analytics | Manage Members | Org Settings |
|------|--------|-------|-----------|----------------|--------------|
| viewer | ✗ | ✗ | own only | ✗ | ✗ |
| editor | ✓ | own | ✗ | ✗ | ✗ |
| admin | ✓ | all | all | non-owner | ✗ |
| owner | ✓ | all | all | all | ✓ |

### Schema

```sql
-- Migration 016
CREATE TABLE organizations (
  id UUID PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  slug VARCHAR(100) NOT NULL UNIQUE,
  saml_domain VARCHAR(255),
  is_active BOOL NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
);

CREATE TABLE org_memberships (
  id UUID PRIMARY KEY,
  org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  role VARCHAR(16) NOT NULL DEFAULT 'viewer',
  invited_by_user_id UUID,
  created_at TIMESTAMPTZ,
  UNIQUE(org_id, user_id)
);

ALTER TABLE documents ADD COLUMN org_id UUID REFERENCES organizations(id) ON DELETE SET NULL;
```

### Security Rules

- Owner cannot be removed if last owner (prevents lockout)
- Role change cannot escalate beyond actor's own role (`role_gte()`)
- Org deletion cascades memberships; documents get `org_id=NULL` (not deleted)

### API

`POST /api/orgs` · `GET /api/orgs` · `GET /api/orgs/{id}` · `PATCH /api/orgs/{id}` · `DELETE /api/orgs/{id}` · `GET /api/orgs/{id}/members` · `POST /api/orgs/{id}/members` · `PATCH /api/orgs/{id}/members/{uid}` · `DELETE /api/orgs/{id}/members/{uid}`

### Files Changed

- `app/models/org.py` — `Organization`, `OrgMembership`, `ORG_ROLES`, `role_gte()`
- `alembic/versions/016_add_organizations.py`
- `app/services/org_service.py` — `_slugify()`, `get_membership()`, `require_role()`, `ensure_unique_slug()`
- `app/routers/orgs.py` — full CRUD + member management

---

## Action 16: RBAC

**Status:** COMPLETE | **Risk:** Low (enforced via existing role_gte helper)

### Design

Role-Based Access Control is enforced by the `role_gte(role, minimum)` helper in `org.py`:

```python
_ROLE_RANK = {"viewer": 0, "editor": 1, "admin": 2, "owner": 3}

def role_gte(role: str, minimum: str) -> bool:
    return _ROLE_RANK.get(role, -1) >= _ROLE_RANK.get(minimum, 999)
```

Every mutation endpoint in `orgs.py` passes `minimum_role` to `_get_org_and_member()`:

| Operation | Minimum Role |
|-----------|-------------|
| Read org / list members | viewer |
| Add / remove / update members | admin |
| Update org name/slug/domain | owner |
| Delete org | owner |
| Domain verify | admin |

Actor cannot grant a role higher than their own. Last owner is protected from demotion/removal.

No separate files — RBAC logic lives in `app/routers/orgs.py` and `app/models/org.py`.

---

## Action 17: Admin Audit Log

**Status:** COMPLETE | **Risk:** P1 (required for SOC2 CC6.1)

### Problem

Admin actions left no durable trace. SOC2 auditors require evidence that access changes are logged and reviewable.

### Schema

```sql
-- Migration 017
CREATE TABLE admin_audit_log (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  actor_user_id UUID NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  target_type VARCHAR(32),
  target_id VARCHAR(64),
  details_json TEXT,
  ip_hash VARCHAR(64),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Audit Event Types (11)

`org.created` · `org.updated` · `org.deleted` · `member.added` · `member.role_changed` · `member.removed` · `api_key.created` · `api_key.revoked` · `api_key.deleted` · `document.deleted` · `link.revoked`

### Key Implementation Rules

- `log_audit_event()` **never raises** — audit failure cannot block the primary operation
- Uses `db.flush()` not `db.commit()` — participates in the caller's transaction
- Emitted automatically at all org/member mutation call sites in `orgs.py`

### API

`GET /api/admin/audit-log?org_id=<id>&limit=50&offset=0`
- With `org_id`: requires admin/owner role; returns org-scoped entries
- Without `org_id`: returns entries where current user is the actor

### Files Changed

- `app/models/audit.py` — `AdminAuditLog` model, `AUDIT_EVENT_TYPES`
- `alembic/versions/017_add_audit_log.py`
- `app/services/audit_service.py` — `log_audit_event()` helper
- `app/routers/admin.py` — read-only API endpoint
- `app/routers/orgs.py` — emit events on all mutations

---

## Action 18: Document Version History

**Status:** COMPLETE | **Risk:** P2 (compliance: "which version did the investor see?")

### Problem

When a document was updated, existing share links pointed to new content with no record of what was seen. Compliance and legal workflows require knowing exactly which version was reviewed.

### Design

Each upload can optionally specify `parent_document_id`. Version chain is purely additive — existing documents and share links are unchanged. Links always point to the specific `document_id` they were created with (no implicit latest-version redirection).

```
Upload v1 → document A (version=1, parent=None)
Upload v2 with parent=A → document B (version=2, parent=A)
Upload v3 with parent=B → document C (version=3, parent=B)

GET /api/documents/A/versions → [A, B, C] ordered by version
GET /api/documents/C/versions → same [A, B, C] (walks to root, then forward)
```

### Schema Change

```sql
-- Migration 018
ALTER TABLE documents ADD COLUMN version INT NOT NULL DEFAULT 1;
ALTER TABLE documents ADD COLUMN parent_document_id UUID
  REFERENCES documents(id) ON DELETE SET NULL;
```

### Security

- `parent_document_id` must be owned by the caller — cross-user version chains blocked
- Invalid parent UUID → 400; nonexistent parent → 404

### Files Changed

- `app/models/document.py` — `version`, `parent_document_id` fields
- `alembic/versions/018_add_version_history.py`
- `app/routers/documents.py` — `parent_document_id` upload param; `GET /{id}/versions` chain walk

---

## Action 19: Real-Time SSE Notifications

**Status:** COMPLETE | **Risk:** P2 (DocSend's "your prospect just opened the doc" is a key differentiator)

### Problem

Users had no real-time feedback when a share link was viewed. They had to manually refresh analytics. DocSend sends a push notification within seconds of a prospect opening a document.

### Architecture

**Channel pattern:** `securedoc:notifications:user:{user_id}` — one Redis pub/sub channel per user.

Publishers (viewer.py, tasks.py) push JSON events to the user's channel. The SSE endpoint subscribes and forwards events to connected browsers.

### Event Format

```
id: <uuid>
event: link.viewed
data: {"document_id":"...","filename":"...","link_id":"...","session_id_prefix":"ab12cd34"}

id: <uuid>
event: document.processed
data: {"document_id":"...","filename":"...","status":"ready","page_count":5}
```

### SSE Endpoint

`GET /api/notifications/stream`
- Authenticated (Bearer or X-API-Key)
- Sends `: ping\n\n` comment every 15 seconds as keepalive
- On client disconnect: unsubscribes from Redis cleanly
- When Redis unavailable: stream sends pings only (no error to client)

### Reliability Rules

- `publish_notification()` **never raises** — Redis failure cannot block API responses
- Max payload: 4096 bytes (oversized payloads return False and are not published)
- SSE generator catches all exceptions internally

### Files Changed

- `app/services/notification_service.py` — `publish_notification()`, `_user_channel()`
- `app/routers/notifications.py` — `GET /api/notifications/stream` SSE endpoint + 15s keepalive
- `app/routers/viewer.py` — `link.viewed` publish after validate
- `app/workers/tasks.py` — `document.processed` publish after pipeline (inside `_fire_document_processed_event()`)

---

## Action 20: Custom Domains

**Status:** COMPLETE | **Risk:** P2 (enterprise differentiator; white-label share links)

### Problem

All share links used `secure.wowmyspace.com/v/{token}`. Enterprise customers need white-label links from their own domain (`docs.acme.com/v/{token}`) to maintain brand consistency and avoid training employees/prospects to trust a third-party URL.

### Solution

1. Add `custom_domain` + verification columns to `organizations`
2. DNS TXT verification endpoint — prevents domain squatting
3. Share URL generation uses org's verified custom domain when available

### Schema Change

```sql
-- Migration 019
ALTER TABLE organizations ADD COLUMN custom_domain VARCHAR(253) NULL UNIQUE;
ALTER TABLE organizations ADD COLUMN custom_domain_verified BOOLEAN NOT NULL DEFAULT false;
ALTER TABLE organizations ADD COLUMN custom_domain_verified_at TIMESTAMPTZ NULL;
```

### Verification Token Algorithm

```python
def _domain_verify_token(org_id: str) -> str:
    h = hmac.new(settings.domain_verify_salt.encode(), org_id.encode(), hashlib.sha256).hexdigest()[:32]
    return f"securedoc-verify={h}"
```

Token is deterministic from `org_id + domain_verify_salt`. No DB state needed for the challenge itself. Changing the custom domain resets `custom_domain_verified = False`.

### API

| Method | Path | Description |
|--------|------|-------------|
| PATCH | /api/orgs/{id} | Set `custom_domain`; resets verified on change |
| GET | /api/orgs/{id}/domain/token | Get TXT record value to add to DNS |
| POST | /api/orgs/{id}/domain/verify | Look up DNS TXT; mark verified on match |

### URL Generation

In `links.py`, `_get_base_url_for_doc(doc, db)` checks whether the document's org has a verified custom domain:

```python
if doc.org_id and org.custom_domain_verified and org.custom_domain:
    return f"https://{org.custom_domain}"
return settings.app_public_base_url
```

Called in `create_link`, `list_links`, and `update_link` — all share URLs respect the org's domain.

### Security

- Domain validated by regex before storage (valid hostname, no path, no `http://`)
- HMAC-based token — not guessable without server salt
- Verified flag resets on domain change — prevents stale verification
- DNS lookup runs in thread pool executor (non-blocking)

### Files Changed

- `alembic/versions/019_add_custom_domains.py`
- `app/models/org.py` — three new columns
- `app/config.py` — `domain_verify_salt`
- `app/routers/orgs.py` — PATCH domain field, `GET /domain/token`, `POST /domain/verify`
- `app/routers/links.py` — `_get_base_url_for_doc()` helper; all share URL generation updated
