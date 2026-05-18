"""
Phase 4 — shared byte cache for viewer page and thumbnail assets.

Two-level cache
───────────────
L1: Process-local LRU OrderedDict (submillisecond access, bounded at 600/2000 entries).
L2: Redis-backed shared cache (1–5 ms, shared across all replicas and cold-starts).

Lookup order: L1 → L2 → storage (caller is responsible for storage).
On a L2 hit the entry is promoted to L1 so the next request is L1-local.
On a storage fetch both L1 and L2 are populated.

Security contract
─────────────────
• Only raw page bytes (pre-watermark) and thumbnail bytes are stored here.
• Callers MUST complete all auth / session / revocation / expiry checks
  BEFORE calling any get function.  The visible watermark (session-specific)
  is applied by the caller AFTER the cache hit.
• Cache keys encode the storage path (doc + page specific) — no user or
  token information is ever stored or used as a key.

Key scheme
──────────
  page:  securedoc:page:v1:{storage_key}   e.g. securedoc:page:v1:pages/{uuid}/0001.webp
  thumb: securedoc:thumb:v1:{thumb_key}    e.g. securedoc:thumb:v1:thumbs/{uuid}/0001.webp

The "v1" prefix can be bumped to flush all cached bytes on a format change.

Availability
────────────
Redis operations are fully wrapped in try/except.  If Redis is unreachable,
get helpers return None (cache miss) and put/invalidate helpers are no-ops.
The caller degrades gracefully to the storage path.

Invalidation
────────────
• Document delete  → clear_doc_bytes(doc_id)  clears L1 + L2 for the doc.
• Document reprocess (recover) → clear_doc_bytes_redis(doc_id) clears L2
  (L1 in the API server is a separate process; it will repopulate from fresh
  storage bytes after the next L1 eviction hits the now-cleared L2).
"""
import collections
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Version tag — bump to invalidate all L2 cached bytes (e.g. after image format change)
_KEY_VERSION = "v1"
_PAGE_PREFIX = f"securedoc:page:{_KEY_VERSION}:"
_THUMB_PREFIX = f"securedoc:thumb:{_KEY_VERSION}:"

# ── L1: Process-local LRU caches ──────────────────────────────────────────────
# Sizing: 50 docs × 60 pages × ~50 KB ≈ 150 MB worst-case at max capacity.
# LRU eviction keeps only the hottest pages in memory.

_PAGE_BYTES_CACHE: collections.OrderedDict = collections.OrderedDict()
_PAGE_BYTES_CACHE_MAX = 600

# Thumbnails are ~5 KB each; 2 000 entries ≈ 10 MB.
_THUMB_BYTES_CACHE: collections.OrderedDict = collections.OrderedDict()
_THUMB_BYTES_CACHE_MAX = 2000


def _page_local_get(key: str) -> Optional[bytes]:
    if key not in _PAGE_BYTES_CACHE:
        return None
    _PAGE_BYTES_CACHE.move_to_end(key)
    return _PAGE_BYTES_CACHE[key]


def _page_local_put(key: str, data: bytes) -> None:
    _PAGE_BYTES_CACHE[key] = data
    _PAGE_BYTES_CACHE.move_to_end(key)
    if len(_PAGE_BYTES_CACHE) > _PAGE_BYTES_CACHE_MAX:
        _PAGE_BYTES_CACHE.popitem(last=False)


def _thumb_local_get(key: str) -> Optional[bytes]:
    if key not in _THUMB_BYTES_CACHE:
        return None
    _THUMB_BYTES_CACHE.move_to_end(key)
    return _THUMB_BYTES_CACHE[key]


def _thumb_local_put(key: str, data: bytes) -> None:
    _THUMB_BYTES_CACHE[key] = data
    _THUMB_BYTES_CACHE.move_to_end(key)
    if len(_THUMB_BYTES_CACHE) > _THUMB_BYTES_CACHE_MAX:
        _THUMB_BYTES_CACHE.popitem(last=False)


def clear_local_page_cache() -> None:
    """Flush the process-local page byte cache.  Called in tests."""
    _PAGE_BYTES_CACHE.clear()


