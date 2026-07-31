# Workflow Progress — Live QA Sprint

Append-only. Never overwritten. Resume point if this sprint is interrupted: read the last entry below, then `docs/ui-audit/SESSION_STATE.md` for full detail.

Environment: live deployed instance at `https://wowmyspace--tracelink.up.railway.app`, test account `23z274@psgtech.ac.in`. Driven via Playwright (Python, headless Chromium) — no code review performed before testing; every finding below was reproduced live before any fix was written.

---

## [1/6] Document Lifecycle — COMPLETE

Upload → Protect → Configure Access → Create Share Link → Read (anonymous, password-gated) → Reading Intelligence → Analytics → Notifications → Audit Log → Delete.

- Uploaded a real 3-page PDF, reached Ready status, confirmed via toast + status column.
- Configured password protection, 30-day expiry, watermark toggle, IP allowlist on Access Control.
- Created a share link with password correctly set (after correcting a test-script error on the first attempt — see `docs/ui-audit/ACTION_LOG.md` 09:38–09:41).
- Opened the link in a fully anonymous (no auth) browser context: wrong-password error path, correct-password recovery path, document rendered.
- **Found and fixed WATERMARK-001**: the visible watermark was a near-total no-op on all shared pages in production (alpha-squaring bug in `WatermarkService.apply_visible_watermark`). Root-caused, fixed, unit-verified, regression test added, full backend suite re-run clean.
- **Found and fixed READ-OWNER-001**: the document owner's own internal Viewer could get locked behind a password gate meant for public recipients, because `useViewerSession.js` blindly reused the first active link instead of preferring an unrestricted one.
- Verified Reading Insights panel, Analytics overview (+ tablet/mobile), Notifications feed, Audit Log entries.
- Delete workflow: dialog names the exact target, Cancel path preserves the document, Confirm path deletes it (verified via fresh reload after an initial screenshot-timing false negative).

Evidence: `docs/ui-audit/Screenshots/{Dashboard,Upload,Viewer,Reading,Access_Control,Share,Analytics,Notifications,Audit_Log}/`, `docs/ui-audit/Before_After/WATERMARK_BUG_*`, `docs/ui-audit/Before_After/READ-OWNER-001...` entry.

---

## [2/6] Organizations — COMPLETE

Create → Members → Invite/Add-Member → (no Accept-Invite step exists in this app — see note) → Assign Role → Remove Member → Delete Organization.

