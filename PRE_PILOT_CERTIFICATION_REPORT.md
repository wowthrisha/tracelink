# SecureDoc — Pre-Pilot Certification Report

**Date:** 2026-06-08  
**Auditor:** Automated 9-phase audit (18 agents, 689 tool uses, 1.5M tokens)  
**Repo:** `wowthrisha/tracelink` (public)  
**Commit audited:** pre-push working tree  

---

## Scorecard

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Repository Cleanliness | **2 / 10** | 34 untracked functional files, 22 modified tracked files unstaged, live Supabase key committed at HEAD in a public repo, stray `200`/`404` files, 4 test DBs at root |
| Code Quality | **4 / 10** | 20 silent `except Exception: pass` swallows in production paths, dead stub (Copy button), dead UI button (Filter), no token refresh, viewer.py at 1016 lines |
| Feature Completeness | **4 / 10** | 8 of 18 features PARTIAL or BROKEN; Organizations/RBAC/API Keys/Webhooks/Notifications/Custom Domains have zero frontend UI; org document assignment is architecturally impossible |
| Security | **5 / 10** | SSRF protection present but DNS rebinding TOCTOU at delivery; scope enforcement missing on 5 routers; Supabase key live in public git history; IP hash salt mismatch between config and .env.example |
| Pilot Readiness | **2 / 10** | 3 auth/config P0s mean a demo user with no prior knowledge cannot sign up, cannot upload, and cannot recover a lost password without developer intervention |

---

## Feature Classification

| Feature | Status | Notes |
|---------|--------|-------|
| Documents | **COMPLETE** | Full CRUD, quota gating, org-scoped visibility, version CTE, 30+ tests |
| Links | **COMPLETE** | PATCH cache invalidation, password_hash never serialized, email allowlist lowercase |
| Viewer | **COMPLETE** | Bytes proxied (never redirect), session from header/cookie only, watermark in executor |
| Analytics | **COMPLETE** | VIEWER_LOGGABLE_EVENTS restriction, PII protected, user isolation, 20 tests |
| Watermarking | **COMPLETE** | Visible + dual forensic stamps, session-unique angle, executor-offloaded |
| Downloads | **COMPLETE** | Streaming O(1)-RAM PDF, permission-gated, temp file cleanup, frontend wired |
| PPTX | **PARTIAL** | Worker pipeline exists but untracked (git); no frontend upload UI for PPTX |
| XLSX | **PARTIAL** | Same as PPTX — untracked file; adapter bytes tests only |
| Organizations | **PARTIAL** | Backend fully implemented (models, migrations, CRUD, 52 tests); **zero frontend UI** |
| RBAC | **PARTIAL** | Backend role hierarchy complete; **zero frontend UI**; no `require_scope` on org routes |
| Audit Logs | **COMPLETE** | All 11 event types fire; fire-and-forget service; `details_json` omitted from response (minor) |
| API Keys | **PARTIAL** | Backend complete (SHA-256, scopes, audit); **zero frontend UI**; no per-user count cap |
| Webhooks | **PARTIAL** | SSRF guard + HMAC signing + retry; **DNS rebinding TOCTOU at delivery**; no frontend UI |
| Notifications | **PARTIAL** | SSE + Redis pub/sub + idle timeout; **fake test**; no frontend UI; process-local cap |
| Custom Domains | **PARTIAL** | Backend DNS verification + share URL generation; **zero frontend UI** |
| Layout Modes | **COMPLETE** | FIT_WIDTH / FIT_HEIGHT / CUSTOM, localStorage persistence, toggle buttons |
| Zoom Controls | **COMPLETE** | Keyboard + Ctrl+wheel + pinch-to-zoom + presets, clamped to [10, 400] |
| Session Management | **COMPLETE** | 128-bit ID, header/cookie only, 120-min inactivity, Beat purge every 30 min |

---

## E2E Journey Results

| Journey | Status | Blocker |
|---------|--------|---------|
| A: Upload → Link → View → Download → Analytics | **INTACT** | — |
| B: Org → Invite → Role → Upload doc → Share | **BROKEN** | `doc.org_id` always NULL; no upload form field; no PATCH to assign |
| C: API Key → Use → Scope check → Denial | **COMPLETE** (backend only) | No frontend UI |
| D: Webhook → Events → Signatures → Retries | **COMPLETE** (backend only) | DNS rebinding TOCTOU at delivery |
| E: Fit Width → Fit Height → Custom Zoom → Refresh | **INTACT** | — |

---

## Security Controls

| Control | Status | Notes |
|---------|--------|-------|
| SSRF protection | **PARTIAL** | Active at registration; DNS rebinding TOCTOU at delivery (webhook_tasks.py) |
| Scope enforcement | **PARTIAL** | Active on documents/links/analytics/webhooks; missing on billing/groups/notifications/orgs/admin |
| Session validation | **ACTIVE** | Header/cookie only, DB-validated, inactivity window enforced |
| Metrics protection | **ACTIVE** | Bearer token or IP allowlist; config trap if both set to empty |
| Security headers | **ACTIVE** | CSP (no unsafe-eval), HSTS, X-Frame-Options: DENY, Referrer-Policy |
| Audit logging | **ACTIVE** | All 11 event types confirmed firing |
| IP hashing | **ACTIVE** | HMAC-SHA256, production enforces non-default salt |
| Password hash leakage | **ACTIVE** | Never serialized in any response |

---

## Top Deployment Risks (Ranked)

1. **Live Supabase key in public git history and at HEAD** — treat as compromised; rotate immediately
2. **Migration 020 crash on fresh install** — FIXED in this commit
3. **34 untracked files** — fresh clone produces ImportError; commit all functional files
4. **DNS rebinding TOCTOU** — webhook delivery makes outbound HTTP with no SSRF re-validation
5. **No forgot-password** — pilot users permanently locked out on credential loss
6. **Org document assignment missing** — entire org collaboration workflow is unreachable

---

## Verdict

```
╔══════════════════════════════════════════════╗
║                                              ║
║              VERDICT:  FAIL                  ║
║                                              ║
╚══════════════════════════════════════════════╝
```

**I would not allow 50 external pilot users onto this system today.**

### Exact Blockers

1. **Real Supabase key live in public repo** (HEAD file + 3 commits in history) — any pilot user who clones the repo can extract production credentials
2. **Migration 020 crashes every fresh deployment** — fixed here, but must be the first commit that goes out
3. **34 untracked source files** — any deploy from a fresh clone fails with `ImportError` before the app starts
4. **No auth recovery path** — users who forget passwords have zero self-service option
5. **Org document sharing broken by design** — `doc.org_id` can never be set through any existing API; the flagship enterprise feature is dead in practice
6. **DNS rebinding TOCTOU** — low-exploitability but live: an attacker can use a registered webhook to reach internal Railway/AWS metadata services after DNS flip

### Path to PASS

1. Remove `TRACEVIEW_AUDIT_B.md` from git tracking; rotate Supabase anon key; scrub git history
2. Stage and commit all 34 untracked functional files
3. Stage and commit all 22 modified tracked files  
4. Add `org_id` Form field to `POST /api/documents/upload` or add `PATCH /api/documents/{id}` endpoint
5. Add forgot-password flow (Supabase `/auth/v1/recover` is one API call + one frontend form)
6. Add `validate_ssrf_url(ep.url)` before `httpx.Client().post()` in `webhook_tasks.py`
7. Re-run this audit; target all P0s resolved before pilot
