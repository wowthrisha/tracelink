# Workflow Completeness — Sprint 7.0

Method: for each of the 17 named workflows, source (not bundle) was read directly — frontend screens/hooks/components and their exact backend counterparts — checking for dead ends, meaningful empty states, confirmation dialogs on destructive actions, actionable error messages, and graceful failure recovery. Every finding below has a file:line citation. Status legend: ✅ Fixed this sprint · 📝 Documented, not fixed (reason given) · ✔ Already correct (no action needed).

---

## Upload → OCR/Processing

- ✔ Stuck/failed documents are recoverable: `POST /{id}/reprocess` (`documents.py:281-316`) is reachable from a "↺ Retry" button on any non-ready doc (`DocRow.jsx:11,60` → `UploadScreen.jsx:198-205`).
- ✔ Stale processing never hangs forever: a 5-minute Celery Beat sweep (`tasks.py:299-359`, `celery_app.py:42-45`) plus in-task self-heal (`tasks.py:64-80,113-129`) requeue anything stuck >15-20 min.
- ✔ Empty state: "No documents yet — upload your first PDF above" (`UploadScreen.jsx:360-363`).
- ✔ Delete confirmations present and clear for both documents and groups.
- ✅ **Fixed**: Document/group delete confirm buttons now show a loading state and the modal only closes on success rather than immediately — closes a double-click and silent-failure risk (`UploadScreen.jsx`).
- 📝 **Not fixed** — no explicit encrypted/password-protected PDF detection on the backend; the frontend's "friendly" message for this case is a lucky regex match against whatever text `pdf2image`/poppler happens to raise, not a real contract (`rasterizer.py`, `UploadScreen.jsx:99-105`). Recommend a dedicated `EncryptedPDFError` classification in the rasterizer — deferred as a backend adapter change, not a UI fix.
- 📝 **Not fixed** — LibreOffice conversion failures can surface raw subprocess stderr to the end user (`libreoffice_converter.py:208-214` → `UploadScreen.jsx:104`). Needs a generic-message/detailed-log split — deferred, moderate scope.
- 📝 **Not fixed** — no pre-upload warning as a user approaches their document quota (only a hard block at the limit). This is UI-polish/feature-adjacent; left out per "do not add new product features."

## Protection → Share → Viewer

- ✅ **Fixed**: hitting a link's view limit was shown as "Link Expired" instead of the real reason — `useViewerSession.js` now classifies "max views" detail text into its own `view_limit_reached` status, and `AccessGate.jsx` has a matching message ("View Limit Reached...").
- ✅ **Fixed**: the network-error fallback in `usePageLoader.js` used to silently set a bare `<img src>` with no session header, which always 400s with no error shown — a genuine dead end. Now surfaces a real, actionable error ("Network error loading this page...") instead.
- ✅ **Fixed**: added a Retry button to the page-load error overlay (`ViewerScreen.jsx`), wired to a new `retryPage()` in `usePageLoader.js` — previously the only recovery was navigating away and back.
- ✅ **Fixed**: all five `GateMessage` icons in `AccessGate.jsx` were unescaped HTML-entity strings (e.g. `"&#x1F50D;"`) rendered literally as garbled text instead of emoji, since React doesn't decode entities inside `{expression}` children — replaced with real emoji characters.
- ✅ **Fixed**: no warning when creating a password/email-gated link with no expiry (indefinite protected access) — `AccessScreen.jsx` now shows an inline hint when this combination is selected.
- ✅ **Fixed**: Revoke vs. Delete had no tooltip explaining the difference (ACCESS-002, confirmed still valid) — added `title` support to the shared `Btn` component and tooltips to both buttons.
- ✅ **Fixed**: "Revoke All Access" looped through links swallowing every per-link failure and always reported "All access revoked" regardless of outcome — a false-positive security claim. Now uses `Promise.allSettled` and reports actual success/partial/failure counts (`AccessScreen.jsx:handleRevoke`).
- ✔ Confirmation dialogs already present and correct for: revoke link, delete link, revoke-all, quick/unrestricted link creation.
- 📝 **Not fixed** — no explicit "Retry" affordance existed before this sprint (now added, see above) for HTTP-error page loads either; confirmed both paths (network error and HTTP error) now converge on the same error+retry UI.

## Reading Analytics → Notifications

