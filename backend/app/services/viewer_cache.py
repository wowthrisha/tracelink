"""
Process-local TTL caches for viewer hot-path metadata.

Caches the three DB SELECTs that fire on every page/thumb request
(link lookup, document lookup, page-record lookup) so repeated access
to the same document skips the database for those reads entirely.

Security contracts
──────────────────
  Revocation   — link cache TTL is 10 s.  link_service.revoke_link() calls
                 invalidate_link() immediately so the revocation propagates
                 within < TTL seconds for new requests.  The revoked_at field
                 in the cached snapshot is also checked against the current
                 clock on every cache hit, so a snapshot with a non-None
                 revoked_at is rejected without touching the DB.

  Expiry       — expires_at is in the cached snapshot and checked against
                 datetime.now(utc) on every request, even on hits.  A TTL
                 expiry and a wall-clock expiry are two independent checks.

  max_views    — enforced at validate time inside link_service.validate_link,
                 which reads fresh from the DB and is rate-limited.  The page-
                 serving path does not re-check view counts, so caching the
                 snapshot there is safe.

  IP allowlist — the ip_allowlist field is cached with the link snapshot and
                 applied on every page request.  Changes to the allowlist
                 propagate when the TTL expires (≤ LINK_TTL_SEC seconds).

Async / thread safety
─────────────────────
  All mutations happen on the single asyncio event loop thread (FastAPI runs
  uvicorn with workers=N using forked *processes*, not threads).  Within one
  process, dict operations are atomic between await points, so no explicit
  lock is needed.  If you ever switch to threading workers, add a threading.Lock.
"""
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional


# ── TTL constants ─────────────────────────────────────────────────────────────
# Short TTL for links: revocations must take effect quickly.
LINK_TTL_SEC: float = 10.0
# Document status stabilises after initial processing; 60 s is safe.
DOC_TTL_SEC: float = 60.0
# Page records (storage_key + dimensions) are immutable after creation.
PAGE_TTL_SEC: float = 300.0
# Session validation cache: short TTL so revocation propagates quickly.
# 5 s means at most one extra page is served after a link is revoked via
# invalidate_link() (which also purges sessions immediately, making the
# effective revocation latency <1 s in the common case).
SESSION_TTL_SEC: float = 5.0


# ── Snapshot dataclasses ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class LinkSnapshot:
    """Immutable snapshot of the ShareLink fields used for page/thumb serving."""
    id: uuid.UUID
    token: str
    document_id: uuid.UUID
    revoked_at: Optional[datetime]
    expires_at: Optional[datetime]
    ip_allowlist: Optional[str]


@dataclass(frozen=True)
class DocSnapshot:
    """Immutable snapshot of the Document fields used for page/thumb serving."""
    id: uuid.UUID
    status: str
    file_type: str = "pdf"
    storage_key: Optional[str] = None
    page_count: Optional[int] = None


@dataclass(frozen=True)
class PageSnapshot:
    """Immutable snapshot of the DocumentPage fields used for storage access."""
    storage_key: str
    width_px: int
    height_px: int


# ── TTL cache ─────────────────────────────────────────────────────────────────

