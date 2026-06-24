# Competitive Feature Gap Analysis
Sprint 4.4 — Production Certification Sprint
Date: 2026-06-22
Auditor role: Product Manager
Method: Direct comparison against DocSend (primary competitor) and adjacent tools (PandaDoc Rooms, Notion, Google Drive).
SecureDoc feature status derived from source code reading only. Competitor status from product knowledge.

Gap status:
- MATCHED ✅ — SecureDoc has this feature, verified from source
- AHEAD ★ — SecureDoc has something competitors lack
- BEHIND (BACKEND READY) 🔒 — SecureDoc backend complete, no frontend
- BEHIND (NOT BUILT) ❌ — Feature does not exist in any layer
- BEHIND (BROKEN) 💔 — Feature partially exists but is defective

---

## Primary Competitor: DocSend

DocSend is the direct competitor — document sharing with per-viewer analytics, access control, and real-time notifications.

### Core Document Sharing

| Feature | DocSend | SecureDoc | Status | Notes |
|---|---|---|---|---|
| Upload PDF for sharing | ✅ | ✅ | MATCHED ✅ | SecureDoc also supports DOCX, DOC, TXT, MD, LOG |
| Shareable link generation | ✅ | 💔 BROKEN | BEHIND 💔 | "New Link" button is a non-functional stub (UI-002). Backend works. |
| Password-protected links | ✅ | ✅ | MATCHED ✅ | Backend-enforced. Frontend policy tab works. |
| Email-restricted links (allow-list) | ✅ | ✅ | MATCHED ✅ | `allowed_emails` textarea in policy. |
| Link expiry | ✅ | ✅ | MATCHED ✅ | `expiry_at` with date picker. |
| Max view count | ✅ | ✅ | MATCHED ✅ | `max_views` field. |
| Revoke link | ✅ | ✅ | MATCHED ✅ | `DELETE /api/links/{id}` confirmed. |
| Disable download | ✅ | ✅ | MATCHED ✅ | `can_download` permission toggle. |
| Disable print | ✅ | ✅ | MATCHED ✅ | `can_print` permission toggle. |
| Disable copy | ✅ | ✅ | MATCHED ✅ | `can_copy` permission toggle. |

### Viewer Analytics

| Feature | DocSend | SecureDoc | Status | Notes |
|---|---|---|---|---|
| Per-viewer session tracking | ✅ | ✅ | MATCHED ✅ | Session-based with session_id. |
| Page-by-page view time | ✅ | ✅ | MATCHED ✅ | `access_events` log per page. |
| Per-page heatmap | ✅ | ✅ | MATCHED ✅ | `GET /api/analytics/page-heatmap` — top 20 pages. |
| Analytics dashboard | ✅ | ✅ | MATCHED ✅ | AnalyticsScreen with Overview/By Document/By Group tabs. |
| Date-range filtering in analytics | ✅ | 💔 BROKEN | BEHIND 💔 | Range selector exists but data is never filtered (UI-004). |
| Export analytics to CSV | ✅ | 💔 BROKEN | BEHIND 💔 | Export button is a stub (UI-005). |

### Notifications

| Feature | DocSend | SecureDoc | Status | Notes |
|---|---|---|---|---|
| Real-time alert when document opened | ✅ | ❌ | BEHIND 🔒 | Backend SSE infrastructure exists + link.viewed not dispatched. Neither SSE consumer nor viewer.py dispatch is wired. |
| Email notification on open | ✅ | ❌ | BEHIND ❌ | No email notification system anywhere in codebase. |
| Webhook on document open | ✅ | 🔒 | BEHIND 🔒 | Webhook backend complete but link.viewed never dispatched, no frontend. |

### Document Viewing Experience

| Feature | DocSend | SecureDoc | Status | Notes |
|---|---|---|---|---|
| In-browser PDF viewer | ✅ | ✅ | MATCHED ✅ | Custom canvas-based renderer. |
| Page thumbnails | ✅ | ✅ | MATCHED ✅ | `GET /api/viewer/thumb/{token}/{page}`. |
| Table of contents | ✅ | ✅ | MATCHED ✅ | TOC sidecar with page fallback. |
| Zoom + fit modes | ✅ | ✅ | MATCHED ✅ | Pinch-to-zoom + button zoom + fit-width/fit-page. |
| Text search in document | ✅ | ✅ | MATCHED ✅ | Search panel confirmed. |
| Viewer annotations | ❌ | ✅ | **AHEAD ★** | SecureDoc allows viewer annotations with threading. DocSend does not have this natively. |
| Link extraction panel | ❌ | ✅ | **AHEAD ★** | LinksPanel shows all hyperlinks in PDF by page. DocSend lacks this. |
| Dynamic watermark (per-viewer) | ✅ | ✅ | MATCHED ✅ | Per-session watermark: email + timestamp + session_id prefix. |
| Forensic steganographic watermark | ❌ | ✅ | **AHEAD ★** | `apply_viewer_forensic_stamp` — invisible watermark per session. DocSend has visible watermark only. |
| Watermark angle randomization per session | ❌ | ✅ | **AHEAD ★** | SHA-256 of session_id determines angle — unique per viewer. |

