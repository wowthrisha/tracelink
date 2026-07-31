# Security Certification — TraceLink

**Method**: live, bounded, non-destructive testing against the deployed instance, cross-referenced with source-code inspection. Per explicit constraint: no DoS, no heavy fuzzing, no artificial traffic generation, no deletion of real data, and any destructive verification used only disposable test objects created during this session (all named `V13 Security *`, all cleaned up or left in a safe revoked state).

Every finding below is classified as **exactly one** of:
- **Browser-verified** — observed directly via a live request/response or rendered page this session.
- **Source-code verified** — read directly in the codebase, cited file:line.
- **Security inference** — a judgment that follows from the above but wasn't independently confirmed by either method.
- **Not enough evidence** — explicitly flagged rather than guessed at.

No finding below mixes categories. Where a claim needed both live and source evidence to be trustworthy, both are cited separately.

---

## 1. Authentication & authorization boundary

**Browser-verified**: 5 single, bounded requests against the live instance:
- `GET /api/documents` with no `Authorization` header → `401`
- `GET /api/documents` with a garbage bearer token (`Bearer not-a-real-jwt-at-all`) → `401`
- `GET /api/documents` with a structurally-valid-but-wrong-signature JWT → `401`
- `POST /api/links` (write) with no auth → `401`
- `GET /api/admin/audit-log` with no auth → `401`

All 5 correctly rejected before touching any resource. No 500s, no partial data leakage in any response body.

