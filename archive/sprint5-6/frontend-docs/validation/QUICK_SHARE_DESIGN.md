# Quick Share Design
Sprint: 4.6 — Workstream 1
Date: 2026-06-22
Status: DESIGN ONLY — Do not implement without sprint approval

---

## Problem Statement

The primary action in SecureDoc — sharing a document — requires 7–8 steps and 60–90 seconds. Every competitor does it in 2 clicks. All three owner personas (Architect, Consultant, Builder) fail the 30-second task completion test. The gap is not a missing feature: `createLink` exists, `POST /api/links` works, and the API accepts a minimal `{document_id}` payload. The gap is a missing shortcut to that capability from the primary document list.

---

## Design Goal

A user who uploads a document should be able to share it in 2 clicks and under 10 seconds, without leaving the Upload screen and without reading a form.

Secondary goal: the full Access Control screen remains untouched for power users who want to configure password, expiry, domain restriction, etc.

---

## Where It Lives

**Location:** Each document row in the Upload screen (`UploadScreen.jsx`).

The document table currently renders rows with: filename, file type, status badge, size, and an action menu (⋯). The Quick Share button is added as a visible action on each row — not hidden inside the action menu.

**Placement within the row:**
```
[filename] [type] [status] [size]   [↗ Share]  [⋯]
```

The "↗ Share" button appears only when `doc.status === 'ready'`. It is disabled and shows a tooltip "Document is still processing" when status is not ready.

---

## Interaction Design

### Mode A — Instant Share (default path)

1. User clicks "↗ Share" on a document row.
2. A small popover opens anchored to the button.
3. Inside the popover, a loading spinner shows for ~500ms while the API call completes.
4. On success, the popover shows:
   - The full share URL (truncated with ellipsis if long)
   - A "⧉ Copy link" button (copies to clipboard)
   - A small line: "Shared with defaults — watermark on, download off"
   - A "Configure settings →" link that opens the Access Control screen with this document pre-selected

5. User clicks "⧉ Copy link". Button label changes to "✓ Copied" for 1.5 seconds.
6. Popover closes on click-outside or pressing Escape.

**Total time: under 10 seconds.**

### Mode B — Navigate to Access Control (power user path)

The "Configure settings →" link in the popover (or clicking the document name) navigates to the Access Control screen using the existing `onAccessDoc(doc)` callback, which sets `activeDoc` in AppShell and switches to the `access` screen. This path is unchanged.

---

## Default Share Parameters

When Quick Share creates a link, it uses these defaults — chosen to be safe for the majority of professional sharing scenarios:

```json
{
  "document_id": "<id>",
  "label": "Quick Share",
  "permissions": {
    "can_download": false,
    "can_print": false,
    "can_copy": false,
    "can_right_click": false,
    "watermark_enabled": true,
    "can_annotate": false,
    "enable_info": true
  }
}
```

**Rationale for defaults:**
- `watermark_enabled: true` — forensic tracing is on by default. Protects the owner without requiring configuration.
- `can_download: false` — a conservative default. The architect and builder personas both need download disabled. Downloading can be enabled via Access Control if needed.
- `can_annotate: false` — annotation is an intentional grant, not a default.
- No password, no expiry, no email restriction — the instant path is for speed. Security restrictions are applied via Access Control.

These defaults can be reviewed per product decision before implementation. They are not hardcoded in this design — they should be configurable via a product-level constant.

---

## Component Structure

### New component: `QuickSharePopover`

**File:** `frontend/src/components/QuickSharePopover.jsx`

**Props:**
```javascript
QuickSharePopover({
  doc,          // document object with .id, .filename
  onClose,      // called when popover should close
  onConfigure,  // called to navigate to access screen; receives doc
})
```

**Internal state:**
```javascript
const [phase, setPhase] = useState('loading')  // 'loading' | 'ready' | 'error'
const [shareUrl, setShareUrl] = useState(null)
const [copied, setCopied] = useState(false)
```

**On mount:** immediately calls `window.SecureDocAPI.createLink({document_id: doc.id, label: 'Quick Share', permissions: QUICK_SHARE_DEFAULTS})`. On resolve: sets `shareUrl`, sets `phase = 'ready'`. On reject: sets `phase = 'error'` with error message.

**Positioning:** absolute, anchored below the "↗ Share" button using a `ref` on the button and `getBoundingClientRect()`. Z-index above the document table. Closes on `mousedown` outside via a document-level listener added in a `useEffect` and removed on unmount.

**Width:** 320px fixed. No resize behavior.

### Changes to `UploadScreen.jsx`

1. Import `QuickSharePopover`.
2. Add state: `quickShareDocId` (string | null) — tracks which doc's popover is open.
3. On each document row, add a "↗ Share" button:
   ```jsx
   <Btn
     size="sm"
     variant="secondary"
     disabled={doc.status !== 'ready'}
     onClick={() => setQuickShareDocId(doc.id)}
   >
     ↗ Share
   </Btn>
   ```
4. Render `QuickSharePopover` when `quickShareDocId` is non-null:
   ```jsx
   {quickShareDocId && (
     <QuickSharePopover
       doc={docs.find(d => d.id === quickShareDocId)}
       onClose={() => setQuickShareDocId(null)}
       onConfigure={doc => { setQuickShareDocId(null); onAccessDoc(doc); }}
     />
   )}
   ```

**No changes to AppShell, api.js, or any backend file.**

---

## State Transitions

```
[button click]
      │
      ▼
  phase: loading
  (createLink API call in flight)
      │
      ├─ success ──► phase: ready — show URL + Copy button
      │
      └─ error ────► phase: error — show "Failed to create link. Try again."
                                     with a "Retry" button
```

---

## Error Handling

| Scenario | Behavior |
|---|---|
| API call fails (network) | phase → error. Show: "Could not create share link. Check your connection." |
| API call fails (server error) | phase → error. Show error message from `e.detail` if present, else generic. |
| Clipboard write fails | Copy button still shows. If `navigator.clipboard.writeText` rejects, show the URL as a selectable text field instead. |
| Document status changes to 'error' | Button is disabled before popover opens, so this scenario does not arise. |

---

## What This Does NOT Change

- Access Control screen: no changes
- Policy form: no changes
- Share Link tab: the link created by Quick Share appears here when the user navigates to Access Control, labeled "Quick Share"
- api.js: no changes — `createLink` already accepts the required payload
- Backend: no changes — `POST /api/links` already handles this payload
- AppShell navigation: no changes — `onAccessDoc` callback already works

---

## Measurement (for future sprint)

Once implemented, define success as:
- Time-to-first-share (upload → copy link) drops below 30 seconds for new users
- Quick Share button click rate > Access Control navigation rate on Upload screen (indicates users prefer the fast path)
- Zero support reports of "I didn't know how to share a document"

---

## Edge Cases

| Case | Handling |
|---|---|
| User clicks Share on two documents in rapid succession | Only one popover shows at a time. Second click closes first popover and opens second. |
| User has no documents | Button doesn't exist; table is empty. |
| Document is in 'processing' state | Button is disabled. Tooltip: "Document still processing." |
| User has hit link quota (billing limit) | API returns error. Phase → error, message from API response. |
| Very long document filename | Filename shown in popover truncated to 40 chars with ellipsis. |

---

## Implementation Estimate

- `QuickSharePopover.jsx` new component: 2.5 hours
- `UploadScreen.jsx` button + popover state: 1 hour
- Manual testing (copy path, error path, configure path, Escape close, click-outside close): 0.5 hours

**Total: ~4 hours. No backend work. No database changes. No API contract changes.**
