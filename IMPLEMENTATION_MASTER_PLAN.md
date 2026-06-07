# SecureDoc Enterprise Transformation — Implementation Master Plan
**Date:** 2026-06-07  
**Status:** IN PROGRESS  
**Target Score:** 9.5/10  
**Baseline Score:** 5.2/10

---

## Programme Overview

This plan governs the complete transformation of SecureDoc from a capable prototype (5.2/10) to an enterprise-grade document security platform (9.5/10) competitive with DocSend, Box Enterprise, and Adobe Document Cloud.

### Governance
- Each action has a design document (`ACTION_<N>_DESIGN.md`) authored before coding begins
- Progress tracked in `IMPLEMENTATION_PROGRESS.md`  
- All architecture decisions recorded in `ARCHITECTURE_DECISIONS.md`
- All risks tracked in `RISK_REGISTER.md`
- All changes logged in `CHANGELOG_ENTERPRISE.md`

---

## Dependency Graph

```
Action 1 (HSTS)                      → no deps
Action 2 (max_views race)            → no deps
Action 3 (forensic identity stamp)  → no deps
Action 4 (session cache)             → no deps
Action 5 (JSON logging)              → no deps

Action 6 (streaming download)        → no deps
Action 7 (Prometheus)                → Action 5 (logging aligned)
Action 8 (OpenTelemetry)             → Action 7 (shared export pipeline)
Action 9 (CDN)                       → Actions 2,3 complete (security must be solid first)

Action 10 (PPTX)                     → no deps
Action 11 (XLSX)                     → Action 10 (shared LO pipeline)
Action 12 (time-on-page)             → no deps (additive to analytics)
Action 13 (webhooks)                 → Action 12 (event model expanded)
Action 14 (public API)               → Actions 12,13 (full feature surface)

Action 15 (SSO)                      → no deps
Action 16 (RBAC)                     → Action 15 (user identity model)
Action 17 (admin audit logs)         → Action 16 (org-scoped queries)
Action 18 (version history)          → no deps (document model extension)
Action 19 (real-time notifications)  → Action 13 (event pipeline)
Action 20 (custom domains)           → Action 15 (workspace model)

Phase 5 (SOC2)                       → All Phase 1-4 complete
```

---

## Phase 1 — Security Critical

### Action 1: Enable HSTS by Default
**Risk:** P0 — SSL strip attacks in all current deployments  
**Effort:** 30 minutes  
**Files:** `config.py`, `middleware/security_headers.py`, `tests/integration/test_phase_enterprise1.py`

| | Detail |
|-|--------|
| Migration | Config-only change; no DB migration |
| Rollback | Set `HSTS_MAX_AGE=0` in env |
| Test | Header present on HTTPS, absent on HTTP, includes preload directive |
| Breaking | No backward-compat break; purely additive |

**What changes:**
1. `config.py`: `hsts_max_age: int = 31536000` (default 1 year, was 0)
2. `security_headers.py`: Add `; preload` to HSTS header value
3. `main.py`: Production startup check now validates HSTS is enabled

---

### Action 2: Fix max_views Race Condition (Atomic Check-and-Increment)
**Risk:** P0 — concurrent validation allows view_count to exceed max_views  
**Effort:** 3 hours  
**Files:** `services/link_service.py`, `routers/viewer.py`, tests

| | Detail |
|-|--------|
| Migration | No schema change; query logic only |
| Rollback | Revert link_service.py changes |
| Test | Concurrent validate requests, race scenarios, edge cases (null max_views) |
| Breaking | None; same API surface |

**What changes:**
1. `link_service.py`: Replace 2-query pattern with single atomic `UPDATE ... RETURNING`
2. Remove separate `increment_view_count()` call from `viewer.py:validate_link`
3. The atomic query: `UPDATE share_links SET view_count=view_count+1 WHERE id=:id AND (max_views IS NULL OR view_count < max_views) RETURNING view_count`
4. If 0 rows → max_views exceeded → HTTP 410

---

### Action 3: Viewer Identity Forensic Stamp
**Risk:** P0 — direct R2 storage access bypasses viewer identity tracking  
**Effort:** 4 hours  
**Files:** `services/watermark.py`, `routers/viewer.py`, tests

