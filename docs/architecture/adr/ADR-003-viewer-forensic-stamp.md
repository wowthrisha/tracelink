# ADR-003: Per-Viewer Forensic Stamp at Serve Time

**Status:** Accepted
**Date:** 2026-06-07

## Context

The existing forensic stamp identified the document but not the viewer. An insider with storage credentials could download pages with no viewer identity evidence.

## Decision

Add `apply_viewer_forensic_stamp(image_bytes, session_id, page_number)` to `WatermarkService`. Applied after the visible watermark in the same thread pool call.

- Stamp format: `VS:{sha256(session_id)[:8]}:{page:04d}` at 1.5% opacity
- Location: lower-left corner (document stamp is lower-right)
- Session ID is hashed before embedding — proves identity to someone with DB access, not to a random observer

## Consequences

- Viewer identity burned into every served byte without increasing storage costs
- Two complementary stamps: document identity (lower-right) + viewer identity (lower-left)
- ~2ms additional PIL pass per page (marginal against existing 20–80ms watermark time)
