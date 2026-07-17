# Engineering Triage — TraceLink / SecureDoc Product Audit

**Source artifacts**: `~/Downloads/TraceLink_Product_Audit/` (ISSUE_DATABASE.md, PRODUCT_REVIEW.md, SECURITY_REVIEW.md, SESSION_PAUSED.md, STATE.json, CHECKPOINT.json, WORKFLOW_STATUS.json, SCREENSHOT_MANIFEST.json, Screenshots/)
**Repo**: `/Users/thrisha/traceview/securedoc` (working tree, branch `main`)
**Triage date**: 2026-07-17

---

## 0. Evidence-integrity finding (read this before the table)

Before triaging individual issues, I cross-checked the audit's own bookkeeping against its claimed findings, because the task brief states "the browser audit has already been completed." **That premise does not hold up:**

| Check | Result |
|---|---|
| `WORKFLOW_STATUS.json` / `CHECKPOINT.json` / `STATE.json` | All workflows except Login are `not_started`, `steps_completed: 0`. `current_progress_percent: 10`. `completed_screens: ["login"]`. 13 of 14 screens listed as `remaining_screens`. |
| `SESSION_PAUSED.md` | States explicitly: session paused 2026-07-14 on **browser-quota exhaustion**, before Dashboard *interactions* were tested, and before Viewer, Access Control, Feedback, Analytics, Storage, API Keys, Webhooks, Audit Log, Organizations, Notifications, Billing, or Profile were opened at all. |
| `SCREENSHOT_MANIFEST.json` + `find Screenshots/` | **25 screenshot/recording files total, all under `Screenshots/Desktop/` and `Screenshots/dashboard/`.** Zero screenshots exist for any of the other 12 screens. |
| `CHECKPOINT.json.buttons_tested` | `["Login Tab", "Signup Tab", "Sign In Button", "Create Account Button"]` — no dashboard button, dropdown, modal, or upload interaction was ever clicked. |
| `ISSUE_DATABASE.md` (top-level, dated 3 days *after* the pause) | Lists **47 issues across all 14 screens**, including the 12 that were never opened, each with a `Source:` citation. |

The `Source:` citations for the untested screens (e.g. `wn component`, `zn component`, `bn component`, `gn component`, `hn component`, `uo empty state component`, `Vi navigation config`, `l.slice(0, 5)`) are minified single/two-letter identifiers. I confirmed these exist verbatim in `frontend/dist/app.bundle.js` (`grep "function zn(" frontend/dist/app.bundle.js` → match). This is **static inspection of the built bundle**, not browser observation — the exact evidence class this mission brief says not to use, and not something a paused browser session could have produced.

I spot-checked three of these "untested-screen" findings against the actual current source (not the bundle) to see whether they're even directionally correct:

- **ORG-001** ("deleteOrg fires directly with no cascade warning") — false. `frontend/src/screens/OrgsScreen.jsx:355-367` shows a confirmation `Modal` with explicit text ("will permanently remove the organization and all its settings. Members will lose access.") gating a danger-styled button before `deleteOrg` is ever called.
- **AUDIT-001** ("Audit log accessible to all users") — false. `backend/app/routers/admin.py:45-50` enforces `role_gte(membership.role, "admin")` and returns 403 with `"Requires admin role or higher"` otherwise.
- **ACCESS-006** ("no warning when creating an unprotected link") — false. `frontend/src/screens/AccessScreen.jsx:807-808` renders exactly this warning: *"This creates a link with no restrictions. Anyone with the link can view the document..."*

Three-for-three of the spot-checks I ran on the un-browser-tested portion of the database turned out to describe behavior that is either absent or the opposite of what's implemented. That's not enough to clear every remaining item in that bucket, but it is enough to say the bucket as a whole cannot be trusted as "verified," and implementing fixes against it risks patching problems that don't exist. Full reasoning per issue is in the table below.

**Net effect on classification**: issues on Login and the partially-reviewed Dashboard layout get real (if partial) evidentiary weight. Issues on the other 12 screens are treated as unverified claims requiring either a fresh, real browser pass or direct source confirmation — which I did selectively where cheap and noted below.

---

## 1. Classification table

Legend: **VERIFIED** (reproducible now, confirmed against current source/screenshot) · **NOT REPRODUCIBLE** (checked against current source, behavior does not match the claim) · **INSUFFICIENT EVIDENCE** (no screenshot/interaction evidence, and a quick source check was inconclusive or not attempted) · **EXPECTED BEHAVIOUR** (real, but working as intended / not a defect) · **NEEDS BROWSER RECHECK** (claim rests on an untested screen and/or bundle-derived evidence)

