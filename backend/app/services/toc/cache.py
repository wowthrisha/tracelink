"""
TOC cache — stores extracted TOC trees so the /toc endpoint never
re-parses documents on repeat viewer requests.

Two-level:
  L1: process-local TTL cache (submillisecond, 500 entries)
  L2: Redis JSON cache (1-5 ms, shared across replicas)

Cache key: "toc:{doc_id}"

Invalidation triggers:
  - document delete  → invalidate_toc(doc_id)
  - document reprocess → invalidate_toc(doc_id)
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Redis key prefix and TTL
_REDIS_KEY_PREFIX = "securedoc:toc:v1:"
_REDIS_TTL_SEC = 300


def _redis_key(doc_id: str) -> str:
    return f"{_REDIS_KEY_PREFIX}{doc_id}"


# ── L1: process-local cache (reuses viewer_cache infrastructure) ──────────────

def _get_l1():
    from app.services.viewer_cache import toc_cache
    return toc_cache


async def get_cached_toc_async(doc_id: str) -> Optional[List[dict]]:
    """Async L1 → L2 lookup. Returns list of TocEntry dicts, or None on miss."""
    l1 = _get_l1()

    # L1
    result = l1.get(doc_id)
    if result is not None:
        return result

    # L2 (Redis)
    try:
        from app.services.page_cache import get_redis_page_cache
        r = get_redis_page_cache()
        if r is not None:
            raw = await r._r.get(_redis_key(doc_id))
            if raw is not None:
                data = json.loads(raw)
                l1.put(doc_id, data)  # warm L1
                return data
    except Exception as exc:
        logger.debug("toc_cache L2 get failed for doc_id=%s: %s", doc_id, exc)
    return None


async def store_toc_async(doc_id: str, entries: List[dict]) -> None:
    """Persist TOC to L1 and L2."""
    l1 = _get_l1()
    l1.put(doc_id, entries)

    try:
        from app.services.page_cache import get_redis_page_cache
        r = get_redis_page_cache()
        if r is not None:
            await r._r.setex(_redis_key(doc_id), _REDIS_TTL_SEC, json.dumps(entries))
    except Exception as exc:
        logger.debug("toc_cache L2 set failed for doc_id=%s: %s", doc_id, exc)


def invalidate_toc(doc_id: str) -> None:
    """Evict TOC from L1. L2 evicts naturally via TTL."""
    _get_l1().invalidate(doc_id)