- Created `QA_Test_Org` (duplicate created by a test-script timing false-negative, cleaned up via precise `DELETE /api/orgs/{id}` by exact ID rather than an ambiguous same-name UI click).
- **Architectural finding, not a gap**: this app has no invite-token/accept-invite flow. "Add Member" adds an *existing* SecureDoc user by email immediately (per the modal's own copy). Verified the error path for a non-existent email: a clear, specific message ("No registered user found with email '...'. They must sign up for SecureDoc first."). There is no "Accept Invite" step to test because the feature doesn't exist as the mission assumed.
- Assign-Role edge case: attempted to demote the sole owner (self) to editor — correctly blocked server-side (409, "Cannot remove the last owner from the organization").
- Remove-Member edge case: the Remove button is **disabled** in the UI for the sole owner — an even stronger safeguard than the backend check alone.
- Delete Organization: dialog names the exact target, Cancel preserves it, Confirm deletes it (verified via the success toast, corrected after an initial check false-negative — see log).

Evidence: `docs/ui-audit/Screenshots/Organizations/`.

---

## [3/6] API Keys — COMPLETE

Create → Edit scopes → Rotate → Revoke → Delete.

- Created `QA_Test_Key` with a scope selected; confirmed the reveal-once modal shows the real key value.
- Noted (not deeply chased): clicking "Create key" with zero scopes selected produces no visible feedback — a minor UX gap, logged but not treated as blocking.
- Edit: added a second scope, saved, confirmed in the list.
- Rotate: dialog names target, Cancel path, Confirm path (real, since key is disposable/session-created) — new key value issued.
- Revoke: dialog names target, Cancel path, Confirm path — status flips to REVOKED, Rotate/Revoke buttons disappear per design (`k.is_active` gate).
- Delete: dialog names target, Cancel path, Confirm path — key removed, list returns to empty state.

Evidence: `docs/ui-audit/Screenshots/API_Keys/`.

---

## [4/6] Webhooks — COMPLETE

Register → Test delivery → View history → Pause/Resume → Delete.

- Registered `QA_Test_Webhook` pointing at a non-listening `https://example.com/...` URL (deliberately, to exercise the failure path); confirmed the signing-secret reveal-once modal.
- Test: sent a real test ping, confirmed via toast and by checking Delivery History, which showed the `ping` event in `PENDING` state (correct — async dispatch via Celery, not expected to resolve instantly against a non-real endpoint).
- Pause/Resume: verified the status badge flips both ways and the Test button's title correctly explains why it's disabled while paused.
- Delete: dialog names target, Cancel path, Confirm path — webhook removed.

Evidence: `docs/ui-audit/Screenshots/Webhooks/`.

---

## [5/6] Billing — COMPLETE

- Verified the Billing screen's own plan/usage/feature display is correct (Pro, Unlimited uploads, etc.) and that the "billing not configured" message is accurate (Stripe keys unset on this deployment by design — app works fully without it).
- No Upgrade button shown — correct, since the account is already Pro.
- **Found and fixed BILLING-PLAN-BADGE-001**: the persistent sidebar plan badge showed "FREE" for this real Pro account on every screen except the Billing screen itself, reproduced on 3 separate fresh page loads. Root cause: `AppShell.jsx` hardcoded `plan` state to `'free'` and only ever corrected it reactively when `BillingScreen` happened to mount. Fixed with a mount-time billing-status fetch.

Evidence: `docs/ui-audit/Screenshots/Billing/`, `docs/ui-audit/Before_After/BILLING-PLAN-BADGE-001...` entry.

---

## [6/6] Storage — COMPLETE

- Verified usage totals, 30-/90-day projections, and per-document storage table render correctly with real data (13.85 MB / 29 documents at time of test).
- Per-org breakdown section present and correctly scoped (only rendered for multi-org accounts, per existing design).
- Tablet/mobile viewport checks captured — this app has an explicit "desktop-only beta" gate below 768px width (`AppShell.jsx`), so responsive layout is intentionally out of scope, not a defect (see `docs/engineering/ARCHITECTURE_DECISIONS.md` AD-6 from the prior sprint).

Evidence: `docs/ui-audit/Screenshots/Storage/`.

---

## Sprint summary at this checkpoint

- **3 real bugs found, root-caused, fixed, and verified this sprint** (backend suite 1703/1 skipped clean, frontend suite 13/13 clean, builds clean): WATERMARK-001 (critical), READ-OWNER-001 (high), BILLING-PLAN-BADGE-001 (high).
- **1 incident, disclosed and resolved**: an overly broad Playwright selector in an early Delete-workflow test accidentally deleted a real pre-existing group ("Automated Testing Group") — its 2 documents were preserved (app correctly ungroups rather than deletes), but the group itself could not be recovered. Full disclosure and root cause in `docs/ui-audit/ACTION_LOG.md` and in this session's conversation. All destructive-action scripts from that point forward use exact-ID or exact-text-scoped selectors, pre-action target verification with a hard abort if the confirmation dialog doesn't name the expected target, and restrict real (non-cancelled) destructive confirms to resources created this session and clearly disposable per the live-environment safety policy.
- **Zero deployment**: all 3 fixes exist only in the local working tree. The live Railway instance still exhibits all 3 bugs as of this writing, since nothing has been pushed — consistent with this session's standing policy of never committing/deploying without explicit request.
- **No "Accept Invite" workflow exists** in this application's actual design — documented as an architectural fact, not a testing gap.