### Access Control — Advanced

| Feature | DocSend | SecureDoc | Status | Notes |
|---|---|---|---|---|
| Domain-restricted links | ✅ | ✅ | MATCHED ✅ | `allowed_domains` comma-separated. |
| IP allowlist per link | ❌ | ✅ | **AHEAD ★** | `ip_allowlist` per share link. DocSend lacks this. |
| Max concurrent sessions per link | ❌ | ✅ | **AHEAD ★** | `max_concurrent_sessions` — prevents credential sharing. DocSend lacks this. |
| Right-click disable | ❌ | ✅ | **AHEAD ★** | `can_right_click` toggle. DocSend does not expose this. |
| Document embedding (iframe) | ✅ | ✅ | MATCHED ✅ | Embed code generated for iframes. |

### Developer / Integration Features

| Feature | DocSend | SecureDoc | Status | Notes |
|---|---|---|---|---|
| API access | ✅ | 🔒 | BEHIND 🔒 | API key backend complete, no frontend, no documentation. |
| Webhooks | ✅ | 🔒 | BEHIND 🔒 | Webhook backend complete, no frontend. link.viewed missing. |
| Zapier integration | ✅ | ❌ | BEHIND ❌ | Not built. |

### Team / Organization Features

| Feature | DocSend | SecureDoc | Status | Notes |
|---|---|---|---|---|
| Team workspaces | ✅ | 🔒 | BEHIND 🔒 | Organizations backend complete, no frontend. UUID-only member add blocks UX. |
| Role-based access (viewer/editor/admin) | ✅ | 🔒 | BEHIND 🔒 | 4-tier RBAC built. No frontend. |
| Custom domain branding | ✅ | 🔒 | BEHIND 🔒 | DNS TXT verification built. No frontend. |
| Team analytics | ✅ | 🔒 | BEHIND 🔒 | Per-group analytics exists. No org-scoped view in frontend. |

### Billing / Plans

| Feature | DocSend | SecureDoc | Status | Notes |
|---|---|---|---|---|
| Free tier | ✅ | ✅ | MATCHED ✅ | PLAN_FREE default. |
| Paid upgrade (Stripe) | ✅ | ✅ | MATCHED ✅ | Stripe Checkout + webhook lifecycle. |
| Subscription management | ✅ | ✅ | MATCHED ✅ | Stripe Customer Portal. |

---

## Competitive Scorecard vs. DocSend

| Category | DocSend | SecureDoc | Gap |
|---|---|---|---|
| Core sharing | 10/10 | 7/10 | New Link broken, no real-time notification |
| Analytics | 9/10 | 6/10 | Range filtering broken, CSV export broken |
| Notifications | 10/10 | 1/10 | No email notification, SSE/webhook not wired |
| Viewer experience | 8/10 | 10/10 | SecureDoc AHEAD on annotations, links, forensic watermark |
| Access control | 8/10 | 10/10 | SecureDoc AHEAD on IP allowlist, concurrent session limit, right-click |
| Developer / API | 8/10 | 2/10 | API keys and webhooks invisible to users |
| Team features | 9/10 | 1/10 | Organizations backend complete but not exposed |
| **Overall** | **~88%** | **~53%** | **35-point gap** |

---

## SecureDoc's Unique Advantages (things competitors don't have)

1. **Forensic steganographic watermark** — per-session invisible watermark baked into pages. No DocSend equivalent.
2. **IP allowlist per share link** — restrict which IP addresses can access a document. No DocSend equivalent at per-link granularity.
3. **Max concurrent sessions per link** — prevent credential sharing (link shared across multiple devices). No DocSend equivalent.
4. **Viewer annotations with threading** — viewers can annotate and discuss directly on the document. DocSend offers feedback forms only.
5. **Hyperlink panel (LinksPanel)** — extracts and presents all hyperlinks from a PDF by page. No DocSend equivalent.

These 5 advantages represent genuine enterprise security differentiation. They should be prominently featured in product marketing.

---

## Critical Gaps to Close Before Competitive Parity

### P0 — Fix before any marketing:
1. **UI-002: New Link button is broken** — the foundational workflow of the product does not work end-to-end
2. **SEC-006: link.viewed event not dispatched** — the core value proposition ("know when your doc is viewed") is silent

### P1 — Fix to match DocSend baseline:
3. **Real-time notification on document open** — requires SEC-006 fix + SSE frontend wiring
4. **Analytics range filtering** — UI-004
5. **CSV export** — UI-005

### P2 — Unlock locked value:
6. **API keys UI** — unlocks developer market
7. **Webhooks UI** — unlocks integration market
8. **Organizations UI** — unlocks team/enterprise market

### P3 — Long-term:
9. **Email notifications** — high-frequency customer request
10. **Zapier/n8n integration** — needs API key + webhook first
