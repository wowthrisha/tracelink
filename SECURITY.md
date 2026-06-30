# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 8.1.x (RC-1) | Yes |
| < 8.0 | No |

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Email security reports to the maintainers. Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested mitigations

You will receive acknowledgement within 48 hours and a status update within 7 days.

## Security Model

### Authentication

- Users authenticate via Supabase JWT (ES256, verified against JWKS endpoint)
- API keys (`sd_` prefix) accepted for programmatic access
- All endpoints require authentication except the public viewer (`/v/{token}`)

### Document Access

- Documents are never directly accessible from object storage — all page bytes are proxied through the API
- Each viewer session is independently authenticated and rate-limited
- Per-link controls: expiry date, max views, IP allowlist, password, domain restriction
- Link revocation propagates within 10 seconds (link cache TTL)
- Session revocation propagates within 5 seconds (session cache TTL)

### Watermarking

- Visible watermark (viewer email + timestamp) applied to every page at serve time
- Forensic document stamp embedded at lower-right of stored pages
- Per-viewer forensic stamp embedded at lower-left at serve time (hashed session ID)

### Transport

- HSTS enabled by default (1 year + preload)
- All secrets injected via environment variables — never hardcoded
- `.env` files are gitignored; `backend/.env.example` contains only placeholders

### DRM

Client-side DRM controls (print disable, right-click disable, copy prevention) are UX gates only — they are not security boundaries. Server-side controls (access expiry, revocation, max views) are the security boundary.

## Known Limitations

- Client-side DRM can be bypassed by a determined user with browser devtools
- Thumbnail CDN URLs (when enabled) have a 60-second TTL window where they can be shared
- Demo storage mode (`USE_DEMO_STORAGE=1`) stores files unencrypted on local disk — not for production use
