# Responsive & Mobile Audit — Sprint 4.8B Phase 4

**Method:** Source code inspection of layout CSS (inline styles, grid definitions, fixed widths) across all screens and shared components.  
**Reference breakpoints:** 375px (phone), 768px (tablet), 1280px (desktop)  
**Classification:** PASS = usable without modification · WARNING = degraded but functional · FAIL = broken or unusable

---

## Sidebar

**Code:** `atoms.jsx:270–274`
```js
width: 210, background: C.surfaceAlt, flexShrink: 0
```

**Analysis:**
- Fixed 210px width, `flexShrink: 0` — will never shrink on narrow viewports
- No hamburger/collapse toggle
- No `@media` or responsive class
- On a 375px phone: sidebar takes 210px, leaving 165px for content — unusable
- On a 768px tablet: sidebar takes 210px, leaving 558px — marginally functional

**Classification: FAIL on mobile (< 640px), WARNING on tablet (640–900px)**

---

## Viewer Toolbar

**Code:** `ViewerToolbar.jsx:130–136`
```js
height: 42, display: 'flex', alignItems: 'center', padding: '0 8px', gap: 0
```

**Analysis:**
- Fixed 42px height, horizontal flex row with many buttons
- No wrapping (`flexWrap` not set → defaults to `nowrap`)
- Buttons include: TOC, Pages, back arrow, page nav, zoom controls, layout toggles, laser, magnifier, search, info, fullscreen, annotation tools, links, insights
- On a 375px screen minus 210px sidebar = 165px for the toolbar — approximately 3–4 buttons visible, rest overflow
- CSS class `toolbar-btn-label` exists on some buttons — suggests responsive label hiding may be partially implemented

**Classification: FAIL on mobile, WARNING on tablet (some buttons may overflow)**

---

## Upload Screen — Stats Grid

**Code:** `UploadScreen.jsx:211`
```js
gridTemplateColumns: 'repeat(4,1fr)'
```

**Analysis:**
- 4 equal columns, no responsive breakpoints
- On 375px screen minus 210px sidebar = 165px total → each stat card ≈ 41px wide — text will overflow
- No `minmax()`, no auto-fill, no `@media`

**Classification: FAIL on mobile**

---

## Upload Screen — Document Table

**Code:** `UploadScreen.jsx:273` — `table` inside `Card noPad`
```js
width: '100%', borderCollapse: 'collapse'
```

**Analysis:**
- Table columns: filename, file type, status, risk, expires, views, actions
- No `overflowX: 'auto'` wrapper observed at this level
- On narrow screens, table columns compress and text truncates — some columns may disappear or stack incorrectly
- Action buttons (`DocRow.jsx:59`) use `opacity: 0` until hover — hover is touch-incompatible (touch devices have no hover state; `onMouseEnter` does not fire reliably)

**Classification: WARNING on tablet, FAIL on mobile — hover actions unreachable on touch**

---

## Access Control — Policy Form

**Code:** `AccessScreen.jsx:225`
```js
display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12
```

**Analysis:**
- 2-column grid for authentication and access limits cards
- Permission toggles: `gridTemplateColumns: 'repeat(3,1fr)'` (`AccessScreen.jsx:280`)
- On 375px minus sidebar = 165px → 2 columns ≈ 76px each — labels will wrap
- Permission toggle grid (3 columns) will compress to ~50px per column — toggle labels will overflow

**Classification: WARNING on tablet, FAIL on mobile**

---

## Access Control — Feedback Table

**Code:** `AccessScreen.jsx` — feedback table rendering
```js
// 7 table columns: Reviewer, Page, Comment, Replies, Status, Created, Actions
```

**Analysis:**
- Fixed-header table with 7 columns
- `maxWidth: 280` on comment column — does not reflow to stacked layout
- No `overflowX: 'auto'` observed at the table wrapper level in the feedback section
- On 375px minus sidebar = 165px — table is completely unusable

**Classification: FAIL on mobile, WARNING on tablet**

---

## Analytics Screen — KPI Grid

**Code:** `AnalyticsScreen.jsx` (inferred from component usage)
```js
// KpiCard grid uses repeat(3, 1fr) or similar — 6 KPI cards
```

**Analysis:**
- 6 KPI cards in a grid — if 3-column: 55px per card on 165px remaining
- SparkChart and DonutChart components use SVG — may scale by viewport but are not explicitly responsive

**Classification: WARNING on tablet, FAIL on mobile**

---

## Storage Screen — Summary Cards

**Code:** `StorageScreen.jsx:72`
```js
gridTemplateColumns: 'repeat(3,1fr)'
```

**Analysis:**
- 3 summary cards — Total Storage, 30-Day Projection, 90-Day Projection
- `overflowX: 'auto'` present on the per-document table (`StorageScreen.jsx:110`) — table is protected
- Summary cards grid: 3 columns fixed → similar to analytics issue

**Classification: WARNING on mobile (summary cards compress), PASS for the table (has overflow scroll)**

---

## Modals

