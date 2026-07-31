# Fix Implementation — JWKS fetch graceful degradation

See `ROOT_CAUSE_ANALYSIS.md` for the full trace. This document covers the
code-level fix only. Restoring the Supabase project itself is a separate,
non-code action — see `DEPLOYMENT_VERIFICATION.md`.

## What changed

**File: `backend/app/auth.py`**

1. **Added `JWKSUnavailableError`** — a typed exception distinguishing "the
   JWKS endpoint could not be reached" from any other failure, so callers can
   handle it explicitly instead of letting a raw `httpx.ConnectError`
   propagate.

2. **`_fetch_jwks()`** now wraps its `httpx.AsyncClient.get(...)` call in
   `try/except httpx.HTTPError`, logs the failing URL and error, and raises
   `JWKSUnavailableError` instead of letting the transport exception escape
   uncaught.

3. **`_get_public_key()`** now catches `JWKSUnavailableError` from a refresh
   attempt and branches:
   - If a previously cached key set exists (even if past its TTL), log a
     warning and **keep serving from the stale cache** — a transient Supabase
     blip no longer breaks live traffic that was working seconds earlier.
   - If there is no cache at all (cold start during an outage, or the outage
     has outlasted every prior cache), raise `HTTPException(503,
     "Authentication service temporarily unavailable. Please try again
     shortly.")` — a clean, documented, retryable error instead of an
     unhandled 500 with a stack trace.

4. **`verify_supabase_token()`**'s key-rotation retry path (the second
   `_fetch_jwks()` call, previously unguarded) now also catches
   `JWKSUnavailableError` and falls through to the existing stale-cache/503
   handling in `_get_public_key()`, rather than crashing on retry.

No other file needed changes: `list_documents()` in
`app/routers/documents.py` itself makes zero outbound network calls (see
root-cause trace) — the entire fix lives in the shared auth dependency,
which means it protects **every** JWT-gated route in the app
(`/api/documents`, `/api/links`, `/api/analytics`, `/api/groups`,
`/api/billing`, etc.), not just the one in the bug report.

## Why this satisfies "must never crash, return a useful error or partial
response instead"

For this specific failure mode, a "partial response" isn't meaningful: the
request can't be attributed to any user until the JWT is verified, so there
is no safe partial document list to return without first confirming
identity. The correct degradation is:

- **Warm cache present** → full, correct response, unaffected by the outage
  (network call skipped entirely).
- **No cache, Supabase down** → immediate, clean `503` with a human-readable
  `detail` message and no stack trace — never a `500`.

This mirrors standard practice for auth-provider outages (e.g. Auth0, Okta):
degrade to "try again shortly," not to unauthenticated or fabricated data.

## Diff summary

```
backend/app/auth.py
  + class JWKSUnavailableError(Exception)
  ~ _fetch_jwks(): network call now wrapped in try/except httpx.HTTPError
  ~ _get_public_key(): refresh failure now falls back to stale cache or 503
  ~ verify_supabase_token(): key-rotation retry no longer crashes on outage

backend/tests/integration/test_jwks_outage.py   (new file, see REGRESSION_REPORT.md)
```
