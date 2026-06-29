> **HISTORICAL ARCHIVE** — Reflects repository state before Sprint 4.2D extraction (2026-06-22). Not current. Do not use for active decision-making.

# TRACEVIEW UNIVERSAL DOCUMENT ARCHITECTURE
## Phase D — Design Audit for PDF / TXT / MD / LOG / DOCX / DOC / PPTX

**Audit Date:** 2026-06-04  
**Auditor Role:** Principal Architect  
**Repository:** `/Users/thrisha/traceview/securedoc/`  
**Scope:** Architecture design for universal document support. No code changes.

---

## Executive Summary

TraceView already supports 6 of the 7 target formats (PDF, TXT, MD, LOG, DOCX, DOC). PPTX is the single remaining gap. The architecture for adding PPTX requires **one decision and one new pipeline module** — it does not require rearchitecting anything else.

The more important finding is this: the existing format-specific if/elif chains scattered across 5 files (`tasks.py`, `viewer.py`, `documents.py`, `text_processor.py`, `toc/extractor.py`) are a maintainability liability. Adding PPTX cleanly requires first establishing the `DocumentAdapter` pattern — which Phase A deleted as "dead code" — as the actual shared interface. Without it, PPTX will add an eighth chain of `elif file_type == "pptx"` conditionals across all the same locations.

**Recommendation:** Do Phase D1 (adapter wiring) before D2/D3 (PPTX). D1 is a refactor with no behavioral change. D2/D3 are feature work. Both phases are straightforward.

**The architecture is ready to extend. PPTX can begin in 2–3 days of focused work.**

---

## Section 1 — Current Pipeline Analysis

### Full Flow Map

```
Upload (documents.py)
│
├─ ALLOWED_CONTENT_TYPES check               ← list must be extended for pptx
├─ detect_file_type() → "pdf"|"txt"|...|"doc" ← must add "pptx" branch
├─ Size validation (by file_type)            ← must add pptx branch
├─ Storage upload (originals/{doc_id}.{ext}) ← generic, no changes needed
├─ Document model INSERT                     ← generic
└─ Celery queue → process_document.delay()  ← generic
           │
           ▼
Worker (tasks.py → pipeline/*.py)
│
├─ process_document_with_session()
│   └─ if txt/md/log → process_text_document()    ← text pipeline
│      elif docx     → process_docx_document()     ← word pipeline
│      elif doc      → process_doc_document()      ← word pipeline
│      else (pdf)    → process_pdf_document()      ← pdf pipeline
│                     (pptx has no branch yet)      ← GAP
│
├─ PDF pipeline: rasterize → stamp → upload pages + thumbs → TOC sidecar
├─ Text pipeline: decode → count chunks → ready (NO pages stored)
└─ Word pipeline: download → convert text → overwrite storage → ready
           │
           ▼
Storage (S3/R2)
│
├─ originals/{doc_id}.{ext}   ← original file (kept for can_download)
├─ pages/{doc_id}/{p:04d}.webp ← PDF only: rasterized pages
├─ thumbs/{doc_id}/{p:04d}.webp ← PDF only: thumbnails
└─ toc/{doc_id}.json           ← PDF/DOCX: TOC sidecar
           │
           ▼
Viewer (viewer.py)
│
├─ _get_cached_link_and_doc()  ← generic (all formats)
├─ GET /page/{token}/{p}       ← PDF only
├─ GET /thumb/{token}/{p}      ← PDF only
├─ GET /text/{token}/{chunk}   ← text/docx/doc only
├─ GET /toc/{token}            ← all formats, dispatches to right sidecar/extractor
└─ GET /download/{token}       ← if txt/md/log/docx/doc → raw bytes
                                 if pdf → PIL-assembled watermarked PDF
```

### Where Format Assumptions Exist (All Must Change for PPTX)

