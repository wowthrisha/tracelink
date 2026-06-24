# Sprint 4.6 Product Experience Proposal
Sprint: 4.6 — Final Deliverable
Date: 2026-06-22
Status: DESIGN ONLY — Awaiting implementation approval

---

## Executive Summary

Three targeted improvements that require no database changes, no new API endpoints, and no architectural changes — yet collectively move SecureDoc from a product that frustrates first-time users to one that competes head-to-head with DocSend on the metrics that drive adoption.

| Workstream | Change | Effort | Impact |
|---|---|---|---|
| 1 — Quick Share | ↗ Share button on Upload screen document rows | ~4 hours | Critical — fixes the core adoption blocker |
| 2 — Viewer Open Notifications | SSE auth fix + AppShell hook + toast | ~4 hours | High — delivers DocSend's #1 value proposition |
| 3 — Language Simplification | 25 label renames, 2 tool removes, 1 tab merge | ~3.5 hours | High — every user benefits on every session |

**Total estimated implementation effort: ~11.5 hours (under 2 days).**
**Expected outcome: All owner personas pass the 30-second task completion test.**

---

## Workstream 1 — Quick Share

### What it does

Adds a "↗ Share" button on each document row in the Upload screen. Clicking it calls `POST /api/links` with sensible defaults (watermark on, download off), then shows the generated URL in a popover with a one-click copy button.

Full design in `QUICK_SHARE_DESIGN.md`.

### Expected impact

| Metric | Before | After |
|---|---|---|
| Time to first share (upload → link in clipboard) | 60–90 seconds | Under 10 seconds |
| Architect 30-second test | FAIL | PASS |
| Consultant 30-second test | FAIL (on share step) | PASS |
| Builder 30-second test | FAIL | PASS |
| Steps to share with defaults | 7–8 | 2 |

### User value

For a consultant sending a proposal before a meeting: share happens in 2 clicks while the calendar notification is on screen. For an architect sharing drawings: the link is in their clipboard before they switch to their email client. For a builder sharing specs: they don't need to know what "Policy" means.

### Implementation effort

~4 hours. One new component (`QuickSharePopover.jsx`), small additions to `UploadScreen.jsx`. No backend work. No API changes. No database changes.

### Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| User creates a link with defaults they didn't intend (e.g., no password on a sensitive document) | Medium | Popover clearly states "Shared with defaults — watermark on, download off." "Configure settings →" link is visible immediately. |
| Link creation fails (network error) | Low | Phase → error state with retry button and clear error message. |
| User expects Quick Share to show a form before creating the link | Low | The instant-create is the design intent. Users who want forms use the Configure path. Copy in the popover sets expectations. |
| Popover positioning issues on small screens | Low | Fixed 320px width. If the button is near screen edge, CSS can flip popover direction. Tested in implementation. |

---

## Workstream 2 — Viewer Open Notifications

### What it does

Completes the SSE notification loop for the `link.viewed` event. The backend dispatch (`dispatch_webhook_event` + `publish_notification`) is already implemented in `viewer_session_service.py`. The remaining work is: (a) add query-param token support to the SSE endpoint so `EventSource` can authenticate, (b) add a `useNotificationStream` hook in AppShell, (c) wire a toast for `link.viewed` messages.

Full design in `VIEWER_OPEN_NOTIFICATION_PLAN.md`.

### Expected impact

| Metric | Before | After |
|---|---|---|
| Real-time notification when document opened | NOT AVAILABLE | AVAILABLE |
| Consultant 30-second test (awareness flow) | IMPOSSIBLE | PASS |
| Webhook delivery for link.viewed | Already working | Unchanged — continues working |
| DocSend competitive parity on "know when opened" | NO | YES |

### User value

The consultant persona's primary need — "did they read my proposal?" — is fulfilled. A toast appears in the owner's browser within seconds of the viewer opening the document. No manual checking of the Access Log or Analytics screen. This is the feature that makes the product worth recommending to anyone who uses document sharing professionally.

### Implementation effort

~4 hours. Backend: 1.5 hours (SSE endpoint query param auth). Frontend: 2 hours (hook + AppShell wiring + toast). Testing: 0.5 hours.

### Key technical note

The backend is already dispatching `link.viewed` events (both webhook and SSE publish). The only missing piece is the browser connection. Once the SSE connection is established, every document opened by any viewer immediately surfaces to the owner — with zero additional backend work.

### Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Token in query param appears in server logs | Medium | HTTPS is already required. Logs can be configured to scrub query params. Short-lived tokens (Option 2) are available as a future upgrade if required by compliance. |
| EventSource does not reconnect cleanly on token expiry | Low | On 401, EventSource fails. Hook closes connection. No error shown to user — missing a notification on logout is acceptable. |
| Redis unavailable | Very low | Already guarded by try/except in `publish_notification`. Owner misses one toast; view is still logged in analytics. |
| Multiple tabs open (owner) | Low | Each tab holds one SSE connection. Per-user limit is 5. Two tabs = 2 connections. Toast appears in every open tab — minor UX annoyance, not a failure. |
| Viewer opens document during owner page refresh | Low | Notification missed for that specific event. EventSource reconnects; future opens are captured. |

---

## Workstream 3 — Language Simplification

### What it does

25 label renames, 2 tool removals from the viewer toolbar (laser pointer, magnifier), 1 tab merge (Annotations into Reviews/Feedback), and the removal of Storage from the primary navigation — all with zero behavior changes.

