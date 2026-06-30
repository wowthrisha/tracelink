# SecureDoc Enterprise Transformation — Risk Register

**Last Updated:** 2026-06-07  
**Format:** ID | Description | Probability | Impact | Mitigation | Status

---

## Active Risks

| ID | Risk | Prob | Impact | Score | Mitigation | Owner | Status |
|----|------|------|--------|-------|-----------|-------|--------|
| R-001 | HSTS locks users out on HTTP-only deployment | L | H | 6 | Middleware only injects HSTS when X-Forwarded-Proto=https; HTTP-only deploys unaffected | Infra | ✅ Mitigated |
| R-002 | Session cache stale for up to 5s after revocation | M | M | 4 | `invalidate_link()` purges all sessions for that link immediately; max exposure 5s | Dev | ✅ Accepted |
| R-003 | PPTX rendering quality degradation | M | M | 4 | LibreOffice output tested against common enterprise templates; known limitation documented | QA | ⚠️ Watch |
| R-004 | SSO lock-out if SAML misconfigured | L | H | 6 | Keep username/password auth path; SSO is additive, not replacement | Dev | ⏳ Pending |
| R-005 | CDN signed URL shared within TTL window | L | L | 1 | Thumbnails are 200px; forensic stamp present; acceptable risk | Security | ✅ Accepted |
| R-006 | Race condition in CDN signed URL expiry | M | L | 2 | Add 30s buffer to TTL; retry on 403 | Dev | ⏳ Pending |
| R-007 | pypdf streaming API incompatibility | L | M | 2 | Pin pypdf==5.1.0; test streaming against PDF samples | Dev | ⏳ Pending |
| R-008 | Webhook delivery failures cause data loss | M | M | 4 | Celery retry with exponential backoff; 72h retention before drop | Dev | ⏳ Pending |
| R-009 | API key brute force | M | H | 6 | Rate limiting per IP on `/api/v1/*`; bcrypt hash comparison throttles timing attacks | Security | ⏳ Pending |
| R-010 | Version history migration corrupts existing documents | L | H | 6 | Migration adds nullable columns; no existing rows affected; test on staging first | Dev | ⏳ Pending |
| R-011 | SSE connection exhaustion under load | M | M | 4 | Connection limit per user; timeout after 30 min idle; Redis pub/sub async | Dev | ⏳ Pending |
| R-012 | Custom domain DNS hijacking via dangling CNAME | L | H | 6 | TXT record ownership verification before CNAME activation; auto-deactivate on 404 | Security | ⏳ Pending |
| R-013 | OTel exporter latency adds to request path | L | L | 1 | OTLP exporter is async/non-blocking; fails open (trace dropped, not request) | Dev | ✅ Mitigated |
| R-014 | Prometheus /metrics endpoint exposing internal data | M | M | 4 | Bind metrics server to internal port only; exclude from Cloudflare routing | Infra | ⏳ Pending |
| R-015 | RBAC privilege escalation via org membership race | L | H | 6 | Role changes require re-authentication; JWT scopes refreshed on next login | Security | ⏳ Pending |

---

## Risk Scoring Guide

**Probability:** L=Low(<10%), M=Medium(10-40%), H=High(>40%)  
**Impact:** L=Low(cosmetic), M=Medium(degraded service), H=High(security breach/data loss)  
**Score:** L×L=1, L×M=2, L×H=3, M×L=2, M×M=4, M×H=6, H×L=3, H×M=6, H×H=9

---

## Closed Risks

| ID | Risk | Resolution | Date |
|----|------|-----------|------|
| R-100 | max_views race condition allows excess views | Fixed via atomic UPDATE | 2026-06-07 |
| R-101 | Direct R2 download bypasses viewer identity | Fixed via viewer forensic stamp | 2026-06-07 |
| R-102 | Session DB reads bottleneck at 100+ viewers | Fixed via session cache | 2026-06-07 |
| R-103 | HSTS disabled allows SSL strip attacks | Fixed via default-on | 2026-06-07 |