| | Detail |
|-|--------|
| Migration | No schema or storage change; applied at serve time |
| Rollback | Remove viewer_forensic_stamp call from viewer.py |
| Test | Stamp contains session hash, pixel opacity ≤ 2%, preserved through format conv |
| Breaking | None |

**What changes:**
1. `watermark.py`: New `apply_viewer_forensic_stamp(bytes, session_id, page_number)` method
   - 1.5% opacity corner stamp: `VS:{sha256(session_id)[:8]}:{page:04d}`
   - Applied AFTER visible watermark, in same executor call
2. `viewer.py:get_page()`: Chain the viewer stamp after visible watermark

---

### Action 4: Session Validation Redis Cache (5-second TTL)
**Risk:** P1 — DB read per page request; bottleneck at moderate concurrent viewers  
**Effort:** 4 hours  
**Files:** `services/viewer_cache.py`, `services/policy.py`, tests

| | Detail |
|-|--------|
| Migration | No schema change; additive caching layer |
| Rollback | Remove session_cache from viewer_cache.py; policy.py reverts to DB-only |
| Test | Cache hit, miss, invalidation, revocation propagation, expiry |
| Breaking | None |

**What changes:**
1. `viewer_cache.py`: Add `session_cache: _TTLCache` (TTL=5s, max=50000 entries)
2. `policy.py:is_active_session()`: Check session_cache first; populate on miss
3. `policy.py:upsert_session()`: Update cache after DB write
4. `viewer_cache.py:invalidate_link()`: Clear all session cache entries for that link

---

### Action 5: Structured JSON Logging — Enable by Default
**Risk:** P1 — no structured observability; incident response is manual grep  
**Effort:** 3 hours  
**Files:** `config.py`, `middleware/json_logging.py`, `middleware/request_id.py`, tests

| | Detail |
|-|--------|
| Migration | No schema change; logging format change only |
| Rollback | Set `ENABLE_JSON_LOGGING=false` in env |
| Test | JSON-parseable output, required fields present, sensitive field redaction |
| Breaking | Log consumers expecting plaintext will need updates (Docker log drivers) |

**What changes:**
1. `config.py`: `enable_json_logging: bool = True` (default, was False)
2. `json_logging.py`: Add fields: `user_id`, `doc_id`, `link_id`, `event`, `status_code`, `path`, `method`, `duration_ms`, `cache_hit`
3. `request_id.py`: Emit structured access log per request as JSON
4. Celery worker: Configure JSON logging in celery_app.py startup

---

## Phase 2 — Scalability

### Action 6: Streaming Downloads
**Risk:** P1 — 100-page PDF download uses ~500 MB API server RAM  
**Effort:** 1 day  
**Files:** `routers/viewer.py` (download endpoint), tests

| | Detail |
|-|--------|
| Migration | No schema change |
| Rollback | Revert download endpoint; keep max_download_pages_pdf constraint |
| Test | 10/50/100 page downloads, memory profile, partial failure handling |
| Breaking | None; same API surface |

**What changes:**
1. Replace in-memory PDF assembly with async generator
2. Use `pypdf.PdfWriter` with streaming-compatible API
3. `StreamingResponse` with async generator yields PDF bytes page-by-page
4. Raise `max_download_pages_pdf` to 500

---

### Action 7: Prometheus Metrics Endpoint
**Risk:** P1 — no metrics → no on-call, no auto-scaling, no SLO  
**Effort:** 1 day  
**Files:** `main.py`, `requirements.txt`, `docker-compose.yml`

| | Detail |
|-|--------|
| Migration | Add `prometheus-client` to requirements |
| Rollback | Remove metrics endpoint; remove library |
| Test | /metrics returns valid Prometheus format, counters increment correctly |
| Breaking | None |

**What changes:**
1. Add `prometheus-client==0.21.0` to requirements.txt
2. Add `prometheus-fastapi-instrumentator==7.0.0`
3. Mount `/metrics` endpoint (internal-only; not routed through Cloudflare)
4. Custom metrics: page requests, cache hit rates, active sessions, queue depth
5. Docker Compose: Add prometheus + grafana services

