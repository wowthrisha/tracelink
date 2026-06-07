"""
OpenTelemetry distributed tracing setup.

Tracing is disabled by default (no-op tracer when OTEL_EXPORTER_OTLP_ENDPOINT
is not set). Set the endpoint in .env to enable:

  OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4318
  OTEL_SERVICE_NAME=securedoc   (optional, default: securedoc)

Compatible with any OTLP-capable backend: Grafana Tempo, Jaeger, Honeycomb,
Datadog agent, AWS X-Ray ADOT collector.

Security: no PII (emails, IPs, session IDs) is added to span attributes.
The auto-instrumentation for FastAPI and SQLAlchemy does not capture query
parameters or request bodies — only method, path pattern, and status codes.
"""
import logging

_log = logging.getLogger("securedoc.telemetry")


def setup_tracing(otlp_endpoint: str, service_name: str = "securedoc") -> None:
    """Configure OpenTelemetry tracing with OTLP HTTP export.

    Idempotent — safe to call multiple times (only the first call takes effect
    because the global tracer provider is set once).
    """
    if not otlp_endpoint:
        _log.debug("OTEL: tracing disabled (OTEL_EXPORTER_OTLP_ENDPOINT not set)")
        return

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

    # No-op if already configured (lifespan may be called in tests multiple times)
    if isinstance(trace.get_tracer_provider().__class__.__name__, str) and \
            trace.get_tracer_provider().__class__.__name__ == "TracerProvider":
        _log.debug("OTEL: tracer provider already configured, skipping")
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint.rstrip('/')}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    _log.info("OTEL: tracing enabled, exporting to %s (service=%s)", otlp_endpoint, service_name)


def instrument_app(app) -> None:
    """Attach FastAPI and SQLAlchemy auto-instrumentation to the app.

    Called after setup_tracing(). Safe to call when tracing is disabled —
    the no-op tracer produces zero overhead.
    """
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        _log.debug("OTEL: FastAPI instrumented")
    except Exception as e:
        _log.warning("OTEL: FastAPI instrumentation failed: %s", e)

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        SQLAlchemyInstrumentor().instrument()
        _log.debug("OTEL: SQLAlchemy instrumented")
    except Exception as e:
        _log.warning("OTEL: SQLAlchemy instrumentation failed: %s", e)
