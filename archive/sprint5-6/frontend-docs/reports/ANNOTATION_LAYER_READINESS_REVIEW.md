> **HISTORICAL ARCHIVE** — Sprint milestone record. Reflects state at time of writing. Not current state.

# AnnotationLayer Extraction Readiness Review
Sprint 3.4 — Phase 4
Date: 2026-06-17
Status: REVIEW ONLY — DO NOT EXTRACT (per Sprint 3.4 Phase 4 instruction)

---

## Component Identity

| Field | Value |
|---|---|
| Name | `AnnotationLayer` |
| Location | `app.jsx` line 1476 |
| LOC | ~150 lines (1476–1625) |
| Sibling | `CommentPopup` (line 1628, analyzed separately below) |

---

## Prop Graph

| Prop | Type | Source | Usage |
|---|---|---|---|
| `annotations` | `Array<AnnotationRecord>` | parent ViewerScreen | Rendered in `annotations.filter(a => !a.parent_id).map(...)` |
| `activeTool` | `string \| null` | parent ViewerScreen | Controls draw mode, pointer events, cursor |
| `sessionPrefix` | `string` | parent ViewerScreen | Ownership check `a.session_id?.startsWith(sessionPrefix)` |
| `commentDraft` | `object \| null` | parent ViewerScreen | **RECEIVED BUT NOT USED** — used by sibling CommentPopup, not AnnotationLayer |
| `onDraw` | `(coords, type) => void` | parent ViewerScreen | Called on mouseup to commit new annotation |
| `onDelete` | `(id) => void` | parent ViewerScreen | Called on annotation click when tool is inactive and isOwn |
| `onOpenThread` | `(annotation) => void` | parent ViewerScreen | Called on comment/sticky_note click |
| `C` | design token object | parent ViewerScreen | **Prop — no closure dep to tokens.js** |
| `mono` | font object | parent ViewerScreen | **Prop — no closure dep to tokens.js** (unused inside AnnotationLayer — only referenced in external `_pathD` context check; actually not referenced at all) |

**Observation:** `mono` is declared in the prop signature but grep finds zero usage inside AnnotationLayer's body. Safe to keep for interface consistency.

**Observation:** `commentDraft` is declared in the prop signature but has zero usage inside AnnotationLayer. It is used by the sibling `CommentPopup` component which is rendered above AnnotationLayer in the parent.

---

## State Graph

| State | Init | Setter | Purpose |
|---|---|---|---|
| `preview` | `null` | `setPreview` | Current in-progress shape; `true` for draw mode, `{x,y,w,h,x1,y1,x2,y2}` for box types |
| `drawPoints` | `[]` | `setDrawPoints` | Accumulates freehand path points during draw |
| `svgRef` | `useRef(null)` | assigned in JSX | Bound to `<svg>` element; used for `getBoundingClientRect()` |
| `dragRef` | `useRef(null)` | mutated directly | Drag origin `{x, y}` in normalized coords; `null` when not dragging |

**State machine diagram:**

```
[idle]
  → onMouseDown (activeTool set)
      draw mode: setDrawPoints([{x,y}]), setPreview(true)
      other mode: setPreview({x,y,w:0,h:0,...})
      → dragRef.current = {x,y}

[dragging]
  → onMouseMove (dragRef.current != null)
      draw mode: setDrawPoints(pts => [...pts, {x,y}])
      other mode: setPreview({recalculated box/line})

  → onMouseUp
      comment/sticky_note: onDraw({x,y}, type) → setPreview(null)
      draw: onDraw({points}, 'draw') → setDrawPoints([]) → setPreview(null)
      box/line: if minDrag exceeded → onDraw(coords, type) → setPreview(null)
      dragRef.current = null → [idle]
```

**No async state.** All state transitions are synchronous mouse events.

---

## Mutation Graph

| Mutator | Reads | Writes | Calls |
|---|---|---|---|
| `_toNorm(e)` | `svgRef.current.getBoundingClientRect()`, `e.clientX/Y` | — | — |
| `_pathD(pts)` | `svgRef.current.getBoundingClientRect()` | — | — |
| `_onMouseDown(e)` | `activeTool`, `dragRef.current` | `dragRef.current`, `drawPoints`, `preview` | `_toNorm`, `setDrawPoints`, `setPreview` |
| `_onMouseMove(e)` | `dragRef.current`, `activeTool` | `drawPoints`, `preview` | `_toNorm`, `setDrawPoints`, `setPreview` |
| `_onMouseUp(e)` | `dragRef.current`, `preview`, `drawPoints`, `activeTool` | `dragRef.current`, `preview`, `drawPoints` | `_toNorm`, `onDraw`, `setPreview`, `setDrawPoints` |
| annotation `onClick` | `activeTool`, `isOwn` | — | `onDelete(a.id)` or `onOpenThread(a)` |

**Cross-closure dependency check:** `_onMouseUp` reads `drawPoints` state directly (not via functional update). This is a stale-closure risk but was present before extraction — not introduced by extraction.

---

## Event Graph

