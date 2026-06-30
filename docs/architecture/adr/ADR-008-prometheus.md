# ADR-008: Prometheus Native Client

**Status:** Accepted
**Date:** 2026-06-07

## Context

`prometheus-fastapi-instrumentator` provides automatic route metrics but with limited customization over metric names, labels, and bucketing.

## Decision

Use `prometheus-client` directly with custom metric definitions:

- `securedoc_requests_total{method, route, status}` — Counter
- `securedoc_request_duration_seconds{method, route}` — Histogram
- `securedoc_page_cache_hits_total{level}` — Counter (l1/l2/miss)
- `securedoc_active_sessions_gauge` — Gauge (updated by periodic task)
- `securedoc_documents_by_status{status}` — Gauge

Exposed at `/metrics` (internal only; not proxied through Cloudflare).

## Consequences

- Full control over metric definitions and cardinality
- Manual instrumentation requires more code than auto-instrumentation — centralized in `app/middleware/metrics.py`
