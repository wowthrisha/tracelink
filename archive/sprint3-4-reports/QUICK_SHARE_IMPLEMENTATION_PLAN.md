# Quick Share Implementation Plan
Sprint: 4.6A
Date: 2026-06-22
Status: APPROVED FOR IMPLEMENTATION

---

## Scope

Add a "↗ Share" button to each document row in the Upload screen. Clicking it calls `createLink()` with safe defaults and surfaces the resulting URL in a modal for one-click copy. No backend changes. No new API endpoints. No database changes.

---

## Affected Files

| File | Change |
|---|---|
| `src/components/upload/QuickShareModal.jsx` | NEW — modal component with loading/ready/error states |
| `src/components/upload/DocRow.jsx` | ADD — `onQuickShare` prop + "↗ Share" button (ready docs only) |
| `src/screens/UploadScreen.jsx` | ADD — 4 state vars + 1 handler + `QuickShareModal` render |

**No changes to:** AppShell, AccessScreen, api.js, atoms.jsx, any backend file.

---

## Component Tree

```
AppShell
  └── UploadScreen
        │  State additions:
        │    quickShareDoc    — null | doc object
        │    quickSharePhase  — 'loading' | 'ready' | 'error'
        │    quickShareUrl    — string | null
        │    quickShareError  — string | null
        │
        ├── DocRow (×N)
        │     New prop: onQuickShare(doc)
        │     New button: "↗ Share" — visible on hover, disabled if doc.status !== 'ready'
        │
        └── QuickShareModal (new)
              Props: doc, phase, url, error, onClose, onConfigure, onRetry
              Renders inside existing Modal atom
```

---

## State Flow

```
User hovers DocRow
  → "↗ Share" button appears (opacity: hov ? 1 : 0, same as other actions)

User clicks "↗ Share" (doc.status === 'ready')
  → e.stopPropagation() — prevents row-level onAccess navigation
  → UploadScreen.handleQuickShare(doc)
      sets quickShareDoc = doc
      sets quickSharePhase = 'loading'
      calls createLink({document_id, label, permissions})

  ── API call in flight ──
  → on success:
      sets quickSharePhase = 'ready'
      sets quickShareUrl = result.share_url
  → on failure:
      sets quickSharePhase = 'error'
      sets quickShareError = _errMsg(e, 'Failed to create link')

User clicks "⧉ Copy" (phase === 'ready')
  → navigator.clipboard.writeText(quickShareUrl)
  → button shows "✓ Copied" for 1.5 seconds
  → toast('Link copied to clipboard', 'success')

User clicks "Configure in Access Control →"
  → closeQuickShare()
  → onAccessDoc(quickShareDoc) — navigates to Access Control with doc pre-selected

User clicks ✕ or modal backdrop
  → closeQuickShare() — resets all quickShare state to null
```

---

## API Flow

```
handleQuickShare(doc)
  │
  └── window.SecureDocAPI.createLink({
        document_id: doc.id,
        label: 'Quick Share',
        permissions: {
          can_download: false,
          can_print: false,
          can_copy: false,
          can_right_click: false,
          watermark_enabled: true,
          can_annotate: false,
          enable_info: true,
        }
      })
  │
  ├── POST /api/links
  │     headers: Authorization: Bearer <token>
  │     body: { document_id, label, permissions }
  │
  └── response: { id, share_url, label, created_at, ... }
                         │
                         └── quickShareUrl = response.share_url
```

**Returns:** `share_url` field (confirmed by AccessScreen.jsx line 352/356 which reads `link.share_url` for copy and display).

No polling. No secondary calls. Single API round-trip.

---

## Default Permissions

```javascript
const QUICK_SHARE_DEFAULTS = {
  can_download: false,
  can_print: false,
  can_copy: false,
  can_right_click: false,
  watermark_enabled: true,
  can_annotate: false,
  enable_info: true,
};
```

These match the default `permissions` state in `AccessScreen.jsx:52-60` — no duplication of business logic. The same values the Access Control screen starts with.

---

## Error States

| Scenario | UI behavior |
|---|---|
| createLink() throws (network) | phase → 'error', error message shown, Retry button calls createLink again |
| createLink() throws (server, e.g. billing quota) | phase → 'error', `e.detail` shown if present, else generic message |
| clipboard.writeText() fails | Copy button still visible; on failure shows URL as selectable text field |
| doc.status !== 'ready' | Button is disabled (no click possible) |
| Multiple rapid clicks on same doc | Handler guards: if `quickShareDoc?.id === doc.id && quickSharePhase === 'loading'` → no-op |

---

## Test Plan (Phase 4)

Tests run via vitest + jsdom + @testing-library/react. `window.SecureDocAPI` mocked globally in setup.

| Test case | What's verified |
|---|---|
| Success path | createLink called, URL displayed, copy button works |
| API failure | Error message shown, Retry button calls createLink again |
| Empty document list | No DocRow rendered, no Share button visible |
| Duplicate clicks | Second click while loading is ignored |
| Loading state | Spinner shown while createLink in flight |
| Only ready docs | Share button disabled/absent for non-ready docs |
| Configure path | "Configure" click fires onAccessDoc with correct doc |
| Modal close | State resets on ✕ click |

---

## Rollback Risk

- **Low.** All changes are additive.
- Reverting: remove 3 state vars + 1 handler from UploadScreen, remove `onQuickShare` prop from DocRow, delete QuickShareModal.jsx. No data is mutated; share links created via Quick Share are identical to links created via Access Control and can be revoked normally.
- The existing Access Control flow is completely untouched.
