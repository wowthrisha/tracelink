# Hidden Feature Recommendation
Production Readiness — Hidden Feature Recovery, Phase 5
Date: 2026-06-22

---

## Ranking

### Tier 1 — Ship Immediately (Sprint 4.4)

**SSE Real-Time Notifications**
**API Keys**

These two have the best ROI in the entire codebase: the backend is fully production-ready, the frontend work is minimal (0.5d and 1d respectively), and they deliver immediate user-visible value.

**SSE Notifications** specifically requires zero new screens and zero nav changes. It is a hook wired into existing AppShell infrastructure. The `document.processed` event is already being published from `tasks.py` — users are getting zero benefit from it today. After wiring, every document upload shows a toast notification when processing completes. This is table-stakes polish that every async-upload product has.

**API Keys** unlock the developer market. The backend has SHA-256 key storage, 7 scopes, expiry, audit logging, and full CRUD. The frontend work is one new screen in a new "Developer" nav section. There is no UX complexity — it is a standard token management screen that every developer-facing product has (GitHub, Stripe, Vercel all have an identical UI pattern).

**Prerequisites before shipping:**
1. Sprint 4.3 security hardening must complete first (the `link.url` javascript: guard fix — Action 1 from NEXT_10_ACTIONS.md)
2. Verify that `GET /api/notifications/stream` accepts JWT via query parameter or implement a mechanism for EventSource auth (EventSource does not support Authorization headers natively)

---

### Tier 2 — Ship After Security Sprint (Sprint 4.4 or 4.5)

**Webhooks**
**Admin Audit Log**

**Webhooks** are the second natural extension of the Developer screen being built for API Keys. Since the DeveloperScreen tab structure is being created for API Keys, adding a Webhooks tab is incremental work on top of an already-planned screen. The backend is fully production-ready (HMAC signing, retry logic, SSRF protection, delivery logs, test-fire).

One pre-ship fix required: **the `link.viewed` event is never dispatched from `viewer.py`**. The event type exists in `WEBHOOK_EVENTS` and users will be able to subscribe to it in the UI, but they will never receive a delivery. Before shipping the Webhooks UI, either:
- Wire `dispatch_webhook_event(db, user_id, event_type="link.viewed", data={...})` into `viewer.py:validate` — this is a single `try/except`-wrapped call, matching the pattern in `tasks.py:188-191`. This also simultaneously activates the SSE `link.viewed` notification by adding the matching `publish_notification` call.
- Or hide `link.viewed` from the UI event type list with a "coming soon" badge.

**Admin Audit Log** has low customer value for current solo users but LOW effort (0.5 days). It should ship as a personal audit tab in the Analytics screen OR as a tab inside the Organization screen. The data is already being written — surfacing it is a read-only display exercise. Dependency: if shipped as an org tab, Organizations must be built first; if shipped as a standalone personal view, it has no dependencies.

---

### Tier 3 — Not Worth Shipping Yet

**Organizations (in current form)**

Organizations have HIGH business value and HIGH customer value — but the current backend has a UX-breaking constraint that makes the feature near-unusable without a prior backend change.

**The blocker: member invitation requires the target user's Supabase UUID.** There is no user lookup by email, no invitation email, no pending invite state. An admin who wants to add a colleague must somehow obtain that colleague's Supabase UUID and paste it into a form field. This is not viable for non-technical users. Shipping this UI as-is would generate constant support tickets, create a frustrating first impression of team features, and potentially increase churn among users who try the feature and find it confusing.

**Condition to move to Tier 2:** The backend must add one of:
- A `GET /api/users?email={email}` endpoint to look up a user by email (requires careful auth — only admins should be able to look up users, and only after confirming they're already in the system)
- A `POST /api/orgs/{id}/invitations` flow that sends an email invitation (requires email notification backend from NEXT_10_ACTIONS Action 3)

Once either of those exists, the Organizations UI becomes viable and should be promoted to Tier 2.

**What can be shipped from Organizations without the UX blocker:**
- The "create your first organization" flow (org name, slug) — works fine, no member add required
- The org settings screen (rename, custom domain verification) — works fine
- The audit log tab — works fine once user has an org

**Recommendation:** Ship org creation and settings now (low risk, works today). Gate the Members tab behind a "User lookup coming soon" state until the email-lookup or invitation backend is built.

---

## Decision Table

| Feature | Tier | Sprint | Gate | Est. Effort |
|---|---|---|---|---|
| SSE Notifications | **Ship Immediately** | 4.4 | EventSource auth method confirmed | 0.5d |
| API Keys | **Ship Immediately** | 4.4 | Sprint 4.3 security complete | 1d |
| Webhooks | **Ship After Security** | 4.4 | `link.viewed` wired in viewer.py | 1.5d |
| Admin Audit Log | **Ship After Security** | 4.4 | None (personal view standalone) | 0.5d |
| Organizations (full) | **Not Yet** | 4.5+ | Backend email lookup or invite flow | 3d |
| Organizations (create + settings only) | **Ship After Security** | 4.4 | None | 1d |

---

## The `link.viewed` Gap Is The Common Thread

Both SSE and Webhooks are significantly less valuable without `link.viewed` events. Today:
- `document.processed` — SSE fires ✅, Webhook fires ✅
- `link.viewed` — SSE does not fire ❌, Webhook does not fire ❌

The fix is **two lines** in `viewer.py:validate`, wrapped in try/except to match the existing pattern in `tasks.py`:

```python
# After successful session creation in POST /api/viewer/validate:
try:
    from app.services.webhook_service import dispatch_webhook_event
    await dispatch_webhook_event(db, user_id=str(doc.user_id), event_type="link.viewed", data={
        "document_id": str(doc.id),
        "token": token,
        "viewer_email": validated_email,
    })
except Exception:
    pass

try:
    from app.services.notification_service import publish_notification
    await publish_notification(str(doc.user_id), "link.viewed", {
        "document_id": str(doc.id),
        "viewer_email": validated_email,
    })
except Exception:
    pass
```

This is the single highest-ROI backend change in the codebase. It activates both Webhooks and SSE for the `link.viewed` event simultaneously, and it is the "notify me when my document is opened" feature that every DocSend competitor has. Two `try/except` blocks, zero schema changes, zero API contract changes.

This should be included in Sprint 4.4 alongside the frontend work.

---

## Summary

**Do now (Sprint 4.4, ~2 days total frontend):**
1. Wire `link.viewed` event in `viewer.py` (backend, ~15 min, high impact)
2. SSE hook in AppShell (0.5d)
3. API Keys screen (1d)

**Do next (Sprint 4.4 or 4.5, ~2 days):**
4. Webhooks screen — tab in DeveloperScreen (1.5d)
5. Admin Audit Log — personal view tab (0.5d)
6. Organization creation + settings screen (1d, gates members tab until invite flow built)

**Block until backend UX fix:**
7. Organization Members management tab — blocked on email lookup or invite backend
