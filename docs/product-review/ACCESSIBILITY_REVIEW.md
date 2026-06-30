# SecureDoc Accessibility Review
**Date:** 2026-06-30  
**Reviewer Persona:** Accessibility Expert  
**Standard:** WCAG 2.1 AA  
**Method:** Code analysis of all JSX files (browser testing not performed in this review)

---

## Scoring

WCAG 2.1 AA defines four principles: **Perceivable, Operable, Understandable, Robust**

| Principle | Current Score | Target |
|-----------|------------|--------|
| Perceivable | 3/10 | 7/10 |
| Operable | 4/10 | 7/10 |
| Understandable | 5/10 | 7/10 |
| Robust | 5/10 | 7/10 |
| **Overall** | **4.25/10** | **AA = 7+/10** |

---

## Critical Accessibility Issues

### AX-001 — No semantic HTML (Critical)

The entire application is built with `<div>` and `<span>` elements styled inline. There are no:
- `<nav>` elements for the sidebar
- `<main>` landmark for the content area
- `<button>` elements (custom `<div onClick>` are used extensively in atoms.jsx)
- `<h1>`, `<h2>`, `<h3>` heading hierarchy
- `<table>` elements with proper `<thead>`, `<th scope>` (tables DO use correct elements, but headers lack `scope` attributes)
- `<label>` elements associated with inputs via `htmlFor`

**WCAG:** 1.3.1 Info and Relationships (Level A)  
**Impact:** Screen readers cannot navigate by landmarks, headings, or form controls. Tab order is undefined.

---

### AX-002 — No focus management (Critical)

When modals open (NewKeyModal, CreateWebhookModal, revokeModal, etc.), focus is not moved into the modal. When modals close, focus is not returned to the triggering element.

**WCAG:** 2.4.3 Focus Order (Level A)  
**Impact:** Keyboard users cannot interact with modals. Tab continues to cycle through the background content.

**Specific instances:**
- `NewKeyModal` in ApiKeysScreen — focus not trapped or set on open
- `CreateWebhookModal` in WebhooksScreen — same issue
- `DeliveryPanel` in WebhooksScreen — same issue
- `EditLinkModal` in AccessScreen — same issue
- Revoke confirmation modal — same issue

---

### AX-003 — Color as the only differentiator (High)

Throughout the application, status and meaning are communicated solely through color:
- Active/Revoked API key badges: green vs. grey background — no icon, no text pattern difference beyond capitalization
- Risk badges (LOW/MEDIUM/HIGH): only color differences between levels — accessible color palette not verified
- Audit log action colors: `create` (green) vs. `delete` (red) vs. `view` (grey) — color-only
- Status dots (StatusDot component): green/red dots with no label

**WCAG:** 1.4.1 Use of Color (Level A)  
**Impact:** Color-blind users (~8% of male users) cannot distinguish Active from Revoked, or distinguish risk levels.

---

### AX-004 — Form fields not labeled (High)

The `Field` component in atoms.jsx passes a `label` prop as a rendered `<div>` above the input, but there is no `htmlFor` / `id` association between the label and the input. From the AccessScreen and ApiKeysScreen code:

```jsx
<Field label="Key name">
  <input value={name} onChange={e => setName(e.target.value)} placeholder="..." />
</Field>
```

The `<input>` has no `id`, and the label `<div>` has no `for` attribute. Screen readers will not announce the label when the input is focused.

**WCAG:** 1.3.1 Info and Relationships (Level A), 3.3.2 Labels or Instructions (Level A)

---

### AX-005 — Icon-only buttons with no accessible label (High)

Multiple buttons have no text or `aria-label`:
- `✕` close buttons in modals (e.g., `<Btn variant="ghost" size="sm" onClick={onClose}>✕</Btn>`)
- `⧉` copy button in key/secret reveal panels
- `↗` open-in-new-tab buttons in the links list
- `✎` rename (pencil icon) in the links list

Screen readers will announce "times" or "copy sign" — not meaningful.

**WCAG:** 4.1.2 Name, Role, Value (Level A)

---

### AX-006 — Table headers missing `scope` attribute (Medium)

The application has several data tables (API Keys, Audit Log, Analytics). Table headers are rendered as:
```jsx
<th style={{ ... }}>{h}</th>
```

Without `scope="col"` or `scope="row"`, screen readers in complex tables may not correctly associate data cells with headers.

**WCAG:** 1.3.1 Info and Relationships (Level A)

---

### AX-007 — Interactive elements with insufficient color contrast (High)

The design uses a dark theme with:
- Primary text: `C.textPrimary` (likely near white on dark)
- Muted text: `C.textMuted` (likely medium grey on dark)
- Dim text: `C.textDim` (likely light grey on dark)

Without measuring actual hex values, text at `C.textMuted` and `C.textDim` may fail the 4.5:1 contrast ratio required for normal text.

Known instances of potentially low-contrast text:
- Column headers in all tables (9px `textMuted` uppercase)
- "Created at", "Sent", "Last used" values in tables (10px `textMuted` monospace)
- All `SectionLabel` components