| Location | Current assumption | PPTX impact |
|----------|-------------------|------------|
| `documents.py:ALLOWED_CONTENT_TYPES` | No pptx MIME | Add `application/vnd.openxmlformats-officedocument.presentationml.presentation` |
| `text_processor.py:detect_file_type()` | No pptx branch | Add pptx ZIP-magic detection |
| `text_processor.py:SUPPORTED_WORD_EXTENSIONS` | `{docx, doc}` | Add `pptx` — or create `SUPPORTED_PRESENTATION_EXTENSIONS` |
| `documents.py:upload_document()` | PDF magic bytes checked separately | pptx uses ZIP magic (already has `_is_zip_magic`) |
| `tasks.py:process_document_with_session()` | `elif file_type == "docx"` chains | Add `elif file_type == "pptx"` |
| `workers/pipeline/` | No pptx pipeline module | Create `workers/pipeline/pptx.py` |
| `viewer.py:download_document()` | `if doc.file_type in ("txt","md","log","docx","doc")` | Add `"pptx"` to text-mode download |
| `viewer.py:get_text_chunk()` | `if file_type not in ("txt","md","log","docx","doc")` | Add `"pptx"` |
| `toc/extractor.py:TOC_SUPPORTED_TYPES` | Missing pptx | Add `"pptx"` |
| `frontend:isTextDoc` | `doc_type !== 'pdf'` — accidental pptx support? | PPTX served as text chunks: `isTextDoc` is correct if pptx → text path |
| `viewer_cache.py:DocSnapshot.file_type` | Default `"pdf"` | No change if pptx is `"pptx"` string |

**Total change surface for PPTX: 10 locations.** Without a shared adapter, this must be done by hand in each location. With a proper `DocumentAdapter`, most of this becomes a single adapter class registration.

### What Works Today Without Changes

- Analytics events: generic (link_id, session_id) — ✓ format-agnostic
- Session management: generic — ✓
- IP allowlist / email policy: generic — ✓
- Rate limiting: generic — ✓
- Watermarking: text-path uses `watermark_text` in JSON response (no PIL) — ✓
- L1/L2 caching infrastructure: generic — ✓ (pptx served as text → text_content_cache)
- TOC model (`TocEntry`): universal — ✓
- Security headers: generic — ✓

---

## Section 2 — Universal Document Model

### The Current State

Phase A removed `document_adapter.py` as dead code. That decision was correct at the time — the adapter was written but never connected to any production path. However, the 10-location change surface for adding PPTX demonstrates exactly why the abstraction exists.

### Proposed Universal Document Adapter

```
DocumentAdapter (ABC)
├─ file_type: str                      → canonical type identifier
├─ viewer_mode: "image" | "text"       → which viewer protocol to use
├─ supports_thumbnails() → bool        → whether thumbs are generated at processing
├─ supports_search() → bool            → whether full-text in-viewer search works
├─ supports_toc() → bool               → whether TOC is extracted
├─ content_mime_type() → str           → MIME of the served content
├─ upload_mime_types() → set[str]      → accepted MIME types at upload
├─ magic_bytes_valid(data: bytes) → bool → fast-path validation at upload
│
├─ # Worker interface (called by pipeline dispatcher)
├─ process(db, doc, document_id, storage, rasterizer, watermark) → dict
│
└─ # TOC interface
   └─ extract_toc(content, **kwargs) → list[TocEntry]
```

**Registered adapters (at startup, not per-request):**

| Adapter | file_type | viewer_mode | thumbnails | TOC source |
|---------|----------|-------------|-----------|-----------|
| `PDFAdapter` | pdf | image | ✓ | PDF bookmarks |
| `TextAdapter` | txt, log | text | ✗ | Heuristic headings |
| `MarkdownAdapter` | md | text | ✗ | ATX headings |
| `DocxAdapter` | docx | text | ✗ | Heading styles → markdown |
| `DocAdapter` | doc | text | ✗ | antiword → plain text |
| `PptxAdapter` | pptx | text | ✗ (Phase D3) or image | Slide titles |

**Registry:**
```python
_REGISTRY: dict[str, DocumentAdapter] = {}

def register(adapter: DocumentAdapter) -> None:
    _REGISTRY[adapter.file_type] = adapter

def for_file_type(ft: str) -> DocumentAdapter:
    return _REGISTRY[ft]  # KeyError → caught as "unsupported" 400
```

### Where the Adapter Replaces if/elif Chains

**tasks.py** (dispatch):
```python
# Before: if/elif chain
file_type = doc.file_type or "pdf"
if file_type in ("txt", "md", "log"):
    return await process_text_document(...)
elif file_type == "docx":
    ...

# After: single dispatch
adapter = document_adapter.for_file_type(file_type)
return await adapter.process(db, doc, document_id, storage, rasterizer, watermark)
```

