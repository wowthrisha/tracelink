# Security Scorecard
**Generated:** 2026-06-30  
**Framework:** OWASP ASVS / OWASP Top 10  
**Baseline:** 8/10 (from Enterprise Readiness Review)

---

## Score: 8.5/10 (was 8/10)

---

## Fixes Applied in This Program

| Issue | Fix | Impact |
|-------|-----|--------|
| Zero-restriction link creation (BLOCK-003) | Added warning modal requiring explicit "Create Anyway" | Prevents accidental data exposure |
| `window.confirm()` for destructive actions | Replaced with styled `<Modal>` — consistent, accessible | Removes edge case where browser dialog could be spoofed or bypassed |

---

## Confirmed Security Controls (Unchanged)

| Control | Status |
|---------|--------|
| JWT verification (ES256/JWKS) | ✅ Enforced on all auth'd endpoints |
| API key authentication (`sd_` prefix, scope enforcement) | ✅ |
| Share link session integrity (watermark, max views, expiry) | ✅ |
| SSRF protection on webhook URLs (`validate_ssrf_url`) | ✅ |
| Content Security Policy (download disabled by image-rasterization) | ✅ |
| Forensic watermark (`_session_watermark_angle()`) | ✅ |
| Org RBAC (owner > admin > viewer, last-owner protection) | ✅ |
| Prevent last owner removal | ✅ (backend + frontend both enforce) |
| Supabase invite endpoint uses service role key | ✅ — fails gracefully if key not set |
| IP address hashing (not stored in plaintext) | ✅ |

---

## Security Items Deferred (No Business Decision Yet)

| Item | Risk | Decision Needed |
|------|------|----------------|
| No password minimum for share links (any length OK) | Low | Product: minimum length policy |
| Share link password stored as bcrypt | ✅ Correct behavior, no change needed | — |
| No MFA / 2FA in auth flow | Medium | Product: opt-in MFA strategy |
| Notification read state in localStorage | Low | RD-007 |
| No audit log IP/geo data (only ip_hash) | Low | Product: compliance level needed |

---

## Remaining OWASP Top 10 Assessment

| OWASP | Category | Status |
|-------|----------|--------|
| A01 | Broken Access Control | ✅ RBAC enforced at every org endpoint |
| A02 | Cryptographic Failures | ✅ JWT ES256, bcrypt for passwords |
| A03 | Injection | ✅ SQLAlchemy ORM (parameterized), no raw SQL |
| A04 | Insecure Design | ✅ — zero-restriction link now gated |
| A05 | Security Misconfiguration | ⚠️ CORS config from env; Docker non-root UID 1001 |
| A06 | Vulnerable Components | Unknown — no `safety` or `npm audit` run |
| A07 | Identification and Auth Failures | ✅ JWT, scope enforcement |
| A08 | Software Integrity Failures | Unknown — no SBOM |
| A09 | Security Logging Failures | ✅ Immutable audit log |
| A10 | SSRF | ✅ `validate_ssrf_url` on webhook registration |

---

## Recommendation

Run `pip install safety && safety check` and `npm audit` as part of CI to address A06.
