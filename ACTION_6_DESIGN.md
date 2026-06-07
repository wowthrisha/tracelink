# Action 6: Streaming PDF Downloads

## Problem

The current download endpoint (`GET /api/viewer/download/{token}`) loads ALL page images from R2
into memory simultaneously, composites them into a single PDF using `pypdf`, and only then streams
the response. For a 100-page document at 85 quality WebP ≈ 200KB/page, this buffers ~20MB of
images plus the assembled PDF before the first byte is sent to the client.

Problems:
1. **Memory spike**: 100-page doc ≈ 40–80MB resident for the duration of the request. Under
   concurrent downloads this can OOM the API container (512MB–1GB typical on Railway/Render).
2. **Time-to-first-byte**: Client waits for full assembly before receiving anything.
3. **Current page limit**: `max_download_pages_pdf = 100`. Raising it safely requires streaming.
4. **No progress feedback**: Client connection appears stalled during assembly.

## Solution

Use `pypdf.PdfWriter` as a streaming generator:
- Fetch page images from R2 one at a time (or in small batches of N=5).
- For each page: create a single-page PDF in memory, write it to the response body immediately.
- Use FastAPI `StreamingResponse` with `media_type="application/pdf"`.
- Add `Content-Disposition: attachment; filename="{doc_name}.pdf"` header.
- Apply a lightweight visible watermark to each page before embedding.
- Raise `max_download_pages_pdf` config default from 100 → 500 (safe now that pages are not
  all held in memory simultaneously).

## Architecture

```
Client                     API                    R2
  |-- GET /download/{tok} -->|
  |                          |-- HEAD page/1 ------>|
  |                          |<-- 200 key exists ---|
  |                          |-- GET page/1 -------->|
  |                          |<-- 200 bytes (200KB) -|
  |<-- 200 (first chunk) ----|  (PDF page 1 written)
  |                          |-- GET page/2 -------->|
  |                          |<-- 200 bytes ---------|
  |<-- chunk (page 2) -------|
  ...
```

## Changes

### `backend/app/routers/viewer.py`
- Replace `_build_download_pdf()` helper that returns `bytes` with a generator function
  `_stream_download_pages()` that yields bytes chunks.
- `StreamingResponse` wraps the generator.
- Per-page fetch uses existing `fetch_page_bytes()` helper.
- Watermark applied to each page using `watermark_svc.apply_visible_watermark()` (already
  offloaded to executor in Phase 1 — keep same pattern).
- Add `Content-Disposition` header with sanitised filename.

### `backend/app/config.py`
- `max_download_pages_pdf: int = 500` (was 100)

### `backend/app/services/pdf_assembler.py` (new)
- `create_single_page_pdf(image_bytes: bytes) -> bytes` — wraps one image in a PDF page.
- `merge_pdf_pages(page_pdfs: list[bytes]) -> bytes` — concatenates page PDFs.
- Both are synchronous (CPU-bound) and called from executor.
- Kept separate from watermark service (single responsibility).

### Alembic migration
- None required (no schema change).

## Security
- Session and link validation unchanged — download endpoint still requires valid session.
- Watermark still applied per-page to downloaded bytes.
- `Content-Disposition: attachment` prevents inline rendering in browser.
- No storage keys or paths exposed in response headers.

## Performance Budget
- Peak RSS during 100-page download: ~5MB (1 page in flight) vs ~80MB (all-at-once).
- Time to first byte: ~300ms (first page fetch) vs ~30s (all-100-pages assembled).
- Throughput: unchanged (network-bound).

## Test Plan
- Unit: `test_pdf_assembler.py` — single-page creation, merge, output is valid PDF.
- Integration: `test_enterprise_scalability.py` — download returns 200 with `application/pdf`,
  `Content-Disposition: attachment`, first chunk arrives before last page is fetched,
  memory usage during download stays bounded (mock-based page count verification).
- Regression: existing download tests pass.

## Rollback
- Revert `_stream_download_pages` → original `_build_download_pdf` helper.
- Revert `max_download_pages_pdf` default to 100.
