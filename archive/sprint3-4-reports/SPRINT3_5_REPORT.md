> **HISTORICAL ARCHIVE** — Sprint milestone record. Reflects state at time of writing. Not current state.

# Sprint 3.5 — Implementation Report
Date: 2026-06-18
Status: COMPLETE

---

## Build Result

```
npm run build → dist/app.bundle.js  197.4kb  ⚡ Done in 22ms  ✅
```

app.jsx: 3,687 → 3,275 lines (−412 lines, −11.2%)
Cumulative from baseline: 5,085 → 3,275 lines (−1,810 lines, −35.6%)

---

## Components Extracted

| File | Lines | Props | Deps |
|---|---|---|---|
| `components/AnnotationLayer.jsx` | ~148 | annotations, activeTool, sessionPrefix, commentDraft, onDraw, onDelete, onOpenThread, C, mono | none (C/mono as props) |
| `components/CommentPopup.jsx` | ~18 | draft, onSave, onCancel, C | none (C as prop) |
| `components/DocumentPicker.jsx` | ~72 | onSelect | tokens.js, atoms.jsx, toast.jsx |
| `components/upload/StatCard.jsx` | ~26 | s | tokens.js, atoms.jsx |
| `components/upload/DocRow.jsx` | ~78 | doc, isLast, onView, onAccess, onDelete, onReprocess, groups, onAssignGroup | tokens.js, atoms.jsx |
| `components/upload/UploadDropZone.jsx` | ~28 | dragging, setDragging, simulate, fileRef | tokens.js |
| `components/upload/UploadMetadataPanel.jsx` | ~28 | selectedGroupId, setSelectedGroupId, groups, retentionPolicy, setRetentionPolicy, setGroupModal, setGroupForm | tokens.js, atoms.jsx |
| `components/upload/UploadProgressPanel.jsx` | ~28 | uploading, uploadDone, progress, uploadedDoc, setUploadDone, onAccessDoc | tokens.js, atoms.jsx |

---

## Phase 4 — Security Review

### Security Findings Table

| ID | Severity | Component | Finding | Status |
|---|---|---|---|---|
| S-001 | Low | AnnotationLayer | `isOwn` delete gate is client-side only — hides delete button but does not enforce ownership | Accepted — server-side auth in `SecureDocAPI.deleteAnnotation` via `session.link_token` + `session_id` |
| S-002 | Low | AnnotationLayer | `comment`/`sticky_note` thread open is unrestricted (`!activeTool` only, no `isOwn` check) | Accepted — by design; all viewers can read threads; write/reply auth is server-enforced |
| S-003 | Info | AnnotationLayer | `a.comment_text` rendered in SVG `<foreignObject>` as React text node | Safe — React JSX text nodes are HTML-escaped; no XSS vector |
| S-004 | Info | AnnotationLayer | `coords` parsed from JSON string (`typeof a.coords === 'string' ? JSON.parse(a.coords)`) | Pre-existing; coordinates are numeric only (x/y/w/h floats); no code execution risk |
| S-005 | Info | CommentPopup | `maxLength={2000}` on textarea — client-side only | Accepted — server should also enforce; client limit is UX only |
| S-006 | Info | DocumentPicker | Calls `window.SecureDocAPI.getDocuments()` directly | Accepted — same API call as pre-extraction; session auth handled in API layer |
| S-007 | Info | UploadDropZone | File type validation (`simulate()` + `_detectFileType`) remains in UploadScreen parent | Correct ownership — UploadDropZone is pure presentation; validation stays with logic |
| S-008 | Info | All extracted | No `dangerouslySetInnerHTML`, `eval`, or `Function()` calls | ✅ Verified via grep |
| S-009 | Info | All extracted | No `console.log` of tokens, session data, or user PII | ✅ Verified via grep |
| S-010 | Info | All extracted | No new localStorage reads/writes | ✅ Verified via grep |

### Annotation Permission Flow (confirmed correct post-extraction)

```
useAnnotations hook
  → gates all API calls behind session.permissions?.can_annotate
  → passes pageAnnotations down to AnnotationLayer as prop

AnnotationLayer (extracted)
  → renders annotations (pure presentation)
  → isOwn = client-side UI gate only (hides delete button)
  → onDelete prop → ViewerScreen → SecureDocAPI.deleteAnnotation(link_token, id, session_id)
  → onDraw prop → ViewerScreen → SecureDocAPI.createAnnotation(link_token, ...)

Server always validates: link_token + session_id ownership
```

**Verdict: ZERO security regressions. No new attack surface introduced.**

---

## Phase 5 — Manual Verification Matrix

| Check | Result |
|---|---|
| Build: zero errors | ✅ 197.4 kb |
| Bundle size delta | ✅ +0.7 kb (8 new files, expected) |
| AnnotationLayer: NOT extracted in Sprint 3.4 | ✅ (now extracted in 3.5 per readiness review approval) |
| isOwn ownership check preserved exactly | ✅ Code identical to app.jsx original |
| 7 annotation type renderers all present | ✅ highlight, rectangle, arrow, bookmark, comment, sticky_note, draw |
| Drawing preview section preserved | ✅ All 4 preview conditions present |
| CommentPopup: focus timer preserved | ✅ setTimeout 50ms onMount |
| CommentPopup: keyboard shortcuts preserved | ✅ Enter (Cmd/Ctrl) save, Escape cancel |
| DocumentPicker: data-testid attributes preserved | ✅ document-picker, document-picker-empty, doc-picker-item |
| DocRow: group assignment select preserved | ✅ groups.length > 0 condition preserved |
| UploadDropZone: fileRef.current.click() path preserved | ✅ fileRef passed as prop; Header button in UploadScreen still works |
| UploadProgressPanel: Configure Access callback preserved | ✅ onAccessDoc prop passed through |
| UploadMetadataPanel: — None — option preserved | ✅ em dash intact |
| No new UX elements added | ✅ Zero feature additions |
| No API contract changes | ✅ All SecureDocAPI calls unchanged |
| Circular dependency check | ✅ No cycles in import graph |

### Build Error Encountered and Fixed

**Error:** Orphaned `/* ─── DOCUMENT PICKER ──` comment block left open after Python deletion stopped before the opening `/*` line. The closing `*/` (which contained `─` chars) was inside the deletion range but the opening line was not. This left an unclosed block comment that swallowed all JSX between lines 394 and the next `*/` in the file.

**Fix:** Detected the orphaned line dynamically via Python pattern match and deleted lines 394–398.

**Root cause:** Walk-back logic stopped at plain comment body text (`the user click to select...`) that didn't match any detection pattern. Mitigation added for future sprints: use explicit line ranges from grep rather than walk-back heuristics when deleting comment blocks.

---

## Regression Analysis

All UploadScreen state, handlers, and callbacks are unchanged — the 3 new components receive them as props with identical signatures to the original inline JSX. DocumentPicker, StatCard, DocRow are pure function extractions — zero caller changes needed. AnnotationLayer and CommentPopup are prop-identical to original.

**Verdict: ZERO regressions.**