**documents.py** (upload validation):
```python
# Before: hardcoded sets
ALLOWED_CONTENT_TYPES = {"application/pdf", "text/plain", ...}

# After: derived from adapters
ALLOWED_CONTENT_TYPES = {m for a in _REGISTRY.values() for m in a.upload_mime_types()}
```

**viewer.py** (download and text dispatch):
```python
# Before: if doc.file_type in ("txt", "md", "log", "docx", "doc"):
# After:
adapter = document_adapter.for_file_type(doc.file_type)
if adapter.viewer_mode == "text":
    ...
```

**TOC extractor** (dispatch):
```python
# Before: if file_type == "pdf": ... else: text_extractor
# After:
adapter = document_adapter.for_file_type(file_type)
return await adapter.extract_toc(content, **kwargs)
```

### Should the Phase A Deletion Be Reversed?

Yes — but differently. The deleted `document_adapter.py` was an ABC with `for_file_type()` factory and stub subclasses. It had the right idea but was wired to nothing.

The new adapter is **not a resurrection** of the old file. The key difference: each adapter's `process()` method directly contains or calls the existing pipeline function. The adapter does not replace the pipeline — it wraps it. `PDFAdapter.process()` calls `process_pdf_document()` directly. No behavior changes.

---

## Section 3 — DOCX Strategy

### Current DOCX Implementation (Already Shipped)

DOCX is already fully supported via `pipeline/word.py`:
1. `python-docx` → `extract_docx_toc()` → native heading styles → TOC sidecar JSON
2. `python-docx` → `docx_to_markdown()` → stored as markdown text
3. Served via `/api/viewer/text` with watermark text in response
4. Viewer renders as markdown in `<pre>` with search + chunk nav

**Assessment: DOCX implementation is production-ready. No strategy change needed.**

### What python-docx vs alternatives would mean:

| Library | Fidelity | Memory | Security | Maintenance | Verdict |
|---------|---------|--------|---------|-------------|--------|
| **python-docx (current)** | Good for text/structure | Low | ZIP parse, lxml XML | Mature, stable | ✓ Keep |
| Docling | Better OCR, table extraction | High (~500MB model) | ML model surface | New, evolving | Overkill for current needs |
| LibreOffice headless | Best fidelity | Very high (1+ GB) | Subprocess, wider attack surface | Complex Dockerfile | Not needed yet |

**Recommendation: Keep python-docx for DOCX.** It correctly handles the primary use case (training documents): headings, paragraphs, basic tables. If rich table fidelity becomes a requirement, LibreOffice conversion to PDF → PDF pipeline can be added as a secondary path. Not needed for Phase D.

---

## Section 4 — PPTX Strategy

### Evaluation

PPTX (`.pptx`) is also a ZIP-based OpenXML format. The choice is between:

| Option | Description | Quality | Complexity | Docker size | Recommended? |
|--------|------------|---------|-----------|------------|-------------|
| **python-pptx → text** | Extract slide text, store as markdown-ish text chunks | Good for content | Low | +0 MB | ✓ Phase D3 |
| **LibreOffice → PDF → PDF pipeline** | Convert to PDF, then rasterize | Best fidelity | High | +~400MB | Later |
| **pdf2image + unoconv** | unoconv wrapper for LibreOffice | Good | Medium | +~400MB | Not yet |
| **Docling** | Layout + OCR analysis | Best for tables | Very high | +2GB+ model | Premature |

### Recommended PPTX Strategy: python-pptx → text chunks (Phase D3)

**Rationale:**

1. **Zero new system dependencies.** `python-pptx` is pure Python (like `python-docx`). The Dockerfile gains one `pip install` line and nothing else.

2. **Processing path mirrors DOCX exactly.** `PptxAdapter.process()` would:
   - Download pptx bytes
   - Extract slide titles → TOC sidecar JSON (using `python-pptx` `Slide.shapes`)
   - Convert slide text to markdown-style text (one heading per slide, body text below)
   - Store as text, count chunks, mark ready
   - Serve via `/api/viewer/text` — identical to DOCX

3. **Viewer requires zero changes.** `isTextDoc` already handles any `doc_type !== "pdf"`. PPTX viewed as text chunks works today.

