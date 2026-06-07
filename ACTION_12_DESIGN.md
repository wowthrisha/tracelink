# Action 12 Design: Time-on-Page Analytics

**Status:** COMPLETE  
**Risk:** P2 — Missing engagement depth metric  
**Effort:** 2 hours

## Problem

SecureDoc logs page_viewed events but captures no dwell time. DocSend's core value prop is "see which pages engaged them." Without time_spent_ms, the Access Log is a click-stream, not an engagement story.

## Solution

Add a nullable `time_spent_ms` integer field to `access_events`. The viewer frontend sends it alongside event_type (e.g. `completed`, `print_attempt`). The backend validates and caps the value before storage.

## Schema

```sql
ALTER TABLE access_events ADD COLUMN time_spent_ms INTEGER NULL;
-- Migration 013
```

## Validation Rules

- Must be a non-negative integer (not a float, not a bool)
- Capped server-side at 14,400,000 ms (4 hours) — prevents skewed averages from abandoned sessions
- Fully optional — historical events have NULL, not 0

## API Changes

**POST /api/analytics/events**: body may include `"time_spent_ms": 12500`  
**GET /api/analytics/events**: response events now include `"time_spent_ms": null|<int>`

## Security

- Bool subclass rejected (`isinstance(v, bool)` check before `isinstance(v, int)`)
- Only allowed for `VIEWER_LOGGABLE_EVENTS` — server-side events cannot carry client-supplied timing
- Session still validated before any logging occurs

## Files Changed

| File | Change |
|------|--------|
| `app/models/event.py` | `time_spent_ms` mapped column |
| `alembic/versions/013_add_time_spent_ms.py` | DB migration |
| `app/services/analytics_service.py` | `time_spent_ms` kwarg in `log_event()` |
| `app/routers/analytics.py` | extract, validate, cap, pass, expose in GET |
| `tests/integration/test_enterprise_product.py` | `TestTimeOnPageAnalytics` (2 tests) |
