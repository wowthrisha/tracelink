"""
Application-level Prometheus metrics for SecureDoc.

All metric objects are module-level singletons. Callsites import and use them
directly — no dependency injection needed.

Security constraints:
- Labels must never contain user data, emails, IPs, or session IDs.
- Path labels are normalized to pattern strings to prevent cardinality explosion
  (e.g. /api/viewer/page/{token}/{page} not /api/viewer/page/abc123.../1).
"""
import re
from prometheus_client import Counter, Histogram, Gauge, REGISTRY

# ── HTTP layer ────────────────────────────────────────────────────────────────

http_requests_total = Counter(
    "securedoc_http_requests_total",
    "Total HTTP requests by method, path pattern, and status code",
    ["method", "path_pattern", "status_code"],
)

http_request_duration_seconds = Histogram(
    "securedoc_http_request_duration_seconds",
    "HTTP request latency by method and path pattern",
    ["method", "path_pattern"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# ── Viewer flow ───────────────────────────────────────────────────────────────

viewer_validations_total = Counter(
    "securedoc_viewer_validations_total",
    "Viewer link validations by result",
    ["result"],  # success | denied_password | denied_ip | expired | revoked | max_views
)

page_requests_total = Counter(
    "securedoc_page_requests_total",
    "Page image requests by cache outcome",
    ["cache_hit"],  # true | false
)

viewer_sessions_total = Counter(
    "securedoc_viewer_sessions_total",
    "Viewer sessions started by outcome",
    ["outcome"],  # created | resumed | rejected
)

# ── Document operations ───────────────────────────────────────────────────────

document_uploads_total = Counter(
    "securedoc_document_uploads_total",
    "Document uploads by outcome",
    ["result"],  # queued | rejected_quota | rejected_type | rejected_size
)

upload_duration_seconds = Histogram(
    "securedoc_upload_duration_seconds",
    "Time from upload receipt to storage completion",
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

processing_duration_seconds = Histogram(
    "securedoc_processing_duration_seconds",
    "Document processing time by stage (rasterize, extract, ocr)",
    ["stage"],  # rasterize | text_extract | toc_extract | watermark
    buckets=[0.5, 1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0],
)

downloads_total = Counter(
    "securedoc_downloads_total",
    "Document download requests by outcome",
    ["result"],  # success | denied_permission | denied_session | too_large
)

# ── Share links ───────────────────────────────────────────────────────────────

share_links_created_total = Counter(
    "securedoc_share_links_created_total",
    "Share links created",
)

share_links_revoked_total = Counter(
    "securedoc_share_links_revoked_total",
    "Share links revoked",
)

# ── Annotations ───────────────────────────────────────────────────────────────

annotations_total = Counter(
    "securedoc_annotations_total",
    "Annotation operations by type and action",
    ["annotation_type", "action"],  # (highlight|comment|...) x (create|delete|resolve)
)

# ── Webhooks ──────────────────────────────────────────────────────────────────

webhook_deliveries_total = Counter(
    "securedoc_webhook_deliveries_total",
    "Webhook delivery attempts by outcome",
    ["outcome"],  # success | failure | skipped
)

webhook_retries_total = Counter(
    "securedoc_webhook_retries_total",
    "Webhook delivery retries (excludes first attempt)",
)

# ── Database ──────────────────────────────────────────────────────────────────

db_query_duration_seconds = Histogram(
    "securedoc_db_query_duration_seconds",
    "Database query latency",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1.0, 5.0],
)

# ── Cache ─────────────────────────────────────────────────────────────────────

cache_hits_total = Counter(
    "securedoc_cache_hits_total",
    "Cache hits by cache layer",
    ["layer"],  # redis | memory
)

cache_misses_total = Counter(
    "securedoc_cache_misses_total",
    "Cache misses by cache layer",
    ["layer"],  # redis | memory
)

# ── Session state ─────────────────────────────────────────────────────────────

active_sessions = Gauge(
    "securedoc_active_sessions",
    "Number of entries currently in the session validation cache",
)

# ── Path normalization ────────────────────────────────────────────────────────

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
_TOKEN_RE = re.compile(r"/([0-9a-f]{16,})/")
_PAGE_NUM_RE = re.compile(r"/(\d+)$")
_CHUNK_NUM_RE = re.compile(r"/(\d+)$")


def normalize_path(path: str) -> str:
    """Replace variable path segments with pattern placeholders.

    Prevents label cardinality explosion from unique tokens, UUIDs, and page
    numbers. Examples:
      /api/viewer/page/abc123.../1       → /api/viewer/page/{token}/{page}
      /api/documents/550e8400-e29b.../status → /api/documents/{id}/status
      /v/abc123...                        → /v/{token}
    """
    # Replace UUIDs first (they contain hyphens)
    path = _UUID_RE.sub("{id}", path)
    # Replace long hex tokens (share link tokens, session IDs in path)
    path = _TOKEN_RE.sub("/{token}/", path)
    # Replace trailing numeric segments (page numbers, chunk numbers)
    path = _PAGE_NUM_RE.sub("/{n}", path)
    return path
