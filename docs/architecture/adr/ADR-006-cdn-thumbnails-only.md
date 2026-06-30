# ADR-006: CDN for Thumbnails Only

**Status:** Accepted
**Date:** 2026-06-07

## Context

CDN for full page images would require either pre-generating per-session watermarked variants (high storage cost) or moving watermarking to edge workers (significant complexity). Neither is acceptable without larger architectural changes.

## Decision

CDN for thumbnails only. Thumbnails contain the forensic document stamp but NOT the per-viewer visible watermark. A thumbnail being served via CDN without per-request auth is acceptable because:

1. Thumbnails are low-resolution (200px wide)
2. Thumbnails contain the forensic document stamp
3. Full-page access still requires a validated viewer session

Full pages: API proxy with visible watermark applied per request.

## Consequences

- Thumbnail latency reduced 50–80% via CDN edge cache
- Egress from storage to API server eliminated for thumbnails
- Signed thumbnail URLs have a 60-second TTL — shareable within that window (acceptable for low-res previews)
