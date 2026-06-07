# Action 1 Design: Enable HSTS by Default

**Status:** APPROVED  
**Date:** 2026-06-07  
**Risk Level:** Low (config change only)

---

## Current Architecture

`config.py:96`: `hsts_max_age: int = 0`

`security_headers.py:72–78`: HSTS injected only when `hsts_max_age > 0` AND request is HTTPS.
`main.py:62–67`: Emits a WARNING (not error) when HSTS disabled in production.

**Result:** Every deployment that doesn't explicitly set `HSTS_MAX_AGE` gets no HSTS header.

---

## Problem

HTTP Strict Transport Security prevents SSL strip attacks (MITM downgrades HTTPS → HTTP). Without HSTS, a network attacker who intercepts traffic can silently strip TLS before it reaches the browser, preventing the padlock and intercepting all document content including session tokens.

This is especially critical for SecureDoc because:
1. Documents contain sensitive business information
2. Session tokens in `X-Session-ID` header would be exposed
3. Passwords sent to `/validate` would be exposed

**Threat Model:**
- Attacker on same network (coffee shop, corporate proxy)
- Attacker controls intermediate router
- Attacker MITMs connection before TLS handshake

---

## Alternative Designs

**Option A: Keep default=0, add warning** (current)
- Pro: Conservative; operators opt-in
- Con: Default is insecure; operators who don't read docs stay vulnerable

**Option B: Default=31536000, opt-out** (chosen)  
- Pro: Secure by default
- Con: Operators who accidentally run HTTP-only and don't set HSTS_MAX_AGE=0 might have issues
- Mitigated: Middleware checks `X-Forwarded-Proto: https` before injecting — HTTP-only deploys will NEVER receive the HSTS header

**Option C: Force-enable with no opt-out**  
- Pro: Always secure
- Con: Too restrictive; no escape hatch

---

## Chosen Design

Default `hsts_max_age=31536000`. The middleware already correctly handles the HTTP/HTTPS check — HSTS is only injected when `is_https=True`. Adding `; preload` enables submission to the HSTS preload list for max-security deployments.

Production startup check changed from `warning` → `error` for HSTS disabled, matching the existing pattern for other critical security configs.

---

## Migration Plan

1. Change `config.py` default value
2. Add `; preload` to `security_headers.py` HSTS header  
3. Change `main.py` HSTS warning → error for production
4. Write tests

No database migration required.  
No deployment downtime required.

---

## Rollback Plan

Set `HSTS_MAX_AGE=0` in `.env`. HSTS header immediately stops being sent. No redeploy required.

---

## Performance Impact

Zero. HSTS is a single HTTP response header. No computational cost.

---

## Security Impact

**Eliminates:** SSL strip attack surface  
**Does not address:** Certificate validity checking (handled by browser/TLS stack)  
**Meets:** PCI DSS 4.0 req 6.5.1, NIST SP 800-52 §3.3, SOC2 CC6.7

---

## Test Plan

1. HSTS header present on HTTPS responses (X-Forwarded-Proto: https)
2. HSTS header absent on HTTP responses (no X-Forwarded-Proto header)
3. HSTS max-age value = 31536000
4. HSTS header contains `includeSubDomains`
5. HSTS header contains `preload`
6. Production startup raises error when HSTS disabled
7. Development startup does not raise error for HSTS disabled
8. `HSTS_MAX_AGE=0` env var disables HSTS (regression: opt-out works)