| Event | Bound To | Handler | Propagation |
|---|---|---|---|
| `onMouseDown` | `<svg>` | `_onMouseDown` | `e.preventDefault()` called |
| `onMouseMove` | `<svg>` | `_onMouseMove` | — |
| `onMouseUp` | `<svg>` | `_onMouseUp` | — |
| `onClick` | per annotation `<g>`/`<rect>`/`<path>` | inline | calls `onDelete` or `onOpenThread` |

**No window/document event listeners.** All events are React synthetic events on the SVG element. No cleanup needed.

---

## Renderer Registry (7 annotation types)

| Type | SVG Element | Ownership-gated delete? | Thread-open? |
|---|---|---|---|
| `highlight` | `<rect fill>` | yes (isOwn) | no |
| `rectangle` | `<rect stroke>` | yes (isOwn) | no |
| `arrow` | `<g><defs><marker><line>` | yes (isOwn) | no |
| `bookmark` | `<g><circle><text>` | yes (isOwn) | no |
| `comment` | `<g><circle><text>` + optional `<foreignObject>` | no | yes (any viewer) |
| `sticky_note` | `<g><rect><text>` + optional `<foreignObject>` | no | yes (any viewer) |
| `draw` | `<path>` via `_pathD` | yes (isOwn) | no |

Arrow type uses a unique `<defs>` marker per annotation: `id="ah-${a.id}"` — safe, no collision risk.

---

## External Dependencies

| Dependency | Type | Resolution on extraction |
|---|---|---|
| `C` | Prop | Already a prop — zero change needed |
| `mono` | Prop | Already a prop — zero change needed (also unused in body) |
| `useState` | React global destructure | Add `const { useState, useRef, useEffect } = React;` |
| `useRef` | React global destructure | Same |
| `useEffect` | React global destructure | Not used in AnnotationLayer (used in CommentPopup) |
| Parent callbacks | Props | No change needed |

**Zero import statements needed.** C and mono arrive as props. No context reads. No hook imports.

---

## Extraction Complexity Assessment

| Factor | Score | Notes |
|---|---|---|
| Prop surface | LOW | 9 props, all primitive or function, no complex objects beyond annotation array |
| State machine | MEDIUM | 2 state vars + 2 refs, but transitions are clear and documented |
| External deps | LOW | C/mono as props, no context, no tokens.js closure needed |
| SVG drawing | MEDIUM | `_pathD` uses live `svgRef.current.getBoundingClientRect()` — cannot be split out |
| Event cleanup | NONE | No window listeners, no timers, no subscriptions |
| Test surface | LOW | Pure visual SVG; drag state machine predictable |
| `commentDraft` noise | LOW | Unused prop — can document and keep for signature compatibility |

**Overall Extraction Complexity: LOW-MEDIUM**

The component is more readable than complex. The main "complexity" is the draw state machine, but it is already well-scoped to 3 handlers and produces clean output via `onDraw`. Extraction is straightforward.

---

## CommentPopup (Sibling Component — Supplementary Review)

**Location:** `app.jsx` line 1628–1645, ~18 lines

| Factor | Detail |
|---|---|
| Props | `{ draft, onSave, onCancel, C }` |
| State | `text` (useState), `inputRef` (useRef) |
| useEffect | `setTimeout(() => inputRef.current?.focus(), 50)` — auto-focus on mount |
| External deps | `C` as prop — zero closure to tokens.js needed |
| Context | None |
| Complexity | **LOW** |

CommentPopup is among the simplest remaining components. It is a controlled textarea popup with two action buttons. Suitable for extraction in the same sprint as AnnotationLayer.

---

## Risk Register Entry

| ID | Risk | Severity | Mitigation |
|---|---|---|---|
| R-AL-01 | `drawPoints` stale closure in `_onMouseUp` | LOW | Pre-existing issue, not introduced by extraction; document in extracted file |
| R-AL-02 | `commentDraft` prop declared but unused | INFO | Keep in signature for caller compatibility; add inline comment |
| R-AL-03 | `mono` prop declared but unused | INFO | Same as above |
| R-AL-04 | `_pathD` requires live SVG bbox | LOW | `svgRef` and `_pathD` must colocate — cannot be split to utils |
| R-AL-05 | Arrow marker IDs use annotation ID (unique per render) | LOW | IDs are document-scoped; if multiple AnnotationLayer instances exist on page, IDs could collide. Current app uses one per page — not an issue now |

**Risk Score: LOW-MEDIUM**
Extraction is safe. No blockers identified. Recommended for Sprint 3.5.

---

## Extraction Readiness Verdict

| Question | Answer |
|---|---|
| Can be extracted to standalone file? | **YES** |
| Requires new imports? | **NO** — C/mono as props, React globals only |
| Requires refactoring before extraction? | **NO** |
| Changes UX/behavior? | **NO** |
| Requires caller changes? | **NO** |
| Recommended sprint | **Sprint 3.5** (pair with CommentPopup) |

**DO NOT EXTRACT in Sprint 3.4 per explicit instruction.**