- ✅ **Fixed**: `SparkChart.jsx` fabricated a plausible-looking sin/cos wave when there was no real data — actively misleading, not just a missing-data gap. Now renders a flat, dimmed baseline with an explicit "No activity recorded yet" caption.
- ✅ **Fixed**: `DonutChart.jsx` hardcoded "100% success rate" when there were zero views AND zero blocked attempts (a brand-new account) — now shows "No data" instead of a fabricated 100%.
- ✅ **Fixed**: `AnalyticsScreen.jsx` declared `analyticsLoading` but never rendered it — a slow initial fetch looked identical to "no data exists." Added a loading indicator gating the tab content.
- ✔ Empty states are otherwise good throughout: `InsightsModal.jsx` (reading/pages/viewers/insights tabs), documents table, heatmap panel, groups tab, `NotificationsScreen.jsx`.
- ✔ `_errMsg` is used consistently — no raw error/stack-trace leakage found in this area.
- 📝 **Not fixed** — "Mark all read" on Notifications only writes to `localStorage`; there's no backend persistence or per-item read/dismiss (`NotificationsScreen.jsx:129-134`, confirmed no REST read/dismiss routes in `notifications.py`, only an SSE stream). This is a real gap but adding backend state is a feature-shaped change, not a bug fix — documented for a future backend endpoint.
- 📝 **Not fixed** — CSV/JSON analytics export is client-side and silently truncates at the backend's default `limit=100` for `getDocumentAnalytics()` with no warning (unlike the Audit Log export, which now warns — see below). Deferred; would need either raising the export-time limit or backend export support.
- 📝 **Not fixed** — heatmap load failures are swallowed silently (`.catch(() => setHeatmapData(null))`), indistinguishable from "no page views yet." Low severity, documented.
- 📝 **Not fixed** — reading-event batching (`useReadingAnalytics.js` → `batchReadingEvents`) is fire-and-forget with no retry/backoff; confirmed intentional per the file's own header comment (non-critical telemetry), but has zero resilience if the network drops for a whole session. Flagged, not changed, since this is a deliberate design tradeoff, not an obvious bug.

## Organizations / Invite Member / Role Management

