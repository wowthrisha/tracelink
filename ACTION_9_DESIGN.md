# Action 9: CDN Offload for Thumbnails

## Problem

Every thumbnail request hits the API server, which:
1. Checks the session
2. Downloads from R2 (or local cache)
3. Applies visible watermark
4. Applies forensic stamp
5. Returns bytes to client

For a 50-page document, the first viewer fetches all 50 thumbnails sequentially.
Subsequent viewers repeat the same R2 downloads and PIL work — thumbnails are
the same for all viewers (the document-level forensic stamp is already in them).

This is avoidable: thumbnails don't contain session-specific watermarks or forensic
stamps. They are pre-rendered at upload time and are identical for all viewers.

## Solution

Add a CDN URL configuration path for thumbnails. When a CDN base URL is set:
1. The thumbnail endpoint returns a `302 Redirect` to a presigned R2 URL or a CDN URL.
2. Subsequent thumbnail requests for the same page bypass the API entirely.
3. Full page images MUST continue to be proxied (they contain the session-specific
   forensic stamp — see ADR-003 and Action 3).

The CDN redirect is protected:
- Session validation still happens (the API validates before redirecting).
- The redirect URL is a presigned R2 URL (short-lived, unguessable).
- No storage key is exposed in query parameters — only in the presigned URL signature.

## Architecture

### Presigned R2/S3 URL generation
- Add `generate_presigned_url(key, expires_in=300)` to `StorageService`.
- Returns a URL valid for 300 seconds (5 minutes) — long enough for the page to load,
  short enough to not be useful if extracted.

### `backend/app/config.py`
- `cdn_thumbnail_enabled: bool = False` — default off.
- `cdn_thumbnail_presign_ttl_sec: int = 300` — presigned URL TTL.

### `backend/app/routers/viewer.py`
- `GET /api/viewer/thumb/{token}/{page}`: when `cdn_thumbnail_enabled=True`, generate
  presigned URL via storage service and return `302 Redirect` instead of proxied bytes.
- Session validation still runs before the redirect.

### Security invariants preserved
- Full page endpoint (`/api/viewer/page/{token}/{page}`) NEVER redirects — still proxied.
  This is a hard rule from the project security spec.
- Thumbnail redirect only happens after session is validated.
- Presigned URLs are short-lived (5 minutes).

## Test Plan
- CDN disabled (default): thumbnail endpoint returns bytes as before.
- CDN enabled: thumbnail endpoint returns 302 with Location header.
- Full page endpoint always returns bytes (never redirects), even when CDN enabled.
- Session validation still required for thumbnail redirect.
- Presigned URL TTL is configurable.
