# SecureDoc Dependency Audit

**Date:** 2026-07-01  
**Version:** 8.1.0  
**Tool:** pip-audit 2.10.1, npm audit

---

## Executive Summary

| Category | Count |
|----------|-------|
| Backend packages audited | 27 |
| Backend vulnerable packages | 6 |
| Frontend packages audited | 9 |
| Frontend vulnerabilities | 0 |
| Critical severity | 0 |
| High severity | 4 |
| Medium severity | 2 |

---

## Backend Vulnerabilities

### HIGH: starlette 0.38.6

| CVE | Description | Fix Version |
|-----|-------------|-------------|
| CVE-2025-54121 | Path traversal via crafted URL | 0.47.2 |
| CVE-2024-47874 | Request smuggling via multipart | 0.40.0 |
| PYSEC-2026-248/249 | StaticFiles path traversal | 1.3.0/1.3.1 |
| CVE-2026-48817/48818 | Not yet disclosed | 1.1.0 |

**Risk:** HIGH — path traversal in StaticFiles could expose backend files.  
**Remediation:** Upgrade `starlette` → pinned via `fastapi`. Upgrade `fastapi>=0.115.6` which bundles starlette 0.47.2+.  
**Workaround:** SecureDoc's StaticFiles mount serves only `frontend/dist/` — attack surface limited to frontend assets, not backend code.

---

### HIGH: python-multipart 0.0.12

| CVE | Description | Fix Version |
|-----|-------------|-------------|
| CVE-2024-53981 | Denial of service via malformed form data | 0.0.18 |
| CVE-2026-24486 | Memory exhaustion | 0.0.22 |
| CVE-2026-40347 | Boundary parsing issue | 0.0.26 |
| CVE-2026-42561 | Header injection | 0.0.27 |
| CVE-2026-53538/39/40 | Multiple parsing bugs | 0.0.30/0.0.31 |

**Risk:** HIGH — file upload endpoint is a primary attack surface.  
**Remediation:** Upgrade to `python-multipart>=0.0.31`.  
**Workaround:** Existing `MAX_UPLOAD_MB` limit (100MB) and rate limiting (10/min) reduce DoS risk.

---

### HIGH: pyjwt 2.10.1

| CVE/ID | Description | Fix Version |
|--------|-------------|-------------|
| PYSEC-2026-120 | Algorithm confusion attack | 2.12.0 |
| PYSEC-2026-175/176/177/178/179 | Multiple JWT attacks | 2.12.1–2.13.0 |

**Risk:** HIGH — JWT validation bypass could allow auth circumvention.  
**Remediation:** Upgrade to `PyJWT>=2.13.0`.  
**Workaround:** SecureDoc uses `algorithms=["ES256"]` explicitly — algorithm confusion attack requires `algorithms=["RS256", "HS256"]` which we do not use. Risk is MEDIUM in practice.

---

### HIGH: cryptography 44.0.0

| CVE/ID | Description | Fix Version |
|--------|-------------|-------------|
| CVE-2024-12797 | RSA key validation bypass | 44.0.1 |
| CVE-2026-26007 | X.509 parsing issue | 46.0.5 |
| PYSEC-2026-35 | AES-GCM nonce reuse | 46.0.6 |
| GHSA-537c-gmf6-5ccf | OpenSSL vulnerability | 48.0.1 |

**Risk:** MEDIUM-HIGH — primarily affects RSA operations; SecureDoc uses ES256 (ECDSA), not RSA.  
**Remediation:** Upgrade to `cryptography>=46.0.6`.

---

### MEDIUM: pillow 11.0.0

| CVE | Description | Fix Version |
|-----|-------------|-------------|
| CVE-2026-25990 | Image parsing DoS | 12.1.1 |
| CVE-2026-40192/42310/42311 | Image processing vulnerabilities | 12.2.0 |
| PYSEC-2026-165 | Not yet disclosed | 12.2.0 |

**Risk:** MEDIUM — exploitable only if processing attacker-controlled images. SecureDoc processes uploaded PDFs converted to images server-side.  
**Remediation:** Upgrade to `Pillow>=12.2.0`.

---

### MEDIUM: pypdf 5.1.0

| CVE | Fix Version | Notes |
|-----|-------------|-------|
| CVE-2025-55197 | 6.0.0 | PDF parsing issue |
| CVE-2025-62707/62708 | 6.1.3 | |
| CVE-2025-66019 | 6.4.0 | |
| CVE-2026-22690/22691 | 6.6.0 | |
| 20+ more CVEs | 6.6.2–6.13.3 | See full pip-audit output |

**Risk:** MEDIUM — SecureDoc uses pypdf for TOC and text extraction only, not for security-critical operations.  
**Remediation:** Upgrade to `pypdf>=6.13.3`.

---

## Frontend Vulnerabilities

```
npm audit: found 0 vulnerabilities
```

All frontend devDependencies (React 18, esbuild, vitest, testing-library) are current with no known vulnerabilities.

---

## Remediation Plan

| Priority | Package | Current | Target | Timeline |
|----------|---------|---------|--------|---------|
| 1 | starlette (via fastapi) | 0.38.6 | 0.47.2+ | Sprint 6.6 |
| 2 | python-multipart | 0.0.12 | 0.0.31 | Sprint 6.6 |
| 3 | pyjwt | 2.10.1 | 2.13.0 | Sprint 6.6 |
| 4 | cryptography | 44.0.0 | 46.0.6+ | Sprint 6.6 |
| 5 | pillow | 11.0.0 | 12.2.0 | Sprint 6.7 |
| 6 | pypdf | 5.1.0 | 6.13.3 | Sprint 6.7 |

**Estimated effort:** 1 engineering day (dependency upgrades + regression testing).

---

## License Compliance

All dependencies use OSI-approved licenses compatible with commercial SaaS:

| License | Packages |
|---------|---------|
| MIT | fastapi, pydantic, httpx, redis, celery, stripe, slowapi |
| BSD-3-Clause | sqlalchemy, alembic, cryptography, pillow |
| Apache-2.0 | opentelemetry-*, botocore, boto3 |
| PSF | asyncpg |
| LGPL-3.0 | python-docx |

No GPL or AGPL packages that would require open-sourcing the application.

---

## Abandoned / At-Risk Packages

| Package | Status | Notes |
|---------|--------|-------|
| python-docx | Active (1.1.2, 2024) | Regular releases |
| slowapi | Active (0.1.9, 2024) | Maintained |
| pdf2image | Active (1.17.0, 2024) | Wrapper around poppler |
| pypdf | Active (many recent releases) | Very active |

No abandoned packages identified.

---

*Generated by pip-audit 2.10.1 and npm audit. Raw output available in CI artifact.*
