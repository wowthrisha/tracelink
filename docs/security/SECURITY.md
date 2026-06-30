# SecureDoc Security Guide

## Security Architecture

SecureDoc is built with defense-in-depth: multiple independent controls protect each document and session.

## Authentication & Authorization

### User Authentication (Supabase JWT)
- ES256-signed JWTs verified against Supabase JWKS endpoint
- JWKS cached in-process, refreshed on verification failure
- Token expiry enforced; no session storage server-side
- JWT leakage mitigated: tokens never logged (only user_id extracted)

### API Key Authentication
- Keys are `sd_` + 32 random bytes (URL-safe base64)
- Stored as SHA-256 hash in database — raw key never persisted
- Per-key scopes: `documents:read`, `documents:write`, `links:read`, `links:write`
- Org-level API keys supported for team access

### RBAC (Organizations)
- Roles: `owner` > `admin` > `viewer`
- Role checked on all org-level operations
- Document ownership separate from org membership

## DRM Session Security

| Control | Implementation |
|---------|---------------|
| Session creation | 32-byte cryptographically random ID |
| Session binding | IP hash stored at creation, verified on page requests |
| Session heartbeat | `last_seen` updated per page; expires after 2h inactivity |
| Concurrent session limit | Configurable per link (`max_concurrent_sessions`) |
| Session ID logging | Only first 8 chars ever logged |

## Share Link Security

| Control | Default | Notes |
|---------|---------|-------|
| Token entropy | 32 bytes | 256 bits, URL-safe base64 |
| Password protection | Optional | bcrypt with work factor 12 |
| Email allowlist | Optional | Exact match + domain wildcard |
| IP/CIDR allowlist | Optional | Validated with `ipaddress` module |
| Max views | Optional | Atomic decrement, no race condition |
| Expiry | Optional | UTC timestamp |
| Revocation | Immediate | Invalidates in-process cache within 30s |

## Watermarking

Every page served to a viewer has a forensic watermark embedded:
- Viewer email (or "anonymous"), date, session prefix (6 chars)
- Random angle variation ±`WATERMARK_ANGLE_JITTER_DEG` degrees per session
- Watermark is server-side; cannot be removed by the browser

## IP Address Handling

- Client IP extracted from `CF-Connecting-IP` (Cloudflare) or `X-Forwarded-For` (configurable depth)
- Raw IPs are never stored; stored as HMAC-SHA256 hash with `IP_HASH_SALT`
- SSRF guard: webhook URLs validated against RFC-1918 and link-local ranges

## API Security

- **HTTPS enforcement**: `HTTPS_REDIRECT=true` + `HSTS_MAX_AGE=31536000`
- **Security headers**: CSP, X-Frame-Options: DENY, X-Content-Type-Options: nosniff, Referrer-Policy
- **CORS**: Restricted to `ALLOWED_ORIGINS` in production
- **Rate limiting**: Per-IP via SlowAPI + Redis
- **Request size limits**: `MAX_UPLOAD_MB` (default 100MB)
- **Filename validation**: Path traversal check (`../` and `\` rejected)
- **Content type validation**: Only allowed MIME types accepted

## Storage Security

- Documents stored with server-side encryption (S3 SSE or R2 equivalent)
- Storage keys are non-guessable UUIDs
- No direct S3 URL exposure for pages (always proxied through API)
- Optional CDN thumbnail URLs are presigned with short TTL (default 5 minutes)

## Secrets Management

| Secret | How to Generate |
|--------|----------------|
| `IP_HASH_SALT` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DOMAIN_VERIFY_SALT` | Same as above |
| `STRIPE_WEBHOOK_SECRET` | From Stripe dashboard |
| `METRICS_TOKEN` | Same as IP_HASH_SALT |

Production startup is blocked if `IP_HASH_SALT` or `DOMAIN_VERIFY_SALT` are at their insecure defaults.

## Logging & Audit

- All API operations produce structured JSON logs with `request_id`, `correlation_id`, `user_id`, `org_id`
- Error responses include `error_category`: `auth_error`, `validation_error`, `not_found`, `server_error`
- `link.created`, `link.revoked`, `link.deleted` events written to audit log table
- Prometheus `/metrics` endpoint protected by `METRICS_TOKEN` and/or `METRICS_ALLOWED_IPS`

## Dependency Security

Production dependencies have known vulnerabilities in several packages (see DEPENDENCY_AUDIT.md). Priority remediation:
1. **starlette**: upgrade past 0.47.2 (path traversal CVE-2025-54121)
2. **python-multipart**: upgrade past 0.0.31
3. **pyjwt**: upgrade past 2.13.0
4. **cryptography**: upgrade past 46.0.6
5. **pillow**: upgrade past 12.2.0
6. **pypdf**: upgrade past 6.13.3

## Incident Response

See [INCIDENT_RESPONSE.md](../operations/INCIDENT_RESPONSE.md) for procedures.

## Security Contact

Report vulnerabilities to: security@securedoc.io (private disclosure)
