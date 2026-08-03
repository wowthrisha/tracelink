# Security Hardening Plan — AUTH-006: Session Token Storage

**Status**: Planned, not implemented this sprint (see §7 for why)
**Owner**: TBD
**Related**: `ENGINEERING_TRIAGE.md` (AUTH-006), `VERIFIED_ISSUES.md`

---

## 1. Problem statement

The SPA session token is stored in `localStorage` and attached to every request as an `Authorization: Bearer` header:

- `frontend/src/screens/LoginScreen.jsx:51` — `localStorage.setItem('securedoc_token', token)` on successful login/signup.
- `frontend/api.js:26-31` — `authHeaders()` reads the same key and adds `Authorization: Bearer <token>` to requests.
- **60 call sites** in `frontend/api.js` spread the token via `authHeaders()`.

Any script that runs in the page's origin (via XSS, a compromised dependency, a malicious browser extension, etc.) can read `localStorage` synchronously and exfiltrate the token — no additional exploitation step needed. A cookie marked `httpOnly` is invisible to JavaScript and closes that specific exfiltration path.

This is real and reproducible against current source (confirmed in `ENGINEERING_TRIAGE.md`), and is the single highest-severity confirmed finding from this audit cycle.

---

## 2. Current architecture (baseline)

| Layer | Current behavior |
|---|---|
| Token acquisition | `LoginScreen.jsx` calls Supabase directly (`/auth/v1/token`) or the backend's `/api/auth/register`, gets a JWT access token back, stores it in `localStorage`. |
| Token transport | Every authenticated request sends `Authorization: Bearer <jwt>` via `authHeaders()` in `api.js` (60 call sites). |
| Token verification | `backend/app/auth.py:get_current_user` reads the `Authorization` header, dispatches to `verify_supabase_token` (JWT/JWKS) or `verify_api_key` (for `sd_...` API keys). |
| Backend consumers | **72** `Depends(get_current_user)` / `Depends(require_scope(...))` call sites across **13** router files (`documents`, `links`, `groups`, `orgs`, `analytics`, `reading`, `storage`, `billing`, `webhooks`, `api_keys`, `annotations`, `notifications`, `admin`). |
| Refresh | **None.** There is no `refresh_token` handling anywhere in the frontend — when the access token expires, requests start 401ing and `_clearAndReload()` forces a full re-login. |
| CORS | `backend/app/main.py:195-210` — dev mode uses `allow_origins=["*"], allow_credentials=False` (the code comment explicitly notes this is because "Bearer token auth doesn't need allow_credentials=True"). **A wildcard origin is incompatible with cookies** — browsers refuse to send/accept cookies cross-origin unless `allow_credentials=True` and the origin is an explicit value, never `*`. Production mode already sets `allow_credentials=True` with an explicit origin list, so only dev config needs to change. |
| API keys | Programmatic (non-browser) clients authenticate with `X-API-Key` or `Authorization: Bearer sd_...` — this path is orthogonal to the session-cookie problem and must not change. |

**Blast radius if migrated naively**: 60 frontend call sites + 72 backend dependency sites + CORS config + login/signup/reset flows + logout + every integration test that currently constructs `Authorization` headers directly (a `grep` of `backend/tests` shows the same header pattern used pervasively in test fixtures).

---

## 3. Target architecture

- **Session cookie**: on successful login/signup, the backend sets a `Set-Cookie: sd_session=<jwt>; HttpOnly; Secure; SameSite=Lax; Path=/` header instead of (or alongside, during transition — see §4) returning the token in the JSON body for the SPA to store.
- **CSRF protection**: cookie-based auth is vulnerable to CSRF (the browser attaches cookies automatically to cross-site requests), which Bearer-header auth was implicitly immune to. Mitigate with a double-submit CSRF token: a non-httpOnly `sd_csrf` cookie whose value the frontend must echo back in an `X-CSRF-Token` header on all state-changing (`POST`/`PATCH`/`PUT`/`DELETE`) requests; the backend middleware verifies the two match. `SameSite=Lax` alone blocks most cross-site POST forgery but a same-origin subdomain or a `<form>` GET-triggered mutation isn't fully covered by `SameSite` alone, so a real CSRF token is the safer baseline given this app handles document deletion/sharing.
- **Backend auth dependency**: `get_current_user` gains a cookie-reading path (`request.cookies.get('sd_session')`) that runs *before* falling back to the `Authorization` header, so existing API-key and any legitimate Bearer-JWT programmatic consumers keep working unchanged.
- **Frontend**: `api.js` stops reading/writing `localStorage` for the session token entirely; `fetch` calls add `credentials: 'include'`; `authHeaders()` is deleted (or reduced to a no-op) since the browser now handles the cookie automatically.
- **Logout**: backend gains a `POST /api/auth/logout` that clears the cookie server-side (`Set-Cookie` with `Max-Age=0`) — currently logout is purely client-side (`localStorage.removeItem`), which is insufficient for a cookie-based session.
- **API keys**: entirely unaffected — `X-API-Key` / `Authorization: Bearer sd_...` continues to work exactly as today for CLI/integration use, since those are not the browser session flow this plan changes.

---

## 4. Migration strategy — phased, not a single cutover

A single-PR flip of all 60+72 call sites is exactly the kind of change the remediation brief told me to avoid ("don't rewrite working code," "preserve backward compatibility," "no half-finished implementations"). Proposed phases:

