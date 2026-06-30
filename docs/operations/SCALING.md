# SecureDoc Scaling Guide

## Current Architecture Limits

| Component | Current Default | Bottleneck |
|-----------|----------------|------------|
| API workers (uvicorn) | 1 process, async | CPU-bound endpoints |
| Celery workers | 2 processes | PDF rasterization RAM |
| DB pool | 10 + 20 overflow | Connection exhaustion |
| Redis | Single instance | Memory |

## Scaling Tiers

### Tier 1: 1–10 concurrent users

Default configuration. Single API instance, 2 Celery workers, shared PostgreSQL.

```
API: 1 × uvicorn (1 CPU, 512MB RAM)
Worker: 2 × celery processes (2 CPU, 4GB RAM)
DB: shared PostgreSQL (2 CPU, 4GB RAM)
Redis: shared (512MB RAM)
```

### Tier 2: 10–100 concurrent users

```bash
# Scale API horizontally (stateless — safe to scale freely)
docker compose scale api=4

# Scale workers based on upload volume
# Rule: 1 worker per 5 simultaneous uploads
docker compose scale worker=4  # ~20 concurrent uploads

# Increase DB pool to handle more connections
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Upgrade Redis to 2GB for page cache
# Target: cache stores ~500 pages × 100KB avg = 50MB
# With 2GB and LRU eviction: caches ~20,000 pages
```

### Tier 3: 100–500 concurrent users

```bash
# API: 8+ uvicorn workers behind load balancer
# Use gunicorn with uvicorn workers:
gunicorn app.main:app -w 8 -k uvicorn.workers.UvicornWorker

# Workers: scale based on queue depth
# Monitor: redis-cli LLEN celery
# Add workers when queue depth > 50 consistently
WORKER_CONCURRENCY=4  # per worker container
# Scale to 4 worker containers = 16 concurrent processing jobs

# Database: read replica for analytics queries
# Route GET /api/analytics/* to read replica

# Redis: Redis Cluster or Redis Sentinel for HA
```

### Tier 4: 500–1000+ concurrent users

```
API: Kubernetes + HPA (scale on CPU > 70% or request queue > 20)
Workers: Kubernetes + KEDA (scale on Celery queue depth)
Database: PostgreSQL + PgBouncer connection pooler
Redis: Redis Cluster (3 primary + 3 replica shards)
CDN: Enable CDN_THUMBNAIL_ENABLED=true (offloads 60% of bandwidth)
```

## Bottleneck Identification

### CPU Bottleneck (API)

```bash
# Check CPU usage per process
top -p $(pgrep -d, uvicorn)

# Profile slow endpoints via Prometheus
# Query: histogram_quantile(0.99, securedoc_http_request_duration_seconds_bucket)
# If /api/documents/upload is slow: pre-validate file size before storage upload
```

### Memory Bottleneck (Workers)

```bash
# PDF rasterization uses 200MB–4GB per job depending on page count
# Monitor: docker stats securedoc-worker
# Solution: limit WORKER_MAX_TASKS_PER_CHILD=5 to recycle RAM more aggressively
# Or: limit MAX_PAGES_PER_DOC to reduce peak memory
```

### Database Bottleneck

```bash
# Check slow queries
psql $DATABASE_URL -c "
  SELECT query, calls, mean_exec_time, total_exec_time
  FROM pg_stat_statements
  ORDER BY total_exec_time DESC
  LIMIT 10;
"

# Check connection pool exhaustion
psql $DATABASE_URL -c "
  SELECT count(*), state FROM pg_stat_activity GROUP BY state;
"
# If 'idle in transaction' is high: reduce DB_POOL_TIMEOUT
# If 'active' hits max_connections: add PgBouncer
```

### Redis Bottleneck

```bash
# Check memory usage
redis-cli info memory | grep used_memory_human

# Check eviction rate (should be near 0 for page cache efficiency)
redis-cli info stats | grep evicted_keys

# Check cache hit rate
# Prometheus: securedoc_cache_hits_total / (hits + misses)
```

## Horizontal Scaling Considerations

The API is fully stateless — all shared state is in PostgreSQL + Redis. Safe to run N instances behind any load balancer.

**Celery workers** are also stateless. Beat scheduler must run as a single instance (use Kubernetes leader election or `celery-redbeat`).

**No sticky sessions required** — session validation uses DB lookup per request (cached in-process).

## CDN Configuration (Performance Multiplier)

```bash
# Enable presigned thumbnail URLs (bypasses API for thumbnails)
CDN_THUMBNAIL_ENABLED=true
CDN_THUMBNAIL_PRESIGN_TTL_SEC=300  # 5-minute presigned URLs

# Configure Cloudflare (or equivalent) to:
# - Cache /static/* with long TTL (CSS/JS assets are versioned)
# - Pass-through /api/* (no caching)
# - Pass-through /v/* (dynamic viewer, no caching)
```

With CDN enabled, thumbnail requests (often 60% of viewer traffic) bypass the API entirely, reducing API load proportionally.