---

### Action 8: OpenTelemetry Distributed Tracing
**Risk:** P2 — no span visibility for latency incidents  
**Effort:** 1 day  
**Files:** `main.py`, `workers/tasks.py`, `requirements.txt`

| | Detail |
|-|--------|
| Migration | Add OTel packages to requirements |
| Rollback | Remove instrumentation calls; no data loss |
| Test | Spans created per request, trace propagation via X-Request-ID |
| Breaking | None |

**What changes:**
1. Add `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-instrumentation-sqlalchemy`, `opentelemetry-instrumentation-celery`
2. OTLP exporter to Tempo/Jaeger
3. Docker Compose: Add Grafana Tempo service
4. Propagate `X-Request-ID` as trace correlation

---

### Action 9: CDN for Thumbnails (Hybrid Architecture)
**Risk:** P2 — R2 round-trip on every thumb; high egress cost at scale  
**Effort:** 3 days  
**Files:** `routers/viewer.py` (thumb endpoint), `services/storage.py`, `config.py`

| | Detail |
|-|--------|
| Migration | R2 bucket policy change; no schema change |
| Rollback | Revert thumb endpoint to proxy mode |
| Test | Signed URL generation, expiry enforcement, CDN cache behavior |
| Breaking | None |

**What changes:**
1. Full-page images: keep API-proxy (security requirement for visible watermark)
2. Thumbnails: generate Cloudflare R2 signed URL (60s expiry) → 302 redirect
3. Browser caches thumb at CDN edge; no egress from R2 to API server
4. `config.py`: Add `cdn_thumb_signed_url_ttl_sec: int = 60`, `cdn_enabled: bool = False`

---

## Phase 3 — Product Completeness

### Action 10: PPTX Format Support
**Risk:** P1 — most common enterprise presentation format unsupported  
**Effort:** 2 days  
**Files:** `services/text_processor.py` (detection), `services/adapters/`, `workers/pipeline/`, migration

| | Detail |
|-|--------|
| Migration | Extend `file_type` VARCHAR; add PPTX to enum |
| Rollback | Remove pptx from detect_file_type(); documents already processed remain valid |
| Test | Upload, process, serve for PPTX files; LibreOffice conversion |
| Breaking | None |

---

### Action 11: XLSX Format Support
**Risk:** P2 — financial models and data files commonly requested  
**Effort:** 2 days  
**Files:** Same as Action 10 + `openpyxl` for better rendering  

| | Detail |
|-|--------|
| Depends on | Action 10 (shared pipeline patterns) |
| Migration | Add xlsx to file_type enum |
| Breaking | None |

---

### Action 12: Time-on-Page Analytics
**Risk:** P1 — primary DocSend differentiator; required for sales enablement use case  
**Effort:** 2 days  
**Files:** `models/event.py`, `routers/analytics.py`, `frontend/src/app.jsx`, migration

| | Detail |
|-|--------|
| Migration | Add `time_spent_ms INTEGER` to `access_events` |
| Rollback | Ignore time_spent_ms; column can remain null |
| Test | Time tracked, aggregated per page, heatmap rendered |
| Breaking | None |

---

### Action 13: Webhooks for View Events
**Risk:** P2 — no push integration; enterprise teams need CRM automation  
**Effort:** 2 days  
**Files:** New `models/webhook.py`, `routers/webhooks.py`, `workers/tasks.py`

| | Detail |
|-|--------|
| Migration | New `webhook_endpoints` table |
| Rollback | Remove table; remove router |
| Test | Webhook delivery, HMAC signature, retry on failure |
| Breaking | None |

---

### Action 14: Public API + API Keys
**Risk:** P2 — no programmatic access; blocks enterprise integration  
**Effort:** 3 days  
**Files:** New `models/api_key.py`, `middleware/api_key_auth.py`, versioned routers

| | Detail |
|-|--------|
| Migration | New `api_keys` table |
| Rollback | Remove table; remove middleware |
| Test | Key generation, auth, rate limiting per key, key revocation |
| Breaking | None; additive |

