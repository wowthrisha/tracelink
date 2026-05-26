"""
Structured JSON log formatter for production observability.

Emits single-line JSON records compatible with log aggregators:
  Grafana Loki, Datadog, CloudWatch Logs, GCP Cloud Logging, Splunk.

Usage:
  From config: set ENABLE_JSON_LOGGING=true
  From code:   call configure_json_logging() once at startup.

Fields always present: ts, level, logger, msg
Optional extras attached by request handlers:
  request_id, session_id, doc_id, link_id, cache_source, latency_ms
"""
import json
import logging

_EXTRA_KEYS = (
    "request_id",
    "session_id",
    "doc_id",
    "link_id",
    "cache_source",
    "latency_ms",
)


class JSONLogFormatter(logging.Formatter):
    """Formats log records as single-line JSON strings."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": record.created,
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in _EXTRA_KEYS:
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_json_logging() -> None:
    """Install JSONLogFormatter on all existing root-logger handlers.

    Call once during application startup when enable_json_logging=True.
    Idempotent — safe to call multiple times.
    """
    fmt = JSONLogFormatter()
    root = logging.getLogger()
    for handler in root.handlers:
        handler.setFormatter(fmt)
    # Also patch uvicorn loggers if they are already set up
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        for handler in logging.getLogger(name).handlers:
            handler.setFormatter(fmt)
