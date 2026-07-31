# UI ↔ API Contract Matrix — Sprint V6.0 (Phase 4)

Every visible, user-triggerable action across all 12 screens, mapped to its API call, permission, audit event, analytics event, loading/success/error state, and confirmation dialog (where destructive). Built by reading `frontend/api.js` call sites against their exact backend route handlers — not inferred. ~75 actions catalogued across two research passes; this document consolidates both, condensed to the columns that matter for governance (full raw per-action detail is in the underlying research transcripts).

Legend: ✅ = present/correct and unchanged · **[FIXED]** = a real gap found this sprint and fixed · **[DOCUMENTED]** = a real gap found and deliberately left for later (with reasoning) · **[VERIFIED-OK]** = flagged as a possible issue but checked and found to be working as intended

## Login

All four auth flows (Sign In, Sign Up, Forgot Password, Reset Password) map correctly to their Supabase/backend endpoints, have loading state, and have both specific and generic-fallback error paths. One real bug found and fixed: **[FIXED]** reset-password left the used `#access_token=...&type=recovery` fragment in the URL after success, so a refresh could re-enter the reset form with an already-invalid token — now cleared via `history.replaceState`.

## Upload

- ✅ Upload, Delete Document — full contract (audit event, loading, confirmation where destructive) present and correct.
- **[DOCUMENTED]** Retry/Reprocess, Assign-to-group, Remove-from-group, Create/Edit/Delete Group — none of these call `log_audit_event`, unlike Upload (`document.uploaded`) and Delete (`document.deleted`) on the same screen. Reprocess and the group `<select>` actions also have no per-action loading/disabled state, so a user gets no visual confirmation the request is in flight. Not fixed this sprint — this is a whole class of endpoints (7 actions), not a single line; see `MODULE_BOUNDARIES_AND_CODE_QUALITY.md` for why broad audit-logging additions were scoped down to the highest-value gap (webhooks, below) rather than attempted everywhere at once.

## Viewer