---

## Phase 4 — Enterprise

### Action 15: SSO / SAML via Supabase SAML
**Risk:** P1 — required for Fortune 500 procurement  
**Effort:** 5 days  
**Files:** `auth.py`, `models/` (Organization), `routers/` (SSO routes)

| | Detail |
|-|--------|
| Migration | New `organizations`, `org_memberships` tables |
| Rollback | Keep existing Supabase JWT auth; SSO is additive |
| Test | SSO login flow, SCIM provisioning, team membership |
| Breaking | None; existing auth path unchanged |

---

### Action 16: Role-Based Access Control
**Risk:** P1 — single-owner model blocks team use  
**Effort:** 5 days  
**Depends on** | Action 15 (org model)

| | Detail |
|-|--------|
| Migration | Add `role` column to `org_memberships`; update document ownership model |
| Rollback | Revert to user_id-based ownership |
| Test | Role enforcement for all endpoints, privilege escalation prevention |
| Breaking | Potential: document ownership moves to org; migration needed |

---

### Action 17: Admin Audit Log UI
**Risk:** P1 — required for SOC2 CC6.1 evidence  
**Effort:** 3 days  
**Depends on** | Action 16 (org-scoped queries)

| | Detail |
|-|--------|
| Migration | Add audit event types to event_type_enum |
| Rollback | Remove audit log UI tab; keep raw events in DB |
| Test | Audit events captured, filtered, exported |
| Breaking | None |

---

### Action 18: Document Version History
**Risk:** P2 — required for compliance workflows  
**Effort:** 3 days  

| | Detail |
|-|--------|
| Migration | Add `version` INT, `parent_id` FK to documents |
| Rollback | Ignore version chain; existing links still work |
| Test | Version upload, link resolution to latest version |
| Breaking | None |

---

### Action 19: Real-Time View Notifications (SSE)
**Risk:** P2 — competitive feature (DocSend sends push on open)  
**Effort:** 3 days  
**Depends on** | Action 13 (Redis pub/sub event pipeline)

| | Detail |
|-|--------|
| Migration | No schema change |
| Rollback | Remove SSE endpoint; no data loss |
| Test | SSE stream opens, event received within 1s of view |
| Breaking | None |

---

### Action 20: Custom Domain per Workspace
**Risk:** P3 — white-label requirement for enterprise tier  
**Effort:** 3 days  
**Depends on** | Action 15 (workspace model)

| | Detail |
|-|--------|
| Migration | Add `custom_domain` to organizations |
| Rollback | Revert to default domain |
| Test | Custom domain DNS verification, SSL cert provisioning, URL generation |
| Breaking | None |

---

## Phase 5 — SOC2 Readiness

### Additional Controls (beyond Top 20)

These are required for SOC2 Type II but not captured in the Top 20:

| Control ID | Requirement | Implementation |
|-----------|-------------|----------------|
| CC6.1 | Logical access — audit trail | Actions 16, 17 |
| CC6.2 | Authentication strength | Action 15 (SSO + MFA) |
| CC6.3 | Access removal | SCIM + automated deprovisioning |
| CC6.7 | Transmission encryption | Action 1 (HSTS) |
| CC7.1 | Change detection | Add file integrity monitoring |
| CC7.2 | Monitoring | Actions 7, 8 (metrics + tracing) |
| CC7.3 | Security incidents | Add incident response runbook |
| CC8.1 | Change management | Add GitHub Actions CI/CD |
| CC9.2 | Vendor risk | Document dependency security posture |
| A1.1 | Availability | Add uptime monitoring + PagerDuty |
| A1.2 | Capacity | Add auto-scaling config |
| A1.3 | Recovery | Add DB backup + DR runbook |
| PI1.1 | Privacy | Add data retention policy + purge jobs |

---

## Testing Strategy

### Per-Action Requirements

Every action must include:

1. **Unit tests** — isolated function/class tests
2. **Integration tests** — database + HTTP layer tests
3. **Failure tests** — error conditions, timeouts, invalid input
4. **Security tests** — abuse cases, injection, privilege escalation
5. **Regression tests** — existing test suite must remain green