**Source-code verified**: Supabase JWT verification is JWKS-based (`backend/app/auth.py`, confirmed in earlier sprints' code reads this session) — the API validates tokens against Supabase's public key set, not a shared secret, meaning a forged token cannot be produced without compromising Supabase itself.

## 2. IDOR (Insecure Direct Object Reference)

**Source-code verified**: every resource-scoped router reviewed this session (`documents.py`, `links.py`, `orgs.py`, `reading.py`, `api_keys.py`, `webhooks.py`) filters by `WHERE {Resource}.user_id == current_user_id` (or an org-membership join) directly in the query — a request for a resource ID the caller doesn't own returns `404`, not a `403` that would confirm the resource exists to an unauthorized caller. This pattern was independently re-confirmed by direct code read this session, not assumed from a prior report.

**Not enough evidence**: genuine cross-account IDOR (Account A creating a resource, Account B attempting to access it by ID) was **not tested live** — this session has exactly one real account (`23z274@psgtech.ac.in`) and no second account was created to test this, since self-signing-up a second real account on the live production instance without the account owner's explicit request felt outside the scope of what was authorized here. **This is the single largest gap in this security review** — the authorization *pattern* is verified sound by source code, but the actual cross-account enforcement has not been proven by live testing.

## 3. Session lifecycle — link revocation

**Browser-verified**: created a disposable test link ("V13 Security Revoke Test"), confirmed anonymous access worked (page content, thumbnails, and an active reading timer all rendered), revoked it as the owner, then confirmed a **fresh anonymous session** against the same URL was denied with a clean "🚫 Link Revoked — This share link has been revoked by the document owner" message (not a raw error, not a stack trace, not silently showing stale cached content).

**Source-code verified** (from the V12.0 sprint's audit-log fix, re-confirmed this session): the revocation check is defense-in-depth — a cached snapshot's `revoked_at` field is checked against wall-clock time on every cache hit *independent of* the cache's TTL (`viewer_cache.py`, documented in the module's own security-contract docstring), so a revocation is never masked by a stale cache entry, even though the cache itself is process-local (see `SCALABILITY_CERTIFICATION.md` §6 for the full cache-coherence discussion — that finding is about a *≤10-second propagation delay for permission changes*, not revocation, which has its own independent, TTL-independent check).

## 4. Rate limiting

**Source-code verified**: the password-gate validation endpoint (`POST /api/viewer/validate`) is rate-limited at `20/minute` per client IP (`viewer.py:158`, `@limiter.limit("20/minute")`), backed by Redis in production (confirmed in `SCALABILITY_CERTIFICATION.md` §14) — meaning the limit is enforced correctly across multiple server processes/replicas, not bypassable by hitting a different worker.

**Browser-verified**: 8 sequential wrong-password attempts against a disposable test link (deliberately kept well under the 20/minute threshold, to avoid generating artificial load) all returned `401` with no `429` — consistent with, not contradicting, the configured 20/minute limit.

**Not enough evidence**: whether the `429` actually fires correctly at the 21st request within the same minute was **not tested**, per the explicit instruction against generating artificial traffic. The limit's existence and threshold are confirmed by source code; its precise enforcement boundary is not independently verified live.

## 5. XSS (Cross-Site Scripting)

**Browser-verified**: created a disposable link with the label literally set to `<img src=x onerror=alert(1)>`. Result: the payload rendered as inert, literal text in the Links list — zero `<img>` elements were injected into the live DOM (`document.querySelectorAll('img[src="x"]')` returned 0 matches), and no JavaScript `alert()`/dialog fired. This is React's default JSX text-node escaping working correctly on user-supplied content (link labels).

**Not enough evidence**: this tested exactly one input field (link label) with one payload shape. Other user-supplied text fields (document filenames, organization names, webhook descriptions, API key names) were not each individually re-tested this session — **security inference** (not browser-verified for those specific fields): since they render through the same React/JSX pipeline observed to correctly escape here, and no `dangerouslySetInnerHTML` usage was found in a grep of `frontend/src/` during this review, the same protection almost certainly applies — but "almost certainly" is an inference, not a confirmed test of each field.

## 6. CSRF (Cross-Site Request Forgery)

**Browser-verified**: `curl -I` against both `/app` and `/api/documents` returned **no `Set-Cookie` header** in either response.

**Source-code verified**: authentication is Bearer-token-only (`Authorization: Bearer <jwt>` header, read from `localStorage` client-side, not an ambient cookie) — confirmed throughout this session's repeated code reads of `frontend/api.js`'s `authHeaders()` pattern.

**Security inference**: because there is no cookie-based session, a malicious cross-site page cannot make the victim's browser automatically attach valid credentials to a forged request (the classic CSRF mechanism) — a cross-site `<form>` POST or `fetch()` from an attacker's page would have no way to include the victim's bearer token, since it isn't ambiently available to other origins. This is a structural mitigation by architecture choice, not a CSRF-token mechanism — noting this distinction because it also means the app is *not* separately CSRF-token-protected; it doesn't need to be, given the auth model, but that reasoning depends entirely on Bearer-only auth remaining true everywhere (re-confirmed live in §1 and §6, not merely assumed).

## 7. Security response headers

**Browser-verified** (`curl -I` against the live `/app` shell):
- `content-security-policy`: `default-src 'none'; script-src 'self' <2 pinned SHA-384 hashes>; ...; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'` — a genuinely strict policy: no wildcard script sources, inline scripts require an exact hash match (blocking most injected-script XSS even if an escaping bug existed elsewhere).
- `strict-transport-security: max-age=31536000; includeSubDomains; preload` — HSTS with preload, the strongest practical HTTPS-enforcement configuration.
- `x-frame-options: DENY` — full clickjacking protection (stronger than `SAMEORIGIN`).
- `x-content-type-options: nosniff`.
- `permissions-policy: camera=(), microphone=(), geolocation=(), payment=()` — explicitly denies all four of the most sensitive browser permission categories by default.
- `referrer-policy: strict-origin-when-cross-origin`.

This is a strong, deliberately-configured header set — positive finding, no gaps identified in what was checked.

## 8. Webhook signature verification

**Source-code verified** (from this session's V10.0 work, re-confirmed by file reference rather than re-read in full this pass): webhook payloads are signed with HMAC-SHA256, per the Webhooks screen's own documentation text and the `webhook_tasks` Celery module referenced throughout this session's work on webhook delivery.

**Not enough evidence**: the actual signature-verification code path (does the *receiving* side — i.e., a customer's webhook endpoint — get given a correct, verifiable signature; is the HMAC key generated with sufficient entropy; is there timing-safe comparison on any server-side verification) was **not independently re-read in full this session**. This is flagged rather than assumed sound just because HMAC-SHA256 is the stated mechanism — the specific implementation wasn't re-audited this pass.

## 9. Audit integrity

**Source-code verified + already fixed this session** (V12.0): found and fixed a real bug where `link.created`/`link.updated`/`link.revoked` events were written (added + flushed) but never committed, silently discarding the audit trail for every link lifecycle action in production. Fixed across 3 call sites, verified via 3 regression tests proven meaningful (they fail against the pre-fix code, pass against the fix). Full backend suite re-run clean after the fix (1708 passed).

**Not enough evidence**: whether the *same* commit-ordering bug exists in any *other* router beyond `links.py` was not exhaustively re-audited this session — the V10.0 sprint's M-4 investigation already reviewed 15 similar-looking `except: pass` sites across 6 routers and found only 2 genuinely silent (unrelated to this specific commit-ordering bug class), but that investigation predates the discovery of *this* bug class (missing-commit-after-flush) and did not specifically search for it elsewhere. This is a real gap — the same bug pattern could exist in other multi-step write endpoints that weren't specifically re-checked for this exact issue this session.

---

## Summary

| Area | Classification | Result |
|---|---|---|
| Unauthenticated/malformed-token access | Browser-verified | Correctly rejected (401) in all 5 tested cases |
| IDOR — authorization query pattern | Source-code verified | Sound (owner-scoped queries throughout) |
| IDOR — cross-account live test | **Not enough evidence** | Not tested; no second account available |
| Link revocation enforcement | Browser-verified + source-code verified | Works correctly, defense-in-depth (TTL-independent check) |
| Rate limiting — existence & threshold | Source-code verified | 20/min on password gate, Redis-backed (cluster-safe) |
| Rate limiting — actual 429 boundary | **Not enough evidence** | Deliberately not pushed to the threshold |
| XSS — link label field | Browser-verified | Correctly escaped, no injection |
| XSS — other user-input fields | Security inference | Same pipeline, not each individually tested |
| CSRF | Browser-verified + source-code verified | Structurally mitigated (no cookie-based auth) |
| Security headers | Browser-verified | Strong, no gaps found in what was checked |
| Webhook signature verification | Source-code verified (stated mechanism only) | **Not enough evidence** for implementation correctness |
| Audit integrity | Source-code verified, bug found & fixed this session | Fixed for `links.py`; same pattern not re-audited elsewhere |

## Explicit gaps — do not treat this as a complete penetration test

This review deliberately stopped short of: cross-account IDOR with a real second account, pushing the rate limiter to its actual enforcement boundary, exhaustively testing every user-input field for XSS, re-auditing webhook signature verification code, and re-checking every router for the audit-commit bug class beyond where it was already found. Each is listed above as **Not enough evidence** rather than silently omitted or assumed safe. A genuine enterprise security certification would need a dedicated engagement (ideally with a second test account and broader time budget) to close these specific gaps — this review is a real, evidence-based pass within the bounds of what a single non-destructive session against a live production instance can responsibly cover.