- ✅ Open/validate session, download, most annotation actions — correct contracts.
- **[FIXED]** View-limit-reached was misclassified as "Link Expired" (already fixed in the prior sprint's work, reconfirmed still correct).
- **[FIXED]** Network-error page-load fallback silently 400'd with no error shown (prior sprint) — reconfirmed fixed, now also has a Retry button.
- **[FIXED]** Search: a network/auth failure rendered identically to "No matches found" — actively misleading, not just generic. Now shows a distinct "Search failed — check your connection and try again" message.
- **[FIXED]** Extract Sidecars: bare empty `catch {}` gave zero feedback on failure, and success was claimed on HTTP 202 (request accepted) rather than actual completion of the fire-and-forget background task. The silent-failure half is fixed (now shows a toast on error); the success-timing gap is **[DOCUMENTED]**, not fixed — a real fix needs the backend to expose completion status (polling or a status field), which is a backend contract change, not a "fix only when safe" frontend patch.
- **[DOCUMENTED]** Print (`logEvent` fire-and-forget with a swallowed `.catch`), bookmark toggle, create/delete annotation, and comment-thread actions have no loading/disabled affordance during their request — inconsistent with the thread-reply action on the same screen, which does track a sending state. Left as-is; cosmetic polish, not a correctness bug.
- **[DOCUMENTED]** Insights modal (heatmap + reading-summary calls): all failures are swallowed (`.catch(() => null)`) by design in `api.js` — intentional so a 401 doesn't force-reload the public viewer, but it means a real backend error and "no data yet" render identically inside the modal. Left as-is; changing this shared API function's behavior would need to distinguish the public-viewer context (where swallowing is correct) from the authenticated-analytics context (where it arguably isn't) — a scoped follow-up, not a quick patch.

## Access Control

- ✅ Create/Quick-Link, Rename/Edit/Revoke/Delete Link — full contracts, all destructive actions confirmed.
- **[FIXED]** "Revoke All Access" always reported success even on partial/total per-link failure (prior sprint's fix, reconfirmed).
- **[FIXED]** Same bulk action had no loading state while N revokes were in-flight and the modal closed instantly — this specific gap (as opposed to the reporting-accuracy gap) was newly confirmed this sprint but **not separately fixed**; it's a smaller residual issue on top of an already-fixed action, tracked as **[DOCUMENTED]**.
- **[FIXED]** Copy Link: success toast fired even when `navigator.clipboard.writeText()` failed (caught synchronously, but the async rejection was never handled). Now awaited properly with a real error path.
- **[FIXED]** CSV exports (Feedback Conversations, Reviewer Activity, Visual Annotations) — all three had **zero error handling**, not even a generic fallback; bare unhandled promise expressions. Now wrapped in try/catch with an error toast, matching every other action on the screen.
- **[DOCUMENTED]** Resolve/Reopen feedback has no loading state and no success toast, while the adjacent Reply-to-feedback action (same tab) has both — inconsistent polish, not fixed.

## Analytics

- ✅ CSV export (client-side, correctly handles the empty-data case with a specific toast).
- **[DOCUMENTED]** Page-heatmap click: `getPageHeatmap()` never throws on failure by design (`if (!r.ok) return null`), so the `.catch()` handler in `AnalyticsScreen.jsx` is dead code — a real failure is indistinguishable from "no page views yet." Same root cause as the Viewer Insights finding above; left for the same reason (shared API function used in both a context where swallowing is correct and one where it arguably isn't).

## Notifications

- ✅ Refresh, Load More — correct contracts.
- **[DOCUMENTED]** "Mark all read" is presented as a real state-changing action but is purely `localStorage`-based with no backend concept of "read" at all — resets on a different browser/device. Real UX-contract gap, but fixing it means adding backend read-state, a feature-shaped change out of this sprint's "no new product features" scope.

## Organizations

- ✅ Create/Rename/Delete Org, Invite Member, Change Role — full contracts.
- **[FIXED, prior sprint, reconfirmed]** Member removal had no confirmation dialog (now fixed) and self-removal was broken for non-admin roles (now fixed, with 2 regression tests).
- **[VERIFIED-OK]** Role-change and member-removal audit logging (`member.role_changed`, `member.removed`) is wrapped in `try/except: pass` — investigated this sprint (see `MODULE_BOUNDARIES_AND_CODE_QUALITY.md`) and confirmed `log_audit_event()` cannot actually raise, so this was never a real failure risk despite looking inconsistent with the unwrapped calls elsewhere in the same file.

## API Keys

- ✅ Create/Revoke/Delete/Rotate — all confirmed correct with proper confirmations and audit events (prior sprint).
- **[FIXED]** `api_key.rotated` was logged but **absent from `AUDIT_EVENT_TYPES`**, making it permanently unfilterable in the Audit Log screen's Event Type dropdown and rejected with 422 if queried directly by event type. Added to the enum.
- **[FIXED]** Copy-to-clipboard success toast fired unconditionally, outside the `.then()`, with no `.catch()` — same class of bug as Access Screen's copy-link. Fixed identically.
- **[DOCUMENTED]** Edit (rename/rescope) logs no audit event, unlike its Create/Rotate/Revoke/Delete siblings on the same screen. Not fixed — lower value than the Rotate enum bug and the copy-paste bug, deferred.

## Webhooks

- ✅ Create/Edit/Delete/Test/Pause-Resume, delivery history — all functionally correct, with confirmations where destructive.
- **[FIXED]** **The entire screen had zero audit logging** across Create/Edit/Delete — the largest single audit-coverage gap found this sprint (flagged independently by two research agents, and already the top-priority carried-forward item from the prior sprint's architecture review). Added `webhook.created`/`webhook.updated`/`webhook.deleted` events, registered in `AUDIT_EVENT_TYPES`.
- **[FIXED]** Copy-secret-to-clipboard had the identical unconditional-success-toast bug as API Keys and Access Screen. Fixed identically.

## Storage

- ✅ Retention-policy change now has a confirmation dialog (prior sprint's fix, reconfirmed) and now uses danger styling only when the change actually schedules deletion (this sprint — see `CONSISTENCY_MATRIX.md`).
- **[FIXED]** Retention change logged no audit event despite being the one action on this screen the frontend itself flags as consequential enough to confirm. Added `document.retention_changed`.

## Billing

- Uses raw `fetch()` throughout rather than the shared `api.js` client (no `_clearAndReload()` on 401, no shared error helper) — noted as an inconsistency, not changed (would mean rewriting this screen onto the shared client, out of proportion for this sprint).
- **[FIXED]** "↻ Refresh" was **completely silent on failure** — no error state set on a non-OK response, `catch (_) {}` swallowing network errors, and no toast context on this screen at all. This was the only action across all 12 screens with zero user-facing feedback of any kind on failure. Now sets the screen's existing inline error state on both failure paths.
- Upgrade/Manage (Stripe redirect flows) — correct: specific error messages, no confirmation needed since Stripe's own checkout/portal UI provides it.

## Audit Log

- ✅ Filter, Clear, Load More, CSV/JSON export — all correct.
- **[FIXED, prior sprint, reconfirmed]** Export truncation at 500 rows now warns with an accurate "Exported N of M" message instead of a plain success toast.
- **[DOCUMENTED]** The Event Type filter dropdown is populated from the static `AUDIT_EVENT_TYPES` set — before this sprint's fix, `api_key.rotated` events existed in the log but could never be selected in this filter. Now fixed as a side effect of the enum addition above.

---

## Summary

Of the concrete **[MISMATCH]**-class findings surfaced by this phase (roughly 20 distinct issues across both research passes): **9 were fixed this sprint** (search misleading-empty-state, extract-sidecars silent failure, 3× copy-to-clipboard false-success, 3× CSV-export silent failure, api_key.rotated enum gap, webhook audit-logging gap, storage retention audit-logging gap, billing refresh silent failure, plus the login URL-fragment bug), and the remainder are explicitly documented above with the reasoning for not fixing them this sprint — mostly because the correct fix is a backend contract change, a feature-shaped addition, or a broad multi-file consistency sweep better done as its own scoped piece of work rather than folded into this governance pass.
