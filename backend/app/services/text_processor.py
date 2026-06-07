"""
Text document processing utilities — Phase 5+ (detection, chunking, TOC).

Handles file-type detection, safe UTF-8 decoding, binary rejection, and
line-based chunking.

Supported types
───────────────
  pdf  — rasterizer pipeline
  txt  — plain text
  md   — Markdown
  log  — log files
  docx — Word XML (processed by toc/docx_extractor, stored as markdown)
  doc  — Legacy Word (processed by toc/docx_extractor via antiword, stored as text)

XSS contract: this module never generates HTML.
"""

import re

# Plain-text extensions (text viewer handles these directly)
SUPPORTED_TEXT_EXTENSIONS: frozenset[str] = frozenset({"txt", "md", "log"})

# Word document extensions (converted to text by worker, viewed as text)
SUPPORTED_WORD_EXTENSIONS: frozenset[str] = frozenset({"docx", "doc"})

# Content-types that map to text documents.
SUPPORTED_TEXT_CONTENT_TYPES: frozenset[str] = frozenset({
    "text/plain",
    "text/markdown",
    "text/x-log",
    "text/x-log-file",
})

# Bytes scanned for null-byte binary detection
_BINARY_SNIFF_SIZE = 512


def detect_file_type(filename: str, content_type: str, file_bytes: bytes) -> str:
    """
    Return the canonical file type for the upload.

    Returns one of: 'pdf', 'txt', 'md', 'log', 'docx', 'doc'

    Detection order:
      1. Extension (most reliable)
      2. Content-type (fallback for extensionless names)

    Raises ValueError for unsupported or binary files.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # PDF — magic bytes validated separately in the upload router
    if ext == "pdf" or content_type == "application/pdf":
        return "pdf"

    # DOCX — ZIP-based XML format (PK magic bytes)
    if ext == "docx" or content_type in (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ):
        if not _is_zip_magic(file_bytes):
            raise ValueError(
                f"File {filename!r} does not appear to be a valid DOCX (missing ZIP header)."
            )
        return "docx"

    # PPTX — ZIP-based XML format (PK magic bytes)
    if ext == "pptx" or content_type in (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ):
        if not _is_zip_magic(file_bytes):
            raise ValueError(
                f"File {filename!r} does not appear to be a valid PPTX (missing ZIP header)."
            )
        return "pptx"

    # XLSX — ZIP-based XML format (PK magic bytes)
    if ext == "xlsx" or content_type in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ):
        if not _is_zip_magic(file_bytes):
            raise ValueError(
                f"File {filename!r} does not appear to be a valid XLSX (missing ZIP header)."
            )
        return "xlsx"

    # DOC — Legacy OLE2 compound document (D0CF magic bytes)
    if ext == "doc" or content_type == "application/msword":
        if not _is_ole2_magic(file_bytes):
            raise ValueError(
                f"File {filename!r} does not appear to be a valid DOC (missing OLE2 header)."
            )
        return "doc"

    if ext in SUPPORTED_TEXT_EXTENSIONS:
        _reject_if_binary(file_bytes, filename)
        return ext

    # Fallback: content-type driven (no recognised extension)
    if content_type in SUPPORTED_TEXT_CONTENT_TYPES:
        _reject_if_binary(file_bytes, filename)
        return "md" if content_type == "text/markdown" else "txt"

    raise ValueError(
        f"Unsupported file type: extension={ext!r}, content-type={content_type!r}. "
        "Supported formats: .pdf, .docx, .pptx, .xlsx, .doc, .txt, .md, .log"
    )


def _is_zip_magic(file_bytes: bytes) -> bool:
    """DOCX/XLSX/PPTX are ZIP archives — check for PK magic bytes."""
    return len(file_bytes) >= 4 and file_bytes[:2] == b"PK"


def _is_ole2_magic(file_bytes: bytes) -> bool:
    """Legacy .doc files are OLE2 Compound Documents."""
    return len(file_bytes) >= 8 and file_bytes[:8] == b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"


def _reject_if_binary(file_bytes: bytes, filename: str) -> None:
    """
    Raise ValueError if the file looks like binary (null bytes in the first 512 bytes).

    Valid UTF-8 text never contains null bytes, so this heuristic reliably
    detects executables, ZIPs, images, and other binary blobs renamed to text
    extensions.
    """
    if b"\x00" in file_bytes[:_BINARY_SNIFF_SIZE]:
        raise ValueError(
            f"File {filename!r} appears to be binary (null bytes detected). "
            "Only plain text files (.txt, .md, .log) are accepted for text uploads."
        )


def decode_text_safe(raw_bytes: bytes) -> str:
    """
    Decode raw bytes to a Unicode string.

    Tries UTF-8 first; falls back to latin-1 (which never fails) so that
    legacy log files with mixed encodings are still accepted.

    Normalises all line endings to \\n (covers CRLF, CR-only, and LF).
    """
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_bytes.decode("latin-1")

    # Normalise: CRLF → LF, then any remaining CR → LF (old Mac)
    return text.replace("\r\n", "\n").replace("\r", "\n")


def chunk_text(text: str, lines_per_chunk: int) -> list[str]:
    """
    Split decoded text into chunks of at most *lines_per_chunk* lines each.

    Returns a non-empty list; the last chunk may have fewer lines than the
    limit.  Blank lines and indentation are preserved exactly.

    An empty document returns a list with a single empty-string chunk so that
    chunk_number=1 is always a valid request.
    """
    if not text:
        return [""]

    lines = text.split("\n")
    chunks: list[str] = []
    for start in range(0, len(lines), lines_per_chunk):
        chunks.append("\n".join(lines[start : start + lines_per_chunk]))
    return chunks or [""]


def count_chunks(text: str, lines_per_chunk: int) -> int:
    """Return the number of chunks for the given decoded text."""
    if not text:
        return 1
    line_count = text.count("\n") + 1
    return max(1, (line_count + lines_per_chunk - 1) // lines_per_chunk)


def extract_toc(text: str, file_type: str, lines_per_chunk: int = 100) -> list[dict]:
    """
    Extract TOC entries from decoded text content.

    Delegates to app.services.toc.text_extractor for all formats.
    Returns backward-compatible dicts with keys: level, title, chunk, line.
    (New keys id, anchor, source, confidence are also included.)
    """
    if file_type == "pdf" or not text:
        return []
    from app.services.toc.text_extractor import extract_text_toc
    entries = extract_text_toc(text, file_type, lines_per_chunk=lines_per_chunk)
    return [e.to_dict() for e in entries]
