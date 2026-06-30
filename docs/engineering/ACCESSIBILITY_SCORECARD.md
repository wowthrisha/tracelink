# Accessibility Scorecard
**Generated:** 2026-06-30  
**Standard:** WCAG 2.1 AA  
**Baseline:** 4.25/10 (from Accessibility Review, 2026-06-30)

---

## Score Comparison

| Principle | Before | After | Δ |
|-----------|--------|-------|---|
| Perceivable | 3/10 | 4.5/10 | +1.5 |
| Operable | 4/10 | 5/10 | +1.0 |
| Understandable | 5/10 | 6/10 | +1.0 |
| Robust | 5/10 | 6.5/10 | +1.5 |
| **Overall** | **4.25/10** | **5.5/10** | **+1.25** |

---

## Issues Resolved

| ID | Issue | Fix |
|----|-------|-----|
| AX-004 | Form fields not labeled | `Field` component now uses `<label>` wrapping `<input>` |
| AX-005 | Icon-only buttons without aria-label | Added `aria-label` to all `✕`, `↗`, `✎` buttons |
| AX-006 | Table headers missing `scope` | Added `scope="col"` to all `<th>` in 4 tables |
| AX-009 | Toast container not announced | Added `role="status"` + `aria-live="polite"` to toast container |
| AX-010 | `window.confirm()` inaccessible | Replaced with `<Modal>` component |
| AX-002 (partial) | Modal has no ARIA | Added `role="dialog"`, `aria-modal="true"`, `aria-label={title}` to `Modal` component |

---

## Issues Remaining

| ID | Issue | Effort | Status |
|----|-------|--------|--------|
| AX-001 | No semantic HTML (`<nav>`, `<main>`, heading hierarchy) | M | Partial — `<nav>` already in Sidebar; `<main>` not added; no heading hierarchy |
| AX-002 | No focus management in modals | M | Partial — role/aria added; focus trap not implemented |
| AX-003 | Color-only status indicators | M | Not addressed — needs design system update |
| AX-007 | Low contrast muted/dim text | S | Not addressed — needs color audit |
| AX-008 | Hard block at 768px | L | Not addressed (RD-005) |
| AX-011 | Keyboard trap in viewer | M | Not addressed |
| AX-012 | autoFocus without context | S | Not addressed |

---

## What Would Achieve WCAG 2.1 AA

1. Add focus trap to all modals (focus lock on open, return on close) — 2 days
2. Add `<main>` landmark and heading hierarchy (`h1`, `h2`) — 1 day
3. Audit color contrast for `C.textMuted` and `C.textDim` — 1 day
4. Add text/icon alternatives for color-only status — 1 day
5. Fix mobile block (RD-005) — 2–3 weeks

Items 1–4 total: ~5 days. Would bring score to approximately **7.5/10**.