**Phase 0 — CORS & backend dual-read (no frontend behavior change)**
- Fix dev CORS to `allow_credentials=True` with explicit origins (drop the `*` wildcard in dev too — this was already correct for prod).
- Add cookie-setting to login/signup responses **in addition to** the existing JSON `access_token` body (frontend ignores the cookie for now).
- Add cookie-reading to `get_current_user`, tried *after* the existing header check so nothing currently working changes.
- Ship, verify via existing test suite + a manual smoke pass, no visible behavior change.

**Phase 1 — Frontend cutover**
- Switch `api.js` to `credentials: 'include'` on all requests.
- Stop storing the token in `localStorage`; stop sending `Authorization` from the SPA.
- Implement the CSRF double-submit token on all mutating calls.
- Implement `POST /api/auth/logout`.
- This is the phase that actually touches all 60 `api.js` call sites — mechanical (add `credentials: 'include'`, remove `...authHeaders()`) but wide, so it should land as its own reviewed PR, ideally behind a runtime flag (e.g. a `?cookie_auth=1` query param or environment flag) so it can be toggled off instantly if something regresses in production.

**Phase 2 — Backend header-path deprecation (browser flow only)**
- Once Phase 1 is stable in production for a full session-TTL cycle (so no lingering `localStorage` tokens are still active anywhere), remove the JSON `access_token` from login/signup responses for the SPA flow and drop the now-unused header-check branch *for JWT* — but keep the API-key header path forever, since that's a distinct, intentional integration surface.

**Phase 3 (stretch, optional) — real refresh-token flow**
- Since this touches the same login/session code, this is a natural point to also add the currently-missing refresh-token handling (short-lived access cookie + longer-lived refresh cookie + a `/api/auth/refresh` endpoint), fixing the "session dies without warning" gap noted in AUTH-007's surrounding investigation. Not required for AUTH-006 itself — flagging as a bundled opportunity, not scope creep into this plan's execution.

---

## 5. Compatibility considerations

- **API keys / CLI / integrations**: zero impact — different auth path, untouched.
- **Existing frontend sessions at deploy time**: users with a token already in `localStorage` will keep working through Phase 0–1 (header path stays live until Phase 2), so no forced logout on deploy.
- **CORS**: any current or future non-cookie consumer of the API from a browser context (if one exists outside this SPA) would need `credentials: 'include'` added too, or it should stay on the API-key path — worth an inventory check before Phase 1 ships.
- **Load balancers / CDN / Cloudflare tunnel** (per `frontend/api.js` comments, production is fronted by a Cloudflare tunnel): confirm the tunnel forwards `Set-Cookie` and cookie headers unmodified, and that `Secure` cookies work correctly behind it (should be fine over HTTPS, but worth an explicit staging check).
- **Backend test suite**: the ~72 call sites' tests construct `Authorization` headers directly; those keep passing unchanged through Phase 0–1 since the header path isn't removed until Phase 2. Phase 2 needs its own test-fixture update pass.

---

## 6. Rollout plan

1. Phase 0 to staging → full regression suite → production, dark (no frontend change yet).
2. Phase 1 behind a flag, enabled first in staging, then production for internal/test accounts only, monitored for 401 spikes / CSRF rejections / login failures for at least one full business day.
3. Flip the flag on for all production traffic; keep the flag wired (not deleted) for at least one release cycle in case of rollback need.
4. Only after a full clean cycle with the flag on, proceed to Phase 2 removal of the JSON-token / header path for the browser flow.
5. Each phase gets its own PR, its own entry in `FIX_LOG.md`, and its own regression run — not bundled into one giant diff.

---

## 7. Regression checklist (per phase)

- [ ] Login (email/password), signup, forgot-password, reset-password flows all succeed
- [ ] Every existing frontend integration/unit test still passes
- [ ] Full backend suite (`pytest tests/unit tests/integration tests/regression`) passes
- [ ] API key auth (`X-API-Key` and `Authorization: Bearer sd_...`) unaffected — dedicated test pass
- [ ] CSRF token correctly blocks a forged cross-origin mutating request (add a new regression test for this)
- [ ] CSRF token correctly allows legitimate same-origin mutating requests (upload, delete, revoke, org actions)
- [ ] Logout actually invalidates the server-side cookie (not just client-side clear)
- [ ] 401 handling (`_clearAndReload()` pattern) still triggers correctly on expired/invalid session
- [ ] CORS: staging smoke test from the actual deployed origin, not just `localhost`
- [ ] No token value appears in browser dev tools' Application → Local Storage after Phase 1
- [ ] No regression in the viewer's public (unauthenticated, link-token-based) flow, which uses `X-Session-ID`, not user auth, and is untouched by this plan

---

## 8. Effort estimate

| Phase | Size | Rough estimate |
|---|---|---|
| 0 — CORS + dual-read backend | Small–medium, backend only | 0.5–1 day incl. tests |
| 1 — Frontend cutover + CSRF + logout endpoint | Large, cross-cutting (60 call sites, all auth screens) | 2–4 days incl. regression pass and flagged rollout monitoring |
| 2 — Header-path deprecation | Small | 0.5 day, gated on a full clean production cycle after Phase 1 |
| 3 — Refresh tokens (optional/stretch) | Medium | 1–2 days, separate initiative |

**Why this isn't done in this sprint**: it fails the brief's own "smallest correct fix" and "don't change APIs unnecessarily" tests — this is an authentication-mechanism change (adds CSRF handling, changes CORS credential semantics, changes what every one of 72 backend routes and 60 frontend call sites relies on for identity) that needs a dedicated review and a flagged, monitored rollout, not a same-session mechanical patch alongside seven unrelated UI fixes. Recommend scheduling Phase 0–1 as its own tracked piece of work.
