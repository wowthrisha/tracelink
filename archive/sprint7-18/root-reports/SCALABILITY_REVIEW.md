# Scalability Review — Sprint V6.0 (Phase 6)

Reviewed: database queries, pagination, sorting, filtering, indexes, caching, streaming, background jobs, N+1 queries, memory usage, large payloads.

## Already well-designed (positive findings, unchanged)

- Composite indexes are proactively added across `models/*.py` with migration references documented in comments — this is a genuinely mature pattern, not something added reactively.
- Multi-tier viewer cache (`viewer_cache.py` process-local + `page_cache.py` L1/Redis L2) applied consistently across every viewer hot-path endpoint, with correct invalidation on delete/reprocess/retention-expiry.
- Document download (`viewer.py:download_document`) streams the assembled PDF in 64KB chunks via `StreamingResponse`, watermarks and discards each page's bytes as it goes rather than holding the whole document in memory, and is bounded by `settings.max_download_pages_pdf` — a well-built streaming path.
- Webhook delivery fan-out is capped at 20 per user and re-validates SSRF at delivery time (TOCTOU-safe).
- Analytics/audit endpoints consistently push filtering, sorting, and pagination into SQL rather than doing it in Python.

## Indexes

| Finding | Status |
|---|---|
| `WebhookDelivery` only indexed `webhook_id`; `get_deliveries()` filters on it **and** sorts by `created_at DESC`, forcing an uncovered sort once deliveries accumulate | ✅ **Fixed** — composite index added (`ix_webhook_deliveries_webhook_created`, migration `027`). |
| `OrgMembership.org_id` has no dedicated index (only as the leading column of a unique constraint); `list_members()` filters on it and orders by `created_at`, uncovered | 📝 **Documented, not fixed** — minor at typical org member-list sizes; deferred rather than adding a migration for a low-traffic list endpoint under time pressure. |

## Pagination — real gaps, documented not fixed

The following list endpoints return a genuinely unbounded collection with no `limit`/`offset`, unlike the well-paginated reference pattern already used by `admin.py`'s audit log and `analytics.py`:

- `documents.py:list_documents` — every document the user/org can see, plus 3 more unbounded `IN (doc_ids)` follow-up queries
- `links.py:list_links` — every share link for a document
- `storage.py:storage_dashboard` — every non-deleted document, **plus** a Python-side `sorted()` over the full unbounded set (compounding the issue — see Sorting below)
- `orgs.py:list_members` — every org member, plus a per-member Supabase HTTP lookup fan-out
- `reading_analytics_service.py`'s per-viewer reading-sessions table — every `ReadingSession` for a document, unbounded

**None of these were changed this sprint.** Adding backend `limit`/`offset` params is individually low-risk (additive, backward-compatible if defaulted generously), but the frontend for each of these lists doesn't currently send or consume pagination params — a backend-only change would cap responses without giving the UI any way to actually page through the rest, which is a half-fix. Doing this properly means a coordinated frontend+backend change per endpoint, which is more scope than "implement only low-risk optimizations" comfortably covers in one pass. Documented here as the top scalability follow-up, in priority order: `list_documents` (most likely to matter first, as document counts grow), `storage_dashboard` (also has the Python-sort issue), `list_links`, `list_members`, per-viewer reading table.

`webhooks.py:list_webhooks` and `api_keys.py:list_api_keys`/`orgs.py:list_orgs` are technically unbounded too but self-limiting in practice (webhooks capped at 20/user; users rarely accumulate many keys/orgs) — low severity, not prioritized.

## Sorting/filtering

`storage.py:storage_dashboard` sorts its entire unbounded document set in Python (`sorted(docs, key=lambda d: _effective_bytes(d), reverse=True)`) rather than in SQL — compounds the pagination gap above. 📝 Documented — the real fix (push the sort into SQL via `storage_bytes_computed`/`file_size_bytes` ordering) is coupled to fixing the pagination gap itself, not separable.

Everywhere else, sorting/filtering correctly happens in SQL (`analytics_service.py` builds filters then `.order_by().offset().limit()` — the good reference pattern).

## Caching

Multi-tier cache applied consistently (see positive findings). One minor gap: `services/toc/cache.py:invalidate_toc()` is defined but never called anywhere — actual TOC invalidation flows through `viewer_cache.invalidate_doc_entries()` instead, which only clears the L1 tier; the TOC's Redis L2 relies purely on its 300-second TTL to self-expire on delete/reprocess. 📝 Documented — bounded 5-minute staleness window, not urgent, and `invalidate_toc()` being genuinely dead code is also tracked in the repository-health dead-code sweep.

## Streaming vs. buffering

- Document upload (`documents.py:upload_document`) fully buffers the entire file into memory (`await file.read()`) **before** the size-limit check runs. 📝 Documented, not fixed — a real design concern for very large files (streaming validation/hashing would be the correct fix), but changing the upload ingestion path is a bigger change than fits "low-risk" scope this sprint, and current adapter size limits do reject oversized files after the fact as a mitigation.
- CSV exports (`annotation_export_service.py`) build the full CSV in an in-memory `io.StringIO()` rather than streaming. Fine at current annotation-export volumes; documented for future revisiting if export sizes grow.

## Background jobs / fan-out

- Webhook fan-out: bounded, fine (see positive findings).
- `requeue_orphaned_uploads` (5-minute Celery Beat sweep): dispatches one `process_document.delay()` per orphaned document in a tight loop with no batching/throttling. After a worker-fleet outage longer than the orphan threshold, this could burst-dispatch a large number of tasks simultaneously on recovery — a thundering-herd risk. 📝 Documented, not fixed — needs load-testing to size a safe rate limit or chunk size, not a blind change under time pressure.
- `cleanup.py:sync_document_access_times` uses a single set-based SQL `UPDATE...FROM` rather than a Python loop — good pattern; as `access_events` grows into the tens of millions of rows the daily full-table aggregate may eventually need partitioning review, but that's a "watch this" item, not a current problem.

## Large payloads

Same list as the Pagination section above — the concrete enterprise-scale risk is a handful of specific unbounded list/detail endpoints, not a systemic pattern; the rest of the API is well-bounded.

---

## What was actually implemented this sprint (low-risk only, per this phase's instruction)

1. `WebhookDelivery` composite index (migration `027`).

Everything else above is deliberately left as a documented finding rather than implemented, because each one either needs a coordinated frontend change (pagination), needs load-testing to size correctly (worker throttling), or is a larger architectural change (streaming upload ingestion) — none of which are "low-risk optimizations" in the sense this phase asked for.
