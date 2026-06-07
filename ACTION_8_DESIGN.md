# Action 8: OpenTelemetry Distributed Tracing

## Problem

SecureDoc has no distributed tracing. When a document takes 8 seconds to load:
- Is it the DB query? The R2 fetch? The watermark render? The network?
- Without traces, every performance complaint requires a prod debug session.

Enterprise customers expect APM integration (Datadog, Honeycomb, Tempo).

## Solution

Add OpenTelemetry SDK with auto-instrumentation for FastAPI and SQLAlchemy.
Export traces via OTLP (gRPC or HTTP) to any OpenTelemetry-compatible backend
(Grafana Tempo, Jaeger, Honeycomb, Datadog, etc.).

The key design decisions:
1. **Auto-instrumentation**: Use `opentelemetry-instrumentation-fastapi` and
   `opentelemetry-instrumentation-sqlalchemy` — zero manual span creation needed
   for the common case.
2. **OTLP exporter**: Configurable endpoint via `OTEL_EXPORTER_OTLP_ENDPOINT`.
   Default: disabled (no exporter configured) — tracing only activates when
   `OTEL_EXPORTER_OTLP_ENDPOINT` is set in .env.
3. **No-op when disabled**: When OTLP endpoint is not configured, OpenTelemetry
   uses a no-op tracer that has zero overhead.
4. **Service name**: `securedoc` — settable via `OTEL_SERVICE_NAME`.

## Architecture

### `backend/app/telemetry.py` (new)
- `setup_tracing()` — called at startup if `OTEL_EXPORTER_OTLP_ENDPOINT` is set.
- Configures OTLP exporter, batch span processor, `TracerProvider`.
- Registers the global tracer provider.

### `backend/app/config.py`
- `otel_exporter_otlp_endpoint: str = ""` — empty = tracing disabled.
- `otel_service_name: str = "securedoc"`.

### `backend/app/main.py`
- Call `setup_tracing()` in `lifespan()` startup.
- Instrument FastAPI via `FastAPIInstrumentor`.
- Instrument SQLAlchemy via `SQLAlchemyInstrumentor`.

### `backend/requirements.txt`
- `opentelemetry-sdk>=1.28.0`
- `opentelemetry-instrumentation-fastapi>=0.49b0`
- `opentelemetry-instrumentation-sqlalchemy>=0.49b0`
- `opentelemetry-exporter-otlp-proto-http>=1.28.0`

## Security
- No PII in span attributes (no emails, IPs, session IDs).
- Trace data goes to internal observability backend (not external SaaS by default).
- OTLP endpoint is operator-configured — not hardcoded.

## Rollback
- Remove `setup_tracing()` call from lifespan.
- Remove `telemetry.py`.
- Remove otel packages from requirements.txt.
- No schema changes.

## Test Plan
- `settings.otel_exporter_otlp_endpoint = ""` → `setup_tracing()` is a no-op.
- `setup_tracing()` with a mock exporter → tracer provider is registered.
- FastAPI routes produce spans when tracing is active.
