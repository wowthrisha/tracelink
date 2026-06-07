# Action 5 Design: Structured JSON Logging — Enable by Default

**Status:** APPROVED  
**Date:** 2026-06-07  
**Risk Level:** Low (logging format change; no functional impact)

---

## Current Architecture

`config.py:84`: `enable_json_logging: bool = False`

`main.py:75–78`: If `enable_json_logging`, call `configure_json_logging()` which installs `JSONLogFormatter` on root logger.

`json_logging.py`: Formatter with fields: `ts`, `level`, `logger`, `msg` + optional extras.

`request_id.py`: Access log line is a plain-text string via `logger.info(...)`.

---

## Problem

Default `False` means every deployment without explicit opt-in gets plaintext logs. This makes:
- Log aggregation (Loki, Datadog, CloudWatch) impossible without log parsers
- Alerting on error rates/routes requires regex rules instead of field filters
- Incident investigations require `grep` on raw log files
- No correlation between log lines and trace IDs

---

## Alternative Designs

**Option A: Keep False default, add documentation**  
- Con: Problem remains; operators who don't read docs stay with plaintext

**Option B: Default True, opt-out via env var (chosen)**  
- Pro: Secure/observable by default; local dev can set `ENABLE_JSON_LOGGING=false`
- Accepted tradeoff: local terminal logs are harder to read without `jq`

---

## Chosen Design

1. Change `config.py` default to `True`
2. Enhance `json_logging.py` formatter with additional fields:
   - `status_code`, `method`, `path`, `duration_ms` for HTTP requests
   - `event` for named events (page_served, cache_hit, validate_ok)
   - `user_id`, `doc_id`, `link_id` for correlation
3. Update `request_id.py` to emit structured JSON access log per request
4. Add `worker_logging_setup()` to `celery_app.py` startup
5. Sensitive field protection: never log raw `session_id` (only `session_id[:8]`)

---

## Migration Plan

1. `config.py`: change default
2. `json_logging.py`: extend `_EXTRA_KEYS` and add HTTP request fields
3. `request_id.py`: replace plain-text access log with JSON dict emission
4. `celery_app.py`: call `configure_json_logging()` if env var set
5. Write tests

No database migration.

---

## Rollback Plan

Set `ENABLE_JSON_LOGGING=false` in `.env`. No code change needed.

---

## Performance Impact

Negligible. JSON serialization of log records is ~0.1ms per log line. At 1000 log lines/sec (high traffic), this adds 100ms/sec CPU time per process — well within budget.

---

## Security Impact

**Must ensure:**
- Raw `session_id` (32 chars) is never in structured logs (use `session_id[:8]`)
- `password` fields never logged
- `storage_key` / R2 paths never in access logs (path sanitization already present)
- IP addresses: already hashed before storage; raw IP logged at DEBUG only

---

## Test Plan

1. Default `enable_json_logging=True` means JSON logs at startup
2. Each log line is valid JSON (parseable)
3. Required fields present: `ts`, `level`, `logger`, `msg`
4. HTTP access log has: `method`, `path`, `status`, `duration_ms`, `request_id`
5. Sensitive fields absent: no `password`, no full `session_id`, no `storage_key`
6. `ENABLE_JSON_LOGGING=false` produces plaintext logs
7. Celery workers emit JSON logs when enabled
