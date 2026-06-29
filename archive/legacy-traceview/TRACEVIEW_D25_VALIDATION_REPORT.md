> **HISTORICAL ARCHIVE** — Reflects repository state before Sprint 4.2D extraction (2026-06-22). Not current. Do not use for active decision-making.

# TraceView Phase D2.5 — Validation & Production-Readiness Report
## DOCX Visual Rendering Pipeline Review

**Prepared:** 2026-06-04  
**Reviewer:** Phase D2.5 validation pass  
**Branch:** `phase-d2-docx-pipeline`  
**Baseline:** 1166/1166 tests passing  

---

## Table of Contents

1. [Architecture Validation](#1-architecture-validation)
2. [Security Validation](#2-security-validation)
3. [Performance Validation](#3-performance-validation)
4. [TOC Validation](#4-toc-validation)
5. [Deployment Validation](#5-deployment-validation)
6. [Real-World Document Behaviour](#6-real-world-document-behaviour)
7. [Remaining Risks](#7-remaining-risks)
8. [Required Fixes](#8-required-fixes)
9. [Nice-to-Have Improvements](#9-nice-to-have-improvements)
10. [Production-Readiness Verdict](#10-production-readiness-verdict)

---

## 1. Architecture Validation

### 1.1 Processing Path Completeness

The DOCX pipeline after Phase D2 follows a clean, linear path:

```
Upload boundary
  └─ detect_file_type() → "docx"
  └─ DOCXAdapter.validate_bytes() → ZIP magic check
  └─ storage.upload_file(docx_bytes, "originals/{id}.docx")

Celery worker
  └─ get_adapter("docx").process()
  └─ process_docx_as_pdf()
      └─ storage.download_bytes(doc.storage_key)           ← DOCX bytes
      └─ LibreOfficeConverter.convert_to_pdf(docx_bytes)   ← subprocess
      └─ process_pdf_document(... pdf_bytes=<converted>)   ← reuse existing
          └─ rasterizer.rasterize_document(pdf_bytes)
          └─ watermark.apply_forensic_stamp() per page
          └─ storage.upload_file(pages/{id}/{n:04d}.webp)
          └─ storage.upload_file(thumbs/{id}/{n:04d}.webp)
          └─ DocumentPage records
          └─ doc.status = "ready"
          └─ extract_and_store_pdf_toc()  (LO bookmarks, may be empty)
      └─ extract_docx_toc(docx_bytes)    ← overwrites PDF bookmark sidecar
      └─ storage.upload_file(toc/{id}.json)
```

**Result: No duplicate paths exist.** ✓

### 1.2 Dead Code Audit

| Symbol | File | Status |
|--------|------|--------|
| `process_docx_document` | `pipeline/word.py` | ✅ Removed |
| `docx_to_markdown` | `toc/docx_extractor.py` | ✅ Removed |
| `_process_as_converted_text` | `pipeline/word.py` | ✅ Retained — still used by `process_doc_document` |
| `DOCXAdapter.extract_toc(text_content)` | `adapters/word.py` | ✅ Retained — documented defensive fallback; not reached via viewer |
| `_WordBaseAdapter.viewer_mode = "text"` | `adapters/word.py` | ✅ Retained — used by `DOCAdapter` (inherits) |
| `_WordBaseAdapter.toc_fallback_to_text()` | `adapters/word.py` | ✅ Retained — used by `DOCAdapter` (inherits) |
| `import re` | `toc/docx_extractor.py` | ✅ Removed |
| `from typing import Tuple` | `toc/docx_extractor.py` | ✅ Removed |

**No dead code remains.** ✓

### 1.3 Orphaned Text-Mode DOCX Logic

The viewer has three key routing decisions for DOCX:

| Route | Pre-D2 | Post-D2 | Result |
|-------|--------|---------|--------|
| `GET /api/viewer/text/{token}/{chunk}` | Accepted DOCX | `viewer_mode != "text"` → 400 | ✅ Correctly rejects |
| `GET /api/viewer/toc/{token}` | No sidecar → text extraction | `toc_fallback_to_text()=False` → empty TOC | ✅ Correctly blocks text fallback |
| `GET /api/viewer/download/{token}` | Returns raw text file | `viewer_mode != "text"` → image PDF assembly | ✅ Correctly produces watermarked PDF |

**No orphaned text-mode DOCX logic remains.** ✓

### 1.4 Stale Comments

Two locations in `viewer.py` contain stale comment text that references DOCX in the text-mode context it no longer occupies. These are documentation issues only — they have no functional impact.

| Location | Current text | Correct text |
|----------|-------------|-------------|
| `viewer.py:595` | `# DOCX/DOC without sidecar: fall through to text extraction` | `# DOC without sidecar: fall through to text extraction` |
| `viewer.py:597` | `# Text-based extraction (TXT, MD, LOG, and DOCX/DOC without sidecar)` | `# Text-based extraction (TXT, MD, LOG, and DOC without sidecar)` |
| `viewer.py:547` (docstring) | `docx / doc → TOC sidecar if present, else inline text extraction` | `docx → TOC sidecar if present, else empty; doc → sidecar or text extraction` |
| `viewer.py:708` | `# DOCX/DOC are stored as converted text after processing` | `# DOC is stored as converted text after processing` |

**Verdict: Architecture is clean. Four minor stale comments exist.**

---

## 2. Security Validation

### 2.1 Subprocess Safety (`libreoffice_converter.py`)

| Check | Implementation | Result |
|-------|---------------|--------|
| Shell injection | `subprocess.run(cmd, ...)` where `cmd` is a list — no `shell=True` | ✅ Safe |
| Path traversal | Input filename hardcoded as `f"input{suffix}"` in a `mkdtemp()` directory | ✅ Safe |
| Temp file cleanup | `finally: shutil.rmtree(tmp_dir, ignore_errors=True)` | ✅ Unconditional |
| Binary path | `shutil.which("libreoffice")` — no hardcoded paths | ✅ Safe |
| Output isolation | `--outdir tmp_dir` — LibreOffice writes only to the temp directory | ✅ Safe |
| Process timeout | `subprocess.run(..., timeout=CONVERSION_TIMEOUT_SEC)` | ✅ Enforced |

### 2.2 Claimed Security Flag Not Implemented ⚠️

**Finding:** The module docstring states:

> Macros disabled via `--nomacroexecution` (LibreOffice 7.2+) and `--infilter` to constrain the import filter.

The actual `cmd` constructed in `convert_to_pdf()` (lines 117–125) is:

```python
cmd = [
    binary,
    "--headless",
    "--norestore",
    "--nolockcheck",
    "--convert-to", "pdf",
    "--outdir", tmp_dir,
    input_path,
]
```

Neither `--nomacroexecution` nor `--infilter` is present.

**Runtime impact assessment:** LibreOffice in `--headless` mode suppresses all interactive dialogs, which in practice prevents most macro execution prompts. On Debian bookworm, LibreOffice's default macro security level (Medium) will block unsigned macros from untrusted sources in headless mode. The _actual_ security level is acceptable, but the _documentation is false_.

**Risk:** If a future maintainer relies on the docstring to audit security and finds the flag missing, they may incorrectly conclude it was accidentally removed and add it without testing — potentially altering conversion behaviour. Alternatively, the mismatch erodes confidence in the security documentation.

**Severity: MEDIUM** — Documentation inaccuracy, not a runtime vulnerability. The fix is trivial: either add the flags or correct the docstring.

### 2.3 `suffix` Parameter Not Validated ⚠️

`convert_to_pdf(input_bytes, suffix=".docx")` constructs:
```python
input_path = os.path.join(tmp_dir, f"input{suffix}")
```

The docstring says `suffix` must start with `.` and contain only safe characters, but there is no runtime enforcement. The current call site in `docx_pdf.py` hardcodes `".docx"`, making this a latent API design issue rather than an active vulnerability.

**Severity: LOW** — Not exploitable with current call sites. Relevant if the converter is reused for other formats (PPTX).

### 2.4 No Security Regressions

The following Phase D1/prior security properties are preserved:

- `doc.storage_key` is never exposed in API responses ✅
- `password_hash` never appears in any response ✅
- IP stored as SHA-256 hash only ✅
- Per-session visible watermark burned into images ✅ (DOCX now gets forensic stamp + visible watermark on every page, identical to PDF)
- Session validation required before all content endpoints ✅
- `can_download` permission enforced for downloads ✅

**Net security improvement:** DOCX documents now receive the full forensic stamp + session watermark treatment. Previously, DOCX watermarks were CSS overlays removable via DevTools. This is a meaningful security upgrade.

---

## 3. Performance Validation

### 3.1 Worker RAM Profile

| Stage | Memory (typical) | Memory (worst case) |
|-------|-----------------|---------------------|
| LibreOffice subprocess (small DOCX, 10p) | +100–200 MB | +300 MB |
| LibreOffice subprocess (large DOCX, 100p, image-heavy) | +300–500 MB | +800 MB–1.2 GB |
| pdf2image rasterization (existing) | +200–400 MB | +800 MB–4 GB |
| **Peak combined (stages run sequentially)** | **+500 MB–900 MB** | **+1.6 GB–5.2 GB** |

**Risk: HIGH** for 100-page image-heavy DOCX documents on workers configured with 4 GB RAM.

The existing config.py comment documents: `"PDF rasterization uses 800MB–4GB RAM per worker depending on page count."` For large DOCX, LibreOffice adds on top of this. With `worker_concurrency: 2`, two simultaneous large DOCX conversions could push total RAM to 8+ GB.

**Mitigation already in place:** `max_upload_mb: 100` caps upload size, limiting the maximum DOCX size. A 100 MB DOCX is unusually large; most real-world DOCX files are 1–20 MB.

**Recommendation:** Set `worker_concurrency: 1` (not 2) in deployments that primarily process DOCX or PDF documents. This is already documented as a sizing consideration but not enforced by default.

### 3.2 Temporary Disk Usage

Each DOCX conversion creates:
- `securedoc_lo_XXXX/input.docx` — copy of original (same size as uploaded DOCX, max 100 MB)
- `securedoc_lo_XXXX/input.pdf` — LibreOffice output (typically 3–10× input size for text-heavy docs; can be 1× for image-heavy docs where images are already compressed)

For a 50 MB DOCX → 150 MB PDF: **200 MB temp disk peak per conversion**.

With `worker_concurrency: 2` and two simultaneous DOCX conversions: up to **400 MB temp disk**.

Cleanup is unconditional (finally block) ✓. The risk is the window between conversion start and cleanup: if the OS kills the worker process (OOM), the temp dir is not cleaned up. On container restart, orphaned temp dirs in `/tmp` accumulate. This is low-risk in practice (Railway containers have ephemeral storage; `/tmp` is lost on restart).

**Risk: LOW** for normal operation.

### 3.3 Timeout Architecture

```
asyncio.wait_for(
    loop.run_in_executor(None, converter.convert_to_pdf, ...),
    timeout=70,              ← outer (asyncio level)
)
  └─ subprocess.run(cmd, timeout=60)   ← inner (OS level)
      └─ LibreOffice process
```

The layered timeout design is correct. The inner OS-level timeout fires first (60s), causing `subprocess.TimeoutExpired` → `LibreOfficeTimeoutError` → `ValueError` → permanent failure ✅.

**However:** If the outer `asyncio.wait_for` fires (70s) before the inner can propagate (a race condition if subprocess startup takes > 60s before `subprocess.run()` is even called — which is unrealistic but theoretically possible), `asyncio.TimeoutError` is raised. This is NOT caught by `except LibreOfficeError`. See Required Fixes §8.2.

### 3.4 LibreOffice Startup Cost Per Conversion

| Document size | Startup | Conversion | Rasterization | Total |
|--------------|---------|-----------|---------------|-------|
| Small (10p, 100 KB) | ~2–5s | ~1–3s | ~2–5s | ~5–13s |
| Medium (50p, 2 MB) | ~2–5s | ~5–12s | ~10–25s | ~17–42s |
| Large (100p, 20 MB) | ~2–5s | ~15–30s | ~20–50s | ~37–85s |

For small documents, LibreOffice startup dominates (50%+ of total). This is inherent to the per-subprocess approach. The impact is fully async (202 returned immediately) so users never experience this as latency.

### 3.5 Performance Risk Summary

| Area | Risk | Rationale |
|------|------|-----------|
| Worker RAM (large image-heavy DOCX) | HIGH | LibreOffice + pdf2image simultaneously need >4 GB |
| LibreOffice startup per conversion | LOW | Async; dominates only for tiny docs |
| Temp disk during conversion | LOW | 100–400 MB peak; cleaned immediately |
| Conversion timeout enforcement | MEDIUM | asyncio.TimeoutError gap (see §8.2) |
| Concurrent DOCX conversions | HIGH | `worker_concurrency: 2` may OOM |

---

## 4. TOC Validation

### 4.1 TOC Source Priority

The DOCX TOC pipeline after D2:

```
Step 1: process_pdf_document() calls extract_and_store_pdf_toc()
  → Extracts PDF bookmarks from LibreOffice-converted PDF
  → Writes toc/{id}.json only if bookmarks exist
  → LibreOffice typically preserves NO bookmarks → sidecar skipped

Step 2: extract_docx_toc(docx_bytes)
  → Extracts heading styles from original DOCX (python-docx)
  → Writes toc/{id}.json (overwrites any Step 1 output)

Net result: DOCX heading sidecar always wins over PDF bookmarks
```

The "DOCX headings win" invariant is correctly implemented. ✓

### 4.2 Critical TOC Defect: Navigation Fields Mismatch ⛔

**Finding:** `extract_docx_toc()` produces `TocEntry` objects with `chunk` and `line` fields but **not** `page`:

```python
# docx_extractor.py lines 97–107
chunk = (line_counter - 1) // lines_per_chunk + 1
entries.append(TocEntry(
    ...
    chunk=chunk,        ← text-mode navigation field
    line=line_counter,  ← source line number
    # page=???          ← NOT SET
))
```

After serialisation via `TocEntry.to_dict()`, the sidecar JSON contains:

```json
{"id": "toc_0001", "title": "Introduction", "level": 1, "anchor": "sec_0001",
 "chunk": 1, "line": 3, "source": "heading_style", "confidence": 0.92}
```

The image viewer (which DOCX now uses) navigates via the `page` field. The frontend's TOC sidebar, when a user clicks an entry, likely uses `entry.page` to call `/api/viewer/page/{token}/{page}`. Without `page`, the click either does nothing, navigates to page 1, or throws a JavaScript error depending on how the frontend handles a missing `page`.

This is not a new regression in `extract_docx_toc()` — the function was always designed for text-mode DOCX, where `chunk` was the right navigation field. The problem is that D2 changed DOCX to image mode without updating the extractor to produce `page`-based navigation data.

**The fundamental problem:** Page numbers in the LibreOffice-converted PDF cannot be known until AFTER conversion, at which point we only have PDF bytes. `extract_docx_toc()` runs on the original DOCX bytes and has no way to know which page each heading will land on in the resulting PDF.

**Severity: HIGH** — TOC entries appear in the sidebar but navigation may be broken for DOCX documents.

### 4.3 TOC Caching Behaviour

The existing cache path (L1 `toc_cache` → L2 Redis via `store_toc_async`) is unchanged. DOCX TOC entries are cached exactly as PDF entries are. The `invalidate_doc_entries()` call on document delete clears the TOC cache. ✓

### 4.4 Viewer TOC Route for DOCX

For a DOCX document after D2:

1. `/api/viewer/toc/{token}` is called with a valid session
2. `_toc_adapter = get_adapter("docx")` → `DOCXAdapter`
3. `DOCXAdapter.supports_toc_sidecar()` → `True`
4. Load `toc/{doc_id}.json` from storage
5. If found (headings exist) → return sidecar (entries have `chunk`, not `page`) ⚠️
6. If not found (`toc_fallback_to_text()=False`) → return `{"toc": [], "supported": False}`

The `supported: False` case is correct and clean. The `supported: True` case returns entries that lack `page` — a functional gap.

### 4.5 PDF Bookmark Extraction from LibreOffice Output

LibreOffice typically generates PDF output **without bookmarks** for most DOCX files, unless the document contains explicit cross-reference links or the Word file was authored with specific PDF export settings. In the majority of cases, `extract_and_store_pdf_toc()` will find no bookmarks and skip the sidecar. The DOCX heading sidecar is therefore the only TOC data available.

This is acceptable. The concern is not the absence of PDF bookmarks — it's that the DOCX heading entries lack `page` numbers.

---

## 5. Deployment Validation

### 5.1 Dockerfile Analysis

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    ...
    libreoffice-writer \
    fonts-liberation \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*
```

**Package dependency chain verified:**
```
libreoffice-writer
  → libreoffice-core
    → libreoffice-common        ← provides /usr/bin/libreoffice
```
Installing `libreoffice-writer` provides the `libreoffice` binary via its dependency chain. ✓

**Font coverage:**
| Font Family | Windows Default | Linux Substitute | Package |
|-------------|----------------|-----------------|---------|
| Arial | Yes | Liberation Sans | fonts-liberation |
| Times New Roman | Yes | Liberation Serif | fonts-liberation |
| Courier New | Yes | Liberation Mono | fonts-liberation |
| Calibri | Yes (default since Word 2007) | **Not covered** | — |
| Cambria | Yes | **Not covered** | — |
| DejaVu Sans/Serif | — | ✓ | fonts-dejavu-core |

**Critical gap:** Calibri is the default font in Microsoft Word 2007–2019. The majority of modern DOCX files use Calibri. It is not provided by `fonts-liberation` or `fonts-dejavu-core`. Without it, LibreOffice will substitute another font (typically DejaVu Sans), causing line-length differences that may reflow text and alter page breaks.

**Severity: MEDIUM** — Layout will visually differ from the original document for any DOCX using Calibri (the majority of modern Word documents). Text content is preserved; visual fidelity degrades.

**Recommended fix:** Add `fonts-crosextra-caladea fonts-crosextra-carlito` (metric-compatible Calibri/Cambria substitutes published by Google/Microsoft for exactly this purpose) to the Dockerfile.

### 5.2 Single Dockerfile for API and Worker ⚠️

The Dockerfile installs LibreOffice in the same image used for both the API server and Celery workers. The API server never calls LibreOffice. This means:

| Container | LibreOffice needed | LibreOffice installed | Wasted disk |
|-----------|-------------------|-----------------------|------------|
| API server | No | Yes | ~500–800 MB |
| Worker | Yes | Yes | — |
| Migration runner | No | Yes | ~500–800 MB |

**Estimated image size increase:** ~600–900 MB over the pre-D2 image.
**Estimated total image size:** ~1.5–1.8 GB.

This is within Railway's limits but increases:
- First-deploy build time: +5–10 minutes (LibreOffice download + install)
- Container startup time: negligible (image is pre-pulled)
- Storage costs on the container registry: minor

**Severity: LOW** for current Railway deployment. Would become MEDIUM at larger scale or if image pull time is a concern.

**Recommended mitigation:** A future Dockerfile split (e.g., `Dockerfile.worker`) would reduce the API image to ~700 MB. Not required now.

### 5.3 Railway Suitability

| Criterion | Assessment |
|-----------|-----------|
| Docker image size (~1.6 GB) | ✅ Within Railway limits |
| Worker RAM (2–4 GB for DOCX) | ✅ Railway Pro supports 4 GB+ containers |
| LibreOffice subprocess isolation | ✅ Container provides process isolation |
| Celery retry on transient errors | ✅ max_retries=3, default_retry_delay=10 |
| `worker_max_tasks_per_child` for memory cleanup | ✅ Already configurable via env |
| `worker_concurrency: 1` for memory safety | ⚠️ Default is 2; recommend reducing for DOCX-heavy deployments |

### 5.4 Build-time Impact

The `libreoffice-writer` layer is large (~400–600 MB downloaded). Docker layer caching means:
- First build after Dockerfile change: +5–10 minutes
- Subsequent builds (code-only changes): this layer is cached; no impact

The LibreOffice layer is placed BEFORE `COPY backend/ .`, which means it is correctly cached independently of application code changes. ✓

---

## 6. Real-World Document Behaviour

### 6.1 Document Type Assessment

| DOCX content type | LibreOffice fidelity | Risk |
|-------------------|---------------------|------|
| Text with Calibri font | Line reflow due to font substitution | MEDIUM |
| Tables (simple) | Good — LibreOffice handles most Word table formats | LOW |
| Tables (complex nested) | Occasional layout differences at cell borders | LOW |
| Embedded images (JPEG/PNG) | Preserved at original resolution | LOW |
| Large embedded images (>10 MB each) | Preserved; increases temp disk usage | LOW |
| Page breaks (explicit) | Preserved by LibreOffice | LOW |
| Headers and footers | Preserved | LOW |
| Word-generated TOC field | Rendered visually in PDF; DOCX heading sidecar provides structured TOC | LOW |
| Track changes / comments | Not shown (converted as accepted) | LOW (expected) |
| Macros | Not executed in headless mode | ✅ Safe |
| Linked OLE objects | Broken links may cause warnings; non-fatal | MEDIUM |
| Charts (embedded Excel) | Rendered as images in PDF | LOW |
| Equations (OMML) | LibreOffice renders most OMML equations | LOW |
| 100+ pages | Within timeout budget at 150 DPI rasterization | LOW |
| Uncommon fonts (Wingdings, Symbol) | Symbol fonts may render incorrectly | MEDIUM |

### 6.2 Font Rendering is the Dominant Fidelity Risk

**For most real-world DOCX documents (using Word defaults):**
- Calibri body text will reflow when substituted with DejaVu Sans or Liberation Sans
- A paragraph that fits on one page in Word may break to two pages in LibreOffice
- TOC page numbers in embedded Word TOC fields will be wrong after reflow
- This is an inherent limitation of server-side conversion without the original fonts

**This is acceptable trade-off for a security platform** — the goal is traceable, watermarked access, not pixel-perfect replication. However, users who share documents where page layout matters (legal contracts, formatted reports) may notice discrepancies.

The recommended fix (`fonts-crosextra-carlito`) would resolve the Calibri case, which covers the majority of modern DOCX files.

---

## 7. Remaining Risks

### 7.1 Risk Matrix

| ID | Description | Severity | Probability | Impact |
|----|-------------|----------|-------------|--------|
| R1 | TOC entries lack `page` field for image navigation | HIGH | Certain | TOC sidebar non-functional for DOCX |
| R2 | `asyncio.TimeoutError` triggers retry instead of permanent failure | MEDIUM | Low | Worker blocked for 3×70s on timed-out conversions |
| R3 | `--nomacroexecution` claimed but not implemented | MEDIUM | — | Documentation/audit confusion |
| R4 | Calibri font not installed → text reflow in most DOCX | MEDIUM | Certain | Layout differences from original |
| R5 | Worker OOM on large image-heavy DOCX with concurrency=2 | MEDIUM | Low–Medium | Worker killed, document retried |
| R6 | `suffix` parameter in converter not validated | LOW | Low | Not exploitable with current callers |
| R7 | Single image for API + worker (API carries LibreOffice) | LOW | — | Image bloat, first-deploy time |
| R8 | No `page` field in DOCX heading sidecar — affects future PPTX too | HIGH | Certain | Systematic gap in TOC design for non-text formats |

### 7.2 Risks That Were Previously Identified and Are Correctly Handled

| Concern | Implementation | Status |
|---------|---------------|--------|
| DOC (legacy .doc) unchanged | DOCAdapter still uses antiword text pipeline | ✅ Preserved |
| TXT/MD/LOG unchanged | Text pipeline untouched | ✅ Preserved |
| PDF unchanged | `process_pdf_document` backward-compatible (`pdf_bytes=None` default) | ✅ Preserved |
| Conversion failure → document error | `LibreOfficeError` → `ValueError` → permanent failure | ✅ Correct |
| Temp file cleanup on error | `finally: shutil.rmtree(...)` | ✅ Correct |
| Watermark for DOCX pages | Forensic stamp + visible watermark applied per-page (same as PDF) | ✅ Correct |
| Analytics for DOCX views | `page_viewed` events logged per page (same as PDF) | ✅ Correct |
| Download behaviour change | DOCX downloads now produce watermarked PDFs (improvement) | ✅ Intentional |

---

## 8. Required Fixes

### Fix 1 (HIGH): TOC `chunk`/`line` navigation for image-mode DOCX

**Location:** `backend/app/services/toc/docx_extractor.py` lines 97–107  
**Problem:** `extract_docx_toc()` produces `chunk` and `line` navigation fields (text-mode artifacts) but not `page`. After D2, DOCX is rendered as images where page-number navigation is required.  

**Root cause:** `extract_docx_toc()` was designed for text-mode DOCX where chunk numbers were meaningful. In image mode, there is no cheap way to know which page a heading will appear on in the LibreOffice-converted PDF — page assignment depends on font rendering, image sizes, and other layout decisions made by LibreOffice.

**Options for the fix:**

Option A — Accept TOC without navigation (simplest, least regressive):  
Clear the `chunk` field from DOCX heading entries in the sidecar. Entries appear in the TOC sidebar with title/level but no navigation target. The sidebar remains useful as a document outline; clicking does nothing or is disabled by the frontend.  
Effort: 5 minutes. Risk: None.

Option B — Extract page numbers from LibreOffice-converted PDF (best):  
After conversion, run `pypdf.PdfReader` on the converted PDF and attempt to extract bookmarks. LibreOffice often preserves `Heading N` styles as PDF bookmarks. If bookmarks exist, merge them with the DOCX heading names to build a `page`-capable sidecar. Bookmarks are stored as a parallel structure in the PDF outline; matching by title handles the common case.  
Effort: 1–2 hours. Risk: pypdf parsing of LO-generated PDFs may be unreliable for some edge cases.

Option C — Suppress DOCX TOC when no page numbers available:  
Return `supported: false` and an empty TOC for DOCX until page-number resolution is implemented. Functionally equivalent to Option A but avoids showing a non-navigable TOC.  
Effort: 5 minutes. Risk: Removes even the outline value from the TOC sidebar.

**Recommended fix:** Option A immediately (remove `chunk` from DOCX sidecar entries; keep `line` as a developer debug hint), followed by Option B as a follow-on improvement.

---

### Fix 2 (MEDIUM): Catch `asyncio.TimeoutError` in `docx_pdf.py`

**Location:** `backend/app/workers/pipeline/docx_pdf.py` lines 57–67  

**Problem:**
```python
try:
    pdf_bytes = await asyncio.wait_for(
        loop.run_in_executor(None, converter.convert_to_pdf, docx_bytes, ".docx"),
        timeout=LibreOfficeConverter.CONVERSION_TIMEOUT_SEC + 10,
    )
except LibreOfficeError as exc:
    raise ValueError(...) from exc
# asyncio.TimeoutError is NOT caught here
```

If `asyncio.wait_for` fires before the inner `subprocess.TimeoutExpired` (a race condition), `asyncio.TimeoutError` escapes to `_process_document_async()` in `tasks.py`, which treats it as a transient error (retried up to 3 times, each up to 70 seconds).

**Fix:**
```python
except (LibreOfficeError, asyncio.TimeoutError) as exc:
    raise ValueError(
        f"DOCX conversion failed for document {document_id}: {exc}"
    ) from exc
```

**Note:** The `import asyncio` is already at the top of `docx_pdf.py`. No new import needed.  
Effort: 2 minutes. Risk: None.

---

### Fix 3 (MEDIUM): Correct or implement `--nomacroexecution` claim

**Location:** `backend/app/services/libreoffice_converter.py` module docstring (lines 24–28)  

**Problem:** The docstring claims macros are disabled via `--nomacroexecution` and `--infilter`, but neither flag is in the actual `cmd` list.

**Option A — Add the flag (implements the claim):**
```python
cmd = [
    binary,
    "--headless",
    "--norestore",
    "--nolockcheck",
    "--nomacroexecution",   # ← add this
    "--convert-to", "pdf",
    "--outdir", tmp_dir,
    input_path,
]
```
`--nomacroexecution` is supported in LibreOffice 7.2+ (which is current on Debian bookworm). It prevents all macro execution during the conversion. This is the recommended approach.

**Option B — Correct the docstring (removes the false claim):**  
Replace the security comment with an accurate description of what headless mode actually prevents.

Effort: 5 minutes. Option A is preferred.

---

### Fix 4 (MEDIUM): Add Calibri-compatible fonts to Dockerfile

**Location:** `backend/Dockerfile` line 28–30  

**Problem:** Calibri (default Word font) is absent. Most modern DOCX files use Calibri, causing font substitution and text reflow in the LibreOffice output.

**Fix:** Add `fonts-crosextra-carlito fonts-crosextra-caladea` to the apt-get install line:
```dockerfile
fonts-liberation \
fonts-dejavu-core \
fonts-crosextra-carlito \    # ← metric-compatible Calibri substitute
fonts-crosextra-caladea \    # ← metric-compatible Cambria substitute
```

These fonts (`carlito` for Calibri, `caladea` for Cambria) are metric-compatible — same character widths — meaning text reflow will not occur when substituting. They are available in Debian bookworm's official package repositories.

Effort: 2 minutes. Risk: None (additive package install).

---

## 9. Nice-to-Have Improvements

These are not defects and do not block deployment.

### 9.1 Separate Dockerfile for Worker

The API container carries LibreOffice (~700 MB) without needing it. A `Dockerfile.worker` for the worker service would reduce the API image from ~1.6 GB to ~700 MB.

### 9.2 Log Total Processing Time

Currently, the conversion step logs start/end separately from rasterization. A structured log line at the end of `process_docx_as_pdf()` reporting total elapsed time would be useful for latency monitoring:

```python
logger.info(
    "docx_pipeline_complete doc=%s conversion_ms=%.0f raster_pages=%d",
    document_id, conversion_ms, result["page_count"]
)
```

### 9.3 `suffix` Parameter Runtime Validation

Add a lightweight assertion in `convert_to_pdf()`:
```python
if not suffix.startswith(".") or "/" in suffix or "\\" in suffix:
    raise ValueError(f"Unsafe suffix: {suffix!r}")
```
This hardens the API for future callers (e.g., PPTX support in Phase D3).

### 9.4 `worker_concurrency: 1` Documentation

Add an explicit comment to `docker-compose.yml` and `config.py` noting that DOCX-heavy deployments should use `WORKER_CONCURRENCY=1` to avoid OOM conditions.

### 9.5 TOC Page Resolution via PDF Bookmarks (Follow-on to Fix 1)

After Fix 1 removes `chunk` from DOCX TOC entries, a follow-on improvement (Option B above) would use `pypdf` to extract any bookmarks LibreOffice preserved in the converted PDF. This provides actual page numbers for TOC navigation when available.

---

## 10. Production-Readiness Verdict

### Summary of Findings

| Category | Defects Found | Severity |
|----------|--------------|---------|
| Architecture | Stale comments only | LOW |
| Security | Missing flag (`--nomacroexecution`), unvalidated `suffix` | MEDIUM / LOW |
| Performance | `asyncio.TimeoutError` gap, font substitution causing reflow | MEDIUM |
| TOC | Navigation fields incompatible with image mode | **HIGH** |
| Deployment | Missing Calibri-compatible fonts | MEDIUM |

### Verdict

**Phase D2 is NOT production-ready in its current state.**

The blocking issue is **Fix 1 (TOC navigation field mismatch)**. DOCX TOC entries stored in the sidecar contain `chunk` navigation data from the former text-mode implementation. After D2, DOCX is image-mode. The frontend TOC sidebar will display headings but users will be unable to navigate to them in the page viewer. This is a visible, user-facing functional defect.

The secondary issues (Fixes 2, 3, 4) are all low-effort (2–5 minutes each) and should be applied in the same commit.

**After applying all four required fixes**, Phase D2 will be production-ready with the following known limitations:

1. Font rendering may differ slightly from Word for documents using fonts not covered by the installed font packages (edge case beyond standard Calibri coverage)
2. DOCX TOC will show headings without page navigation (until the Option B follow-on is implemented)
3. Legacy DOCX documents processed before D2 (stored as text) will display as broken image documents until re-uploaded

### Required Actions Before Merging

- [ ] Fix 1: Remove `chunk` from DOCX heading TOC sidecar entries (or implement page-number resolution)
- [ ] Fix 2: Add `asyncio.TimeoutError` to the except clause in `docx_pdf.py`
- [ ] Fix 3: Add `--nomacroexecution` flag to LibreOffice subprocess command
- [ ] Fix 4: Add `fonts-crosextra-carlito` and `fonts-crosextra-caladea` to Dockerfile

Estimated effort for all four fixes combined: **30 minutes**.

---

*This report covers only Phase D2 code on branch `phase-d2-docx-pipeline`. PPTX, billing, and domain changes are explicitly out of scope per the validation brief.*
