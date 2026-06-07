# Action 3 Design: Viewer Identity Forensic Stamp

**Status:** APPROVED  
**Date:** 2026-06-07  
**Risk Level:** Low (additive to existing watermark pipeline)

---

## Current Architecture

Two watermarks exist:
1. **Forensic stamp** (`apply_forensic_stamp`): Applied during Celery processing. Stored in R2. Identifies document + page via SHA-256 prefix. Does NOT identify viewer.
2. **Visible watermark** (`apply_visible_watermark`): Applied at serve time. Contains viewer email + date + session prefix. Visible to naked eye.

**Gap:** If an insider downloads raw R2 page bytes (e.g., by obtaining storage credentials), they get pages with the forensic document stamp but WITHOUT the visible watermark. The downloaded pages prove they came from "document X" but NOT who viewed them.

---

## Threat Model

1. **Insider threat:** Employee with R2 credentials downloads pages, removes visible watermark layer, leaks document
2. **External attacker with stolen credentials:** Same as above
3. **API bypass:** Attacker finds a way to get raw storage bytes without going through the API

---

## Alternative Designs

**Option A: Per-session storage variants**  
Store separate R2 objects per viewer session: `pages/{doc}/{page}/{session[:8]}.webp`  
- Pro: Stored stamp survives all further download paths  
- Con: Storage multiplies by number of unique viewers; expensive at scale  
- Con: Requires caching/cleanup logic

**Option B: Server-side stamp at serve time (chosen)**  
Apply a second near-invisible stamp AFTER the visible watermark, at serve time.  
- Pro: No storage increase  
- Pro: Reuses existing PIL pipeline  
- Pro: Stamp encodes session_id hash — recoverable to session by DB lookup  
- Con: Not in R2 bytes; only in API-served bytes  
- Mitigated: Forensic stamp in R2 identifies document; viewer stamp identifies session for API-served traffic

**Option C: EXIF-only viewer identity**  
Embed session hash in EXIF at serve time.  
- Con: EXIF is trivially stripped (file → save without EXIF)  
- Rejected: Too easy to bypass

---

## Chosen Design

**Option B: Serve-time viewer stamp.**

New method `apply_viewer_forensic_stamp(image_bytes, session_id, page_number)`:
- Stamp text: `VS:{sha256(session_id)[:8]}:{page_number:04d}`  
  - `VS:` prefix distinguishes from document stamp `SD:`
  - 8-char SHA-256 prefix of session_id — reveals viewer identity to anyone with DB access (session_id → viewer_email_masked), but not to random observers
- Opacity: 1.5% (half of document stamp's 3%, barely detectable)
- Position: Lower-LEFT corner (document stamp is lower-right — different corners enable independent recovery)
- Applied AFTER visible watermark in the same executor call (single PIL round-trip)

---

## Migration Plan

1. Add `apply_viewer_forensic_stamp()` to `watermark.py`
2. Chain it in `viewer.py:get_page()` after visible watermark in same executor lambda
3. Write tests

No database migration. No storage change.

---

## Rollback Plan

Remove the `apply_viewer_forensic_stamp()` call from `viewer.py`. No data loss.

---

## Performance Impact

One additional PIL operation per page serve. The stamp is a tiny corner rectangle — expected time: ~2ms per 1080p image. This is within the existing watermark time (20-80ms). The entire chain runs in a thread pool executor, so it does not block the async event loop.

---

## Security Impact

**Adds:** Viewer identity tracing for API-served page bytes  
**Does not add:** Viewer identity for direct R2 downloads (separate problem — Phase B storage variant addresses this)  
**Preserves:** All existing document forensic stamp behavior  
**Threat addressed:** Insider API content exfiltration

---

## Test Plan

1. `apply_viewer_forensic_stamp()` returns bytes with different pixel values in lower-left corner
2. Stamp text format: `VS:{8 hex chars}:{4 digit page}`
3. Stamp uses 1.5% opacity (barely visible but detectable)
4. Stamp position is lower-LEFT corner (not lower-right, which is document stamp)
5. Different session_ids produce different stamp texts
6. Same session_id always produces same stamp text (deterministic)
7. Chained with visible watermark — combined result contains BOTH marks
8. get_page() response contains viewer forensic stamp (pixel comparison test)
9. Stamp does NOT contain raw session_id (only SHA-256 prefix)
