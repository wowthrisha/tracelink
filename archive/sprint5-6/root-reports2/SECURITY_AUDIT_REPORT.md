# Security Audit Report

Scope: `backend/app/**`. Evidence gathered by direct code reading on 2026-06-17. Every finding cites file:line.

## 1. Authentication & Authorization

| Area | File:Line | Evidence | Status |
|---|---|---|---|
| JWT verification | `app/auth.py:43-74` | Algorithm whitelist enforced (ES256/RS256, no HS256 confusion), `audience="authenticated"` checked, JWKS cached 3600s with refresh-on-invalid | Secure |
| API key auth | `app/auth.py:77-121` | Keys stored as SHA-256 hash, never plaintext; expiry checked with tz normalization; `require_scope()` enforces per-key scopes (`app/auth.py:159-188`) | Secure |
| Password hashing | `app/utils/crypto.py:6-17` | bcrypt with auto-salt, used for share-link passwords (`app/services/link_service.py:126`) | Secure |
| Org RBAC | `app/routers/orgs.py` (role_gte helper) | Role hierarchy enforced for member add/role-change/remove; last-owner-removal blocked | Secure |
| Admin audit-log auth | `app/routers/admin.py:15-78` | Role check (`role_gte(membership.role, "admin")`) happens **inside the function body**, not as a `Depends`, when `org_id` is supplied | **P2** — authorization boundary invisible to API-contract tooling; move to a dependency |

**Attack vector / Likelihood / Impact / Mitigation**

- **JWT algorithm confusion (RS256→HS256 downgrade attack):** Likelihood Low (whitelist enforced) / Impact Critical / Mitigated in `auth.py:43-74`.
- **API key brute-force:** Likelihood Low / Impact High / Mitigated — keys are 256-bit random, hash-compared, rate-limited at the route level.
- **Privilege escalation via admin audit-log:** Likelihood Low (logic is correct) / Impact Medium / Partially mitigated — correct today but fragile to refactors since the check isn't declarative.

## 2. Session Handling (Share-Link Viewer)

| Area | File:Line | Evidence |
|---|---|---|
| Session creation | `app/services/link_service.py:28-81` | Token = `secrets.token_urlsafe(48)` (384 bits) |
| Session ID transport | `app/routers/viewer.py:105-119` | Priority: `X-Session-ID` header > `sdoc_session` cookie. Query-param transport intentionally removed to avoid leaking session IDs into server/proxy access logs. |
| Session validation | `app/routers/viewer.py:354-370` (+5 more raise sites at 510, 634, 934, 1045, 1141, 1189) | `policy_enforcer.is_active_session()` checked on every page/thumb/toc/text/search/links/words/download route; raises `401 Session not recognized. Please re-validate.` on miss |
| Cross-link replay | `app/services/policy.py:144-156` | Session is bound to `link_id`; a session minted for link A is rejected on link B |
| Cache TTL | `app/services/viewer_cache.py:55, 185` | Session snapshot cached 5s, link snapshot 10s; revocation invalidates immediately via `invalidate_sessions_for_link()` (`viewer_cache.py:190-207`) |

**Finding — Attack vector:** Session fixation. Sessions are not reissued after re-validation (same `session_id` persists across the password/email gate flow). **Likelihood:** Low (session ID is high-entropy and not attacker-controllable pre-auth in the normal flow) **Impact:** Medium **Mitigation:** None currently; recommend rotating `session_id` on successful `/api/viewer/validate` if a pre-existing `session_id` was supplied by the client (P2).

## 3. SSRF

| Area | File:Line | Evidence |
|---|---|---|
| Guard implementation | `app/utils/ssrf_guard.py:31-58, 75-157` | Blocks RFC1918, loopback, link-local, cloud metadata IPs (169.254.169.254), blacklists `localhost`/`metadata.google.internal`; resolves DNS and validates **every** resolved IP (defends DNS rebinding) |
| Webhook create/update | `app/routers/webhooks.py:40, 85, 149` | URL validated through the guard before persisting |
| Webhook delivery (TOCTOU) | `app/workers/webhook_tasks.py:80-106` | Re-validates the URL **immediately before** the HTTP POST, not just at creation time — closes the classic SSRF TOCTOU window where a previously-safe hostname's DNS record is changed after registration |