4. **TOC is excellent for presentations.** Slide titles from `python-pptx` are directly the TOC: "Chapter 1", "Slide 5: Methods", etc. TOC quality for PPTX-as-text is arguably better than for DOCX-as-markdown.

5. **The tradeoff: no visual fidelity.** Slide layouts, images, charts, and formatting are stripped. This is the same tradeoff as DOCX→markdown today. For training material (lecture notes, slides), text extraction is sufficient.

**When to upgrade to image rendering:**  
If trainers report that PPTX content is "unreadable without visuals" (i.e., the document is primarily image-heavy or diagram-heavy), the upgrade path is: add LibreOffice to the Dockerfile, create a `PptxRasterAdapter` that converts pptx→PDF via LibreOffice, then runs the PDF pipeline. This upgrade does not affect any other format and does not require changing the viewer or analytics.

**python-pptx PPTX extraction algorithm:**

```python
# PptxAdapter.process() skeleton
from pptx import Presentation
from pptx.util import Pt

def pptx_to_markdown(pptx_bytes: bytes) -> tuple[str, list[TocEntry]]:
    prs = Presentation(io.BytesIO(pptx_bytes))
    slides = []
    toc_entries = []
    
    for i, slide in enumerate(prs.slides, start=1):
        # Title detection: layout placeholder type 0 or 1
        title = _get_slide_title(slide) or f"Slide {i}"
        body_texts = _get_slide_body(slide)
        
        # TOC: each slide is a level-1 section
        toc_entries.append(TocEntry(
            id=f"toc_{i:04d}",
            title=title,
            level=1,
            anchor=f"slide_{i:04d}",
            chunk=i,  # each slide = one chunk (or more for dense slides)
        ))
        
        lines = [f"## {title}"] + body_texts
        slides.append("\n".join(lines))
    
    return "\n\n---\n\n".join(slides), toc_entries
```

**Memory profile:** python-pptx loads only the XML tree, not any rendered images. Memory usage for a 200-slide PPTX: ~50-200MB. Comparable to DOCX.

---

## Section 5 — Universal TOC Strategy

### Current State

The TOC system is already well-designed. `TocEntry` is a universal model. `toc/extractor.py` dispatches by format. `toc/cache.py` provides L1+L2 caching (wired in Phase A).

### What Must Change for PPTX

Add `"pptx"` to `TOC_SUPPORTED_TYPES` in `toc/extractor.py`. TOC extraction for PPTX follows the text path (slide titles are extracted during processing and stored as a JSON sidecar, identical to DOCX).

### Schema: TocEntry (Already Universal)

```json
{
  "id":         "toc_0003",
  "title":      "Introduction to Neural Networks",
  "level":      1,
  "anchor":     "slide_0003",
  "chunk":      3,
  "source":     "pptx_slide_title",
  "confidence": 0.98,
  "children":   []
}
```

The existing `TocEntry` schema handles all 7 formats:

| Format | TOC Source | Navigation | Confidence |
|--------|-----------|-----------|-----------|
| PDF | PDF outline/bookmarks | `page` field | 0.95 |
| TXT | ALL-CAPS, numbered headings | `chunk` + `line` | 0.62–0.80 |
| MD | `#` ATX headings | `chunk` + `line` | 0.90 |
| LOG | Numbered sections, `===` borders | `chunk` + `line` | 0.62–0.75 |
| DOCX | Word heading styles (H1–H6) | `chunk` + `line` | 0.92 |
| DOC | antiword → plain text heuristics | `chunk` + `line` | 0.70 |
| PPTX | Slide title shapes | `chunk` | 0.98 |

**No schema changes needed.** PPTX simply uses `chunk` for navigation (same as DOCX).

### TOC Storage Strategy

| Format | Storage | Trigger | Cache |
|--------|---------|---------|-------|
| PDF | `toc/{doc_id}.json` sidecar | Worker (from bookmarks) | L1+L2 (Redis) |
| DOCX | `toc/{doc_id}.json` sidecar | Worker (from heading styles) | L1+L2 (Redis) |
| PPTX | `toc/{doc_id}.json` sidecar | Worker (from slide titles) | L1+L2 (Redis) |
| TXT/MD/LOG | Inline extraction at first `/toc` request | Viewer (from cached text) | L1+L2 (Redis) |
| DOC | Inline extraction at first `/toc` request | Viewer (antiword → text already stored) | L1+L2 (Redis) |