### Login (AUTH-*) — screenshots + form interaction evidence exists

| ID | Sev | Verdict | Reasoning |
|---|---|---|---|
| AUTH-001 | 🟡 | **VERIFIED** | `frontend/src/screens/LoginScreen.jsx:152-172` — signup password field has no requirements hint; error surfaces only from the server catch block. Matches `04_validation_check.png`. |
| AUTH-002 | 🟢 | **VERIFIED** | `LoginScreen.jsx:166` — `type="password"`, no visibility-toggle control anywhere in the file. Matches `01_login_page.png`. |
| AUTH-003 | 🟢 | **EXPECTED BEHAVIOUR** | No OAuth buttons in `LoginScreen.jsx`, confirmed. But SecureDoc is positioned as a security-first doc-sharing product; deliberately keeping the auth surface to email/password (no third-party OAuth) is a defensible, common security posture, not an omission. Treat as a product decision, not a bug — no fix warranted absent a product ask. |
| AUTH-004 | 🟢 | **VERIFIED** | No ToS/Privacy link in the signup branch of `LoginScreen.jsx`. Real, low-risk legal/copy gap. |
| AUTH-005 | 🟡 | **EXPECTED BEHAVIOUR** | `frontend/SecureDoc.html:9` — `<meta name="supabase-anon-key">` confirmed present. This is a mischaracterization: Supabase's anon/public key is *designed* to be shipped to the client (equivalent to a Firebase web config) — it carries no privileged access on its own; row-level security enforces authorization server-side. Flagging this as a security defect reflects a misunderstanding of the Supabase auth model. No fix needed. |
| AUTH-006 | 🔴 | **VERIFIED** | `LoginScreen.jsx:51` — `localStorage.setItem('securedoc_token', token)`; `frontend/api.js:26-31` reads the same key for every `Authorization: Bearer` header. Real XSS-exfiltration exposure. **However**: see §2 — this is not a "smallest correct fix," it's an auth-architecture change touching every API call in `api.js`, CORS, and the backend session/auth layer. Flagging for a scoping decision rather than folding into a mechanical patch. |
| AUTH-007 | 🟡 | **VERIFIED** | `LoginScreen.jsx:53-64` — the catch block only special-cases `confirm`/`expired`/`invalid`/`otp`/`token` substrings; a raw `TypeError: Failed to fetch` (network/DNS failure) falls through to `setError(msg)` verbatim. Matches `03_login_failed.png`. |

### Dashboard (DASH-*) — layout screenshots exist; **zero interactions were tested** (`buttons_tested` confirms no dashboard control was ever clicked)

| ID | Sev | Verdict | Reasoning |
|---|---|---|---|
| DASH-001 | 🟡 | **VERIFIED** | Visible directly in `dashboard_desktop_1440.png`; a static page title, confirmable from the screenshot alone. |
| DASH-002 | 🟡 | **NEEDS BROWSER RECHECK** | Behavioral claim ("cards are static, cursor:default") cited to bundle component `vn` — no click-test exists to confirm cards aren't wired to anything. |
| DASH-003 | 🟡 | **VERIFIED** | Visible directly in `dashboard_desktop_1440.png` — the notice is a small line at the page bottom. |
| DASH-004 | 🟢 | **INSUFFICIENT EVIDENCE** | Requires seeing the empty state actually rendered; no screenshot shows it and I did not locate the exact empty-state copy in the current upload screen source in the time available. |
| DASH-005 | 🟢 | **NEEDS BROWSER RECHECK** | Behavioral/timing claim (toast auto-dismiss) cited to bundle component `zn`; upload flow was never exercised. |
| DASH-006 | 🟢 | **NEEDS BROWSER RECHECK** | Accessibility claim (`opacity:0` until hover) cited to bundle component `bn`; no keyboard-focus testing occurred. Worth a real recheck — this is a legitimate accessibility pattern to worry about if true, just not evidenced yet. |
| DASH-007 | 🟡 | **NEEDS BROWSER RECHECK** | Claim that Quick Share creates a link "on mount" cited to bundle component `wn`; no click-test exists. |
| DASH-008 | 🟢 | **VERIFIED** | Visible directly in `dashboard_desktop_1440.png`. |
| DASH-009 | 🔴 | **NEEDS BROWSER RECHECK** | High-severity claim about upload-limit warnings, but `SESSION_PAUSED.md` explicitly lists "Upload flow (file upload, size limits, type validation)" as **not started**. A 🔴-severity item with no supporting interaction evidence is exactly the pattern that turned out to be fabricated in the ORG-001/AUDIT-001/ACCESS-006 spot-checks below. |

