"""
Text document processing utilities — Phase 5 + Phase 7 (TOC extraction).

Handles file-type detection, safe UTF-8 decoding, binary rejection, and
line-based chunking for .txt, .md, and .log uploads.

XSS contract
────────────
This module operates on raw bytes and strings only.  It never generates HTML.
All user-visible rendering is done in the React frontend via JSX text nodes,
which auto-escape every character.  No HTML is produced here.

Supported types
───────────────
  pdf — handled by existing rasterizer pipeline (not this module)
  txt — plain text
  md  — Markdown (rendered safely client-side with React elements)
  log — log files (rendered as plain text)
"""

import re

# Extensions that this module can process
SUPPORTED_TEXT_EXTENSIONS: frozenset[str] = frozenset({"txt", "md", "log"})

# Content-types that map to text documents.
# application/octet-stream is included because some browsers send it for .txt
# files; extension-first detection disambiguates from binary octet-streams.
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
    Return the canonical file type for the upload: 'pdf', 'txt', 'md', or 'log'.

    Detection order:
      1. Extension (most reliable for text files)
      2. Content-type (fallback for extensionless names)

    Raises ValueError for unsupported or binary files.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    # PDF — magic bytes validated separately in the upload router
    if ext == "pdf" or content_type == "application/pdf":
        return "pdf"

    if ext in SUPPORTED_TEXT_EXTENSIONS:
        _reject_if_binary(file_bytes, filename)
        return ext

    # Fallback: content-type driven (no recognised extension)
    if content_type in SUPPORTED_TEXT_CONTENT_TYPES:
        _reject_if_binary(file_bytes, filename)
        return "md" if content_type == "text/markdown" else "txt"

    raise ValueError(
        f"Unsupported file type: extension={ext!r}, content-type={content_type!r}. "
        "Supported formats: .pdf, .txt, .md, .log"
    )


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
    Extract table of contents entries from a text document.

    Returns a list of dicts: {level, title, chunk, line}
      level — heading depth (1–6 for Markdown; 1 or 2 for plain text)
      title — heading text (stripped)
      chunk — 1-indexed chunk number where this heading appears
      line  — 1-indexed line number within the document

    For PDFs this always returns an empty list (no text extraction yet).
    For .md: extracts ATX-style Markdown headings (# … ######).
    For .txt/.log: heuristically detects ALL-CAPS section titles and
      "Label:" style sub-headings (≤5 words, ends with colon).

    At most 200 entries are returned to avoid sending huge payloads.
    """
    if file_type == "pdf" or not text:
        return []

    lines = text.split("\n")
    toc: list[dict] = []
    _MD_HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
    _MAX_TOC = 200

    if file_type == "md":
        for i, raw_line in enumerate(lines):
            m = _MD_HEADING.match(raw_line.strip())
            if m:
                level = len(m.group(1))
                title = m.group(2).strip()
                chunk = (i // lines_per_chunk) + 1
                toc.append({"level": level, "title": title, "chunk": chunk, "line": i + 1})
                if len(toc) >= _MAX_TOC:
                    break
    else:
        # Plain text / log heuristics
        for i, raw_line in enumerate(lines):
            stripped = raw_line.strip()
            if not stripped or len(stripped) < 3:
                continue
            words = stripped.split()
            # ALL-CAPS section title: ≤8 words, no leading digit, pure uppercase
            if (
                stripped.isupper()
                and not stripped[0].isdigit()
                and len(words) <= 8
            ):
                chunk = (i // lines_per_chunk) + 1
                toc.append({"level": 1, "title": stripped, "chunk": chunk, "line": i + 1})
            # "Label:" sub-heading: ends with ':', ≤5 words, no tab indent
            elif (
                stripped.endswith(":")
                and len(words) <= 5
                and "\t" not in raw_line
                and not raw_line.startswith(" ")
            ):
                chunk = (i // lines_per_chunk) + 1
                toc.append({"level": 2, "title": stripped[:-1], "chunk": chunk, "line": i + 1})
            if len(toc) >= _MAX_TOC:
                break

    return toc