PPTX joins the "sidecar at processing time" group. This is better than inline extraction: slide titles are available before a viewer opens the document, so the TOC is ready immediately.

---

## Section 6 — Viewer Strategy

### The Core Question

**Option A: Convert everything to page images (rasterize all formats)**  
**Option B: Mixed viewer (images for PDF, text for others)**  
**Option C: Hybrid (same viewer, different data source)**

### Decision: Option C — Already Implemented

The current architecture IS a hybrid viewer. The React `ViewerScreen` already handles two protocols:
- `doc_type === "pdf"` → image viewer (blob URLs, crossfade, thumbnails)
- `doc_type !== "pdf"` → text viewer (`<pre>`, chunks, search)

PPTX as text-path means `isTextDoc = true` and `doc_type = "pptx"`. **Zero viewer changes required for Phase D3.**

### Comparison for Reference

| Dimension | Option A (all images) | Option B (split viewer) | Option C (hybrid, current) |
|-----------|---------------------|------------------------|--------------------------|
| Security | Best (no raw content) | Medium (text leaks raw content) | Same as B — text path sends plaintext |
| Watermarking | Best (burned into pixels) | Partial (visible overlay on PDF; text watermark on text) | Same hybrid approach |
| Latency | High (rasterize all) | Low for text, high for PDF | Low |
| Memory (worker) | High (rasterize all) | Low for text | Low |
| Search | Hard (needs OCR) | Native for text | Native for text docs |
| TOC navigation | Image scroll | Chunk navigation | Both work |
| PPTX fidelity | Perfect | Text only | Text only |
| Maintenance | One viewer | Two viewers | One viewer, two modes |

**For the current use case (trainer slides + training documents), Option C is correct.** Full PPTX visual fidelity requires LibreOffice and is a Phase D4+ decision.

### Future Visual Viewer for PPTX (When Needed)

If LibreOffice is added to the Dockerfile, `PptxRasterAdapter.process()` would:
1. Write pptx bytes to a temp file
2. Call `libreoffice --headless --convert-to pdf input.pptx`
3. Read the output PDF bytes
4. Call `process_pdf_document()` — the existing PDF pipeline handles the rest

This upgrade path produces perfect visual fidelity with no viewer changes. The adapter pattern makes this a one-file change.

---

## Section 7 — Security Impact

### New Attack Surface

| Threat | Format | Mitigation |
|--------|--------|-----------|
| Malicious XML (XXE in OOXML) | DOCX, PPTX | python-docx/python-pptx use lxml's safe parser; no external entity loading by default |
| ZIP bomb (deeply nested or huge expanded size) | DOCX, PPTX | Worker rasterizer_timeout_sec applies; add explicit size check after loading |
| Malformed OOXML (crash parser) | DOCX, PPTX | Wrapped in try/except; parser errors → permanent failure (no retry) |
| Embedded macros (VBA in .doc) | DOC | antiword strips macros; plain text output only |
| Embedded macros (VBA in .docx) | DOCX | python-docx reads XML paragraphs only; ignores VBA modules |
| Embedded macros in PPTX | PPTX | python-pptx reads XML shapes only; ignores VBA |
| Executable embedded in OOXML | All ZIP formats | Worker never executes embedded content |
| PPTX with embedded OLE objects | PPTX | python-pptx skips non-text shapes |
| Large expanded ZIP (250MB pptx → 2GB extracted) | PPTX | Add max_expanded_size check after Presentation() load |

### ZIP Bomb Mitigation (New Requirement for PPTX)

PPTX/DOCX are ZIP archives. A crafted ZIP that expands to many GB could exhaust worker disk or memory.  
**Required addition in PptxAdapter:**
```python
prs = Presentation(io.BytesIO(pptx_bytes))
# python-pptx loads only the XML tree into memory — ZIP entries are not fully extracted.
# However, enumerate slide count as a sanity check.
if len(prs.slides) > settings.max_pages_per_doc:
    raise ValueError(f"PPTX has too many slides ({len(prs.slides)})")
```

python-pptx uses `zipfile.ZipFile` internally, which does not auto-expand all entries into memory — it reads on demand. The risk is bounded by the slide count check above.

### Worker Isolation