### Every other screen (VIEWER-*, ACCESS-*, FEED-*, ANAL-*, STOR-*, APIKEY-*, WEBHOOK-*, AUDIT-*, ORG-*, BILL-*, PROF-*) — confirmed **not opened** by the audit session (`remaining_screens` in `CHECKPOINT.json`), zero screenshots, all evidence is `Source:` citations to minified bundle identifiers

Default verdict for this whole block is **NEEDS BROWSER RECHECK**, with the following exceptions where a direct source check was cheap enough to run now:

| ID | Sev | Verdict | Reasoning |
|---|---|---|---|
| VIEWER-001 | 🟢 | NEEDS BROWSER RECHECK | Untested screen, bundle-cited (`uo`). |
| VIEWER-002 | 🟡 | NEEDS BROWSER RECHECK | Untested screen, bundle-cited (`uo`). |
| VIEWER-003 | ✅ | **VERIFIED (positive)** | `frontend/api.js:353-355,376-436` — `sessionHeaders()` puts the session id in an `X-Session-ID` header on every viewer call, never in the URL. Confirmed directly in maintained source, not the bundle. No action needed — logging as a confirmed-good control. |
| VIEWER-004 | 🟢 | NEEDS BROWSER RECHECK | Untested screen. |
| VIEWER-005 | 🟡 | NEEDS BROWSER RECHECK | Untested screen, mobile-viewport claim with no mobile screenshots captured. |
| ACCESS-001 | 🟡 | INSUFFICIENT EVIDENCE | Untested screen; could not locate a clear default-permissions constant in the time available. |
| ACCESS-002 | 🟢 | NEEDS BROWSER RECHECK | Untested screen. |
| ACCESS-003 | 🟡 | **EXPECTED BEHAVIOUR** | `/hard` being visible in client JS (`frontend/api.js:302`) is unavoidable — any client-side fetch call necessarily reveals its own endpoint path in the shipped JS; this is true of every REST client and isn't a fixable "implementation detail leak" without hiding all endpoints behind a BFF, which is out of scope for a usability bug fix. |
| ACCESS-004 | 🟢 | NEEDS BROWSER RECHECK | Untested screen. `api.js:556-566` does confirm `getEvents(..., limit=50, offset=0)` is a real, overridable parameter (not hardcoded) — whether the UI ever raises it or paginates needs a real screen check. |
| ACCESS-005 | ✅ | NEEDS BROWSER RECHECK | Positive finding, untested screen — nice to confirm but not actionable either way. |
| ACCESS-006 | 🟡 | **NOT REPRODUCIBLE** | See §0 — the warning already exists in `AccessScreen.jsx:807-808`. |
| FEED-001 | 🟡 | NEEDS BROWSER RECHECK | Untested screen. |
| FEED-002 | 🟢 | NEEDS BROWSER RECHECK | Untested screen. |
| FEED-003 | ✅ | NEEDS BROWSER RECHECK | Positive finding, untested screen. |
| ANAL-001 | 🟡 | NEEDS BROWSER RECHECK | Untested screen, copy claim. |
| ANAL-002 | 🟢 | NEEDS BROWSER RECHECK | Untested screen. |
| ANAL-003 | 🟡 | NEEDS BROWSER RECHECK | Untested screen; fake-sparkline-fallback claim needs direct confirmation before touching analytics rendering. |
| ANAL-004 | 🟡 | NEEDS BROWSER RECHECK | Untested screen, performance claim needs an actual large export to reproduce. |
| ANAL-005 | 🟢 | NEEDS BROWSER RECHECK | Untested screen. |
| ANAL-006 | 🟢 | **VERIFIED** | `frontend/src/screens/AnalyticsScreen.jsx:411` — `groupStats.slice(0, 5)` confirmed directly in maintained source. Real, low severity as originally labeled. |
| STOR-001 | 🟢 | NEEDS BROWSER RECHECK | Untested screen. |
| STOR-002 | 🟢 | NEEDS BROWSER RECHECK | Untested screen. |
| STOR-003 | 🟡 | NEEDS BROWSER RECHECK | Untested screen. |
| APIKEY-001 | 🔴 | **NEEDS BROWSER RECHECK** | `backend/app/routers/api_keys.py` confirms `PATCH /{key_id}` handles deactivation and there's no dedicated `POST /revoke` (there is a dedicated `POST /rotate`, showing the pattern exists elsewhere). The structural fact is true, but it's a defensible REST design (state PATCH), not a broken behavior — same functional outcome. Downgrading from the audit's 🔴 "High" pending a real screen check on whether the UI actually surfaces revoke safely; not a "smallest correct fix" candidate regardless (would mean adding a new backend route for a cosmetic API-shape preference — exactly the "don't change APIs unnecessarily" case the brief warns against). |
| APIKEY-002 | 🟡 | NEEDS BROWSER RECHECK | Untested screen. |
| WEBHOOK-001 | 🟡 | NEEDS BROWSER RECHECK | Untested screen. |
| WEBHOOK-002 | 🟢 | NEEDS BROWSER RECHECK | `api.js:978` confirms `limit=50` is a default parameter, not a hard cap — whether `WebhooksScreen.jsx` ever calls it with a higher limit needs a real check. |
| AUDIT-001 | 🟡 | **NOT REPRODUCIBLE** | See §0 — `backend/app/routers/admin.py:45-50` already enforces an admin-role check with a 403 fallback. |
| ORG-001 | 🔴 | **NOT REPRODUCIBLE** | See §0 — `OrgsScreen.jsx:355-367` already shows a confirmation modal with explicit cascade-impact copy before delete fires. |
| BILL-001 | 🟡 | NEEDS BROWSER RECHECK | Untested screen. |
| BILL-002 | 🟢 | NEEDS BROWSER RECHECK | Untested screen. |
| PROF-001 | 🔴 | **VERIFIED** | `find frontend/src -iname "*profile*"` returns nothing, and `AppShell.jsx` has no nav entry matching "Profile" or "Settings". No in-app profile/password-change screen exists — confirmed directly against maintained source, independent of the bundle or the browser session. |
| PROF-002 | 🟡 | NEEDS BROWSER RECHECK | Same untested screen as PROF-001; account-deletion claim not independently source-checked. |