def clear_local_thumb_cache() -> None:
    """Flush the process-local thumbnail byte cache.  Called in tests."""
    _THUMB_BYTES_CACHE.clear()


def clear_doc_from_local_cache(doc_id: str) -> None:
    """Remove all L1 byte cache entries for a specific document."""
    page_prefix = f"pages/{doc_id}/"
    thumb_prefix = f"thumbs/{doc_id}/"
    for key in [k for k in list(_PAGE_BYTES_CACHE) if k.startswith(page_prefix)]:
        del _PAGE_BYTES_CACHE[key]
    for key in [k for k in list(_THUMB_BYTES_CACHE) if k.startswith(thumb_prefix)]:
        del _THUMB_BYTES_CACHE[key]


# ── L2: Redis-backed shared cache ─────────────────────────────────────────────

class RedisPageCache:
    """
    Async Redis-backed byte cache for page images and thumbnails.

    All public methods are async and degrade gracefully when Redis is
    unavailable: get helpers return None, put/invalidate are no-ops.
    """

    def __init__(self, client, ttl_seconds: int = 3600) -> None:
        self._r = client
        self._ttl = ttl_seconds

    @staticmethod
    def _page_key(storage_key: str) -> str:
        return f"{_PAGE_PREFIX}{storage_key}"

    @staticmethod
    def _thumb_key(thumb_key: str) -> str:
        return f"{_THUMB_PREFIX}{thumb_key}"

    async def get_page(self, storage_key: str) -> Optional[bytes]:
        try:
            data = await self._r.get(self._page_key(storage_key))
            if data is not None:
                logger.debug(
                    "cache_hit source=redis type=page key=%s bytes=%d",
                    storage_key, len(data),
                )
            return data
        except Exception as exc:
            logger.warning("redis get_page failed (fallback to storage): %s", exc)
            return None

    async def put_page(self, storage_key: str, data: bytes) -> None:
        try:
            await self._r.setex(self._page_key(storage_key), self._ttl, data)
            logger.debug(
                "cache_populate source=redis type=page key=%s bytes=%d",
                storage_key, len(data),
            )
        except Exception as exc:
            logger.warning("redis put_page failed: %s", exc)

    async def get_thumb(self, thumb_key: str) -> Optional[bytes]:
        try:
            data = await self._r.get(self._thumb_key(thumb_key))
            if data is not None:
                logger.debug(
                    "cache_hit source=redis type=thumb key=%s bytes=%d",
                    thumb_key, len(data),
                )
            return data
        except Exception as exc:
            logger.warning("redis get_thumb failed (fallback to storage): %s", exc)
            return None

    async def put_thumb(self, thumb_key: str, data: bytes) -> None:
        try:
            await self._r.setex(self._thumb_key(thumb_key), self._ttl, data)
            logger.debug(
                "cache_populate source=redis type=thumb key=%s bytes=%d",
                thumb_key, len(data),
            )
        except Exception as exc:
            logger.warning("redis put_thumb failed: %s", exc)

    async def invalidate_doc(self, doc_id: str) -> int:
        """Delete all cached page and thumbnail bytes for a document via SCAN+DEL."""
        deleted = 0
        try:
            for prefix in [
                f"{_PAGE_PREFIX}pages/{doc_id}/",
                f"{_THUMB_PREFIX}thumbs/{doc_id}/",
            ]:
                deleted += await self._scan_delete(prefix)
            if deleted:
                logger.info(
                    "cache_invalidate source=redis doc_id=%s deleted=%d keys",
                    doc_id, deleted,
                )
        except Exception as exc:
            logger.warning("redis invalidate_doc failed for %s: %s", doc_id, exc)
        return deleted

    async def _scan_delete(self, pattern_prefix: str) -> int:
        """SCAN + DEL for all keys matching a prefix.  Non-blocking cursor loop."""
        deleted = 0
        cursor = 0
        pattern = f"{pattern_prefix}*"
        while True:
            cursor, keys = await self._r.scan(cursor, match=pattern, count=100)
            if keys:
                await self._r.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        return deleted


# ── Module-level singleton ────────────────────────────────────────────────────

_redis_cache: Optional[RedisPageCache] = None
_redis_cache_initialised = False


