# Verified Issues — TraceLink/SecureDoc Remediation Sprint

Source: `ENGINEERING_TRIAGE.md` (full reasoning per issue). This is the disposition summary.

**Note on totals**: `ISSUE_DATABASE.md`'s header claims "Total Issues: 47," but the table it ships actually contains **49** rows (AUTH×7, DASH×9, VIEWER×5, ACCESS×6, FEED×3, ANAL×6, STOR×3, APIKEY×2, WEBHOOK×2, AUDIT×1, ORG×1, BILL×2, PROF×2 = 49). Flagging this as one more small data-integrity issue in the source audit, consistent with the larger evidence-quality problem documented in `ENGINEERING_TRIAGE.md` §0. All 49 are dispositioned below.

---

## ✅ Verified and fixed (7)

| ID | Fix |
|---|---|
| AUTH-001 | Added a password-requirements hint ("At least 6 characters") under the signup password field. |
| AUTH-002 | Added a Show/Hide toggle to the password input. |
| AUTH-007 | Generic network failures (`Failed to fetch`, etc.) now map to "Unable to reach the server. Check your connection and try again." instead of showing the raw error string. |
| DASH-001 | Dashboard title changed from "Upload Dashboard" to "Documents" to reflect that the screen is a full document hub, not just an upload tool. |
| DASH-003 | Security notice moved from a 10px footer line to a bordered banner directly under the header, above the stats grid. |
| DASH-008 | "+ New group" button changed from `ghost` (no border/background) to `secondary` variant (visible border + background) for discoverability. |
| ANAL-006 | Groups sidebar widget (previously silently capped at 5) now shows a "Show all N" / "Show fewer" toggle when there are more than 5 groups. |

Full technical detail for each is in `FIX_LOG.md`.

## ⏸ Verified but deferred (3)

| ID | Why deferred | Deliverable produced |
|---|---|---|
| AUTH-006 | Real finding (session token in `localStorage`), but a correct fix is an authentication-architecture migration (httpOnly cookies, CSRF, CORS changes) touching 60 frontend call sites and 72 backend dependency sites — not a "smallest correct fix" for this sprint. | `SECURITY_HARDENING_PLAN.md` |
| AUTH-004 | Real gap (no ToS/Privacy links on signup), but no Terms of Service or Privacy Policy pages exist anywhere in this repo to link to. Adding a link to a nonexistent page, or inventing placeholder legal text, would be worse than the current state. Needs actual legal content from product/legal before an engineering fix is meaningful. | Noted here; no separate doc — blocked on content, not design. |
| PROF-001 | Real finding (no profile/account screen exists at all), but building one is a new feature (new screen + at least one new backend endpoint), out of scope for a remediation sprint per the brief's own rules. | `PRODUCT_PROPOSAL.md` |

## ❌ False positives (6)

Claims that do not hold up against the current source — implementing "fixes" for these would patch problems that don't exist.

| ID | Claim | Why it's false |
|---|---|---|
| AUTH-003 | "No social login options" flagged as a gap | Deliberate: email/password-only auth is a defensible security posture for a security-first document product, not an omission. |
| AUTH-005 | "Supabase anon key exposed in HTML meta tag" flagged as a security issue | Misreads the Supabase auth model — the anon/public key is designed to be shipped client-side (equivalent to a Firebase web config); it carries no privileged access on its own. |
| ACCESS-003 | "`/hard` endpoint path visible in frontend JS" flagged as an implementation-detail leak | Any client-side `fetch` call necessarily reveals its own endpoint path in shipped JS — true of every REST client, not a fixable leak without a full backend-for-frontend layer (out of scope). |
| ACCESS-006 | "No warning when creating an unprotected share link" | False — `AccessScreen.jsx:807-808` already renders exactly this warning. |
| AUDIT-001 | "Audit log accessible to all users" | False — `backend/app/routers/admin.py:45-50` already enforces an admin-role check with a 403 fallback. |
| ORG-001 | "No cascade warning before deleting an organization" | False — `OrgsScreen.jsx:355-367` already shows a confirmation modal with explicit cascade-impact copy before the delete call fires. |

Three of these six (ACCESS-006, AUDIT-001, ORG-001) were the exact issues I spot-checked in `ENGINEERING_TRIAGE.md` §0 to test whether the untested-screen portion of the source audit could be trusted — all three turned out to describe the opposite of what's actually implemented.

## 🔁 Needs browser re-validation (30)

These all sit on screens the source audit's own tracking (`CHECKPOINT.json`, `WORKFLOW_STATUS.json`) confirms were **never opened** in a browser, with `Source:` citations that trace to static inspection of the minified `frontend/dist/app.bundle.js` rather than observed behavior. Per the mission rule ("only browser-verified issues or source-confirmed defects with reproducible evidence may be fixed"), none of these are implemented. A real browser pass against these 12 screens is a prerequisite before any of them can move to "fixed." (This bucket includes DASH-004 and ACCESS-001, which `ENGINEERING_TRIAGE.md` separately flags as "insufficient evidence" rather than "untested screen" — the practical next step for both is identical: re-run against the real app.)

`DASH-002, DASH-004, DASH-005, DASH-006, DASH-007, DASH-009, VIEWER-001, VIEWER-002, VIEWER-004, VIEWER-005, ACCESS-001, ACCESS-002, ACCESS-004, FEED-001, FEED-002, ANAL-001, ANAL-002, ANAL-003, ANAL-004, ANAL-005, STOR-001, STOR-002, STOR-003, APIKEY-001, APIKEY-002, WEBHOOK-001, WEBHOOK-002, BILL-001, BILL-002, PROF-002`

Full per-ID reasoning, including which of these had a partial structural sanity-check already run against source, is in `ENGINEERING_TRIAGE.md`.

## ℹ️ Positive findings — confirmed good, no action needed (3)

Not defects; the source audit flagged these as things already working correctly. Confirmed directly against current source, not the bundle:

- **VIEWER-003** — session ID transported via `X-Session-ID` header, never in the URL (`frontend/api.js:353-355`).
- **ACCESS-005** — access-control toggles use proper `role="switch"` + `aria-checked` ARIA pattern (`atoms.jsx` `Toggle` component).
- **FEED-003** — inline reply/resolve on feedback items already implemented (`api.js:replyToFeedback`, `resolveFeedback`).

---

**Tally**: 7 fixed + 3 deferred + 6 false positive + 30 needs-recheck + 3 positive/no-action-needed = 49/49 issues covered, no double-counting.