### Target Coverage
- Modified files: ≥ 90% line coverage
- New files: 100% line coverage on all happy paths
- All security-critical paths: explicit test for each threat model entry

### Test File Naming
- Unit: `backend/tests/unit/test_<module>.py`
- Integration: `backend/tests/integration/test_enterprise_phase<N>.py`
- Action-specific: `backend/tests/integration/test_action_<N>_<name>.py`

---

## Migration Strategy

### Database Migrations
- All schema changes use Alembic migrations in `backend/alembic/versions/`
- Next migration number: `013_*`
- Each migration must be idempotent and include both `upgrade()` and `downgrade()`
- Migrations must be tested against SQLite (tests) and PostgreSQL (production)

### Deployment
- Zero-downtime: migrations run in `migrate` service (Docker Compose) before API starts
- pg_advisory_lock(7325613) prevents concurrent migration runs
- Feature flags in config for gradual rollout where applicable

---

## Rollback Strategy

Each action's rollback is documented in its design doc. Global rollback:
1. Any config change: revert via environment variable (no redeploy needed)
2. Any code change: `git revert` + redeploy
3. Any migration: `alembic downgrade -1` (each migration has `downgrade()`)

---

## Risk Register

See `RISK_REGISTER.md` for detailed per-risk entries.

Top risks:
1. **HSTS misconfiguration** — enable HSTS before confirming HTTPS → browser locks users out
2. **Session cache invalidation gap** — revoked link sessions not cleared within 5s → 5-second window
3. **PPTX rendering quality** — LibreOffice output varies; embedded fonts may not render
4. **SSO complexity** — SAML implementation bugs can lock all users out
5. **CDN signed URL race** — URL expires between generation and first byte → 403

---

## Performance Budget

| Phase | Expected Latency Change | Expected Memory Change |
|-------|------------------------|----------------------|
| Phase 1 | p99 page serve: -5ms (session cache hit) | +50 MB (session cache) |
| Phase 2 | p99 download: -80% (streaming) | -500 MB peak (streaming download) |
| Phase 3 | PPTX upload: +2s processing | no change |
| Phase 4 | SSO login: +200ms (SAML roundtrip) | no change |

---

## Deliverables Checklist

- [x] `SECUREDOC_CURRENT_STATE_REPORT.md` — baseline inventory
- [x] `TOP_20_ACTIONS_TO_REACH_ENTERPRISE_GRADE.md` — ranked action list
- [x] `IMPLEMENTATION_MASTER_PLAN.md` — this document
- [ ] `IMPLEMENTATION_PROGRESS.md` — per-action progress (in progress)
- [ ] `ARCHITECTURE_DECISIONS.md` — ADRs for key choices
- [ ] `RISK_REGISTER.md` — risk log
- [ ] `CHANGELOG_ENTERPRISE.md` — change log
- [ ] `ACTION_1_DESIGN.md` through `ACTION_20_DESIGN.md`
- [ ] `ENTERPRISE_READINESS_AUDIT.md` — final validation

---

## Implementation Order (Absolute)

```
PHASE 1 (NOW):
  1. HSTS                         [30 min]
  2. max_views race fix           [3 hrs]
  3. Forensic identity stamp      [4 hrs]
  4. Session validation cache     [4 hrs]
  5. JSON logging default on      [3 hrs]

PHASE 2 (NEXT):
  6. Streaming downloads          [1 day]
  7. Prometheus metrics           [1 day]
  8. OpenTelemetry tracing        [1 day]
  9. CDN for thumbnails           [3 days]

PHASE 3 (THEN):
  10. PPTX support                [2 days]
  11. XLSX support                [2 days]
  12. Time-on-page analytics      [2 days]
  13. Webhooks                    [2 days]
  14. Public API                  [3 days]

PHASE 4 (THEN):
  15. SSO / SAML                  [5 days]
  16. RBAC                        [5 days]
  17. Admin audit logs            [3 days]
  18. Version history             [3 days]
  19. Real-time notifications     [3 days]
  20. Custom domains              [3 days]

PHASE 5 (THEN):
  SOC2 controls                   [ongoing]
```
