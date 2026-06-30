# SecureDoc Enterprise Readiness Assessment
**Date:** 2026-06-30  
**Reviewer Persona:** Enterprise Security Architect + Enterprise Admin  
**Benchmark:** SOC 2 Type II, GDPR, enterprise SaaS standards (Stripe, DocSend, Box, Notion)

---

## Executive Summary

SecureDoc has an exceptionally strong **security foundation** — forensic watermarking, session-level DRM, IP allowlisting, HMAC-signed webhooks, advisory-lock migrations, Prometheus metrics, and a complete audit log. The **infrastructure** is production-grade.

However, **enterprise buyers evaluate products on management capability**, not infrastructure. An enterprise admin needs to invite and remove team members, run filtered audit reports, rotate credentials safely, and integrate with their IdP. In all four of these categories, SecureDoc has significant gaps.

**Enterprise Readiness Score: 4.5 / 10**

---

## Evaluation Categories

### 1. Authentication & Identity (7/10)

| Requirement | Status | Notes |
|------------|--------|-------|
| Email/password login | ✓ | Supabase-backed |
| Password reset via email | ✓ | Working |
| JWT-based session management | ✓ | ES256/JWKS |
| Session expiry and invalidation | ✓ | Redis session TTL (5s cache per ADR-004) |
| SSO / SAML 2.0 | Partial | Backend has `saml_domain` field and ADR-010 references Supabase SAML — but NO admin UI to configure it |
| MFA / 2FA | ✗ | Not implemented |
| Enforce minimum password policy | ✗ | Minimum 6 chars — enterprise requires 12+ with complexity |
| Social identity providers (Google/MS) | ✗ | Not implemented |
| IP-based access restrictions (login) | ✗ | IP allowlist exists for share links but not for admin logins |
| Force-reauthentication on sensitive actions | ✗ | Deleting an org, revoking all access — no re-auth required |

**Enterprise Gap:** SSO is implemented in the backend but completely inaccessible from the UI. An IT admin cannot configure SAML without direct database access.

---

### 2. Team & Access Management (1/10)

This is the most critical enterprise gap.

| Requirement | Status | Notes |
|------------|--------|-------|
| Invite team members by email | ✗ | Backend has `add_member` but requires UUID, not email |
| Role-based access control (RBAC) | Partial | Roles exist (owner/admin/viewer) but UI cannot set them |
| Remove team members | ✗ | Backend has `remove_member` but UI doesn't expose it |
| Transfer organization ownership | ✗ | Not implemented in UI |
| Pending invitation management | ✗ | No invitation system at all |
| Directory sync (SCIM) | ✗ | Not implemented |
| Department/team grouping within org | ✗ | Flat org structure |
| Document-level sharing with team members | ✗ | Documents not scoped to org members in any way |
| Guest / external collaborator access | Partial | Share links work for external access, no concept of "guest account" |
| Member audit trail | Partial | `member.added` and `member.removed` events logged, but not viewable with filters |

**Enterprise Impact:** A team of 10 cannot use SecureDoc as a team. Organizations are a non-functional feature. Every member must have their own account and upload their own documents with no sharing between accounts.

---

### 3. Compliance & Auditing (4/10)

| Requirement | Status | Notes |
|------------|--------|-------|
| Immutable audit log | ✓ | Complete event logging for all actions |
| Audit log retention | Unknown | No documented retention period or export |
| Audit log filtering by date range | ✗ | Not implemented |
| Audit log filtering by actor | ✗ | Not implemented |
| Audit log filtering by event type | ✗ | Not implemented |
| Audit log export (CSV/JSON) | ✗ | Not implemented |
| GDPR right-to-erasure support | Unknown | No documented deletion flow for user data |
| Data residency / region control | Unknown | Not documented in DEPLOYMENT.md |
| DPA (Data Processing Agreement) | ✗ | SECURITY.md exists but no DPA template |
| Document retention policies | ✓ | Per-document retention (30/60/90 days) |
| Legal hold | ✗ | No way to prevent deletion of documents under hold |

**SOC 2 Gap:** An auditor asking "show me all document deletion events in Q1 2026 by admin@company.com" cannot be answered from the UI. The data is in the database but inaccessible.

---

### 4. Security Controls (8/10)

This is SecureDoc's strongest category.

| Requirement | Status | Notes |
|------------|--------|-------|
| HTTPS enforced (HSTS) | ✓ | ADR-001: 1yr HSTS + preload |
| API key authentication | ✓ | Granular scopes, `sd_` prefix, bearer auth |
| Webhook payload signing (HMAC) | ✓ | HMAC-SHA256, `X-SecureDoc-Signature` header |
| Forensic watermarking | ✓ | Per-session deterministic tilt (ADR-003) |
| DRM controls | ✓ | download, print, copy, right-click, watermark per-link |
| Session concurrency control | ✓ | max_concurrent_sessions enforced atomically |
| IP allowlisting (share links) | ✓ | CIDR notation supported |
| Email/domain allowlisting (share links) | ✓ | Per-link allowed_emails and allowed_domains |
| Rate limiting | ✓ | Middleware applied |
| Security headers | ✓ | Middleware: CSP, HSTS, X-Frame-Options |
| Vulnerability reporting process | ✓ | SECURITY.md present |
| Secrets in environment variables | ✓ | .env.example documents all secrets |
| Non-root container | ✓ | UID 1001 in Dockerfile |
| Advisory lock for migrations | ✓ | `pg_advisory_lock(7325613)` |
| CORS policy | Unknown | FastAPI CORS — need to verify production allowlist |

