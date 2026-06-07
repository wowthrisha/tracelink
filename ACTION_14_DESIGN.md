# Action 14 Design: Public API + API Keys

**Status:** IN PROGRESS  
**Risk:** P2 — No programmatic access; every integration requires user session (JWT)  
**Effort:** 5 hours

## Problem

Enterprise integrations (Salesforce, HubSpot, custom scripts) cannot use short-lived JWT tokens. They need stable, revocable API keys that authenticate machine-to-machine requests without user interaction.

## Solution

Add an `api_keys` table. Keys are generated as `sd_<48-char-hex>` (196-bit entropy, URL-safe). The full key is shown once at creation; thereafter only `key_prefix` (first 8 chars) and the SHA-256 hash are stored. API requests authenticate via `Authorization: Bearer sd_...` or `X-API-Key: sd_...` headers. The existing `/api/**` surface becomes accessible via API keys with the same authorization model as JWT auth (key is scoped to its owner's user_id).

## Key Format

```
sd_<48 hex chars>
```

- `sd_` prefix: prevents accidental exposure in logs (easily grep-able)
- 48 hex chars = 24 random bytes = 192 bits of entropy
- Total length: 51 chars

## Storage

```sql
CREATE TABLE api_keys (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  name VARCHAR(100) NOT NULL,          -- human label ("production CRM")
  key_prefix VARCHAR(10) NOT NULL,     -- first 10 chars for display
  key_hash VARCHAR(64) NOT NULL,       -- SHA-256 of full key (never stored in plain)
  scopes TEXT NOT NULL DEFAULT '[]',   -- JSON array of scope strings
  is_active BOOL NOT NULL DEFAULT TRUE,
  last_used_at TIMESTAMPTZ,
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## Scopes

Initial scope set:
- `documents:read` — list/status/download documents
- `documents:write` — upload documents
- `links:read` — list/get share links
- `links:write` — create/update/revoke links
- `analytics:read` — read analytics events
- `webhooks:read` — list/get webhooks
- `webhooks:write` — create/update/delete webhooks

Empty scope list = all scopes (legacy / admin key).

## Authentication Flow

1. Request arrives with `Authorization: Bearer sd_...` or `X-API-Key: sd_...`
2. `get_current_user` dependency: try JWT first, then API key path
3. API key path: SHA-256 the supplied key → look up by hash → check is_active + expiry
4. If valid: update `last_used_at` (async, fire-and-forget) → return same `{"user_id": ..., "email": ...}` dict as JWT path
5. Scope enforcement: routes needing write access can check `user["scopes"]`

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/api-keys | Create key (returns full key once) |
| GET | /api/api-keys | List keys (no key value) |
| GET | /api/api-keys/{id} | Get key metadata |
| PATCH | /api/api-keys/{id} | Update name/scopes/is_active |
| DELETE | /api/api-keys/{id} | Revoke key |

## Security

- Key hash stored as SHA-256 only — compromise of DB does not expose live keys
- Prefix stored for UI display ("ends in ...abc123") without full value
- `last_used_at` updated asynchronously (no added latency per request)
- Expired keys rejected at auth time
- Rate limiting applies per-IP regardless of auth method

## Files Changed

| File | Change |
|------|--------|
| `app/models/api_key.py` | `APIKey` model |
| `alembic/versions/015_add_api_keys.py` | Migration |
| `app/routers/api_keys.py` | CRUD router |
| `app/auth.py` | API key path in `get_current_user` |
| `app/main.py` | Include api_keys router |
| `tests/integration/test_enterprise_product.py` | `TestPublicAPI` class |
