# SecureDoc — Release Blockers

Generated: 2026-06-08  
Audit: 9-phase pre-pilot audit (18 agents, 689 tool uses)

---

## P0 — Must Fix Before Pilot

| # | Area | Issue | File(s) |
|---|------|-------|---------|
| P0-1 | **DB / Migration** | Migration 020 re-creates `ix_organizations_slug` which already exists from migration 016 — crashes every fresh deployment with `DuplicateTableError`. **FIXED in this commit.** | `alembic/versions/020_add_performance_indexes.py` |
| P0-2 | **Git / Secrets** | `TRACEVIEW_AUDIT_B.md` tracked at HEAD in a **public** repo contains the live Supabase anon key (`sb_publishable_uTcTOZC9FjEP0VrGQefMkQ_j2XFe1Rc`) and project URL. Must be removed from tracking and history scrubbed. | `TRACEVIEW_AUDIT_B.md` |
| P0-3 | **Git / Secrets** | Same Supabase credentials appear in 3 historical commits (`ffac077`, `704ca80`, `cc50838`) in the public repo — treat key as compromised and rotate via Supabase dashboard. | git history |
| P0-4 | **Auth / Config** | Empty `SUPABASE_URL` causes complete auth blackout with no user-facing error — JWKS fetch silently fails, every API call returns 401, dev-mode startup check is skipped. | `app/main.py`, `frontend/api.js` |
| P0-5 | **Storage / Config** | Unconfigured storage credentials cause silent upload failure — documents stuck in `error` state forever, user sees generic toast with no hint it's a config issue. | `app/config.py`, `app/workers/celery_app.py` |
| P0-6 | **Auth / UX** | No forgot-password flow — pilot users who mistype or forget their password are permanently locked out with zero recovery path in the frontend. | `frontend/src/app.jsx` |
| P0-7 | **Org Workflow** | `doc.org_id` is always NULL after upload — no `org_id` field on upload form and no PATCH endpoint to assign a document to an org. The entire org document-sharing workflow is architecturally unreachable. | `app/routers/documents.py` |
| P0-8 | **Security** | DNS rebinding TOCTOU on webhook delivery — `validate_ssrf_url()` runs at registration time only; `webhook_tasks.py` calls `httpx.Client().post(url)` with zero SSRF re-validation at delivery time. | `app/workers/webhook_tasks.py` |

---

## P1 — Fix Soon (before public launch)

| # | Area | Issue |
|---|------|-------|
| P1-1 | Security | Scope enforcement gap: `billing.py`, `groups.py`, `notifications.py`, `orgs.py`, `admin.py` use only `get_current_user` — any valid API key bypasses scope gating on these routers |
| P1-2 | Git | 22 modified tracked files unstaged — deployed HEAD differs from running code (includes `auth.py`, `viewer.py`, `links.py`, `config.py`, and 18 other files) |
| P1-3 | Git | 34 untracked functional source files — fresh clone produces `ImportError` on startup (new routers, models, migrations, services are not committed) |
| P1-4 | Frontend | Organizations and RBAC have zero frontend UI — no org creation, member management, or role controls in `app.jsx` or `api.js` |
| P1-5 | UX | Dead "Filter" button fires "Search feature coming soon" toast next to a working search input |
| P1-6 | UX | Silent `_clearAndReload()` on 401 destroys unsaved in-progress work without warning; no JWT refresh logic |
| P1-7 | UX | No email verification state or resend-confirmation button after signup |
| P1-8 | UX | Quota 403 has no upgrade CTA; Billing screen shows "not configured" when Stripe is absent |
| P1-9 | UX | Processing gate tells external viewers to "wait and refresh" with no refresh button and no auto-retry |
| P1-10 | Tests | `app/utils/ssrf_guard.py` has zero dedicated unit tests despite being security-critical |
| P1-11 | Tests | `require_scope()` route-level enforcement has no tests verifying 403 when scope is missing |
| P1-12 | Tests | `test_sse_stream_endpoint_requires_auth` is a fake test — body is `with patch(...): pass` with no assertions |

---

## P2 — Nice To Have

| # | Area | Issue |
|---|------|-------|
| P2-1 | Bug | Copy button writes stub string `'Text copied from SecureDoc'` instead of actual content |
| P2-2 | Bug | Retry button visible on actively-processing documents, risks spawning duplicate Celery tasks |
| P2-3 | Security | `IP_HASH_SALT` mismatch between `config.py` default and `.env.example` value — startup guard bypassed by deployers who copy `.env.example` verbatim |
| P2-4 | Config | `ALLOWED_ORIGINS` in `.env.example` defaults to localhost — CORS blocks pilot domain in production |
| P2-5 | Security | `alembic.ini` has hardcoded plaintext password in `sqlalchemy.url` |
| P2-6 | UX | No onboarding context on login screen for first-time pilot invitees |
| P2-7 | UX | No Supabase redirect callback handler after email confirmation |
| P2-8 | Tests | Metrics endpoint has no test for token-protected path (valid/invalid token) |
| P2-9 | Tests | `apply_viewer_forensic_stamp` has no unit test in `test_watermark.py` |
| P2-10 | Ops | 20 silent `except Exception: pass` swallows in production paths mask operational errors |
| P2-11 | Ops | SSE `_active_connections` counter is process-local — per-user cap not enforced across multiple uvicorn workers |
| P2-12 | Ops | No per-user API key count cap (webhooks cap at 20, API keys uncapped) |
| P2-13 | Cleanup | Stray files `200`, `404`, and 4 SQLite `*.db` files at repo root |
| P2-14 | Cleanup | 20 `ACTION_*_DESIGN.md` + audit reports cluttering repo root and not gitignored |
| P2-15 | Schema | Dual index on `documents.user_id`: `idx_documents_user_id` (migration 003) and `ix_documents_user_id` (migration 007) — redundant index wastes space |
| P2-16 | Admin | Audit log `GET` response omits `details_json` — admins cannot see what changed in an event |