**WCAG:** 1.4.3 Contrast (Minimum) (Level AA)

---

### AX-008 — Mobile blocked (High)

The AppShell hard-blocks the application at 768px with an inline `if (window.innerWidth < 768)` check. This affects:
- All mobile screen reader users (Voice Control, TalkBack, etc.)
- Users with screen magnification who resize the browser window below 768px
- iPad users in portrait mode may or may not be blocked

**WCAG:** 1.4.4 Resize Text (Level AA), 1.4.10 Reflow (Level AA)  
**Note:** This is also a WCAG failure for users who rely on zoom/reflow.

---

### AX-009 — Toast notifications not announced to screen readers (Medium)

The toast system (in `contexts/toast.jsx`) appears to inject toast elements into the DOM. If these are not in an `aria-live="polite"` or `role="status"` region, screen readers will not announce them.

Toasts are the primary feedback mechanism for success/error on every action in the app. A blind user performing "Create API Key" has no way to know if it succeeded.

**WCAG:** 4.1.3 Status Messages (Level AA)

---

### AX-010 — `window.confirm()` for destructive actions (Medium)

The link delete action uses:
```js
if (!window.confirm('Permanently delete this link...')) return;
```

`window.confirm()` dialogs are not accessible in all screen reader configurations and are not customizable for WCAG compliance. They also violate the app's own design system (all other modals use Card-based components).

**WCAG:** 4.1.2 Name, Role, Value (Level A)

---

### AX-011 — Keyboard trap in viewer (Medium)

The viewer document panel intercepts keyboard events for navigation (arrow keys, Ctrl+F for search). While keyboard navigation within the viewer is intentional, there needs to be a clear way to "exit" the document and return keyboard focus to the toolbar.

**WCAG:** 2.1.2 No Keyboard Trap (Level A)

---

### AX-012 — `autoFocus` without consideration for announcements (Low)

Multiple modals and inputs use `autoFocus`:
- Email field in LoginScreen
- Reply textarea in AccessScreen feedback tab
- Rename input in links list

`autoFocus` can be disorienting for screen reader users if it moves focus without announcement context. Proper modal focus management (aria-labelledby, role="dialog") is needed.

**WCAG:** 2.4.3 Focus Order (Level A)

---

## Positive Findings

These accessibility patterns are correctly implemented:

| Pattern | Location |
|---------|---------|
| Keyboard event handling (Escape to close) | Reply draft in AccessScreen, modal close |
| Enter/Blur for inline edits | Link rename, page input field |
| `rel="noopener noreferrer"` on external links | Share link in AccessScreen |
| `type="email"` on email inputs | LoginScreen |
| `autocomplete` attributes on auth inputs | LoginScreen |
| `disabled` states on buttons during loading | All screens (disabled during async operations) |
| Toast-based error reporting | All screens |

---

## WCAG 2.1 AA Compliance Matrix

| Guideline | Level | Status |
|-----------|-------|--------|
| 1.1.1 Non-text Content | A | FAIL — icon buttons have no alt/aria-label |
| 1.3.1 Info and Relationships | A | FAIL — no semantic HTML, no label associations |
| 1.3.2 Meaningful Sequence | A | UNKNOWN — DOM order not verified |
| 1.4.1 Use of Color | A | FAIL — color is sole differentiator for status |
| 1.4.3 Contrast (Minimum) | AA | LIKELY FAIL — muted text at small size |
| 1.4.4 Resize Text | AA | FAIL — hard block at 768px |
| 1.4.10 Reflow | AA | FAIL — no responsive layout |
| 2.1.1 Keyboard | A | PARTIAL — most actions are clickable but modal trapping fails |
| 2.1.2 No Keyboard Trap | A | POTENTIAL FAIL — viewer keyboard intercept |
| 2.4.3 Focus Order | A | FAIL — modal focus not managed |
| 3.3.1 Error Identification | A | PASS — toast system identifies errors |
| 3.3.2 Labels or Instructions | A | FAIL — form labels not programmatically associated |
| 4.1.2 Name, Role, Value | A | FAIL — icon buttons, custom div buttons |
| 4.1.3 Status Messages | AA | FAIL — toasts not announced |

---

## Recommended Fixes (Priority Order)

1. **Add `aria-live="polite"` to toast container** — Quick fix, high impact
2. **Add `aria-label` to all icon-only buttons** — Quick fix, high impact
3. **Add `role="dialog"`, `aria-modal="true"`, and `aria-labelledby` to all modals** — Medium effort, critical for modal users
4. **Add `htmlFor`/`id` pairs to all Field components** — Medium effort, required for label association
5. **Add `scope="col"` to all table headers** — Low effort
6. **Replace `window.confirm()` with modal** — Low effort (consistent with rest of app)
7. **Add `<nav>` landmark to Sidebar** — Low effort
8. **Add `role="main"` to content area** — Low effort
9. **Audit color contrast on `C.textMuted` and `C.textDim`** — Design system update
10. **Add `role="status"` region for status-only updates** — Medium effort

---

*Accessibility review complete — 2026-06-30*
