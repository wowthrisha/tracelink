# Action 10: PPTX Support
# Action 11: XLSX Support

## Problem

SecureDoc accepts PDF, DOCX, DOC, TXT, MD, LOG. The enterprise document sharing
market also expects PowerPoint (PPTX) and Excel (XLSX) — common formats in sales,
finance, and operations. Without them, every deck shared with a prospect must be
converted to PDF manually by the sender.

Competitor analysis:
- DocSend: PPTX/XLSX via native upload
- Box Enterprise: PPTX/XLSX via Box View
- Dropbox Enterprise: PPTX/XLSX supported natively
- Adobe Document Cloud: PPTX/XLSX via Acrobat
- Google Drive Enterprise: PPTX/XLSX via Google Slides/Sheets

## Solution

LibreOffice headless is already deployed (for DOCX). It supports PPTX and XLSX
conversion to PDF with high fidelity. The pipeline is identical to DOCX:

1. Download original PPTX/XLSX from storage.
2. Convert → PDF via `LibreOfficeConverter.convert_to_pdf(bytes, ".pptx")`.
3. Pass PDF bytes to `process_pdf_document()` (existing pipeline).
4. Store page WebP images, apply forensic stamp, write thumbnails.

## Architecture

### New files
- `backend/app/services/adapters/presentation.py` — `PPTXAdapter`
- `backend/app/services/adapters/spreadsheet.py` — `XLSXAdapter`
- `backend/app/workers/pipeline/pptx_pdf.py` — PPTX processing (wraps docx_pdf.py pattern)
- `backend/app/workers/pipeline/xlsx_pdf.py` — XLSX processing (same pattern)

### Modified files
- `backend/app/services/text_processor.py` — add PPTX/XLSX to `detect_file_type()`
- `backend/app/services/adapters/registry.py` — register PPTX/XLSX adapters

### No migration needed
- `file_type` column is VARCHAR(10) with no CHECK constraint — supports any value ≤ 10 chars.
- `pptx` (4 chars) and `xlsx` (4 chars) fit. No Alembic migration required.

## Security
- PPTX/XLSX are ZIP-based formats — same `_is_zip_magic()` check as DOCX.
- LibreOffice subprocess already sandboxed (no network access, /tmp working dir).
- Conversion failures raise ValueError → permanent failure, no retry.

## Test Plan
- Unit: `detect_file_type` returns `pptx`/`xlsx` for .pptx/.xlsx files.
- Integration: upload + process → status=ready, page_count > 0.
- Adapter: `PPTXAdapter.file_type == "pptx"`, `XLSXAdapter.file_type == "xlsx"`.
- Viewer: page endpoint returns image bytes for PPTX/XLSX document.
