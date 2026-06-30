# Changelog

All notable changes to SecureDoc are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

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
