# Action 7: Prometheus Metrics

## Problem

SecureDoc has zero observability into application-level performance and behaviour:
- No way to know how many documents are being viewed right now
- No way to alert on high error rates or slow page-load times
- No SLO measurement possible
- Cannot integrate with Grafana, Datadog, or any monitoring platform

Without metrics, SecureDoc cannot be operated in production with any confidence, and cannot
make an enterprise sale where SLA commitments are required.

## Solution

Add `prometheus-client` as a dependency. Expose a `/metrics` endpoint that returns Prometheus
text format. Add application-level counters and histograms covering the key user flows.

This is a pure-additive change: no existing behaviour changes, no breaking schema migrations,
no middleware stack changes (the endpoint is a plain route on the main FastAPI app).

## Metrics Defined

| Metric | Type | Labels | Meaning |
|--------|------|--------|---------|
| `securedoc_http_requests_total` | Counter | method, path_pattern, status_code | All HTTP requests |
| `securedoc_http_request_duration_seconds` | Histogram | method, path_pattern | Latency distribution |
| `securedoc_viewer_validations_total` | Counter | result (success/denied/expired/...) | Viewer gate outcomes |
| `securedoc_page_requests_total` | Counter | cache_hit (true/false) | Page cache hit rate |
| `securedoc_downloads_total` | Counter | result (success/denied/too_large) | Download outcomes |
| `securedoc_document_uploads_total` | Counter | status (queued/rejected) | Upload funnel |
| `securedoc_active_sessions` | Gauge | — | Current active viewer sessions (from cache size) |

## Architecture

### `backend/app/middleware/metrics.py` (new)
- `PrometheusMiddleware` — ASGI middleware that wraps each request, records
  method/path/status/latency. Path is normalized to a pattern (`/api/viewer/page/{token}/{page}`
  not the actual token/page values) to avoid cardinality explosion.
- Uses a module-level registry so metrics persist across requests.

### `backend/app/metrics.py` (new)
- All metric objects as module-level singletons (Counter, Histogram, Gauge).
- `normalize_path(path: str) -> str` — replaces UUIDs and tokens with `{id}` / `{token}`.

### `backend/app/main.py`
- Add `GET /metrics` route that calls `prometheus_client.generate_latest()`.
- Add `PrometheusMiddleware` to middleware stack (outermost layer, after CORS).
- Instrument key callsites via inline `metric.inc()` / `metric.observe()` calls.

### `backend/requirements.txt`
- Add `prometheus-client>=0.21.0`

## Security
- `/metrics` is NOT authenticated — it is on the same port as the app.
- Prometheus scrape should be restricted at the network level (firewall / Cloudflare Access).
- No user data, emails, IPs, or session IDs in metric labels.
- No label value with unbounded cardinality (tokens/UUIDs are normalized to patterns).

## Rollback
- Remove `GET /metrics` route, remove `PrometheusMiddleware`, remove `app/metrics.py`.
- No schema changes to reverse.

## Test Plan
- `/metrics` returns 200 with `text/plain` content-type.
- Response body contains expected metric names.
- Path normalization unit test.
- Counter increments after viewer validate / page load.
