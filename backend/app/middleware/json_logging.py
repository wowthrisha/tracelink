"""
Structured JSON log formatter for production observability.

Emits single-line JSON records compatible with log aggregators:
  Grafana Loki, Datadog, CloudWatch Logs, GCP Cloud Logging, Splunk.

Usage:
  From config: ENABLE_JSON_LOGGING=true (default)
  From code:   call configure_json_logging() once at startup.

Standard fields always present: ts, level, logger, msg
HTTP request fields (when present): method, path, status, duration_ms, request_id
Correlation fields (when present):  user_id, doc_id, link_id, session_id_prefix
Cache fields (when present):        cache_source, cache_hit
Event fields (when present):        event, page_number

Security note: raw session_id (32 chars) is NEVER logged; only session_id[:8]
is captured via the session_id_prefix field.
"""
import json
import logging
from typing import Any

# Fields that route handlers may attach to a LogRecord via extra={}.
# Extend this list when adding new structured log fields.
_EXTRA_KEYS = (
    "request_id",
    "session_id_prefix",   # first 8 chars of session_id only — never full ID
    "doc_id",
    "link_id",
    "user_id",
    "cache_source",
    "cache_hit",
    "latency_ms",
    "duration_ms",
    "status_code",
    "method",
    "path",
    "page_number",
    "event",
    "worker_task",
)


class JSONLogFormatter(logging.Formatter):
    """Formats log records as single-line JSON strings.

    Fields always emitted: ts (float epoch), level, logger, msg.
    Optional extras are emitted when present on the LogRecord (set via
    logging.info(..., extra={...}) or logger.info(..., extra={...})).
    Exception tracebacks are included as the 'exc' field when present.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
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