**Attack vector:** Attacker registers webhook pointing at a public hostname, then re-points DNS to `169.254.169.254` to exfiltrate cloud metadata at delivery time. **Likelihood:** Medium (well-known technique) **Impact:** Critical if unmitigated **Status: Mitigated** — re-validation at delivery time in `webhook_tasks.py:80-106`.

## 4. File Upload / Document Processing

| Area | File:Line | Evidence |
|---|---|---|
| Upload validation | `app/routers/documents.py:107-273` | Content-type whitelist, adapter-based `validate_bytes()`, size limit per adapter |
| Storage key generation | `app/routers/documents.py:154` | `storage_key = f"originals/{doc_id}.{file_type}"` — **user-supplied filename never enters a filesystem/object-storage path**, eliminating path traversal |
| LibreOffice subprocess | `app/services/libreoffice_converter.py:101-241` | `subprocess.run()` invoked with an **argument list**, never `shell=True` (`libreoffice_converter.py:196`); input written to `mkdtemp()` as a hardcoded `input.docx`, not the user's filename (line 137); macros disabled via `MacroSecurityLevel=3` XCU override (lines 55-69); environment passed to the subprocess is an explicit whitelist, not inherited (lines 172-187) — prevents secret leakage if the converter is ever compromised; hard timeout enforced (line 199) |
| Other subprocess calls | `app/services/toc/docx_extractor.py:266` (antiword), `app/services/rasterizer.py:64` (pdftoppm) | Both list-based argv, no shell interpolation |

grep across `backend/app` for `eval(`, `exec(`, `os.system(`, `pickle.loads(`, `yaml.load(`, `shell=True` → **zero hits**.

**Attack vector:** Malicious Office document triggers macro execution or LibreOffice RCE during conversion. **Likelihood:** Medium (LibreOffice has a CVE history) **Impact:** High **Mitigation:** Macro execution disabled, env-whitelisted subprocess, hard timeout, throwaway temp dir cleaned unconditionally (lines 237-241). Residual risk: no seccomp/container-level sandboxing visible — if LibreOffice itself has an exploitable parser bug, the subprocess still runs as the application user. **Recommendation (P1):** run the conversion subprocess inside a separate restricted container/user with no network and minimal filesystem access (defense in depth beyond env/macro hardening).

## 5. Configuration & Secrets

| Area | File:Line | Evidence |
|---|---|---|
| Insecure-looking defaults | `app/config.py:15` (`postgresql+asyncpg://securedoc:password@localhost:5432/securedoc`), `:62` (`ip_hash_salt` placeholder), `:160` (`domain_verify_salt` placeholder), `:22-23` (`test_key`/`test_secret` storage creds) | All are **local-dev defaults only** |
| Startup enforcement | `app/main.py:29-82` | App refuses to boot in production mode if any of the above remain unchanged | Mitigated — but only as strong as the env-detection logic in `main.py`; verify the "is this production" check can't be spoofed by an unset/misconfigured env var (worth a dedicated test) |

**P1 recommendation:** add an explicit unit test asserting the app fails fast when `ENV=production` and `SECRET_KEY`/`ip_hash_salt`/`domain_verify_salt` are left at default — currently this protection exists in code but its own regression risk (someone refactors `main.py` and silently drops the check) is untested.

## 6. Rate Limiting

`app/middleware/rate_limit.py` — slowapi, keyed off the resolved client IP (via `TrustedProxyMiddleware`, `app/middleware/trusted_proxy.py:22-28`). Applied to register (5/min), upload (10/min), validate (20/min), webhook ops (10/min).

