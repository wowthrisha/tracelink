# Changelog

All notable changes to SecureDoc are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — Engineering remediation from product-audit triage

Triaged all 49 issues from the `TraceLink_Product_Audit` artifacts against the current implementation before touching any code — see `ENGINEERING_TRIAGE.md` for the evidence-integrity findings and `VERIFIED_ISSUES.md` for the disposition of every issue. Base commit `2c1795f`; changes below are uncommitted pending an explicit commit instruction.

### Fixed

- **AUTH-001** `frontend/src/screens/LoginScreen.jsx` — Signup form now shows a password-length hint ("At least 6 characters.").
- **AUTH-002** `frontend/src/screens/LoginScreen.jsx` — Password field gained a Show/Hide visibility toggle.
- **AUTH-007** `frontend/src/screens/LoginScreen.jsx` — Network failures on login (`Failed to fetch`, etc.) now show "Unable to reach the server. Check your connection and try again." instead of the raw browser error.
- **DASH-001** `frontend/src/components/atoms.jsx` — Documents screen retitled from "Upload Dashboard" to "Documents" — the screen is a full document hub, not just an upload tool.
- **DASH-003** `frontend/src/screens/UploadScreen.jsx` — Security/watermark notice moved from a 10px footer line to a bordered banner near the top of the screen.
- **DASH-008** `frontend/src/components/upload/UploadMetadataPanel.jsx` — "+ New group" button changed from `ghost` to `secondary` variant for visibility.
- **ANAL-006** `frontend/src/screens/AnalyticsScreen.jsx` — Groups analytics widget no longer silently truncates past 5 groups; added a "Show all N" / "Show fewer" toggle.

### Deferred (planned, not implemented this cycle)

- **AUTH-006** — Session-token storage hardening (`localStorage` → httpOnly cookie). Real XSS-exposure finding, but the correct fix is an auth-architecture migration touching 60 frontend call sites and 72 backend dependency sites — full plan in `SECURITY_HARDENING_PLAN.md`.
- **PROF-001** — In-app profile/account settings screen does not exist. New-feature scope, not a bug fix — proposal in `PRODUCT_PROPOSAL.md`.
- **AUTH-004** — No ToS/Privacy links on signup. Blocked on legal content that doesn't exist yet in this repo; a link to a nonexistent page would be worse than the current state.

### Investigated, not changed — audit claims found inaccurate

- **ACCESS-006, AUDIT-001, ORG-001** — each claims a protection is missing; in all three cases the protection already exists in current source (confirmation modal, admin-role check, unprotected-link warning respectively). No code change made.
- **AUTH-003, AUTH-005, ACCESS-003** — describe intentional design choices or unavoidable properties of client-side REST calls, not defects.

### Verification

`npm test` (frontend, 13/13 passed) · `npm run build` (succeeded) · `pytest tests/unit tests/integration tests/regression` (backend, 1699 passed / 1 skipped / 0 failed) · diff scanned for TODO/FIXME/console.log/debugger (none found).

### Outstanding

30 of the 49 audited issues sit on 12 screens the audit's own session-tracking confirms were never opened in a browser; their evidence traces to static inspection of the minified production bundle rather than observed behavior. None were implemented — see `VERIFIED_ISSUES.md` for the full list. They need a genuine browser re-validation pass before further action.

---

## [8.1.0] — 2026-06-30 — Release Candidate 1

### Fixed

- **FIX-007** `backend/app/routers/viewer.py` — Removed duplicate `_session_watermark_angle` definition. Canonical implementation is in `app/services/viewer_service.py`. Stale `import hashlib as _hashlib` also removed. Test import paths corrected in `test_phase7.py`.

### Certification

1624 passed / 1 skipped / 0 failures. See [`docs/release/RC1_CERTIFICATION.md`](docs/release/RC1_CERTIFICATION.md).

---

## [8.0.0] — 2026-06-29 — Sprint 6.1 Product Polish

### Fixed

- **UX-001** `frontend/src/screens/UploadScreen.jsx` — Upload button changed from "↑ Upload PDF" to "↑ Upload". The button accepts PDF, DOCX, DOC, TXT, MD, and LOG files.
- **UX-002** `frontend/src/screens/UploadScreen.jsx`, `AnalyticsScreen.jsx` — "Total Views" stat card renamed to "Views Today". The underlying field `total_views_today` is today's count only, not all-time.
- **UX-003** `frontend/src/screens/NotificationsScreen.jsx` — `eventLabel()` expanded from 5 mappings to 25+. All backend event types now display human-readable labels (previously showed raw snake_case).
- **UX-004** `frontend/src/screens/BillingScreen.jsx` — Billing "not configured" message no longer exposes the `STRIPE_SECRET_KEY` environment variable name.
- **UX-005** `frontend/src/components/atoms.jsx` — `RiskBadge` returns `—` instead of an empty bordered box when `level` is undefined.
- **UX-006** `frontend/src/screens/AccessScreen.jsx` — Removed `|| 'HIGH'` fallback; documents with no risk score now show `—` instead of a red HIGH badge.
- **UX-007** `frontend/src/components/DocumentPicker.jsx` — Fixed "1 pages · 1 views" grammar; both counts are now conditionally pluralized.

---

## [7.x] — Sprint 6.0 Engineering Excellence

Key fixes from Sprint 6.0 (FIX-005 through FIX-011):

- **FIX-005** `documents.py` — Storage import moved to module level
- **FIX-006** `analytics.py` — `func` imported at module level (not inside function)
- **FIX-008** `analytics_service.py` — `_by_link` helper moved to module level
- **FIX-009** `orgs.py` — `asyncio.get_running_loop()` replaces deprecated `get_event_loop()`
- **FIX-010** `links.py` — Removed redundant document fetch in `list_links`
- **FIX-011** `retention.py` — Sidecar prefixes tuple includes all four types (`toc`, `text`, `links`, `words`)

For full Sprint 6.0 details see [`archive/sprint5-6/frontend-docs/certification/`](archive/sprint5-6/frontend-docs/certification/).