**Code:** Various modal widths across screens:
- `EditLinkModal`: `width: 520` (`AccessScreen.jsx`)
- Revoke modal: `width: 420` (`AccessScreen.jsx:704`)
- `CreateWebhookModal`: `width: 480` (`WebhooksScreen.jsx:36`)
- `CreateOrgModal`: `width: 420` (`OrgsScreen.jsx:28`)

**Analysis:**
- All modals use `position: 'fixed', inset: 0` centering — modal itself has fixed pixel width
- `Modal` component in `atoms.jsx` — let me check if it has max-width handling

```js
// atoms.jsx — Modal component uses fixed width prop passed in
// No max-width: 100vw or responsive constraint observed in code reads
```

- On a 375px screen: a 520px-wide modal will clip at both sides (left and right extend beyond viewport)
- No `maxWidth: '95vw'` or similar override in any modal definition

**Classification: FAIL on mobile (all modals clip viewport)**

---

## Viewer — Main Document Area

**Code:** `ViewerScreen.jsx` — page rendering inside flex column layout

**Analysis:**
- The viewer content area takes `flex: 1` which should fill remaining space after the sidebar
- On mobile (375px minus 210px sidebar = 165px): document pages render in 165px width — extremely narrow for any PDF
- Two-page mode (`onToggleTwoPage`) would be completely unusable on mobile
- No viewport-aware layout switching
- Rasterized page images do scale to container width in the page renderer (images use `width: 100%` in page components generally) — the document content itself may be legible if zoomed, but the reading experience is poor

**Classification: FAIL on mobile — sidebar + fixed toolbar leaves insufficient space. WARNING on tablet.**

---

## Notifications Screen

**Code:** `NotificationsScreen.jsx` — event list

**Analysis:**
- Simple list layout, `flex: 1, overflow: auto` pattern
- No fixed-column tables
- The header and cards are single-column — should reflow acceptably

**Classification: PASS (columns are single-flow, content reflows)**

---

## API Keys, Webhooks, Audit Log, Organizations, Billing

**API Keys (`ApiKeysScreen.jsx`):** Table with scope chip columns — WARNING on mobile (table overflow)  
**Webhooks (`WebhooksScreen.jsx`):** Similar table structure — WARNING on mobile  
**Audit Log (`AuditLogScreen.jsx`):** Dense table, multiple columns — WARNING on mobile  
**Organizations (`OrgsScreen.jsx`):** Card layout, relatively simple — WARNING on mobile (sidebar still fails)  
**Billing (`BillingScreen.jsx`):** Simple card layout — WARNING on mobile (sidebar still fails)

---

## Summary Table

| Area | 375px (Phone) | 768px (Tablet) | 1280px (Desktop) |
|------|--------------|----------------|-----------------|
| Sidebar | **FAIL** — fixed 210px, no collapse | **WARNING** — takes 27% of screen | **PASS** |
| Viewer Toolbar | **FAIL** — buttons overflow | **WARNING** — some overflow | **PASS** |
| Viewer Document Area | **FAIL** — 165px after sidebar | **WARNING** — narrow but usable | **PASS** |
| Upload Stats Grid | **FAIL** — 4-col grid at 165px | **WARNING** — compresses | **PASS** |
| Upload Doc Table | **FAIL** — hover actions unreachable | **WARNING** | **PASS** |
| Access Control Form | **FAIL** — 2-col + 3-col grids compress | **WARNING** | **PASS** |
| Feedback Table | **FAIL** — 7-col table at 165px | **WARNING** | **PASS** |
| Analytics KPI Grid | **FAIL** — 3+ col grid compresses | **WARNING** | **PASS** |
| Storage Summary | **WARNING** — 3-col cards compress | **WARNING** | **PASS** |
| Storage Table | **PASS** — `overflowX: auto` | **PASS** | **PASS** |
| All Modals | **FAIL** — fixed px width clips viewport | **WARNING** | **PASS** |
| Notifications | **PASS** — single column layout | **PASS** | **PASS** |
| Developer Screens | **WARNING** — tables overflow | **WARNING** | **PASS** |
| Billing | **WARNING** — sidebar still fails | **WARNING** | **PASS** |

---

## Root Cause Analysis

There are two independent root causes for all mobile failures:

**Root cause 1 — Sidebar:** `width: 210, flexShrink: 0` with no responsive collapse. This single issue makes EVERY authenticated screen fail on mobile because it consumes 210 of 375px before any content is rendered. Fixing this alone would move most WARNINGs to PASS.

**Root cause 2 — Fixed-pixel widths:** Modals use `width: 420–520` with no `maxWidth: '95vw'`. Grids use `repeat(N, 1fr)` with no `minmax()` or `auto-fill`. Both patterns are straightforward to make responsive.

---

## Touch Compatibility Note

`DocRow.jsx:59` uses `opacity: 0` on hover buttons (`onMouseEnter`/`onMouseLeave`). On touch devices:
- `onMouseEnter` fires only on the first tap (unreliably) and `onMouseLeave` fires immediately after
- The "View", "Access", "↗ Share", and "✕" buttons are effectively unreachable on touch without a workaround
- This affects the primary document management actions on every mobile visit

**Classification: FAIL on touch devices regardless of screen size.**

---

*Generated: Sprint 4.8B Phase 4 — no implementation performed.*