The worker container is separate from the API container. Document processing (including potential parser crashes) cannot affect API availability. This is an existing strength that covers all format additions.

### No New Storage Key Namespaces

PPTX uses the same storage key scheme:
- `originals/{doc_id}.pptx` — original file
- `toc/{doc_id}.json` — TOC sidecar
- No page images, no thumbnails (text path)

Security properties: originals are never returned directly to viewers. The text/chunk endpoints only return decoded text — no storage keys, no original file paths, no binary data.

---

## Section 8 — Latency Impact

### PPTX Processing Time Estimates

| Stage | Small PPTX (20 slides) | Medium PPTX (100 slides) | Large PPTX (400 slides) |
|-------|------------------------|-------------------------|------------------------|
| Download from S3 | ~1s | ~2-5s | ~10-30s |
| `Presentation()` load | ~0.1s | ~0.5s | ~2s |
| Slide title extraction | ~0.05s | ~0.2s | ~0.8s |
| Text extraction | ~0.2s | ~1s | ~4s |
| TOC sidecar upload | ~0.5s | ~0.5s | ~0.5s |
| Text storage overwrite | ~0.5s | ~0.5s | ~1s |
| **Total** | **~3s** | **~8-10s** | **~40s** |

PPTX is significantly faster than PDF processing (PDF rasterization takes 30–300s). A 100-slide PPTX processes in ~8s vs ~60s for a 100-page PDF.

### PPTX Viewer Latency (Text Path)

| Operation | Latency |
|-----------|---------|
| `/validate` (establish session) | ~25-40ms (same as DOCX) |
| `/text/{token}/1` (first chunk) | ~5ms (text cache or ~30ms S3) |
| `/toc/{token}` | ~2ms (L1 cache) or ~10ms (Redis) |
| Each additional chunk | ~5ms (text cache) |

PPTX viewer latency is **identical to DOCX** — both use the text chunk endpoint.

### Memory Profile Comparison

| Format | Worker RAM (100 pages/slides) | API RAM per request |
|--------|------------------------------|---------------------|
| PDF (raster) | ~870MB (PIL images in memory) | ~20MB per page (watermark) |
| DOCX (text) | ~20MB (lxml tree) | ~1MB per chunk |
| PPTX (text) | ~30MB (lxml tree, more shapes) | ~1MB per chunk |

PPTX and DOCX have comparable low memory footprints. This is a major advantage over rasterization.

---

## Section 9 — Competitor Comparison

### How TraceView Compares

| Feature | TraceView (current) | TraceView (post-D) | FlipLink | DocSend | Digify | Box | Adobe |
|---------|--------------------|--------------------|---------|---------|--------|-----|-------|
| **PDF visual viewer** | ✓ Watermarked pages | ✓ Same | ✓ | ✓ | ✓ | ✓ | ✓ |
| **DOCX support** | ✓ Text chunks | ✓ Same | ✗ / limited | ✓ Convert | ✓ | ✓ | ✓ |
| **PPTX support** | ✗ | ✓ Text chunks | ✗ | ✓ Convert | ✓ | ✓ | ✓ |
| **Per-session watermarks** | ✓ Identity + angle jitter | ✓ Same | ✗ | Limited | ✓ | ✗ | ✓ |
| **IP allowlist** | ✓ Per-link | ✓ Same | ✗ | ✓ (enterprise) | ✓ | ✓ | ✓ |
| **Per-viewer analytics** | ✓ Page-level | ✓ Same | Limited | ✓ | ✓ | Limited | Limited |
| **Self-hosted option** | ✓ Docker | ✓ Same | ✗ | ✗ | ✗ | ✗ | ✗ |
| **PPTX visual fidelity** | N/A | Text only | N/A | Full slides | Full slides | Full | Full |
| **Offline/local processing** | ✓ R2/S3 | ✓ Same | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Open source** | Private | Private | ✗ | ✗ | ✗ | ✗ | ✗ |

### Where TraceView Is Stronger

1. **Per-session forensic watermarking** — angle jitter + session identity burned into pixels. No competitor matches this for PDF. Competitors typically use document-level watermarks (not session-specific).

2. **Self-hosted architecture** — all document bytes stay in your own S3/R2 bucket. DocSend, Digify, and FlipLink require uploading to their cloud.

