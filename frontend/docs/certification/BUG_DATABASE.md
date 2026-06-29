# BUG DATABASE — Sprint 5.5 Engineering Investigation
**Date:** 2026-06-29  
**Sprint:** 5.5 Phase 2

---

## BUG-REAL-001 — NameError in analytics.py on webhook failure during `analytics.completed`

| Field | Value |
|-------|-------|
| **ID** | BUG-REAL-001 |
| **Severity** | HIGH |
| **Status** | FIXED (commit `710ff78`) |
| **Component** | `backend/app/routers/analytics.py` |
| **Line** | 342-343 (post-fix: 344-345) |
| **Endpoint** | `POST /api/analytics/events` |
| **Condition** | `event_type == "completed"` AND webhook registered AND webhook dispatch raises |

### Description

`logger.warning()` was called at line 340 (before fix) inside an `except Exception as _exc` block. The name `logger` was never defined in this file. Calling `logger.warning()` raised `NameError: name 'logger' is not defined`, which propagated as a 500 Internal Server Error to the viewer.

### Source Code Evidence

**Before fix — `analytics.py` lines 1-13 (imports section):**
```python
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.event import AccessEvent
from app.models.link import ShareLink
from app.models.document import Document
from app.services.analytics_service import AnalyticsService
from app.middleware.rate_limit import limiter
from app.auth import get_current_user, require_scope
```
No `import logging`. No `logger = ...`.

**Failing line (before fix):**
```python
except Exception as _exc:
    logger.warning("analytics.completed webhook trigger failed: %s", _exc)
```

### Trigger Conditions
1. Viewer sends `POST /api/analytics/events` with `event_type: "completed"`
2. Document owner has at least one active webhook subscribed to `analytics.completed`
3. `dispatch_webhook_event()` raises any exception (e.g. DB error, Celery unavailable)
4. Except block calls `logger.warning()` → NameError → 500 to viewer

### Fix Applied
Added `import logging` (line 1) and `logger = logging.getLogger(__name__)` (line 17) to `analytics.py`.

### Verification
- `grep -n "^import logging\|^logger\s*=" backend/app/routers/analytics.py` → lines 1 and 17
- `python -m pytest tests/ -q` → 1624 passed, 0 failures

---

## FALSE POSITIVE BUGS (Phase 1 Audit — Verified Not Real)

These were flagged in the Phase 1 Playwright audit and have been individually disproven with source code evidence.

| ID | Title | Phase 1 Verdict | Phase 2 Verdict | Evidence |
|----|-------|-----------------|-----------------|----------|
| BUG-001 | Upload stats show 0 | MEDIUM | NOT BUG | New account — `overview.total_views_today` etc. are genuinely 0. Fields verified in `analytics.py:177-181` and `UploadScreen.jsx:194-198`. |
| BUG-002 | Analytics counters all 0 | MEDIUM | NOT BUG | Same — new account. `AnalyticsScreen.jsx:34` reads `overview?.total_views_today` which matches backend field name. |
| BUG-003 | Viewer shows email gate | HIGH | NOT BUG | `ViewerScreen.jsx:150-161` shows `DocumentPicker` when `!docId && !publicToken`. Email gate is `gateInfo && !session` (different code path — requires token). Audit navigated viewer without docId. |
| BUG-004 | Storage loading forever | MEDIUM | NOT BUG | `StorageScreen.jsx:41-43` — `.finally(() => setLoading(false))`. Loading ALWAYS clears. Audit used insufficient mock wait time. |
| BUG-005 | Notifications loading | LOW | NOT BUG | `NotificationsScreen.jsx:61-64` — loading clears in `finally`. `getEvents()` → `/api/analytics/events` → returns `{"events":[],"total":0}` for new user. |
| BUG-006 | Webhook PAUSED badge | LOW | NOT BUG | `WebhooksScreen.jsx:257-259` reads `wh.is_active`. Backend `webhooks.py:29` returns `is_active`. Audit mock used wrong field name `active`. |
| BUG-007 | Link name placeholder truncated | LOW | NOT BUG / COSMETIC | Display width constraint. Not a functional bug. |