**Security Gap:** The DRM system blocks actions without explaining why. Enterprise security requires clear communication to viewers: "Printing is disabled by document policy." Silent blocking leads to support tickets and compliance confusion.

---

### 5. Developer & Integration (6/10)

| Requirement | Status | Notes |
|------------|--------|-------|
| REST API with authentication | ✓ | FastAPI, bearer auth |
| Granular API scopes | ✓ | 7 scopes covering all major resources |
| Webhook event delivery | ✓ | HMAC-signed, delivery tracking |
| API documentation | ✗ | No public API docs (OpenAPI spec exists at /docs but no public documentation) |
| SDK availability | ✗ | No official SDK |
| Sandbox/test environment | ✗ | Not documented |
| API versioning | ✗ | All endpoints at /api/ with no version prefix |
| API rate limit documentation | ✗ | Rate limits applied but not documented |
| API key rotation without downtime | ✗ | Must delete + recreate (causes downtime) |
| Webhook event coverage | Partial | 3 of ~15 expected lifecycle events |

---

### 6. Scalability & Operations (7/10)

| Requirement | Status | Notes |
|------------|--------|-------|
| Horizontal scaling of API | ✓ | Stateless FastAPI with Redis/PostgreSQL |
| Background job queue | ✓ | Celery + Redis |
| Caching layer | ✓ | Redis L2 page cache |
| Database migrations without downtime | ✓ | Advisory lock, alembic migrations |
| Health endpoint | ✓ | `/health` endpoint |
| Prometheus metrics | ✓ | ADR-008 |
| Backup/restore scripts | ✓ | `scripts/backup.sh`, `scripts/restore.sh` |
| Docker/container deployment | ✓ | Multi-stage Dockerfile |
| Database connection pooling | Unknown | SQLAlchemy async — need to verify pool settings |
| CDN for static assets | Partial | ADR-006: thumbnails only — main app bundle not on CDN |

---

### 7. Data Privacy & Residency (3/10)

| Requirement | Status | Notes |
|------------|--------|-------|
| GDPR compliance documentation | ✗ | SECURITY.md mentions security model but not GDPR specifics |
| Data Processing Agreement template | ✗ | Not provided |
| Right to erasure (account deletion) | ✗ | No documented account deletion flow |
| Data export (account portability) | ✗ | No "export my data" feature |
| Data residency options | ✗ | Not documented |
| PII minimization in logs | Unknown | Audit log stores `actor_email`, `viewer_email`, `ip_address` — retention unclear |
| Subprocessor list | ✗ | Not published |

---

### 8. Enterprise Contract Requirements (2/10)

| Requirement | Status | Notes |
|------------|--------|-------|
| SLA documentation | ✗ | Not present |
| Uptime guarantee | ✗ | Not documented |
| Enterprise license terms | ✗ | Only MIT license (for code) |
| Custom contract support | ✗ | No indication |
| Dedicated support tier | Partial | "Priority support" on Pro plan — not defined |
| Training / onboarding documentation | ✗ | No user manual, help center, or onboarding guide |

---

## Critical Blockers for Enterprise Sales

The following items would block an enterprise deal at a Fortune 500:

1. **No member invitation flow** — Teams cannot collaborate
2. **No SAML admin UI** — IT cannot configure SSO without database access
3. **Audit log not filterable/exportable** — Compliance team will reject
4. **No GDPR documentation or DPA** — Legal team will reject
5. **No MFA** — Security team will likely require MFA before approving
6. **API key cannot be rotated atomically** — Security policy violation in most enterprises

---

## Enterprise Readiness Checklist

| Category | Score | Blocker? |
|----------|-------|---------|
| Authentication & Identity | 7/10 | No (MFA is critical path, not day-1 blocker for many) |
| Team & Access Management | 1/10 | YES |
| Compliance & Auditing | 4/10 | YES |
| Security Controls | 8/10 | No |
| Developer & Integration | 6/10 | No |
| Scalability & Operations | 7/10 | No |
| Data Privacy & Residency | 3/10 | YES |
| Enterprise Contract Requirements | 2/10 | YES |
| **Overall** | **4.5/10** | |

---

## Path to Enterprise Readiness

### Phase 1 (Must fix before any enterprise deal — 4-6 weeks)
1. Member invitation flow by email (backend + frontend)
2. SAML configuration UI
3. Audit log date/actor/action filters + CSV export
4. MFA / 2FA support
5. GDPR documentation + right-to-erasure flow

### Phase 2 (Must fix before closing a deal — 6-8 weeks)
1. SCIM directory sync
2. API key rotation without downtime
3. SLA documentation
4. Data residency documentation
5. DPA template

### Phase 3 (Needed for renewal retention — ongoing)
1. Custom domain support UI
2. Document-level org scoping
3. Legal hold feature
4. Public API documentation + SDK

---

*Enterprise readiness assessment complete — 2026-06-30*
