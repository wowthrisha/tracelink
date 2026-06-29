# CHANGELOG — Sprint 6.1 Product Polish
**Date:** 2026-06-29

---

## [Sprint 6.1 Final Product Polish] — 2026-06-29

### Fixed

- **UX-001** `frontend/src/screens/UploadScreen.jsx` — Upload button label changed from "↑ Upload PDF" to "↑ Upload". The button accepts PDF, DOCX, DOC, TXT, MD, and LOG files — the "PDF" label was actively misleading.

- **UX-002** `frontend/src/screens/UploadScreen.jsx`, `frontend/src/screens/AnalyticsScreen.jsx` — Stat card "Total Views" renamed to "Views Today" on both Upload Dashboard and Analytics Overview. The underlying data field is `total_views_today` (today's count only). The old label implied an all-time total, causing confusion when compared against the document performance table which shows historical totals.

- **UX-003** `frontend/src/screens/NotificationsScreen.jsx` — `eventLabel()` function expanded from 5 mappings to 25+. Raw backend event types (`opened`, `page_viewed`, `completed`, `password_wrong`, `print_attempt`, `copy_attempt`, `right_click_attempt`, `download_attempt`, `printed`, `access_denied`, `ip_blocked`, `expired`, `revoked`, `max_views_reached`, `session_limit_reached`, and 10 admin/webhook types) now map to human-readable labels. Previously, all these types fell through to the default `return type` — displaying raw snake_case strings to users.

- **UX-004** `frontend/src/screens/BillingScreen.jsx` — Billing "not configured" notice no longer shows the environment variable name `STRIPE_SECRET_KEY`. Previous text: "Set `STRIPE_SECRET_KEY` to enable upgrades." New text: "Contact your administrator to enable paid plan upgrades."

- **UX-005** `frontend/src/components/atoms.jsx` — `RiskBadge` component added early return for missing/unknown `level`. Previously rendered a styled `<span>` with empty content and a visible border (looked like an unchecked checkbox) when `level` was undefined. Now renders a plain "—" dash.

- **UX-006** `frontend/src/screens/AccessScreen.jsx` — Removed `|| 'HIGH'` fallback from risk badge in the document header. Documents with no risk score now display the "—" badge from the fixed `RiskBadge` component instead of an incorrect "HIGH" (red) badge.

- **UX-007** `frontend/src/components/DocumentPicker.jsx` — Fixed grammatical errors in document subtitle. "1 pages · 1 views" → "1 page · 1 view". Conditional pluralization applied to both page count and view count.

---

## Test Suite

1624 passed / 1 skipped across all Sprint 6.1 changes. Zero regressions. Backend code was not modified.

---

## [Sprint 6.0 Engineering Excellence] — 2026-06-29

See `frontend/docs/certification/CHANGELOG.md` for Sprint 6.0 entries (FIX-005 through FIX-011).