def get_redis_page_cache() -> Optional[RedisPageCache]:
    """Return the module-level Redis page cache, initialising on first call.

    Returns None when Redis is disabled or unreachable — callers treat this
    as a perpetual cache miss and fall back to storage transparently.
    """
    global _redis_cache, _redis_cache_initialised
    if _redis_cache_initialised:
        return _redis_cache
    _redis_cache_initialised = True
    try:
        from app.config import settings
        import redis.asyncio as aioredis
        client = aioredis.from_url(
            settings.redis_url,
            decode_responses=False,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        ttl = getattr(settings, "redis_page_cache_ttl_sec", 3600)
        _redis_cache = RedisPageCache(client, ttl_seconds=ttl)
        logger.info(
            "redis page cache initialised ttl=%ds url=%s", ttl, settings.redis_url
        )
    except Exception as exc:
        logger.warning("redis page cache unavailable: %s", exc)
        _redis_cache = None
    return _redis_cache


def reset_redis_page_cache(cache: Optional[RedisPageCache] = None) -> None:
    """Replace the module-level Redis cache instance.  Called in tests."""
    global _redis_cache, _redis_cache_initialised
    _redis_cache = cache
    _redis_cache_initialised = True  # skip auto-init so tests control the cache


# ── Convenience helpers used by the viewer router ────────────────────────────

async def fetch_page_bytes(
    storage_key: str,
) -> tuple[Optional[bytes], str]:
    """
    L1 → L2 cache lookup for page bytes.  Returns (bytes_or_None, cache_source).

    cache_source is one of: "local", "redis", None (both missed — caller fetches
    from storage and should call store_page_bytes afterwards).
    """
    # L1
    data = _page_local_get(storage_key)
    if data is not None:
        logger.debug("cache_hit source=local type=page key=%s bytes=%d", storage_key, len(data))
        return data, "local"

    # L2
    r = get_redis_page_cache()
    if r is not None:
        data = await r.get_page(storage_key)
        if data is not None:
            _page_local_put(storage_key, data)  # warm L1 from L2
            return data, "redis"

    return None, "storage"


async def store_page_bytes(storage_key: str, data: bytes) -> None:
    """Populate L1 and L2 after a storage fetch."""
    _page_local_put(storage_key, data)
    r = get_redis_page_cache()
    if r is not None:
        await r.put_page(storage_key, data)


async def fetch_thumb_bytes(
    thumb_key: str,
) -> tuple[Optional[bytes], str]:
    """L1 → L2 cache lookup for thumbnail bytes."""
    data = _thumb_local_get(thumb_key)
    if data is not None:
        logger.debug("cache_hit source=local type=thumb key=%s bytes=%d", thumb_key, len(data))
        return data, "local"

    r = get_redis_page_cache()
    if r is not None:
        data = await r.get_thumb(thumb_key)
        if data is not None:
            _thumb_local_put(thumb_key, data)  # warm L1 from L2
            return data, "redis"

    return None, "storage"


async def store_thumb_bytes(thumb_key: str, data: bytes) -> None:
    """Populate L1 and L2 after a storage fetch."""
    _thumb_local_put(thumb_key, data)
    r = get_redis_page_cache()
    if r is not None:
        await r.put_thumb(thumb_key, data)


async def clear_doc_bytes(doc_id: str) -> None:
    """
    Invalidate all cached page and thumbnail bytes for a document.

    Clears both L1 (this process) and L2 (Redis shared cache).  Call this on
    document delete so no stale bytes survive in any cache tier.
    """
    clear_doc_from_local_cache(doc_id)
    r = get_redis_page_cache()
    if r is not None:
        await r.invalidate_doc(doc_id)


async def clear_doc_bytes_redis(doc_id: str) -> None:
    """
    Invalidate only the Redis (L2) cache for a document.

    Used by Celery workers on document reprocess — workers cannot clear the
    API server's L1 cache (separate process), but clearing L2 ensures that
    when the API server's L1 evicts the stale entry it repopulates from fresh
    storage bytes rather than a stale Redis hit.
    """
    r = get_redis_page_cache()
    if r is not None:
        await r.invalidate_doc(doc_id)