class _TTLCache:
    """
    Dictionary-backed TTL cache with a hard capacity limit.

    On capacity overflow the oldest-inserted entry is evicted (FIFO), which
    keeps memory bounded without the overhead of a full LRU doubly-linked list.
    Expired entries are evicted lazily on read — no background sweep needed.
    """

    __slots__ = ("_data", "_maxsize", "_ttl")

    def __init__(self, maxsize: int, ttl_seconds: float) -> None:
        self._data: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)
        self._maxsize = maxsize
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        entry = self._data.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._data[key]
            return None
        return value

    def put(self, key: str, value: Any) -> None:
        self._data[key] = (value, time.monotonic() + self._ttl)
        if len(self._data) > self._maxsize:
            self._data.pop(next(iter(self._data)))  # FIFO eviction

    def invalidate(self, key: str) -> None:
        self._data.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all entries whose key starts with prefix. Returns count deleted."""
        keys = [k for k in self._data if k.startswith(prefix)]
        for k in keys:
            del self._data[k]
        return len(keys)

    def clear(self) -> None:
        self._data.clear()

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None


# ── Module-level cache instances ──────────────────────────────────────────────

link_cache: _TTLCache = _TTLCache(maxsize=2000, ttl_seconds=LINK_TTL_SEC)
doc_cache: _TTLCache = _TTLCache(maxsize=1000, ttl_seconds=DOC_TTL_SEC)
page_cache: _TTLCache = _TTLCache(maxsize=10000, ttl_seconds=PAGE_TTL_SEC)

# Text content cache — stores decoded text strings keyed by storage_key.
# TTL matches PAGE_TTL_SEC (5 min): text content is immutable after processing.
# Max 100 entries: text files can be large (~MB each); 100 entries is ~100 MB worst-case.
# Files larger than 5 MB are NOT cached (caller must skip the put call).
TEXT_CONTENT_MAX_BYTES = 5 * 1024 * 1024  # 5 MB decoded text
text_content_cache: _TTLCache = _TTLCache(maxsize=100, ttl_seconds=PAGE_TTL_SEC)

# Chunk array cache — stores pre-split chunk lists keyed by "{storage_key}:{lines_per_chunk}".
# Avoids re-splitting the full text on every chunk request (O(n) per call → O(1)).
# Shares maxsize/TTL with text_content_cache; entries are always smaller than their source text.
chunk_array_cache: _TTLCache = _TTLCache(maxsize=100, ttl_seconds=PAGE_TTL_SEC)

# TOC cache — stores extracted TOC trees keyed by doc_id (str(UUID)).
# TTL=5 min matches page metadata; TOC is immutable after document processing.
# 500 entries: each entry is a small JSON array; total memory ~50 MB worst-case.
toc_cache: _TTLCache = _TTLCache(maxsize=500, ttl_seconds=PAGE_TTL_SEC)

# Session validation cache — stores active session state keyed by session_id.
# Value: (link_id: uuid.UUID, last_seen_at: datetime, viewer_email_masked: str|None)
# TTL=5 s: short enough to propagate revocation quickly; long enough to
# eliminate 95%+ of viewer_sessions DB reads under continuous page loads.
# 50 000 entries covers 50 000 concurrent unique sessions with ~6 MB RAM overhead.
session_cache: _TTLCache = _TTLCache(maxsize=50_000, ttl_seconds=SESSION_TTL_SEC)


# ── Public helpers ────────────────────────────────────────────────────────────

def invalidate_link(token: str, link_id: Optional[uuid.UUID] = None) -> None:
    """Evict a link snapshot from the cache.

    Call this whenever a link is revoked so the next page request does not
    serve from a stale cached entry that still looks active.

    When link_id is provided, also purges all session cache entries belonging
    to that link — making revocation propagation nearly instantaneous (< 1 ms)
    rather than waiting for the 5-second SESSION_TTL_SEC to expire.
    """
    link_cache.invalidate(token)
    if link_id is not None:
        invalidate_sessions_for_link(link_id)


def invalidate_sessions_for_link(link_id: uuid.UUID) -> int:
    """Remove all session cache entries for the given link.

    Called on link revocation and link update to ensure sessions for
    the affected link are re-validated against the DB on the next request.
    Returns the number of entries removed.
    """
    # Session cache keys are session_ids; values are (link_id, last_seen_at, email).
    # We must scan to find all sessions belonging to this link.
    link_id_str = str(link_id)
    keys_to_remove = []
    for key, (value, _expires) in list(session_cache._data.items()):
        cached_link_id, _last_seen, _email = value
        if str(cached_link_id) == link_id_str:
            keys_to_remove.append(key)
    for key in keys_to_remove:
        session_cache._data.pop(key, None)
    return len(keys_to_remove)


def invalidate_doc_entries(doc_id: str, storage_key: Optional[str] = None) -> None:
    """Evict the doc snapshot and all page-metadata snapshots for a document.

    Call this on document delete or reprocess so metadata caches do not
    serve stale status/storage-key information.

    storage_key is optional — when provided, text content and chunk arrays for
    this document are also evicted (applies to text documents only).
    """
    doc_id_str = str(doc_id)
    doc_cache.invalidate(doc_id_str)
    page_cache.invalidate_prefix(f"{doc_id_str}:")
    toc_cache.invalidate(doc_id_str)
    if storage_key:
        text_content_cache.invalidate(storage_key)
        chunk_array_cache.invalidate_prefix(f"{storage_key}:")


def clear_all_caches() -> None:
    """Flush all caches.  Called in tests to prevent cross-test pollution."""
    link_cache.clear()
    doc_cache.clear()
    page_cache.clear()
    text_content_cache.clear()
    chunk_array_cache.clear()
    toc_cache.clear()
    session_cache.clear()
