# Feature Completeness Matrix
**Generated:** 2026-06-30  
**Scope:** All user-visible features in SecureDoc V3.2

---

## Legend
- ✅ Complete — feature fully works end-to-end
- ⚠️ Partial — works but has known gaps or missing polish
- ❌ Incomplete — not working or not built
- 🔒 Blocked — waiting on external decision (see REMAINING_DECISIONS.md)

---

## Authentication & Identity

| Feature | Status | Notes |
|---------|--------|-------|
| Email/password login (Supabase) | ✅ | — |
| JWT token refresh | ✅ | — |
| API key authentication | ✅ | — |
| Logout | ✅ | — |
| SAML/SSO | 🔒 | RD-008 — UI not built |
| MFA / 2FA | ❌ | Not planned |

---

## Document Management

| Feature | Status | Notes |
|---------|--------|-------|
| Upload PDF | ✅ | — |
| Upload DOCX | ✅ | — |
| Upload PPTX | ✅ | — |
| Background processing (rasterization) | ✅ | V3.1 streaming |
| Document groups | ✅ | — |
| Delete document | ✅ | With confirmation |
| Delete group | ✅ | With confirmation (added) |
| Document sort | ❌ | No sort controls (B-1) |
| Bulk move to group | ❌ | Not built |
| Document search | ❌ | Not built |
| Retention policy per document | ✅ | — |

---

## Document Viewer

| Feature | Status | Notes |
|---------|--------|-------|
| Page-by-page streaming render | ✅ | — |
| Zoom controls | ✅ | — |
| Fit-to-width / fit-to-page | ✅ | — |
| Text search (Ctrl+F) | ✅ | — |
| Table of contents panel | ✅ | — |
| Annotations / highlights | ✅ | — |
| Link extraction panel | ✅ | — |
| Insights panel | ✅ | — |
| Keyboard navigation | ⚠️ | Arrow keys work; focus trap missing (AX-011) |
| Session blur overlay explanation | ⚠️ | Blur works; no explanation text (BLOCK-006) |
| DRM block explanations | ⚠️ | Print/copy/right-click blocked; no toast (BLOCK-014) |
| Forensic watermark | ✅ | — |

---

## Share Links

| Feature | Status | Notes |
|---------|--------|-------|
| Create configured share link | ✅ | — |
| Create quick (unrestricted) link | ✅ | With warning modal (added) |
| Set password on link | ✅ | — |
| Set expiry date | ✅ | — |
| Set max view count | ✅ | — |
| Set domain allowlist | ✅ | — |
| Set IP allowlist | ✅ | — |
| DRM flags (no print/download/copy) | ✅ | — |
| Revoke single link | ✅ | With confirmation (added) |
| Revoke all links | ✅ | — |
| Delete revoked link | ✅ | With confirmation (added) |
| Copy link URL | ✅ | — |
| Open in new tab | ✅ | — |
| Rename link | ✅ | — |
| View link analytics | ✅ | — |
| Viewer feedback/comments | ✅ | — |

---

## Organizations & Teams

| Feature | Status | Notes |
|---------|--------|-------|
| Create organization | ✅ | — |
| Rename organization | ✅ | — |
| Delete organization | ✅ | With confirmation (added) |
| Invite member by email (direct add) | ✅ | Backend: `POST /members/invite` (added) |
| Pending invite flow | 🔒 | RD-001 |
| List members | ✅ | — |
| Remove member | ✅ | Added |
| Change member role | ✅ | Inline select added |
| Transfer ownership | ⚠️ | Works via role change; no dedicated UI |
| Prevent removing last owner | ✅ | Both backend and frontend enforce |
| Search members | ❌ | Not built |
| Leave organization | ✅ | Remove self |
| Organization analytics | ❌ | No org-scoped analytics view |
| SAML domain configuration | 🔒 | RD-008 |

---

## Compliance & Audit

| Feature | Status | Notes |
|---------|--------|-------|
| Immutable audit log | ✅ | — |
| View audit log | ✅ | — |
| Filter by date range | ✅ | Added |
| Filter by event type | ✅ | Added |
| Filter by actor | ❌ | No actor email field in model |
| Export CSV | ✅ | Added |
| Cursor-based pagination | ❌ | Uses OFFSET (degrades at scale) |

---

## Analytics

| Feature | Status | Notes |
|---------|--------|-------|
| View counts | ✅ | — |
| Unique viewers | ✅ | — |
| Session duration | ✅ | — |
| Page heatmap | ✅ | — |
| Completion rate | ✅ | — |
| Risk score | ✅ | — |
| Date range filter | ❌ | 🔒 RD-003 |
| Metric tooltips | ⚠️ | No tooltip explaining Risk, Completion formulas (B-4) |
| Export analytics | ❌ | Not built |

---

## API Keys

| Feature | Status | Notes |
|---------|--------|-------|
| Create API key | ✅ | — |
| List API keys | ✅ | — |
| Edit name / scopes | ✅ | Edit modal added |
| Revoke key | ✅ | With confirmation (added) |
| Delete revoked key | ✅ | With confirmation (added) |
| Key rotation | ❌ | Not built |

---

## Webhooks

| Feature | Status | Notes |
|---------|--------|-------|
| Register webhook | ✅ | — |
| List webhooks | ✅ | — |
| Edit webhook | ✅ | Edit modal added |
| Test webhook | ✅ | — |
| Pause / resume | ✅ | — |
| Delete webhook | ✅ | With confirmation (added) |
| View delivery history | ✅ | — |
| Webhook event catalog (>3 events) | 🔒 | RD-004 |

---

## Storage & Billing

| Feature | Status | Notes |
|---------|--------|-------|
| Storage usage breakdown by org | ✅ | With org name (added) |
| Free plan document counter | ⚠️ | Backend enforces; no UI counter (BLOCK-011/B-8) |
| Usage alerts | ❌ | Not built |

---

## Developer Experience

| Feature | Status | Notes |
|---------|--------|-------|
| API key scopes enforcement | ✅ | — |
| API documentation | ❌ | No Swagger/OpenAPI UI exposed |
| SDK / client libraries | ❌ | Not built |

---

## Summary

| Category | Complete | Partial | Incomplete | Blocked |
|----------|----------|---------|------------|---------|
| Auth | 4 | 0 | 1 | 1 |
| Documents | 8 | 0 | 3 | 0 |
| Viewer | 8 | 3 | 0 | 0 |
| Share Links | 16 | 0 | 0 | 0 |
| Organizations | 9 | 1 | 2 | 2 |
| Compliance | 5 | 0 | 2 | 0 |
| Analytics | 6 | 1 | 2 | 1 |
| API Keys | 5 | 0 | 1 | 0 |
| Webhooks | 6 | 0 | 0 | 1 |
| Storage | 1 | 1 | 1 | 0 |
| DevEx | 0 | 0 | 2 | 0 |
| **Total** | **68** | **6** | **14** | **5** |

**Feature completeness: 68/93 (73%) fully complete, 74/93 (80%) fully or partially complete**
