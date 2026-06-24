# Phase 2.1 — useTextLoader Extraction Report

**Sprint**: Architecture Refactor Sprint 2, Goal #3  
**Date**: 2026-06-17  
**Status**: Complete ✅

---

## Objective

Extract text-document loading logic (txt / md / log) from `ViewerScreen` into a
dedicated custom hook with zero behavior changes.

---

## File Created

**`frontend/src/hooks/useTextLoader.js`** — 47 lines

```js
export function useTextLoader(session, page, isTextDoc)
  → { textContent, textLoading, textError }
```

### Hook internals
| Symbol | Type | Purpose |
|--------|------|---------|
| `textContent` | state | Loaded text chunk string |
| `textLoading` | state | Spinner flag while fetch is in flight |
| `textError` | state | Error message or null |
| `loadTextChunk` | useCallback (empty deps) | Fetches one text chunk via `window.SecureDocAPI.getTextChunk` |
| text load effect | useEffect | Fires on `session`, `page`, `doc_status`, `doc_type` changes; skips non-text docs; handles not-ready status messages |

---

## Lines Removed from ViewerScreen

| Block removed | Lines (original) | Count |
|---------------|-----------------|-------|
| `useState` for `textContent` | 1230 | 1 |
| `useState` for `textLoading` | 1231 | 1 |
| `useState` for `textError` | 1232 | 1 |
| `loadTextChunk` useCallback (+ blank line) | 1424–1436 | 14 |
| Text-load `useEffect` (+ comment + blank lines) | 1607–1625 | 20 |
| **Total removed** | | **37 lines** |

Import line added: **1**  
Hook call added: **1**  
Net change to `app.jsx`: **−35 lines**

---

## Hook API

```js
import { useTextLoader } from './hooks/useTextLoader.js';

// In ViewerScreen, placed immediately after isTextDoc is derived:
const isTextDoc = !!(session?.doc_type && ['txt', 'md', 'log'].includes(session.doc_type));
const { textContent, textLoading, textError } = useTextLoader(session, page, isTextDoc);
```

**Parameters:**
- `session` — the validated session object (`link_token`, `session_id`, `doc_status`, `page_count`)
- `page` — current page / chunk number
- `isTextDoc` — boolean derived from `session.doc_type`; hook is a no-op when false

**Returns:**
- `textContent` — string — rendered in `<pre>` for txt/md/log display
- `textLoading` — boolean — controls spinner
- `textError` — string | null — controls error panel

---

## Build Result

| Metric | Before | After |
|--------|--------|-------|
| Bundle size | 192.5 kb | 192.7 kb |
| Build time | 15 ms | 21 ms |
| Build result | PASS ✅ | PASS ✅ |

Bundle size increased by 0.2 kb due to the hook file's module boilerplate (the
`const { useState, … } = React` line and the export statement).

---

## Risk Encountered — React Global Pattern

**Problem**: The hook file initially used `import { useState, useCallback, useEffect } from 'react'`. 
esbuild immediately errored: `Could not resolve "react"` — the project has no `react` npm package; 
React 18 is loaded via UMD CDN `<script>` tag and exposed as `window.React`.

**Fix**: Replaced the ES module import with a top-of-file destructure from the global:
```js
const { useState, useCallback, useEffect } = React;
```
This matches the exact pattern used at the top of `app.jsx`. All extracted hook files must
follow this pattern. This is a standing constraint for every subsequent hook extraction.

---

## Hook Placement — Ordering Constraint

`isTextDoc` is a derived value (`const isTextDoc = !!(session?.doc_type && ...)`) computed
mid-function, not a state hook. The hook call `useTextLoader(session, page, isTextDoc)` must
appear *after* `isTextDoc` is computed, not at the top of the state declarations block.

This was caught before any runtime error — the misplaced call was never committed.
The final placement is directly after `const isTextDoc = ...` on the same logical line group.

React hook rules are not violated: `useTextLoader` is always called unconditionally on every
render (hook count is stable). The *position* within the function body does not affect this.

---

## Manual Verification Checklist

Since there are no frontend tests, the following must be manually verified before shipping:

- [ ] PDF document opens and pages load normally
- [ ] Keyboard arrow navigation works (PDF)
- [ ] Text document (`.txt`) renders chunk content
- [ ] Markdown document (`.md`) renders chunk content
- [ ] Log file (`.log`) renders chunk content
- [ ] Page navigation updates text content for text docs
- [ ] Not-ready status (uploaded/processing/error) shows correct message for text docs
- [ ] `completed` event fires when last page/chunk is reached for text docs
- [ ] No console errors on viewer mount
- [ ] No console errors on page navigation

---

## Recommended Phase 2.2 Extraction — `useLinksSidecar`

**Why next**: Second-lowest coupling after `useTextLoader`.

**Owns**:
- `linksLoaded` state
- `visitedLinks` state (Set)
- `sidecarExtracted` state
- `pageLinksRef` ref (Map of page → links[])
- `autoExtractAttempted` ref (fire-once flag)
- Two `useEffect` hooks (load sidecar on session; auto-extract if missing)

**Dependencies**: `session?.link_token`, `session?.session_id`, `isTextDoc`, `doc?.id`

**No shared refs with other hooks** — `pageLinksRef` is only written by the sidecar
effects and read by the JSX (link overlays + LinksPanel). `wordPositionsRef` (search)
is reset in `onSidecarExtract` callback but that callback is constructed in ViewerScreen
with access to both hooks' returned refs, so no cross-hook coupling is needed.

**Estimated removal from ViewerScreen**: ~35 lines.
