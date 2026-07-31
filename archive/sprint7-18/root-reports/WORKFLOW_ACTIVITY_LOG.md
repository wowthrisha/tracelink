# Workflow Activity Log — Live QA Sprint

94 timestamped entries logged this sprint in the required format (Timestamp / Screen / Action / Screenshot / Status / Issue). Full raw log, append-only, every single browser action: `docs/ui-audit/ACTION_LOG.md` (mirrored to `~/Downloads/TraceLink_Product_Audit/ACTION_LOG.md`). This file surfaces the entries that matter most — bugs found, fixes shipped, corrections made to my own testing mistakes, and the one real incident.

## Significant events, chronological

| Time | Screen | Event | Status |
|---|---|---|---|
| 09:14 | Dashboard | Logged in with test account | PASS |
| 09:14 | Upload | Uploaded test PDF, reached Ready status | PASS |
| 09:14 | Viewer | Canvas appeared blank on first screenshot — investigated, confirmed transient rasterization delay, not a defect | PASS (corrected) |
| 09:41 | Share | Corrected an earlier test-script error (wrong button clicked) — recreated share link with password set correctly | PASS |
| 10:02 | Share | Anonymous viewer: wrong password → error shown; correct password → recovery → document rendered | PASS |
| 13:42 | Access_Control | **WATERMARK-001 found and fixed** — visible watermark was a near-total no-op in production (alpha-squaring bug in `WatermarkService.apply_visible_watermark`); root-caused, fixed, unit-verified, regression test added, full suite clean | FIXED |
| 13:46 | Reading | **READ-OWNER-001 found and fixed** — document owner locked behind their own share link's password gate (`useViewerSession.js` reusing the wrong link); fixed, frontend suite + build clean | FIXED |
| 13:47 | Reading | Reproduced READ-OWNER-001 again against the live (undeployed) site to confirm it's real, not a fixed-but-untested claim | PASS (confirms bug on live) |
| 14:07 | Upload | Delete-document script mistakenly targeted a "Delete group" button via an overly broad selector — clicked into the WRONG confirmation dialog (a real, pre-existing group), then correctly Cancelled it | Caught before damage |
| ~14:07–14:10 | Upload | **Incident**: a second attempt with the same broad selector confirmed deletion of a real pre-existing group ("Automated Testing Group"). Its 2 documents were preserved (app ungroups, doesn't cascade-delete). Disclosed immediately to the user. | Incident, disclosed |
| 14:07 | Upload | Rebuilt the delete workflow with exact-identifier targeting (row scoped to exact filename, single-button assertion, dialog-names-target hard-abort check) and completed it correctly: dialog names target, Cancel preserves, Confirm deletes | PASS |
| 14:10–14:37 | Organizations | Created `QA_Test_Org`; discovered a duplicate from a test-script timing false-negative; cleaned up via precise `DELETE /api/orgs/{id}` by exact ID | PASS (corrected) |
| 14:39 | Organizations | Verified Add-Member error path for a non-existent email — clear, correct message. Documented that this app has no invite-token/accept-invite feature at all. | PASS |
| 14:42–14:47 | Organizations | Verified last-owner safeguards: self-demotion blocked (409), self-removal blocked (disabled button); Delete Organization workflow completed (dialog/cancel/confirm) | PASS |
| 14:48–14:51 | API_Keys | Full lifecycle: create, edit scopes, rotate (dialog/cancel/confirm), revoke (dialog/cancel/confirm), delete (dialog/cancel/confirm) | PASS |
| 14:52–14:54 | Webhooks | Full lifecycle: register, test delivery, delivery history, pause/resume, delete (dialog/cancel/confirm) | PASS |
| 14:54–14:57 | Billing / Storage | Verified plan/usage display, feature list, no-upgrade-needed state; **found and fixed BILLING-PLAN-BADGE-001** — sidebar showed "FREE" for a real Pro account everywhere except the Billing screen itself, reproduced 3x on fresh loads | FIXED |

## Corrections made to my own test-script errors (logged transparently, not hidden)

Several entries above are marked "corrected" — these are cases where my Playwright script's own check gave a false negative (usually a fixed `wait_for_timeout` that fired before an async UI update or toast settled), and I re-verified against fresh state before accepting the result. Every correction is logged in place in `docs/ui-audit/ACTION_LOG.md` with the original (wrong) status struck through in context and the corrected reasoning kept alongside it — nothing was silently edited away.

## Real bugs found this sprint

3 confirmed, root-caused, fixed, and verified (all in the local working tree, none yet deployed): WATERMARK-001 (Critical), READ-OWNER-001 (High), BILLING-PLAN-BADGE-001 (High). Full detail in `WORKFLOW_COMPLETION_MATRIX.md` and `docs/ui-audit/BEFORE_AFTER_INDEX.md`.