3. **IP allowlist + email restriction per link** — the combination of per-link policies (password + email + IP + expiry + concurrent sessions) is more granular than most competitors.

4. **Build cost** — a fully featured, secure document sharing system for a fraction of SaaS pricing.

### Where TraceView Still Lags

1. **PPTX visual fidelity** — DocSend, Digify, and Box show actual rendered slides. Text-only PPTX is functional but visually inferior for design-heavy presentations. *(Fixable with LibreOffice in Phase D4.)*

2. **No mobile-native app** — competitors have iOS/Android apps. TraceView is a responsive web app but has no offline capability.

3. **No e-signature integration** — DocSend and Adobe have NDA signing built in. TraceView has no signing workflow.

4. **No CRM integration** — DocSend integrates with Salesforce/HubSpot. TraceView has no CRM webhook yet.

5. **Document preview on upload** — competitors show a preview thumbnail before sharing. TraceView shows "processing…" until Celery completes.

---

## Section 10 — Implementation Roadmap

### Phase D1 — Foundation: DocumentAdapter Wiring
**Duration:** 1–2 days  
**Risk:** Low (pure refactor, no behavior change)

**Objective:** Wire `DocumentAdapter` pattern into production paths so new formats can be added without touching 10 locations.

**Files:**
- `backend/app/services/document_adapter.py` — reintroduce as the dispatch registry
- `backend/app/workers/tasks.py` — replace if/elif with `adapter.process()`
- `backend/app/routers/documents.py` — derive ALLOWED_CONTENT_TYPES from registry
- `backend/app/routers/viewer.py` — use `adapter.viewer_mode` for text/image dispatch
- `backend/app/services/toc/extractor.py` — use `adapter.extract_toc()` for dispatch

**Migration requirements:** None. No DB changes.

**Tests required:**
- All existing format tests must pass unchanged (pure refactor)
- Adapter registry integration test: all registered adapters satisfy the interface
- Dispatch test: correct adapter called for each file_type

**Complexity:** Low — the logic already exists, this just centralizes it.

---

### Phase D2 — DOCX Enhancement (Optional)
**Duration:** 0–1 day  
**Risk:** Very low

**Objective:** DOCX is already fully working. Optional enhancements:
- Rich table extraction in `docx_to_markdown()` (currently tables are stripped)
- Support for images via `[Image]` placeholder tags in output text

**Files:** `services/toc/docx_extractor.py`

**Migration requirements:** None.

**Recommendation:** Defer until a trainer reports table content missing. Current implementation is sufficient for most training documents.

---

### Phase D3 — PPTX Support
**Duration:** 2–3 days  
**Risk:** Low

**Objective:** Add PPTX as a text-path document type.

**New files:**
- `backend/app/workers/pipeline/pptx.py` — `process_pptx_document()` function
- `backend/app/services/toc/pptx_extractor.py` — `extract_pptx_toc()` + `pptx_to_markdown()`

**Modified files:**
- `backend/requirements.txt` — add `python-pptx==1.0.2` (or latest stable)
- `backend/Dockerfile` — no changes (python-pptx is pure Python)
- `backend/app/services/document_adapter.py` — add `PptxAdapter` registration
- `backend/alembic/versions/013_add_pptx_file_type.py` — add "pptx" to document_status enum if enum-constrained (check: file_type is `String(10)`, not an enum — no migration needed)

**DB change check:** `Document.file_type` is `String(10), default="pdf"` — no enum constraint. Adding `"pptx"` requires no migration.

**Upload router changes:** Add pptx MIME type and magic bytes check:
```
application/vnd.openxmlformats-officedocument.presentationml.presentation
```
Magic bytes: same ZIP magic (`PK`) as DOCX — disambiguated by file extension.

**Viewer changes:** Zero. `isTextDoc = (doc_type !== 'pdf')` already handles PPTX.

**Tests required:**
- Upload: PPTX accepted, non-PPTX ZIP rejected
- Worker: slide extraction produces non-empty text + TOC sidecar
- Viewer: text chunk served correctly, TOC returned
- Analytics: events logged correctly
- Download: PPTX raw bytes returned (text download path)

---

### Phase D4 — Universal TOC Enhancement
**Duration:** 1 day  
**Risk:** Very low

**Objective:** Improve TOC quality for all formats.

