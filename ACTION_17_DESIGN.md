# Action 17 Design: Admin Audit Log

**Status:** IN PROGRESS  
**Risk:** P1 — Required for SOC2 CC6.1; without it, there's no immutable admin action record  
**Effort:** 3 hours

## Problem

Admin actions (user added to org, document deleted, link revoked, API key created) leave no durable trace. SOC2 auditors require evidence that access changes are logged and reviewable.

## Solution

A dedicated `admin_audit_log` table captures admin-plane events with actor, target, and before/after state. A read-only API endpoint (`GET /api/admin/audit-log`) lets org owners and admins review entries. Events are written automatically at service call sites.

## Schema

```sql
-- In migration 016 (added alongside orgs) or separate 017

CREATE TABLE admin_audit_log (
  id UUID PRIMARY KEY,
  org_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
  actor_user_id UUID NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  target_type VARCHAR(32),              -- "document" | "link" | "member" | "api_key" | "org"
  target_id VARCHAR(64),
  details_json TEXT,                    -- JSON with before/after fields
  ip_hash VARCHAR(64),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Audit Event Types

| Event | Trigger |
|-------|---------|
| `org.created` | POST /api/orgs |
| `org.updated` | PATCH /api/orgs/{id} |
| `org.deleted` | DELETE /api/orgs/{id} |
| `member.added` | POST /api/orgs/{id}/members |
| `member.role_changed` | PATCH /api/orgs/{id}/members/{uid} |
| `member.removed` | DELETE /api/orgs/{id}/members/{uid} |
| `api_key.created` | POST /api/api-keys |
| `api_key.revoked` | PATCH /api/api-keys/{id} is_active=false |
| `api_key.deleted` | DELETE /api/api-keys/{id} |
| `document.deleted` | DELETE /api/documents/{id} |
| `link.revoked` | POST /api/links/{id}/revoke |

## API

`GET /api/admin/audit-log?org_id=<id>&limit=50&offset=0`
- Requires org admin/owner role (when org_id specified) or user must be authenticated (returns own events)
- Returns paginated list of audit entries, newest first

## Files Changed

| File | Change |
|------|--------|
| `app/models/audit.py` | `AdminAuditLog` model |
| `alembic/versions/017_add_audit_log.py` | Migration |
| `app/services/audit_service.py` | `log_audit_event()` async helper |
| `app/routers/admin.py` | `GET /api/admin/audit-log` |
| `app/routers/orgs.py` | Emit audit events on org/member changes |
| `app/routers/api_keys.py` | Emit audit events on key create/revoke/delete |
| `app/main.py` | Include admin router |
