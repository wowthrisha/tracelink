# ADR-007: Streaming Download via pypdf PdfWriter

**Status:** Accepted
**Date:** 2026-06-07

## Context

The original download assembled all pages in a BytesIO buffer before streaming — ~10 MB RAM per 100-page download. At 50 concurrent downloads, this consumed ~500 MB, limiting `max_download_pages_pdf`.

## Decision

Use `pypdf.PdfWriter` incremental writes via an async generator:

1. Fetch page bytes from cache/storage
2. Append to `PdfWriter`
3. Yield serialized chunk when buffer reaches 1 MB

Requires `pypdf >= 5.0` (already in requirements.txt).

## Consequences

- Peak RAM per download reduced to O(1 page) + ~2 MB pypdf overhead
- First-byte latency reduced (client starts receiving before all pages are fetched)
- Tied to pypdf 5.0 streaming API — behavior tested against that specific version