**Changes:**
- `toc/text_extractor.py` — better heuristics for LOG (timestamp patterns, level detection)
- `toc/extractor.py` — add pptx routing
- `toc/cache.py` — already wired; no changes needed

**No new dependencies.**

---

### Phase D5 — Visual PPTX Rendering (LibreOffice Path)
**Duration:** 3–5 days  
**Risk:** Medium

**Objective:** High-fidelity PPTX rendering via LibreOffice headless → PDF → existing PDF pipeline.

**Requires:**
- LibreOffice in Dockerfile (`apt-get install libreoffice`) — **+~400MB image size**
- `PptxRasterAdapter` that converts pptx → pdf bytes → calls `process_pdf_document()`
- Config flag: `PPTX_VIEWER_MODE=image|text` to switch between D3 and D5

**This phase is not required for launch.** Text-path PPTX (Phase D3) covers the majority of training material use cases. Upgrade to visual rendering when trainers report design-heavy slides.

---

## Section 11 — Go / No-Go

### Can PPTX Implementation Begin Immediately?

**Yes, with one prerequisite.**

#### Must-Do Before PPTX (D1): Re-introduce DocumentAdapter (1–2 days)

Without the adapter pattern, adding PPTX requires editing 10 production files with format-specific logic. This is doable but accumulates technical debt and increases the risk of missing a location (as happened with the download endpoint missing the IP allowlist check in Phase B1 — found because of 10 similar locations).

Phase D1 (adapter wiring) makes Phase D3 (PPTX) a 2-file change instead of a 10-file change.

**If the team wants to move faster:** PPTX can be added without D1 by hand-editing the 10 locations. This is acceptable as long as the test coverage covers all 10 locations.

#### D1 → D3 is the Recommended Order

```
Week 1
  D1 (1–2 days): Re-introduce DocumentAdapter, wire into production
  D3 (2–3 days): PPTX support (python-pptx text path)

Week 2+
  D2 (optional): DOCX table enhancement
  D4 (1 day): TOC improvements
  D5 (3–5 days, if needed): LibreOffice visual PPTX
```

#### No Blockers

| Concern | Status |
|---------|--------|
| Security audit (Phase B) | ✓ Complete |
| Performance audit (Phase C) | ✓ Complete, analytics index added |
| Worker sizing | ✓ Configurable (Phase C1) |
| DB changes for pptx | ✓ Not required (file_type is String, not enum) |
| Frontend changes for pptx | ✓ Not required (`isTextDoc` already correct) |
| Viewer endpoints for pptx | ✓ Not required (text path already exists) |
| python-pptx availability | ✓ Pure Python, trivial Dockerfile addition |
| TOC model for pptx | ✓ TocEntry already universal |
| Analytics for pptx | ✓ All events are format-agnostic |
| Caching for pptx | ✓ text_content_cache already works for any text format |

#### The One Real Risk

**python-pptx limitations:** python-pptx cannot render slides visually, extract images, or interpret complex diagrams. For training materials that are primarily visual (e.g., a slide deck that is 80% charts and diagrams), text extraction produces a nearly empty document. Trainers should be informed of this limitation at upload time.

**Mitigation:** Add a warning in the upload UI for PPTX files: "Presentation text will be extracted. Slide images and diagrams are not shown in the viewer." This sets correct expectations and avoids support requests.

---

## Appendix: Format Classification Reference

```
Format    Viewer Mode   Processing      TOC Source          Storage Pattern
────────────────────────────────────────────────────────────────────────────
pdf       image         rasterize       bookmarks           pages/ + thumbs/
txt       text          decode + chunk  heuristics          originals/ (text)
md        text          decode + chunk  # headings          originals/ (text)
log       text          decode + chunk  heuristics          originals/ (text)
docx      text          python-docx     heading styles      originals/ (text)
doc       text          antiword        plain heuristics    originals/ (text)
pptx      text (D3)     python-pptx     slide titles        originals/ (text)
pptx      image (D5)    libreoffice→pdf slide titles        pages/ + thumbs/
```

All 7 formats share: ownership, links, sessions, analytics, security policy, watermark text, caching infrastructure, and TOC storage format. Only the processing pipeline and viewer protocol differ.

---

*End of Phase D Architecture Audit. Phase D1–D5 implementation to follow.*
