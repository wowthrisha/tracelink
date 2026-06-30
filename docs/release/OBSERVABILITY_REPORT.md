# SecureDoc Observability Report

**Date:** 2026-07-01  
**Version:** 8.1.0  
**Sprint:** 6.5 Enterprise Readiness

---

## Executive Summary

SecureDoc V8.1.0 has full production-grade observability across all three pillars: logs, metrics, and traces. All observability components are implemented and verified.

| Pillar | Status | Implementation |
|--------|--------|---------------|
| Structured Logging | ✅ Complete | JSON via JSONLogFormatter |
| Prometheus Metrics | ✅ Complete | 20+ metrics across all subsystems |
| Distributed Tracing | ✅ Complete | OpenTelemetry (OTLP export) |
| Health Endpoints | ✅ Complete | /health, /live, /ready |
| Correlation IDs | ✅ Complete | X-Request-ID + X-Correlation-ID |

---

## Structured Logging

### Implementation

- **Formatter:** `JSONLogFormatter` in `middleware/json_logging.py`
- **Activation:** `ENABLE_JSON_LOGGING=true` (default)
- **Output format:** Single-line JSON, one record per line

### Standard Fields

Every log record includes:

| Field | Type | Example |
|-------|------|---------|
| `ts` | float | `1751366400.123` |
| `level` | string | `INFO` |
| `logger` | string | `securedoc.access` |
| `msg` | string | `access method=GET path=/api/...` |

### HTTP Request Fields (access log)

| Field | Example | Notes |
|-------|---------|-------|
| `method` | `GET` | |
| `path` | `/api/viewer/page/[token]/1` | Tokens redacted |
| `status_code` | `200` | |
| `duration_ms` | `12.4` | |
| `ip` | `203.0.113.1` | Real client IP after proxy header resolution |
| `request_id` | `550e8400-...` | UUID4 or caller-supplied |
| `correlation_id` | `550e8400-...` | X-Correlation-ID or request_id |
| `event` | `http_request` | |

### Correlation Fields (set per-handler)

| Field | Example | Notes |
|-------|---------|-------|
| `user_id` | `usr_abc123` | From JWT/API key |
| `org_id` | `org_xyz789` | From org context |
| `doc_id` | `uuid` | When operating on a document |
| `link_id` | `uuid` | When operating on a share link |
| `session_id_prefix` | `a1b2c3d4` | First 8 chars only — never full ID |
| `error_category` | `auth_error` | auth_error\|validation_error\|not_found\|server_error |
| `worker_task` | `process_document` | In Celery task context |

### Log Aggregator Compatibility

Compatible with: **Grafana Loki**, **Datadog**, **CloudWatch**, **GCP Cloud Logging**, **Splunk**

Loki query examples:
```logql
# All errors
{app="securedoc"} | json | level = "ERROR"

# Slow requests (>500ms)
{app="securedoc"} | json | event = "http_request" | duration_ms > 500

# Document processing failures
{app="securedoc"} | json | worker_task = "process_document" | level = "ERROR"
```

---

## Prometheus Metrics

Endpoint: `GET /metrics` (protected by `METRICS_TOKEN` and/or `METRICS_ALLOWED_IPS`)

### HTTP Layer

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `securedoc_http_requests_total` | Counter | method, path_pattern, status_code | Total HTTP requests |
| `securedoc_http_request_duration_seconds` | Histogram | method, path_pattern | Request latency |

### Viewer / DRM

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `securedoc_viewer_validations_total` | Counter | result | Link validation outcomes |
| `securedoc_page_requests_total` | Counter | cache_hit | Page image requests |
| `securedoc_viewer_sessions_total` | Counter | outcome | Sessions created/resumed/rejected |
| `securedoc_active_sessions` | Gauge | — | Current active sessions |

### Document Operations

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `securedoc_document_uploads_total` | Counter | result | Upload outcomes |
| `securedoc_upload_duration_seconds` | Histogram | — | Time from receipt to S3 completion |
| `securedoc_processing_duration_seconds` | Histogram | stage | Processing time by stage |
| `securedoc_downloads_total` | Counter | result | Download outcomes |

### Share Links

| Metric | Type | Description |
|--------|------|-------------|
| `securedoc_share_links_created_total` | Counter | Share links created |
| `securedoc_share_links_revoked_total` | Counter | Share links revoked |

### Annotations

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `securedoc_annotations_total` | Counter | annotation_type, action | Annotation create/delete/resolve |

### Webhooks

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `securedoc_webhook_deliveries_total` | Counter | outcome | Delivery success/failure |
| `securedoc_webhook_retries_total` | Counter | — | Delivery retry attempts |

### Infrastructure

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `securedoc_db_query_duration_seconds` | Histogram | — | Database query latency |
| `securedoc_cache_hits_total` | Counter | layer | Cache hits (redis\|memory) |
| `securedoc_cache_misses_total` | Counter | layer | Cache misses (redis\|memory) |

### Recommended Grafana Alerts

```promql
# Error rate > 5%
sum(rate(securedoc_http_requests_total{status_code=~"5.."}[5m])) /
sum(rate(securedoc_http_requests_total[5m])) > 0.05

# p99 latency > 2s
histogram_quantile(0.99, rate(securedoc_http_request_duration_seconds_bucket[5m])) > 2

# Webhook failure rate > 20%
rate(securedoc_webhook_deliveries_total{outcome="failure"}[1h]) /
rate(securedoc_webhook_deliveries_total[1h]) > 0.2

# Cache hit rate < 70%
rate(securedoc_cache_hits_total{layer="redis"}[5m]) /
(rate(securedoc_cache_hits_total{layer="redis"}[5m]) + rate(securedoc_cache_misses_total{layer="redis"}[5m])) < 0.7
```

---

## Distributed Tracing (OpenTelemetry)

- **SDK:** `opentelemetry-sdk` with FastAPI + SQLAlchemy instrumentation
- **Export:** OTLP HTTP (`OTEL_EXPORTER_OTLP_ENDPOINT`)
- **Compatible backends:** Grafana Tempo, Jaeger, Honeycomb, Datadog APM
- **When disabled:** No-op tracer (zero overhead) — default for development

Configuration:
```
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4318
OTEL_SERVICE_NAME=securedoc
```

---

## Health Endpoints

| Endpoint | Purpose | Checks |
|----------|---------|--------|
| `GET /live` | Kubernetes liveness probe | None (pure alive check) |
| `GET /ready` | Kubernetes readiness probe | DB `SELECT 1`, Redis `PING` |
| `GET /health` | Detailed health dashboard | DB, Redis, worker queue |

`/ready` returns 503 on failure with detail of which component failed.

---

## Correlation ID Flow

```
Client → X-Correlation-ID: abc123
         ↓
RequestIDMiddleware: request.state.correlation_id = "abc123"
         ↓
All log records in this request: correlation_id="abc123"
         ↓
Response ← X-Request-ID: uuid4
         ← X-Correlation-ID: abc123
```

When `X-Correlation-ID` is absent, it defaults to `X-Request-ID`, ensuring all requests have a trace anchor.
