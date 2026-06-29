> **HISTORICAL ARCHIVE** — Reflects repository state before Sprint 4.2D extraction (2026-06-22). Not current. Do not use for active decision-making.

# TraceView Phase D1.5 — Architecture Decision Report
## DOCX / PPTX Processing Strategy

**Prepared:** 2026-06-04  
**Status:** Decision document — no implementation  
**Precondition:** Phase D1 complete, 1119/1119 tests passing  

---

## Table of Contents

1. [Current Architecture Assessment](#1-current-architecture-assessment)
2. [Phase D1 Architecture Assessment](#2-phase-d1-architecture-assessment)
3. [DOCX Strategy Recommendation](#3-docx-strategy-recommendation)
4. [PPTX Strategy Recommendation](#4-pptx-strategy-recommendation)
5. [LibreOffice Assessment](#5-libreoffice-assessment)
6. [Cost Analysis](#6-cost-analysis)
7. [Latency Analysis](#7-latency-analysis)
8. [Security Analysis](#8-security-analysis)
9. [Competitor Analysis](#9-competitor-analysis)
10. [Recommended Future Architecture](#10-recommended-future-architecture)
11. [Recommended Implementation Order](#11-recommended-implementation-order)
12. [Final Recommendation](#12-final-recommendation)

---

## 1. Current Architecture Assessment

### 1.1 Pipeline Overview

The system operates three distinct processing pipelines, all dispatched via the Phase D1 adapter registry.

#### PDF Pipeline (image-based)
```
Upload → storage (originals/{id}.pdf)
Worker → download PDF bytes
       → RasterizerService (pdf2image, 150 DPI, WebP format, quality 85)
       → WatermarkService.apply_forensic_stamp() per page (0.03 opacity, EXIF embed)
       → upload pages/{id}/{page:04d}.webp + thumbs/{id}/{page:04d}.webp
       → DocumentPage records in DB
       → status = ready
Viewer → page request → fetch WebP from L1/L2/storage
                      → apply_visible_watermark() per session (0.22 opacity, session angle)
                      → serve watermarked WebP inline
```

**DPI:** 150  
**Format:** WebP, quality 85  
**Forensic stamp:** SHA-256 fingerprint in near-invisible pixel layer + EXIF ImageDescription  
**Visible watermark:** Per-session, per-request, burned into image in executor thread  
**Max pages:** 500 (configurable)  
**Rasterizer timeout:** 300 seconds  
**Worker RAM profile:** 800 MB – 4 GB depending on page count (documented in config.py)

#### Text Pipeline (text-based)
```
Upload → storage (originals/{id}.txt|md|log)
Worker → download bytes
       → decode_text_safe() (UTF-8 → latin-1 fallback, CRLF normalisation)
       → count_chunks() (100 lines per chunk)
       → status = ready (no DocumentPage records created)
Viewer → text request → fetch storage_key bytes
                      → chunk_text() → serve chunk N
                      → watermark_text as JSON field (not burned into image)
```

**No DocumentPage records.** Text is served raw from storage, chunked on demand. The "watermark" is a plain string in the JSON response, not a visual element burned into rendered content.

#### Word Pipeline (currently text-based)
```
DOCX:
  Worker → download DOCX bytes
         → extract_docx_toc() via python-docx (heading styles → JSON sidecar)
         → docx_to_markdown() via python-docx (headings → ATX #, body verbatim)
         → overwrite storage_key with markdown text
         → count_chunks()
         → status = ready
  Viewer → identical to text pipeline (markdown text chunks)

DOC:
  Worker → download .doc bytes
         → doc_to_text() via antiword subprocess (plain text)
         → overwrite storage_key with plain text
         → count_chunks()
         → status = ready
  Viewer → identical to text pipeline (plain text chunks)
```

**Critical observation:** Tables are lost. Images are replaced with no content. Fonts, columns, callout boxes, diagrams, colour coding — all discarded. The stored artefact is a structural skeleton at best.

### 1.2 Caching Architecture

| Layer | Scope | TTL | Max entries | Purpose |
|-------|-------|-----|-------------|---------|
| L1 page bytes | Per process | LRU eviction | 600 entries | Pre-watermark WebP bytes |
| L2 page bytes | Redis, shared | 3600 s (1 hr) | Unbounded | Pre-watermark WebP bytes |
| L1 thumb bytes | Per process | LRU eviction | 2000 entries | Thumbnail WebP bytes |
| L2 thumb bytes | Redis, shared | 3600 s | Unbounded | Thumbnail WebP bytes |
| link_cache | Per process | 10 s TTL | 2000 entries | Link metadata (revocation-sensitive) |
| doc_cache | Per process | 60 s TTL | 1000 entries | Document status + storage_key |
| page_cache | Per process | 300 s TTL | 10000 entries | DocumentPage storage_key + dimensions |
| text_content_cache | Per process | 300 s TTL | 100 entries, ≤5 MB | Decoded text strings |
| chunk_array_cache | Per process | 300 s TTL | 100 entries | Pre-split chunk lists |
| toc_cache | Per process | 300 s TTL | 500 entries | TOC trees |
| TOC sidecar | R2/S3 | Permanent | 1 per doc | toc/{id}.json |

**Key insight:** The L1/L2 page byte cache and the DocumentPage record system are designed exclusively around the image pipeline. Text documents bypass both entirely — they have no DocumentPage records, no cached byte entries, and their watermark is a JSON string rather than a burned image layer.

### 1.3 Storage Architecture

```
originals/{doc_id}.{ext}          ← original upload (immutable, then overwritten for word docs)
pages/{doc_id}/{page:04d}.webp    ← forensic-stamped full-res page images (PDF only)
thumbs/{doc_id}/{page:04d}.webp   ← 200px-wide thumbnails (PDF only)
toc/{doc_id}.json                 ← TOC sidecar (PDF bookmarks, DOCX heading styles)
```

DOCX/DOC overwrite their own `originals/` key with the converted text. The original binary is not retained after processing. This is a one-way destructive transform.

### 1.4 Analytics Architecture

Events logged: `opened`, `page_viewed`, `download_attempt`, `print_attempt`, `copy_attempt`, `right_click_attempt`, `completed`, `printed`. The `page_number` field in `AccessEvent` is used for both page numbers (PDF) and chunk numbers (text). This dual-use is transparent to analytics queries today, but a PPTX slide number vs a text chunk number mean different things semantically.

### 1.5 Identified Weaknesses in Current DOCX/DOC Implementation

1. **Fidelity loss is severe.** Tables, images, diagrams, callouts, colour coding, multi-column layouts — all dropped. A training manual with an embedded architecture diagram becomes a sequence of headings and paragraphs.

2. **Watermark security is weaker.** Text viewers apply watermark as a CSS overlay or JSON string. This is cosmetic, not forensic. Browser DevTools can remove a CSS overlay in two clicks. Image watermarks cannot be removed without visible artefacts.

3. **Text selectability.** Text document content is fully selectable, searchable, and copyable at the browser level regardless of the `can_copy` permission flag. The permission flag is enforced only by frontend event handlers (`copy_attempt` logging), not by the rendering medium.

4. **No thumbnail strip.** The sidebar thumbnail navigation works only for PDF. Text documents show no visual navigation aid.

5. **Inconsistent viewer experience.** PDF shows a visually accurate page-by-page view. DOCX shows a text dump. A user sharing both PDFs and DOCX documents through TraceView gets an inconsistent experience.

---

## 2. Phase D1 Architecture Assessment

### 2.1 What Phase D1 Achieved

Phase D1 introduced the `DocumentAdapter` registry at `app/services/adapters/`. The six adapters (PDF, TXT, MD, LOG, DOCX, DOC) replaced eight scattered if/elif chains across four files:

| File | Chains removed | Replaced with |
|------|---------------|---------------|
| `workers/tasks.py` | 4-branch pipeline dispatch | `get_adapter(file_type).process()` |
| `routers/documents.py` | ALLOWED_CONTENT_TYPES set + 3-branch size check + _ct_map | Registry-derived MIME types + `adapter.validate_bytes()` |
| `routers/viewer.py` | 2 format-list checks + TOC if/elif | `adapter.viewer_mode` + `supports_toc_sidecar()` |
| `services/toc/extractor.py` | pdf vs text branch | `adapter.extract_toc()` |

### 2.2 Phase D1 Value for Phase D2

**Adding PPTX requires zero changes to dispatch locations.** A `PPTXAdapter` is registered in `registry.py`, implements the `DocumentAdapter` interface, and the pipeline, viewer, TOC, and upload logic automatically handles it. This is exactly the value of Phase D1.

**Changing DOCX from text-based to image-based** requires only modifying `DOCXAdapter.process()` and `DOCXAdapter.viewer_mode`. No dispatch chain changes. No if/elif updates in four files. The impact is localised.

### 2.3 Key Adapter Properties Relevant to D2

| Adapter | `viewer_mode` | `supports_toc_sidecar()` | `toc_fallback_to_text()` | `supports_thumbnails()` |
|---------|--------------|--------------------------|--------------------------|------------------------|
| PDF | `"image"` | True | False | True |
| TXT | `"text"` | False | False | False |
| MD | `"text"` | False | False | False |
| LOG | `"text"` | False | False | False |
| DOCX | `"text"` | True | True | False |
| DOC | `"text"` | True | True | False |

If DOCX transitions to image-based: `viewer_mode → "image"`, `supports_thumbnails() → True`, `toc_fallback_to_text() → False`. The entire viewer routing updates automatically.

---

## 3. DOCX Strategy Recommendation

### 3.1 Option Analysis

#### Option A — Keep text-based (current)
DOCX continues to be converted to markdown text by python-docx and served through the text viewer.

**Pros:**
- Zero new dependencies
- Zero infrastructure changes
- Fast processing (2–5 seconds per document)
- Low storage cost (text files, no page images)
- Works in the current Railway deployment

**Cons:**
- Severe fidelity loss (tables, images, columns, callouts all dropped)
- Weaker security model (text selectable, CSS watermark removable)
- No thumbnail strip navigation
- python-docx markdown conversion is approximate, not layout-faithful
- Inconsistent experience vs PDF documents
- Not competitive with DocSend/Digify

#### Option B — Convert to PDF via LibreOffice, use image pipeline
DOCX is converted to PDF via LibreOffice headless during worker processing, then passed through the existing RasterizerService → WatermarkService pipeline.

**Pros:**
- Full layout fidelity (tables, images, fonts, columns preserved)
- Identical security model to PDF (image-based, forensic watermark, burned visible watermark)
- Thumbnail navigation strip works automatically
- Consistent viewer experience across PDF and DOCX
- Industry standard approach (DocSend, Digify do this)
- Watermark cannot be removed via browser DevTools

**Cons:**
- LibreOffice adds ~1.2–1.5 GB to Docker image
- Worker RAM increases: 400–800 MB peak for LibreOffice conversion
- Processing time increases: +3–15 seconds for small DOCX, +15–40s for large
- Operational complexity: LibreOffice subprocess management
- Historical security vulnerabilities in LibreOffice parser
- Original DOCX not retained after conversion (same as current behaviour — already destructive)

#### Option C — Support both modes (text + image)
Two processing paths: high-fidelity image conversion (LibreOffice) and fast text extraction (python-docx). User selects at upload time or configured per-plan.

**Pros:**
- Flexibility
- Text mode available as fallback when LibreOffice fails

**Cons:**
- Doubles the adapter complexity
- Two storage layouts per DOCX document
- Two viewer modes for the same format — confusing UX
- Two code paths to maintain
- No competitor does this — unnecessary complexity

### 3.2 DOCX Recommendation

**Option B: Convert DOCX to PDF via LibreOffice.**

The fidelity argument is decisive. DOCX documents shared through TraceView are almost certainly contract documents, training materials, technical specifications, or reports — all of which rely heavily on tables, images, and structured layout. The current text extraction drops all of this.

The security argument is equally strong. A text viewer cannot provide the same level of copy protection as an image viewer. The platform's core proposition is secure, traceable document sharing. Text viewers undermine that proposition for DOCX.

LibreOffice adds infrastructure cost but this cost is justified. The alternative is offering a DOCX viewer that is demonstrably inferior to simply emailing a file.

---

## 4. PPTX Strategy Recommendation

### 4.1 Nature of PPTX

PowerPoint presentations are inherently visual documents. A "text mode" for PPTX is not a degraded experience — it is a fundamentally broken one. Slide content is meaningless without its visual context: slide layout, imagery, animations (where relevant), speaker notes, chart data rendered as graphics, diagrams.

There is no useful text representation of a deck. Bullet points extracted from slides without their visual context convey approximately zero of the intended meaning for most presentation formats.

### 4.2 Option Analysis

#### Option A — Text extraction
PPTX parsed with python-pptx, slide text concatenated, served as text chunks.

**Assessment:** Not viable. A PPTX served as a text dump is essentially unusable for any real-world deck. Speaker notes mixed with slide content, no visual structure, no images. This would be a reputational liability.

#### Option B — Convert to PDF via LibreOffice
PPTX → LibreOffice headless → PDF → pdf2image → WebP pages → existing image pipeline.

**Assessment:** This is the only viable strategy. LibreOffice handles PPTX to PDF with high fidelity: fonts embedded, images preserved, layout accurate. The resulting PDF is rasterized through the exact same pipeline as native PDFs.

#### Option C — Native slide renderer (browser-side)
Serve the raw PPTX to the browser and render it using a JavaScript PPTX renderer (e.g. PptxGenJS, officegen, or similar).

**Assessment:** Not viable for a secure viewing platform. Serving the raw PPTX file to the browser defeats the entire security model. The file is downloadable by definition. Browser-side rendering also has poor fidelity for complex slides.

### 4.3 PPTX Recommendation

**Option B: Convert PPTX to PDF via LibreOffice. Mandatory.**

PPTX support cannot exist without LibreOffice (or a paid cloud conversion API). LibreOffice is the correct choice. Since LibreOffice must be added for PPTX, there is no marginal cost to also using it for DOCX.

---

## 5. LibreOffice Assessment

### 5.1 Component Overview

LibreOffice headless is the standard open-source office suite operated without a display server. Conversion is invoked via:
```
libreoffice --headless --convert-to pdf input.docx --outdir /tmp/
```

Or via the `python-pptx`/`unoconv` Python wrappers that abstract the subprocess.

An alternative is `unoserver` — a persistent LibreOffice server process that avoids per-conversion startup cost by keeping LibreOffice alive and accepting conversion requests over a network socket. This is strongly preferred in production.

### 5.2 Startup Cost

| Mode | Cold startup time | Notes |
|------|------------------|-------|
| Per-process (naive) | 5–15 seconds | LibreOffice process starts, loads UI subsystem, converts, exits |
| unoserver (daemon) | 3–8 seconds once, then 0 | Persistent daemon; conversions are socket calls (~50–200ms overhead) |
| Pre-warmed in worker | ~0 per conversion | unoserver started at container init, stays alive |

**Recommendation:** Use `unoserver` (persistent daemon per worker process). This eliminates startup cost from every document conversion. The daemon uses ~150–250 MB RAM at idle.

### 5.3 Conversion Latency Estimates

These estimates assume unoserver mode (no per-call startup). They include the LibreOffice conversion step only, not subsequent rasterization.

#### DOCX Conversion (LibreOffice only)

| Document size | Pages | Raw file | Conversion time | Notes |
|--------------|-------|----------|-----------------|-------|
| Small | 10 | ~50 KB | 1–3 seconds | Single column, minimal images |
| Medium | 50 | ~500 KB | 3–8 seconds | Tables, embedded images |
| Large | 200 | ~5 MB | 12–30 seconds | Complex tables, many images, custom fonts |

#### PPTX Conversion (LibreOffice only)

| Document size | Slides | Raw file | Conversion time | Notes |
|--------------|--------|----------|-----------------|-------|
| Small | 10 | ~1 MB | 2–5 seconds | Text + minimal graphics |
| Medium | 50 | ~10 MB | 8–20 seconds | Mixed graphics, embedded images |
| Large | 200 | ~50 MB | 35–80 seconds | Image-heavy, videos (dropped), charts |

#### Total Worker Time (conversion + rasterization at 150 DPI)

| Document | Conversion | Rasterization | Total | Within 300s timeout? |
|----------|-----------|--------------|-------|---------------------|
| Small DOCX (10p) | 1–3s | 2–5s | 3–8s | Yes |
| Medium DOCX (50p) | 3–8s | 10–25s | 13–33s | Yes |
| Large DOCX (200p) | 12–30s | 40–100s | 52–130s | Yes |
| Small PPTX (10s) | 2–5s | 2–5s | 4–10s | Yes |
| Medium PPTX (50s) | 8–20s | 10–25s | 18–45s | Yes |
| Large PPTX (200s) | 35–80s | 40–100s | 75–180s | Yes (marginal) |

**Note:** The existing `rasterizer_timeout_sec: 300` accommodates all realistic cases. Very large PPTX (200+ image-heavy slides) approaches the limit and may require a higher timeout setting for this format.

### 5.4 RAM Requirements

| Component | Idle | Peak during conversion |
|-----------|------|----------------------|
| unoserver daemon | 150–250 MB | — |
| LibreOffice conversion (DOCX) | — | +200–400 MB |
| LibreOffice conversion (PPTX) | — | +300–600 MB |
| pdf2image rasterisation (existing) | — | +200–800 MB |
| Combined peak (PPTX conversion) | — | 650–1650 MB |

**Worker container sizing:** The current recommendation in `config.py` states "PDF rasterization uses 800MB–4GB RAM per worker." The addition of LibreOffice adds at most +600 MB during conversion, with conversion and rasterization running sequentially (not simultaneously). The peak RAM profile increases from ~4 GB to ~4.6 GB in the absolute worst case (200-page image-heavy document).

**Railway implication:** A Railway container at 4 GB RAM (their Pro plan) handles this. The recommended setting of `worker_concurrency: 2` should be reduced to `1` if running on 4 GB or below, to avoid two simultaneous conversions exhausting memory.

### 5.5 Docker Image Impact

| Base image (Python + current deps) | ~900 MB |
|-------------------------------------|---------|
| Adding LibreOffice + fonts | +1.2–1.5 GB |
| **Total image size** | **~2.1–2.4 GB** |

This is comparable to other document processing services. Railway stores and serves images from a registry; larger images increase first-deploy time but not ongoing performance. Image layers are cached after the first pull.

**Optimisation available:** Use a multi-stage Docker build. Install LibreOffice in the worker stage only. The API server image does not need LibreOffice (it never performs conversion) and can remain small (~900 MB). This is the same pattern already used for the frontend build.

```
API service image:  ~900 MB (no LibreOffice)
Worker image:      ~2.4 GB (LibreOffice + all deps)
```

### 5.6 Operational Complexity

| Concern | Severity | Mitigation |
|---------|----------|-----------|
| unoserver crash recovery | Medium | Celery task retry already implemented; restart unoserver via supervisor/entrypoint |
| Font rendering differences | Low | Install liberation-fonts, freefont, msttcorefonts-compatible fonts in container |
| User directory isolation | Medium | Each worker process needs a separate LibreOffice user profile dir (`--env "UserInstallation=file:///tmp/lo_{pid}"`) |
| Memory leak over time | Low | Already have `worker_max_tasks_per_child` config; recycle worker after N tasks |
| Conversion failure modes | Medium | LibreOffice returns non-zero exit codes; wrap in try/except, mark document as error |

### 5.7 Security Implications

LibreOffice has a history of parser vulnerabilities. Mitigations required:

1. **Disable macros unconditionally.**  
   `--headless --norestore --nodefault --nolockcheck --infilter="writer8"`  
   Or via unoserver configuration with macro execution disabled.

2. **No network access in worker container.**  
   LibreOffice should not be able to make outbound connections during conversion. Docker network policy or `--no-network` flag.

3. **Input validation before conversion.**  
   Already done: DOCX validated as ZIP magic, PPTX (same ZIP structure) validated similarly. This prevents non-Office files from entering LibreOffice.

4. **Process sandboxing.**  
   Run LibreOffice as a non-root user (already enforced in the Dockerfile). Apply a seccomp profile restricting syscalls if on a hardened deployment.

5. **Timeout enforcement.**  
   A malformed DOCX/PPTX can hang LibreOffice indefinitely. Enforce a hard timeout on the conversion subprocess (30–60 seconds for the conversion step, separate from the rasterizer timeout).

6. **CVE monitoring.**  
   LibreOffice releases security patches quarterly. Pin the version in the Dockerfile and subscribe to LibreOffice security advisories.

### 5.8 Suitability for Railway Deployment

**Assessment: Viable with configuration.**

Railway supports custom Dockerfiles with no restrictions on installed packages. The ~2.4 GB worker image is within Railway's limits. The memory requirements fit a Pro plan container (2–4 GB RAM). Deploy the API service and worker service as separate Railway services with different resource allocations — the API server needs only ~512 MB while the worker needs 2–4 GB.

The per-task memory pattern (spike then release) is compatible with Railway's resource model; there is no sustained high memory usage between tasks.

---

## 6. Cost Analysis

### 6.1 Storage Cost Per Document

| Format | Storage (text pipeline) | Storage (image pipeline) |
|--------|------------------------|--------------------------|
| 10-page DOCX | ~30 KB (text) | ~3–10 MB (WebP pages + thumbs) |
| 50-page DOCX | ~150 KB (text) | ~15–50 MB |
| 10-slide PPTX | n/a | ~5–20 MB |
| 50-slide PPTX | n/a | ~25–100 MB |

**Image pipeline uses 50–100× more storage per document than text pipeline.**

At Cloudflare R2 pricing (~$0.015/GB/month):
- 1000 DOCX uploads (avg 30 pages): text = ~$0.07/month; image = $2–7/month
- At 10,000 documents: text = $0.70/month; image = $20–70/month

Storage cost is marginal at current scale but grows linearly with document count. At DocSend-scale (millions of documents), storage cost becomes the dominant infrastructure cost and drives compression + tiering strategies.

**For TraceView's current scale (free plan: 10 docs/user), storage cost difference is negligible.** The decision should not be driven by storage cost at this stage.

### 6.2 Compute Cost

| Scenario | Text pipeline | Image pipeline (with LibreOffice) |
|----------|--------------|----------------------------------|
| Processing 100 DOCX/day | ~1 min worker time | ~20–50 min worker time |
| Processing 100 PPTX/day | n/a | ~30–80 min worker time |

The image pipeline requires significantly more CPU and worker time. On Railway's consumption-based pricing, this increases worker compute cost. Offset by the fact that processing is one-time per document (not per-view).

### 6.3 Infrastructure Cost Summary

| Component | Text pipeline add-on | Image pipeline (LibreOffice) |
|-----------|---------------------|------------------------------|
| Docker image size | +0 MB | +1.2–1.5 GB (worker only) |
| Worker RAM | +0 MB | +400–600 MB peak |
| Storage per document | +30–150 KB | +3–100 MB |
| Processing time | +2–5s | +15–130s |
| Monthly Railway cost (current scale) | Negligible | ~$5–15 extra |

**Conclusion:** At current and near-future scale, the cost difference between the two approaches is $5–20/month — not a deciding factor.

---

## 7. Latency Analysis

### 7.1 Processing Latency (Upload → Ready)

| Document | Text pipeline | Image pipeline |
|----------|--------------|----------------|
| Small DOCX (10p) | 2–5 seconds | 3–8 seconds |
| Medium DOCX (50p) | 5–15 seconds | 13–33 seconds |
| Large DOCX (200p) | 15–30 seconds | 52–130 seconds |
| Small PPTX (10s) | Not viable | 4–10 seconds |
| Medium PPTX (50s) | Not viable | 18–45 seconds |

Processing happens asynchronously in the Celery worker. The user gets a 202 response immediately on upload. The document status moves from `uploaded → processing → ready`. The upload response latency is identical for both pipelines.

**The question is how long until the document is shareable.** Text pipeline is faster for DOCX. Image pipeline is slower but produces a higher-quality result.

### 7.2 Viewer Latency (First Load)

| Mode | Cold load | Warm load |
|------|-----------|-----------|
| Image (page 1) | 20–200 ms (L2 Redis) | <1 ms (L1 in-process) |
| Image (page 1, cold storage) | 100–500 ms (R2/S3) | — |
| Text chunk 1 | 50–300 ms (storage) | <1 ms (text_content_cache) |

The viewer latency difference between text and image modes is small and dominated by storage/network rather than processing. Both modes cache aggressively.

### 7.3 Download Latency

For image-pipeline documents, download requires assembling all page WebP images into a PDF via PIL. This is CPU-bound and takes 2–10 seconds for a 50-page document. Text downloads are instant (one storage read). The `max_download_pages_pdf: 100` guard exists precisely to prevent memory exhaustion here.

---

## 8. Security Analysis

### 8.1 Watermark Security Comparison

| Property | Image pipeline | Text pipeline |
|----------|---------------|---------------|
| Watermark type | Visual layer burned into image | CSS overlay (frontend only) |
| Removal difficulty | Requires image editing with visible artefacts | One line of CSS or browser extension |
| Copy protection | Text selection disabled at rendering level | Text selectable by definition |
| Print protection | Watermark visible in print | Depends on CSS print styles |
| Screenshot protection | Watermark persists | Watermark persists (CSS overlay survives screenshots) |
| DevTools bypass | Not possible | Trivial |

**The image pipeline provides substantially stronger copy protection.** For a document security platform, this is a first-order concern.

The current `can_copy` permission in the text viewer is enforced only by a frontend event listener on `copy` events. It logs a `copy_attempt` event but cannot prevent the copy at the OS level. A user can open DevTools, select all text, and copy regardless of the `can_copy` flag.

For TraceView's stated mission (secure, traceable document sharing), the image pipeline is the correct model for all formatted documents.

### 8.2 Forensic Stamp

The forensic stamp (`apply_forensic_stamp`) embeds a SHA-256 fingerprint of the document_id at 3% opacity in the bottom-right corner plus EXIF metadata. This is applied at processing time, not serve time.

This mechanism works only for image-pipeline documents. Text documents have no equivalent forensic stamp. If a user screenshots text content and distributes it, there is no embedded forensic marker.

For DOCX/PPTX containing sensitive content (contracts, designs, roadmaps), the absence of a forensic stamp in the text pipeline is a meaningful security gap.

### 8.3 LibreOffice Attack Surface

LibreOffice processing happens only in the Celery worker, never in the API server. The attack surface is:
- A malicious DOCX/PPTX that exploits a LibreOffice parser vulnerability
- A DOCX/PPTX that contains macros or embedded objects attempting code execution

**Mitigations:**
1. Magic-byte validation before conversion (already implemented for DOCX; extend to PPTX)
2. Macro execution disabled via LibreOffice flags
3. Worker container has no credentials, no DB access beyond what Celery provides
4. Processing timeout (30–60s hard limit)
5. Non-root execution
6. Network isolation (no outbound from worker during conversion)

The risk profile is comparable to running pdf2image on user-supplied PDFs — both involve trusted open-source libraries processing untrusted binary input. The existing pattern of treating `RasterizerError` and `ValueError` as permanent failures (no retry, status = error) applies cleanly to LibreOffice conversion failures.

---

## 9. Competitor Analysis

### 9.1 DocSend (Dropbox)

**DOCX handling:** Converted to PDF internally during upload, then rasterized to images for the secure viewer. The user never sees a text-based viewer for DOCX.  
**PPTX handling:** Converted to PDF, rasterized, served as image slides with slide-by-slide navigation.  
**Layout fidelity:** High. Fonts embedded, tables preserved.  
**Copy protection:** Image-based viewer. Text selection disabled. Right-click disabled.  
**Watermark:** Per-viewer visible watermark burned into images per session.  
**Conclusion:** Identical to TraceView's image pipeline model. DocSend validates this architecture at scale.

### 9.2 Digify

**DOCX handling:** Converted to image-based viewer. Formatting preserved.  
**PPTX handling:** Converted to slide images, slide-by-slide viewer.  
**Copy protection:** Image viewer, no text selection.  
**Watermark:** Dynamic per-viewer watermark. Image-based.  
**Conclusion:** Image pipeline. Same model as DocSend.

### 9.3 FlipLink

**DOCX handling:** Converted to flipbook-style image viewer.  
**PPTX handling:** Converted to flipbook slides.  
**Layout fidelity:** High (flipbook format renders page images).  
**Copy protection:** Image viewer.  
**Conclusion:** Image pipeline.

### 9.4 Box (Box.com Document Preview)

**DOCX handling:** Box uses its own document transformation service (Box Transform / Box View). DOCX is rendered to a PDF or image representation for the viewer.  
**PPTX handling:** Slide-by-slide image rendering.  
**Fidelity:** Generally high, with occasional font substitution issues.  
**Copy protection:** Controlled by permission settings; Box's viewer is browser-based and less strict than DocSend/Digify.  
**Conclusion:** Image-based pipeline, with cloud conversion service rather than self-hosted LibreOffice.

### 9.5 Adobe Document Cloud (Acrobat Web)

**DOCX handling:** Converts to PDF. Adobe's conversion is highest-fidelity available.  
**PPTX handling:** Converts to PDF.  
**Layout fidelity:** Highest in class (Adobe's converter).  
**Copy protection:** PDF-based DRM where enabled.  
**Conclusion:** PDF pipeline. Industry-defining standard.

### 9.6 Summary Table

| Platform | DOCX viewer | PPTX viewer | Text selectable | Image-based |
|----------|-------------|-------------|-----------------|-------------|
| DocSend | Image (converted) | Image (converted) | No | Yes |
| Digify | Image (converted) | Image (converted) | No | Yes |
| FlipLink | Image (converted) | Image (converted) | No | Yes |
| Box | Image (converted) | Image (converted) | Depends | Yes |
| Adobe DC | PDF/Image | PDF/Image | Controlled | Yes |
| TraceView (current) | **Text dump** | Not supported | **Yes** | **No** |
| TraceView (proposed) | Image (converted) | Image (converted) | No | Yes |

**Every major competitor uses image-based viewing for DOCX and PPTX.** TraceView's current text-based DOCX viewer is an outlier that reduces security posture and fidelity relative to the market.

---

## 10. Recommended Future Architecture

### 10.1 Unified Image Pipeline

The recommended target architecture unifies PDF, DOCX, DOC, and PPTX into a single image-based secure viewer:

```
┌─────────────────────────────────────────────────────────────────┐
│                      UPLOAD BOUNDARY                            │
│  PDF → validate %PDF- → storage                                 │
│  DOCX → validate ZIP magic → storage                            │
│  DOC  → validate OLE2 magic → storage                           │
│  PPTX → validate ZIP magic → storage                            │
│  TXT/MD/LOG → validate binary → storage                         │
└─────────────────────────────────────────────────────────────────┘
           │                                │
           ▼ (Celery worker)                ▼ (Celery worker)
┌──────────────────────┐         ┌──────────────────────────────┐
│   IMAGE PIPELINE     │         │     TEXT PIPELINE             │
│                      │         │                               │
│  PDF → RasterizerSvc │         │  TXT/MD/LOG → decode → chunks │
│  DOCX → LibreOffice  │         │                               │
│       → PDF → Raster │         └──────────────────────────────┘
│  DOC  → LibreOffice  │                      │
│       → PDF → Raster │                      ▼
│  PPTX → LibreOffice  │         ┌──────────────────────────────┐
│       → PDF → Raster │         │     TEXT VIEWER              │
│                      │         │  chunk-based, JSON response   │
│  → forensic stamp    │         │  text watermark (JSON field)  │
│  → WebP pages+thumbs │         └──────────────────────────────┘
└──────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────┐
│                     IMAGE VIEWER                              │
│  per-request session watermark (burned into WebP)            │
│  forensic stamp (permanent in stored pages)                  │
│  thumbnail strip navigation                                   │
│  L1 + L2 Redis byte cache                                    │
└──────────────────────────────────────────────────────────────┘
```

**TXT/MD/LOG remain in the text pipeline.** These are genuinely text-native formats where:
- Layout fidelity is not relevant (they have no layout)
- The text viewer is appropriate (they are meant to be read as text)
- LibreOffice would add zero value
- The security concern (text selectability) is acceptable — log files and markdown are not the primary security-sensitive document types on the platform

### 10.2 Adapter Changes Required

| Adapter | Current `viewer_mode` | Target `viewer_mode` | Pipeline change |
|---------|----------------------|---------------------|-----------------|
| PDF | `"image"` | `"image"` | None |
| TXT | `"text"` | `"text"` | None |
| MD | `"text"` | `"text"` | None |
| LOG | `"text"` | `"text"` | None |
| DOCX | `"text"` | `"image"` | Replace python-docx markdown with LibreOffice → PDF → Rasterizer |
| DOC | `"text"` | `"image"` | Replace antiword with LibreOffice → PDF → Rasterizer |
| PPTX (new) | — | `"image"` | LibreOffice → PDF → Rasterizer |

DOC's current antiword pipeline is also recommended for replacement with LibreOffice. antiword produces only approximate plain text (tables lost, formatting lost). LibreOffice handles .doc format well via its legacy binary filter. The replacement is a single adapter change.

### 10.3 TOC Strategy Under Unified Pipeline

With DOCX and PPTX moving to the image pipeline:

| Format | TOC source | Extraction timing |
|--------|-----------|------------------|
| PDF | Bookmarks → sidecar | At processing time |
| DOCX | Heading styles → sidecar (python-docx pre-conversion) | At processing time, before LibreOffice |
| DOC | Not extractable | No TOC (antiword removed) |
| PPTX | Slide titles → sidecar (python-pptx pre-conversion) | At processing time, before LibreOffice |

**DOCX and PPTX can still have high-quality TOC** by extracting it from the source document before LibreOffice conversion. DOCX headings are already extracted via `extract_docx_toc()`. PPTX slide titles can be extracted via python-pptx. The sidecar is stored at `toc/{doc_id}.json` as today. No viewer changes needed.

### 10.4 Migration Path for Existing DOCX/DOC Documents

Documents already processed through the text pipeline are in storage as converted text. After the pipeline change:
- Existing text-mode documents continue to be served through the text viewer (no change to stored data)
- New uploads go through the image pipeline
- Re-processing can be offered as an optional endpoint for owners who want layout-faithful versions of previously-uploaded DOCX files

This avoids any migration burden for existing users while immediately benefiting new uploads.

---

## 11. Recommended Implementation Order

### Phase D2 — LibreOffice Infrastructure (prerequisite)

**Goal:** Add LibreOffice to the worker container. No document format changes yet.

1. Add LibreOffice + `unoserver` to the worker `Dockerfile` stage (separate from the API stage)
2. Write a `LibreOfficeConverter` service class that:
   - Manages unoserver lifecycle (start on worker init, health-check, restart on crash)
   - Exposes `convert_to_pdf(input_bytes, input_format) → bytes` with timeout enforcement
   - Disables macros, restricts network, uses isolated user profile per call
3. Add unit tests for the converter with a mock subprocess
4. Add integration tests with a real DOCX/PPTX file (small fixture files)
5. Verify Docker build on Railway produces a working image
6. **No format dispatch changes in this phase**

### Phase D3 — PPTX Adapter

**Goal:** Add PPTX as a new format using the LibreOffice pipeline.

1. Create `PPTXAdapter` in `app/services/adapters/pptx.py`:
   - `file_type = "pptx"`
   - `viewer_mode = "image"`
   - `validate_bytes()`: ZIP magic check (same as DOCX)
   - `upload_mime_types()`: `application/vnd.openxmlformats-officedocument.presentationml.presentation`
   - `process()`: LibreOfficeConverter → PDF bytes → existing `process_pdf_document()` logic
   - `extract_toc()`: python-pptx slide title extraction → TocEntry list
2. Register PPTXAdapter in `registry.py`
3. Add PPTX to `ALLOWED_CONTENT_TYPES` (automatic via registry)
4. Create `workers/pipeline/pptx.py` pipeline function
5. Add DB migration for the `pptx` file_type enum value
6. Tests: upload, processing dispatch, TOC extraction, viewer integration
7. **No changes to DOCX/DOC behaviour in this phase**

### Phase D4 — DOCX/DOC Migration to Image Pipeline

**Goal:** Migrate DOCX and DOC from text pipeline to image pipeline.

1. Update `DOCXAdapter`:
   - `viewer_mode = "image"` 
   - `process()`: extract TOC sidecar (existing) → LibreOfficeConverter → PDF → existing PDF pipeline
   - `supports_thumbnails()`: True
   - `toc_fallback_to_text()`: False (sidecar only)
2. Update `DOCAdapter`:
   - `viewer_mode = "image"`
   - `process()`: LibreOfficeConverter (DOC filter) → PDF → existing PDF pipeline
3. Create `workers/pipeline/libreoffice.py` shared pipeline
4. Tests: full upload-process-view cycle for DOCX and DOC
5. Verify existing DOCX test documents still pass (regression)
6. Document migration strategy for existing text-mode DOCX documents

### Phase D5 — Cleanup

**Goal:** Remove dead code from the text-based Word pipeline.

1. Remove `docx_to_markdown()` from `docx_extractor.py` (no longer needed)
2. Remove `antiword` from the Dockerfile (if DOC is now LibreOffice-based)
3. Remove `doc_to_text()` from `docx_extractor.py`
4. Remove `toc_fallback_to_text()` logic from viewer (no text-mode sidecar-less DOCX/DOC)
5. Update test fixtures: replace text-mode DOCX/DOC tests with image-mode equivalents
6. Update MEMORY.md documentation

---

## 12. Final Recommendation

### Decision

**Proceed with DOCX/PPTX → PDF conversion via LibreOffice headless.**

### Justification

**1. Security parity.** Every major competitor (DocSend, Digify, FlipLink, Box, Adobe) uses image-based viewing for DOCX and PPTX. The current text-based DOCX viewer provides substantially weaker copy protection: text is selectable, the "watermark" is a CSS overlay removable in DevTools, and no forensic stamp is embedded. For a platform whose core proposition is secure, traceable document sharing, this gap is a product-level deficiency.

**2. Fidelity is not optional for DOCX.** The current `docx_to_markdown()` pipeline produces a structural skeleton that drops tables, images, colour, multi-column layouts, diagrams, and callout boxes. For training materials, contracts, technical specifications, and reports — the primary DOCX use cases — this represents an unacceptable loss of document meaning.

**3. PPTX has no viable text mode.** There is no useful way to represent a PowerPoint deck as text. The only path to PPTX support is LibreOffice conversion. Since LibreOffice must be added for PPTX, the marginal infrastructure cost of also using it for DOCX and DOC is near zero.

**4. The Phase D1 adapter architecture makes this change localised.** Migrating DOCX from text to image requires changes to `DOCXAdapter` only — no dispatch chain updates in four files. Phase D1 was built precisely to enable this kind of format strategy change.

**5. Cost is not a barrier at current scale.** The storage increase (~50–100× per document) and compute increase (~5–30s per document) translate to approximately $5–20/month additional infrastructure cost at TraceView's current user volume. This is justified by the product quality improvement.

**6. Industry validation.** DocSend, the market leader in the secure document sharing space, uses exactly this architecture: all non-PDF documents converted to PDF → rasterized to images → served with per-viewer watermarks. TraceView is building toward DocSend-level security and the architecture should reflect that from the start.

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| LibreOffice parser vulnerability | Medium | Disable macros, network isolation, non-root, seccomp, version pinning |
| Worker OOM on large PPTX | Medium | `worker_concurrency: 1` on 4 GB containers; `max_pages_per_doc: 500` guards rasterizer |
| Processing latency regression for DOCX | Low | Text mode was 2–5s, image mode is 13–33s — async processing, user waits either way |
| Existing text-mode DOCX documents | Low | Continue serving via text pipeline; new uploads via image pipeline |
| Railway image size increase | Low | Worker image grows to ~2.4 GB; API image unchanged; acceptable on Railway Pro |
| Font rendering differences | Low | Install liberation-fonts, freefont in worker container for standard font coverage |

### What is explicitly not recommended

- A hybrid mode (text + image per DOCX document) — adds complexity without meaningful benefit
- Cloud conversion APIs (Aspose, GroupDocs) — introduces external dependency, per-conversion cost, data privacy concerns for confidential documents
- Browser-side PPTX rendering — defeats the security model entirely
- Keeping DOC on antiword — antiword is unmaintained, produces lower-quality output than LibreOffice, and requires a separate system dependency

---

*This report represents a non-binding architectural analysis. Implementation requires engineering validation, particularly around LibreOffice Docker integration, unoserver lifecycle management, and Railway resource sizing before committing to the approach.*