---

## 2. What this means for implementation

Per the mission's own rule ("Only implement VERIFIED issues... never implement NOT VERIFIED issues, assumptions, or speculation"), the actionable set is:

**Implementable now (small, source-confirmed, low-risk):**
- AUTH-001 — add password-requirements hint to signup form
- AUTH-002 — add show/hide password toggle
- AUTH-004 — add ToS/Privacy links to signup
- AUTH-007 — map generic network errors (`Failed to fetch`, etc.) to a friendly message
- DASH-001 — rename/clarify dashboard title
- DASH-003 — increase prominence of the security notice
- DASH-008 — increase prominence of the "+ New group" control
- ANAL-006 — either paginate or add a "view all" affordance for the group sidebar cap
- PROF-001 — this is the one High-severity item that's genuinely confirmed missing (no profile/settings screen at all). It's also the largest of the "implementable now" set — a new screen, not a one-line fix — so it should be scoped and confirmed with you before I build it, since the brief also says "never create new features unless they solve verified usability problems," and a whole new screen is a judgment call on how minimal "minimal" should be here.

**Flagged, not auto-implemented — needs a scoping decision, not a mechanical patch:**
- AUTH-006 (token in `localStorage`) — real and the most serious finding in the whole audit, but fixing it properly means moving to httpOnly cookies across every endpoint in `api.js` plus CORS/CSRF changes on the backend. That's an architecture change, not a "smallest correct fix," and directly collides with the brief's own "don't change APIs unnecessarily / preserve backward compatibility" constraints. I'd want your go-ahead on scope before touching it.

**Not implemented — classification says no:**
- AUTH-003, AUTH-005, ACCESS-003, AUDIT-001, ORG-001, ACCESS-006 — EXPECTED BEHAVIOUR or NOT REPRODUCIBLE. Implementing "fixes" here would mean patching problems that don't exist (in two cases, the code already contains the exact protection the audit claims is missing).

**Not implemented — insufficient/no evidence (31 issues across the 12 untested screens plus DASH-002/004/005/006/007/009, ACCESS-001/002/004/005, and others listed above):** a real browser pass against those screens is a prerequisite. Implementing against bundle-derived claims risks the same false-positive rate the ORG-001/AUDIT-001/ACCESS-006 spot-checks just demonstrated (3 for 3).

I'm stopping here rather than proceeding into fixes, since the actionable set is much smaller than "47 issues" and the brief's own severity ranking (5 of 5 real 🔴 items) turned out to be unreliable on inspection. Let me know how you want to handle the two flagged items (AUTH-006 scope, PROF-001 new-screen scope) and whether you want a real browser recheck run on the 12 untested screens before I go further, or want me to proceed with just the eight small, fully-confirmed fixes above.
