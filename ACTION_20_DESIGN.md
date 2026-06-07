# Action 20 Design: Custom Domains

**Status:** IN PROGRESS  
**Risk:** P2 — Enterprise differentiator; allows `docs.acme.com/v/{token}` share links  
**Effort:** 2 hours

## Problem

All share links use `secure.wowmyspace.com/v/{token}`. Enterprise customers need white-label
links from their own domain (e.g. `docs.acme.com/v/{token}`) to maintain brand consistency
and avoid training employees/prospects to trust a third-party URL.

## Solution

1. Add `custom_domain VARCHAR(253)` to the `organizations` table (nullable, unique).
2. Add a `GET /api/orgs/{id}/domain/verify` endpoint that checks DNS TXT records for a
   verification token, then marks the domain as verified.
3. Update `share_url` generation in `link_service.py` to use the org's custom domain when the
   document belongs to an org with a verified custom domain.
4. Verification token format: `securedoc-verify=<sha256(org_id + secret_salt)[:32]>` — stable,
   no DB state needed for the challenge itself.

## Database Changes

**Migration 019**: ALTER TABLE organizations ADD COLUMN:
- `custom_domain VARCHAR(253) NULL UNIQUE` — the requested custom domain (e.g. `docs.acme.com`)
- `custom_domain_verified BOOLEAN NOT NULL DEFAULT false` — whether DNS verification passed
- `custom_domain_verified_at TIMESTAMP WITH TIME ZONE NULL`

## API Design

### Set custom domain
`PATCH /api/orgs/{id}` (existing) — already accepts arbitrary body; extend allowed fields to
include `custom_domain`. On change, reset `custom_domain_verified = false`.

### Verify DNS
`POST /api/orgs/{id}/domain/verify`
- Requires admin/owner role
- Looks up TXT record for the `custom_domain`
- Checks that `securedoc-verify=<token>` is present
- On success: sets `custom_domain_verified = true`, `custom_domain_verified_at = now()`
- Returns `{verified: true, domain: "..."}` or `{verified: false, error: "TXT record not found"}`

### Get verification token
`GET /api/orgs/{id}/domain/token`
- Requires admin/owner role
- Returns `{token: "securedoc-verify=<hex>", domain: "..."}`
- No DB write — token is derived deterministically from org_id + salt

## Verification Token Algorithm

```python
import hashlib, hmac
def _domain_verify_token(org_id: str, salt: str) -> str:
    h = hmac.new(salt.encode(), org_id.encode(), hashlib.sha256).hexdigest()[:32]
    return f"securedoc-verify={h}"
```

Salt comes from `settings.domain_verify_salt` (env var, required in production).
Default: `"securedoc_domain_salt_change_in_production"`.

## URL Generation

In `link_service.py` `create_link()`, when building `share_url`:

```python
base = settings.app_public_base_url  # default
if doc.org_id:
    org = await db.get(Organization, doc.org_id)
    if org and org.custom_domain_verified and org.custom_domain:
        base = f"https://{org.custom_domain}"
share_url = f"{base}/v/{token}"
```

## Security Considerations

- DNS verification prevents domain squatting attacks
- `custom_domain` is validated to be a valid hostname (no path component, no http://)
- Verification token is HMAC-based — not guessable without the server salt
- `custom_domain_verified` resets to false on domain change (prevents stale verification)
- Rate-limit the verify endpoint: 5/minute per org

## Files Changed

| File | Change |
|------|--------|
| `alembic/versions/019_add_custom_domains.py` | Migration |
| `app/models/org.py` | Add custom_domain, custom_domain_verified, custom_domain_verified_at |
| `app/config.py` | Add domain_verify_salt |
| `app/routers/orgs.py` | Add PATCH domain field, POST verify, GET token endpoints |
| `app/services/link_service.py` | Use custom domain in share_url generation |
