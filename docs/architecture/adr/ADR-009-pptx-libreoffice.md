# ADR-009: PPTX via LibreOffice (same as DOCX pipeline)

**Status:** Accepted
**Date:** 2026-06-07

## Context

Two options for PPTX rendering: LibreOffice headless conversion to PDF, or python-pptx with a custom renderer. python-pptx cannot render slides with full fidelity (custom fonts, SmartArt, embedded charts).

## Decision

Use LibreOffice headless `--convert-to pdf` for PPTX, identical to the DOCX pipeline. The existing `LibreOfficeConverter.convert_to_pdf(bytes, suffix=".pptx")` already handles this — only file detection and adapter registration need to be added.

## Consequences

- Reuses the proven DOCX → PDF pipeline; PPTX support is approximately one day of work
- LibreOffice PPTX rendering quality varies with custom fonts and transitions — enterprise customers should validate their specific templates