- ✅ **Fixed — real bug**: a plain viewer/editor member could not leave an organization at all. `orgs.py`'s `remove_member` required `minimum_role="admin"` for the *entire* request before ever checking `is_self`, even though the code's own comment said self-removal should work "at any role." Fixed by resolving the caller at `minimum_role="viewer"` and enforcing the admin-role requirement explicitly only for *non*-self removals. Two new regression tests added (`test_viewer_can_leave_org`, `test_viewer_cannot_remove_other_member`) — both pass, and all 3 pre-existing member-removal tests still pass.
- ✅ **Fixed**: member removal had no confirmation dialog anywhere — the only destructive action in the entire app without one. Added a confirm modal matching the org-delete pattern (`OrgsScreen.jsx`).
- ✔ Last-owner protection confirmed solid on both role-change and remove (`orgs.py:437-447,500-510`).
- ✔ Anti-escalation (can't grant/act above your own role) confirmed correct.
- ✔ Delete-organization confirmation modal confirmed present with accurate cascade-impact copy (memberships do cascade-delete at the DB level).
- 📝 **Not fixed — needs a product decision, not an engineering one**: deleting an org does **not** cascade-delete or block deletion of its documents — `Document.org_id` has no `ForeignKey` constraint at all (unlike `group_id`/`parent_document_id` on the same model), so org-scoped documents are silently orphaned rather than deleted or reassigned. The delete-org modal's copy ("Members will lose access") is not fully accurate — the deleting owner and each document's original uploader retain access via the separate `user_id`-ownership check. This is the same class of decision flagged in `PRODUCT_PROPOSAL.md` for account deletion (transfer vs. delete vs. block) — deliberately not fixed without that decision.
- 📝 **Not fixed**: "Invite Member" has no accept/decline step — the UI is honest about this ("They will be added immediately"), and the backend has no invitation/token model at all. This is accurate current behavior, not a bug, but is worth a product conversation if "invite" semantics are expected. Not changed.
- 📝 **Not fixed**: "Transfer Ownership" does not exist in any form — confirmed via exhaustive grep, frontend and backend. The only workaround is manually promoting another member to owner via the generic role-change endpoint (multi-owner orgs are fully permitted). Not built — this is a new feature, out of scope for this sprint.
- 📝 **Not fixed**: role `<select>` is shown to every member row regardless of the viewer's own permissions — a viewer/editor sees a fully interactive dropdown that will 403 on change. Backend is safe; only a frontend affordance gap. Low severity, deferred.
- 📝 **Not fixed**: a dead, frontend-unreferenced `POST /{org_id}/members` endpoint exists alongside the actively-used `invite_member_by_email` with identical permission semantics — not removed (removing an endpoint is an API surface change, out of scope for "don't change APIs unnecessarily").

## API Keys / Webhooks / Storage / Billing

- ✔ API Keys: reveal-once secret warning, revoke confirmation, delete confirmation, and rotate's "stops working immediately" warning are all present and accurate.
- ✅ **Fixed**: API key delete confirmation copy incorrectly referenced "delivery history" (webhook terminology, copy-pasted) — corrected to describe integration impact accurately (`ApiKeysScreen.jsx`).
- ✔ Webhooks: create/delete confirmations, SSRF re-validation at delivery time, and exponential-backoff retry logic are all solid.
- 📝 **Not fixed**: "Test" only confirms the ping was *queued* ("Test ping sent — check delivery history"), not whether it actually succeeded — the real result requires manually opening History, which doesn't auto-refresh. Documented; fixing well means either polling or a live status indicator, a moderate-scope UI change deferred here.
- 📝 **Not fixed**: webhook delivery failures are not proactively surfaced (no badge/count on the webhook row) — same class of gap as above, deferred together.
- ✅ **Fixed**: Storage retention-policy dropdown fired an immediate PATCH on change with zero confirmation — since a stricter policy can schedule a document for deletion, this was a real data-loss-adjacent gap (confirmed the original audit's STOR-002 claim). Added a confirmation modal describing the exact consequence before the change is applied (`StorageScreen.jsx`).
- ✅ **Fixed**: Storage's per-document table had no empty state (renders as a bare header row with an empty body for a zero-document account) — added "No documents yet" messaging.
- ✔ Billing: the 503 "not configured" friendly message is confirmed accurate and the Upgrade button is correctly hidden rather than left as a dead-end click; money-moving actions (upgrade/manage) correctly redirect to Stripe-hosted flows, which have their own confirmation — no in-app unconfirmed charge/cancel action exists.
- 📝 **Not fixed**: Storage screen can't distinguish "load failed" from "no data" after an initial fetch error (degrades to a silent 0-usage state). Low-medium severity, documented, not changed this sprint.

## Audit Log / Password Reset / Delete (app-wide)

- ✔ Audit log filters, pagination, and empty states all confirmed working end-to-end.
- ✅ **Fixed**: CSV/JSON export silently capped at 500 events with no indication when the filtered set was larger — both export handlers now compare the exported count against the known filtered `total` and show an accurate "Exported N of M — narrow your date range" warning toast instead of a plain success message (`AuditLogScreen.jsx`).
- 📝 **Not fixed**: audit-log search and sort operate client-side over only the already-loaded page(s), not the full server-side filtered set — a real match on an unfetched page renders as "no results." Fixing properly means server-side search, an API change; documented, not attempted this sprint.
- ✅ **Fixed**: password-reset flow left the used `#access_token=...&type=recovery` URL fragment in the address bar after a successful reset — a page refresh would re-parse the stale, now-invalid token and drop the user back into a broken reset form. `LoginScreen.jsx` now clears the fragment via `history.replaceState` immediately after a successful reset.
- ✅ **Fixed — consistency**: of 9 destructive actions app-wide, **org member removal was the only one with zero confirmation dialog** (see Organizations section above — now fixed) — this was the single most actionable finding in the whole delete-consistency sweep.
- ✅ **Fixed**: document-delete confirm button had no loading/disabled state (double-click risk); group-delete closed its modal before the async call resolved and had no loading state at all, unlike every other delete flow in the app. Both now match the loading/close-on-success pattern used everywhere else (`UploadScreen.jsx`).
- ✅ **Fixed**: "Revoke All Access" was the one confirmation flow whose promised outcome didn't match what the handler actually did on partial/total failure (see Protection/Share/Viewer section — same fix).

---

## Summary

| Category | Count |
|---|---|
| Fixed this sprint | 17 |
| Documented, deliberately not fixed (feature-shaped, needs product decision, or out-of-proportion scope for this sprint) | 14 |
| Confirmed already correct, no action needed | 12 |

Full technical detail (root cause, exact diff) for every "Fixed" item is in `FIX_LOG.md`.
