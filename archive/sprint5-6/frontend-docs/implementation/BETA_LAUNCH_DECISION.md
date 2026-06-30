# Beta Launch Decision — Sprint 4.8C Phase 5

**Date:** 2026-06-23  
**Basis:** BETA_LAUNCH_CHECKLIST.md, source code verification across all Sprint 4.8A/B/C commits  
**Tests:** 13/13 passing  
**Build:** Clean

---

## Decision: LAUNCH

SecureDoc is ready for a self-serve beta on desktop browsers.

---

## Evidence

### All 4 beta-blocking conditions from BETA_READINESS_FINAL.md are resolved

**Condition 1 — ⌕ Filter stub:** Removed. `UploadScreen.jsx:204` no longer renders the non-functional button. The inline search at line 268 remains.

**Condition 2 — Mobile / sidebar:** Desktop-only gate added at `AppShell.jsx:75`. Viewports narrower than 768px are blocked with a clear message directing users to a desktop browser. No broken mobile experience ships.

**Condition 3 — Feedback discoverability:** Feedback is now a first-class nav item in the sidebar (Security section, `atoms.jsx:233`). Clicking it navigates directly to the Feedback tab. When a document is selected and has open threads, the count appears as a badge on the sidebar item. Users no longer need to know that feedback lives inside "Access Control."

**Condition 4 — Post-upload CTA:** "Configure Access →" renamed to "Share Document →" in `UploadProgressPanel.jsx:25`. The first action a user takes after uploading now uses the language of sharing, not security configuration.

---

## What is Ready

### Workflows that pass end-to-end verification

| Workflow | Verdict |
|---------|---------|
| Upload PDF, see it in document list | PASS |
| Click document row → opens Viewer | PASS (fixed 4.8A) |
| QuickShare: hover → one click → copy URL | PASS |
| Create Link with policy (expiry, email restriction, password, permissions) | PASS |
| Edit existing link without creating new URL | PASS (fixed 4.8A) |
| Revoke link (single or all) | PASS |
| Viewer: read document, annotate, bookmark, search | PASS |
| Viewer: "← Docs" returns to document list | PASS (added 4.8A) |
| Share link with recipient → they open it in viewer | PASS |
| Owner sees viewer feedback → replies → resolves | PASS (fixed 4.8A/C) |
| Feedback discoverable from sidebar without prior knowledge | PASS (added 4.8C) |
| Analytics: view counts, page heatmap, group breakdown | PASS |
| Storage: per-document usage with group and retention controls | PASS |
| Billing: plan status, Stripe upgrade flow | PASS |
| API Keys: create, scope, revoke | PASS |
| Webhooks: create, test, delivery history | PASS |
| Notifications: event feed, activity stream | PASS |

### Security properties that hold

- All owner endpoints verified via JWT (user_id check on every document/link/annotation operation)
- Viewer sessions are separate from owner JWT — public access does not bleed into authenticated scope
- PATCH /api/links/{id} calls `invalidate_link()` — in-flight viewer sessions see policy changes within one page turn
- IP allowlist, domain restriction, password, expiry, max views, max concurrent sessions all enforced server-side
- Watermark enabled by default in QuickShare (cannot be accidentally disabled)
- Rate limiting on all write endpoints (`@limiter.limit("30/minute")`)

---

## Known Limitations (acceptable for beta)

These items are documented, do not block the launch, and are tracked in the watch list:

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| No URL routing | Browser back/forward inoperative; refresh returns to Upload | Low friction for a new user; communicate in beta onboarding email |
| Desktop-only (< 768px blocked) | Mobile users cannot access the app | Expected for this beta cohort; message is clear |
| Org member add requires raw Supabase UUID | Adding team members to an org is manual | Orgs is a secondary feature; most beta users operate solo |
| Notifications sidebar badge not wired | Unread event count not visible without opening the screen | Notifications screen is directly accessible; event feed works |
| Analytics document rows non-navigable | Clicking a row in the analytics table does nothing | View history is accessible via the Links → View History tab |
| Risk badge criteria undocumented | HIGH/MED/LOW displayed without tooltip | Does not block any workflow; add tooltip in next sprint |

---

## Terminology Improvements Shipped (4.8C)

Labels that confused users in 4.8B are corrected:

| Was | Now | Location |
|-----|-----|---------|
| "⌕ Filter" (non-functional) | Removed | Upload header |
| "Configure Access →" | "Share Document →" | Post-upload CTA |
| "Policy" tab | "Create Link" tab | Access Control |
| "Share Link" tab | "Links" tab | Access Control |
| "Access Log" tab | "View History" tab | Access Control |
| Feedback (hidden) | Feedback (sidebar nav item + badge) | Sidebar |

---

## Scores After 4.8C (updated from BETA_READINESS_FINAL.md)

| Dimension | 4.8B Score | 4.8C Score | Change |
|-----------|-----------|-----------|--------|
| Product Experience | 6/10 | 7.5/10 | Filter removed, labels fixed, CTA improved |
| Discoverability | 5/10 | 8/10 | Feedback in sidebar with badge |
| Workflow Quality | 7/10 | 7.5/10 | All primary workflows verified |
| Consistency | 5/10 | 7/10 | 5 terminology fixes shipped |
| Responsiveness | 3/10 | 6/10 | Desktop-only gate; no false mobile experience |
| Security | 9/10 | 9/10 | Unchanged — already production-grade |
| Reliability | 8/10 | 8/10 | Unchanged |

**Updated average: 7.6 / 10**

---

## Launch Scope

**Beta audience:** Founders, consultants, and professionals sharing documents with external parties on desktop browsers.

**Not included in this beta:** Mobile users, org multi-member collaboration (member-add UX), push email notifications, URL deep-linking.

**Beta success criteria (not defined here — for the team to set):** Suggested metrics: link creation rate, feedback thread creation rate, viewer session completion rate, return visit rate within 7 days.

---

## Commit History (Sprint 4.8C)

```
d8065d4  feat(mobile): block unsupported screen sizes with clear desktop-only notice
e8fef25  feat(nav): add Feedback sidebar entry with open-thread badge
1669da8  fix(terminology): rename misleading tab labels in Access Control
51e4b7f  fix(ux): remove non-functional Filter stub, rename post-upload CTA
```

Sprint 4.8A commits (workflow fixes):
```
741d537  feat(storage): add group column to Storage screen
0b09848  feat(feedback): add Resolve/Reopen action for owner feedback threads
1c3aaac  feat(viewer): add back-to-docs button in ViewerToolbar
4547d73  fix(docs): clicking a document row opens Viewer instead of Access Control
01b8892  feat(links): add Edit Link workflow and fix Policy button label
b4e04b9  feat(api): wire PATCH /api/links/{id} and owner feedback resolve
```

---

## LAUNCH

All blocking conditions resolved. Build is clean. Tests pass. Push to origin.

---

*Generated: Sprint 4.8C Phase 5 — ready to push.*
