# TODO Queue — V10.0

Working queue, most valuable/safest first. Append-only discipline: strike through completed items rather than deleting.

## Completed this session

1. [x] H-1: Fix broken shake-animation keyframe (`AccessGate.jsx`) — done.
2. [x] ~~H-2: Implement real arrow-key page navigation~~ — false positive, already existed, no change needed.
3. [x] H-3: Migrate 9 hand-rolled modals onto shared `Modal` component — done (ApiKeysScreen ×2, WebhooksScreen ×3, OrgsScreen ×4).
4. [x] M-1: Pass `label` prop to the 2 unlabeled `Toggle` call sites — done.
5. [x] M-2: Add missing `aria-label`s — investigated, no genuine defect found on the 6 flagged screens (already accessible via visible text).
6. [x] ~~H-6: Add production-time enforcement for `ip_hash_salt`/`domain_verify_salt`~~ — false positive, `main.py` already enforces this.
7. [x] H-7: Fix `viewer.py:download_document` blocking PDF write — done.
8. [x] M-4: Add loggers to genuinely-silent-except routers — done for the 2 real gaps found (`links.py`, `webhooks.py`); 13 of 15 originally-flagged sites were false positives (already logged internally or benign).
9. [x] M-3: Add a spacing-token scale to `tokens.js` — done (additive).
10. [x] M-9: Standardize delete/revoke toast severity — done for `AccessScreen.jsx`'s 2 single-link toasts (info→success, matching the app-wide convention); left the bulk "Revoke All Access" toast's `error` severity unchanged since it appears to be a deliberate pre-existing emphasis choice for a higher-stakes action, not an inconsistency.

## Completed 2026-07-24

11. [x] Non-technical-user terminology pass — audited all 12 screens via research agent (22 findings), fixed the 9 highest-traffic/highest-severity gaps: `AccessScreen.jsx` Watermark/IP-Allowlist/Info-Panel hints (+ fixed a previously-missed unlabeled `Toggle`), `AnalyticsScreen.jsx` "DRM events" self-reference removed, `UploadScreen.jsx`/`StatCard.jsx` Blocked Attempts tooltip parity, `ApiKeysScreen.jsx` Scopes explainer (both modals), `WebhooksScreen.jsx` plain-language lead sentence, `OrgsScreen.jsx` "optional, skip if alone" clause, `AuditLogScreen.jsx` intent-first subtitle, `BillingScreen.jsx` Watermarking row hint. Left `StorageScreen.jsx`'s low-traffic multi-org-only header and the inherently-developer-facing technical detail on API Keys/Webhooks screens unchanged — see Entry 5 in `ACTION_LOG.md` for full reasoning. Verified: frontend 13/13 tests passed, build clean.

## Completed 2026-07-24 (live QA sprint, docs/ui-audit/)

12. [x] Full workflow-completion end-to-end walkthrough — done live against the deployed Railway instance via Playwright, all 7 workflow groups. See `WORKFLOW_VALIDATION.md`, `WORKFLOW_COMPLETION_MATRIX.md` at repo root. Found + fixed 3 real bugs (WATERMARK-001 critical, READ-OWNER-001 high, BILLING-PLAN-BADGE-001 high), committed as `e7ddf47`.
13. [ ] Per-button validation audit — still not done as a dedicated pass; largely superseded by the live workflow walkthrough's coverage.
14. [ ] Dead-code re-sweep for anything new since V6.0's sweep.

## Not started — next up (V11.0 Viewer Excellence mission, 2026-07-25)

15. [ ] Fix real bug: "Insights" button/modal renders and is clickable for public share-link viewers, not just the owner — causes a 401 → forced page reload for a real viewer. Gate to owner-preview only.
16. [ ] Build viewer-facing page-insights panel (avg reading time on this page, difficulty rating, predicted remaining, pace vs. average reader) — genuinely new, does not exist today (only computed server-side for uploader-only endpoints).
17. [ ] Add `show_reading_insights` permission toggle (reusing the existing `ShareLink.permissions` pattern, not a new generic feature-toggle framework — see reasoning in `ARCHITECTURE_DECISIONS.md`) so uploaders control whether viewers see item 16's panel.
18. [ ] Fix real bug: `ViewerErrorBoundary.jsx` renders raw `String(error)` to users instead of a sanitized, friendly message.

## Completed 2026-07-26 (V12.0 Final Production Certification)

19. [x] Re-verify all 3 V10.0 fixes live in production — confirmed watermark, owner-lockout, and plan-badge all fixed (commit `e7ddf47` was pushed and auto-deployed by Railway during this session).
20. [x] Deep live Viewer certification — search, zoom, keyboard page nav, fullscreen, Links panel, thumbnails, annotation-permission gating all verified working.
21. [x] Live Access Control permission verification — found and fixed AUDIT-LINK-COMMIT-001 (link.created/updated/revoked events silently never persisted to the audit log); verified Edit Link propagates live to active viewer sessions end-to-end.
22. [x] Reading Intelligence end-to-end live verification — pause/resume-on-blur confirmed (plus an undocumented content-blur security behavior), uploader-side data confirmed real/non-fabricated.
23. [x] Scoped accessibility + responsive pass — keyboard-only nav confirmed fully functional, mobile block confirmed intentional (matches AD-6).

## Not started — next up (from V12.0)

24. [ ] Fix WATERMARK-OWNER-ANON-001 (owner's own preview watermark shows "anonymous" instead of their real email) — noted, deserves its own scoped look alongside the READ-OWNER-001 owner-preview-link machinery rather than a rushed fix.
25. [ ] Deploy the V11.0 (viewer-facing reading insights, error boundary) and V12.0 (audit-commit) fixes — all still local-only.

## Explicitly NOT queued (see `ARCHITECTURE_DECISIONS.md` for why)

- AUTH-006 (localStorage token migration), full pagination rollout, typed-schema migration for 7 routers, `links.py` DELETE status-code API changes, `AccessScreen.jsx` 3-way split, doc-set consolidation, backup-service default flip, responsive/mobile support.
- V11.0 mission items explicitly scoped OUT this session: a generic feature-toggle framework (tooltip/help-text/audit/permission/endpoint metadata for ~12 separate toggles), device/browser/country/timezone capture, reading-replay/timeline UI, reading-speed trend charts, and wiring the Reading Intelligence Engine's data into `AnalyticsScreen.jsx` as a dedicated dashboard tab (it's already fully exposed via `InsightsModal.jsx`, reachable from the Viewer toolbar). These are each real, multi-day feature builds in their own right — building them shallowly to hit a checklist would produce unverified, likely-broken code, which is worse than not building them. See `ARCHITECTURE_DECISIONS.md` for the full reasoning per item.
- V12.0 mission items explicitly scoped OUT: full WCAG 2.2 AA audit, full performance profiling (N+1 queries, render-count analysis, memory leaks), full dead-code sweep, offline/slow-network simulation. Each is a genuine multi-day audit in its own right.