**Finding (P2):** slowapi's default store is in-process memory. In any horizontally-scaled (multi-worker/multi-container) deployment, each process enforces its own independent limit — effective limit is `N × limit` where `N` = worker count, not the intended global limit. **Recommendation:** move to a Redis-backed limiter (Redis is already a dependency for Celery) before scaling beyond one process.

## 7. Headers / CSRF / XSS

`app/middleware/security_headers.py:33-50`:
- CSP present: `script-src 'self' <hash>`, `object-src 'none'`, `frame-ancestors 'none'`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Permissions-Policy`.
- `style-src` includes `'unsafe-inline'` (line 36) — low risk since there is no user-controlled CSS injection point, but worth tightening if any future feature accepts user HTML/CSS.
- No CSRF token mechanism — **acceptable** because all authenticated mutating routes use `Authorization: Bearer` (JWT) or `X-Session-ID`, never ambient cookies-as-auth for the dashboard JWT path, which is what makes CSRF exploitable. The viewer session **does** use a cookie fallback (`sdoc_session`, `viewer.py:105-119`) — confirm that cookie is `SameSite=Strict` or `Lax` (not verified in this pass; **P1 action**: confirm cookie attributes in the `Set-Cookie` issuance code path).

## 8. PII Exposure

- `access_events.viewer_email`, `viewer_sessions.viewer_email`, `viewer_annotations.viewer_email` — plaintext, scoped to a single document/link and deleted via CASCADE when the parent document/link is deleted (see DATABASE_REVIEW.md).
- `viewer_profiles.email` (added migration 024) — **global, cross-document identity table with no retention/cleanup logic referencing it** (see DATABASE_REVIEW.md §IV). This is the most significant PII finding in the system: a viewer's email persists indefinitely even after every document/link they ever touched has been deleted. **P1.**
- CSV exports (`annotations.py` feedback/reviewer-activity exports) intentionally include `Reviewer Email` — this is correct/expected for the owner-facing feature, not a leak, since only the document owner can call these endpoints (ownership checked via `doc.user_id == current_user["user_id"]`).

## 9. Summary Table

| # | Finding | File:Line | Likelihood | Impact | Status |
|---|---|---|---|---|---|
| 1 | Admin audit-log authz in function body, not Depends | admin.py:15-78 | Low | Medium | Open (P2) |
| 2 | Session not reissued after re-validation (fixation) | viewer.py validate flow | Low | Medium | Open (P2) |
| 3 | SSRF via webhook DNS rebinding | webhook_tasks.py:80-106 | Medium | Critical | **Mitigated** |
| 4 | LibreOffice RCE blast radius (no container sandbox) | libreoffice_converter.py | Medium | High | Partially mitigated (P1) |
| 5 | Insecure defaults reachable if prod-check regresses | config.py / main.py:29-82 | Low | Critical | Mitigated, untested (P1) |
| 6 | In-process rate limiting under horizontal scale | middleware/rate_limit.py | High (once scaled) | Medium | Open (P2) |
| 7 | Viewer session cookie SameSite attribute unverified | viewer.py:105-119 | Unknown | Medium | Needs verification (P1) |
| 8 | `viewer_profiles.email` never purged | models/viewer_profile.py, migration 024 | High (always true over time) | Medium (GDPR/CCPA exposure) | Open (P1) |
| 9 | No webhook payload replay protection (no timestamp/nonce) | webhook_service.py | Low | Low | Open (P3) |
| 10 | No minimum entropy/length requirement on share-link passwords | link_service.py | Low | Low | Open (P3) |

**Overall assessment:** No critical RCE, SQL injection, auth-bypass, or plaintext-secret-in-repo vulnerabilities were found. The codebase shows deliberate hardening (SSRF re-validation at delivery time, env-whitelisted subprocess, hash-only credential storage, startup-time default-secret rejection). Remaining work is closing PII retention gaps and operational scaling gaps (rate limiter), not fixing exploitable bugs.