Full KEEP/RENAME/REMOVE table in `UX_LANGUAGE_REVIEW.md`.

### Expected impact

| Metric | Before | After |
|---|---|---|
| "Access Control" clicks that lead to confusion | High (mislabeled screen) | Low (now labeled "Share") |
| First-time users who understand Share Settings form without help | ~30% | ~70% |
| Toolbar items in viewer | 15+ | 13 (2 removed) |
| Visible form fields on Share Settings | 11 | 6 (plus 4 in Advanced collapse) |
| Primary nav items | 6 | 5 |

### User value

Every user who visits the Share screen benefits from "Share Settings" instead of "Policy." Every user who clicks "Create Share Link" instead of "Save Policy" knows what just happened. Every user who sees the viewer toolbar with 13 items instead of 15 finds their tool faster. The benefit is not dramatic on any single interaction — it compounds across every session.

### Implementation effort

~3.5 hours. Pure text and layout changes. No API changes. No database changes. No backend changes. Highest ratio of user impact to engineering effort of any workstream.

### Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Power users are confused by renamed labels | Very low | The renames move toward plain language. Any user who understood "Policy" will understand "Share Settings." The reverse is not true. |
| can_right_click removal causes complaint | Low | The field is still accessible via "Advanced" or can remain visible with a caveat added. This is a design-level decision. |
| Annotations tab merge causes loss of discoverability | Low | Merge is handled by a filter toggle within the Reviews tab. Annotations are still visible — they are co-located rather than separated. |

---

## Rollout Sequence

The three workstreams are independent. Each can ship separately. Recommended order based on risk and impact:

### Phase 1 — Language Simplification (ship first)

**Why first:** Lowest risk, zero behavior change, benefits every user immediately. Can be reviewed and approved by any stakeholder in 30 minutes by reading the label diff. If anything is wrong, a text change is the easiest possible rollback.

**Ship condition:** All label renames applied, toolbar cleaned up, manual smoke test on all screens.

### Phase 2 — Quick Share (ship second)

**Why second:** Highest adoption impact. Small surface area. Failure mode is an error toast — no data loss, no broken existing functionality. Existing Access Control path is completely unchanged.

**Ship condition:** Quick Share button appears on ready documents. Popover opens with URL. Copy works. Error state shows on API failure. Configure link navigates correctly. Click-outside and Escape close the popover.

### Phase 3 — Viewer Open Notifications (ship third)

**Why third:** Requires the most careful testing — involves a backend auth change and a persistent browser connection. Failure in this workstream does not break any existing feature; it only means the notification doesn't appear. Risk is low but testing surface is larger than the other two workstreams.

**Ship condition:** SSE connection established after login. `link.viewed` toast appears within 3 seconds of viewer opening document. Toast does not appear when owner views their own document via the Viewer nav item (validate only fires for shared link access, not owner preview). Connection closes cleanly on logout.

---

## What This Does NOT Include

Per sprint rules: no enterprise features, no admin features, no developer features.

The following improvements from TOP_10_PRODUCT_IMPROVEMENTS.md are explicitly deferred:
- Rank 4: Analytics range filter fix (requires backend query param work — separate sprint)
- Rank 5: Pre-select document between screens (straightforward but not top-3)
- Rank 6: Forensic watermark badge in viewer (valuable but low frequency)
- Rank 7: Feedback promotion (larger surface area, separate sprint)
- Rank 8–10: Storage nav removal, toolbar cleanup, active link badge (can accompany Language Simplification if approved)

---

## Combined Risk Register

| Risk | Severity | Workstream | Mitigation |
|---|---|---|---|
| Quick Share creates unintended links with default settings | Medium | 1 | Popover states defaults clearly; Configure path always available |
| SSE token in URL appears in access logs | Low | 2 | HTTPS required; log scrubbing available; Option 2 (short-lived token) available as upgrade |
| Label renames confuse existing users | Very low | 3 | Renames move toward plain language; no behavior changes |
| Workstream 2 backend change introduces regression in SSE stream | Low | 2 | Change is additive (new query param path); existing header-auth path unchanged |
| Multiple toasts on repeated document opens | Low | 2 | Each validate call fires a notification; acceptable for current scale |

---

## Definition of Done

Sprint 4.6 is complete when:

- [ ] "↗ Share" button appears on Upload screen document rows (ready docs only)
- [ ] Clicking Share creates a link with defaults and shows the URL in a popover
- [ ] Copy button in popover writes URL to clipboard; shows "✓ Copied" confirmation
- [ ] Configure link in popover navigates to Share screen with doc pre-selected
- [ ] SSE endpoint accepts `?token=` query param for authentication
- [ ] Owner's browser receives `link.viewed` toast within 3 seconds of viewer opening a shared document
- [ ] Nav label "Access Control" reads "Share"
- [ ] "Policy" tab reads "Share Settings"
- [ ] "Save Policy" button reads "Create Share Link"
- [ ] "Access Log" tab reads "Who Viewed"
- [ ] "Share Link" tab reads "Active Links"
- [ ] "Feedback" tab reads "Reviews"
- [ ] Laser pointer removed from viewer toolbar
- [ ] Magnifier removed from viewer toolbar
- [ ] Share Settings form shows 6 fields by default; remaining 4 behind Advanced collapse
- [ ] No database migrations
- [ ] No API contract changes
- [ ] All four owner-persona 30-second tests pass
