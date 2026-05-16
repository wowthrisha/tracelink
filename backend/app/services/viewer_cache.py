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


# ── Public helpers ────────────────────────────────────────────────────────────

def invalidate_link(token: str) -> None:
    """Evict a link snapshot from the cache.

    Call this whenever a link is revoked so the next page request does not
    serve from a stale cached entry that still looks active.
    """
    link_cache.invalidate(token)


def clear_all_caches() -> None:
    """Flush all three caches.  Called in tests to prevent cross-test pollution."""
    link_cache.clear()
    doc_cache.clear()
    page_cache.clear()
