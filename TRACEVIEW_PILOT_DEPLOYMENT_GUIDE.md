# TraceView — Pilot Deployment Guide
## Railway + Cloudflare + Supabase Production Setup

**Version:** Phase D2.7  
**Status:** Launch-ready (1202/1202 tests passing)  
**Prerequisites:** Railway account, Cloudflare account, Supabase project, Cloudflare R2 bucket  

---

## Table of Contents

1. [Environment Variable Reference](#1-environment-variable-reference)
2. [Deployment Checklist](#2-deployment-checklist)
3. [Pilot Validation Checklist](#3-pilot-validation-checklist)
4. [Go-Live Checklist](#4-go-live-checklist)
5. [Rollback Checklist](#5-rollback-checklist)

---

## 1. Environment Variable Reference

### 1.1 Critical — Application will refuse to start without these in production

| Variable | Purpose | Default | Production Value | If Missing |
|----------|---------|---------|-----------------|-----------|
| `APP_ENV` | Controls startup guard mode and CORS policy | `development` | `production` | In development mode: no startup guards, CORS allows all origins. Pilot may start with incorrect config. |
| `APP_PUBLIC_BASE_URL` | Base URL embedded in every generated share link | `http://localhost:8000` | `https://your-domain.com` | All share links embed the wrong URL. Existing links break if this ever changes. Pilot cannot start without this. |
| `IP_HASH_SALT` | Salt for SHA-256 hashing of viewer IP addresses | `securedoc_ip_salt_change_in_production` | Random 64-char hex string | Default salt is predictable — IP hashes are effectively reversible. **Startup guard blocks production launch with default value.** |
| `SUPABASE_URL` | Supabase project URL for JWT verification | `""` (empty) | `https://<ref>.supabase.co` | All API calls return 401. App is unusable. **Startup guard blocks launch if empty in production.** |
| `SUPABASE_ANON_KEY` | Public Supabase key injected into frontend HTML | `""` (empty) | Supabase anon key | Frontend cannot initialise Supabase client. Login unavailable. |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://securedoc:password@localhost:5432/securedoc` | Railway Postgres internal URL | App fails to start. All DB operations fail. |
| `REDIS_URL` | Redis connection string for Celery + cache | `redis://localhost:6379/0` | Railway Redis internal URL | Celery workers unavailable. Document processing queued but never executed. |

### 1.2 Security — Required for correct IP-based features

| Variable | Purpose | Default | Production Value | If Missing |
|----------|---------|---------|-----------------|-----------|
| `REAL_IP_HEADER` | Header from which to read real client IP behind proxy | `""` (empty — use direct connection) | `CF-Connecting-IP` | **Rate limiting and IP allowlists operate on Cloudflare's edge IP, not the real user IP.** IP allowlists become completely ineffective. All users behind the same Cloudflare datacenter share a rate limit bucket. |
| `HTTPS_REDIRECT` | Redirect HTTP → HTTPS at application level | `false` | `true` | Plain HTTP requests reach the origin. Cloudflare handles TLS, so end-users still get HTTPS via the CDN, but direct origin access is unencrypted. Recommended: `true`. |
| `HSTS_MAX_AGE` | HTTP Strict Transport Security max-age in seconds | `0` (disabled) | `31536000` (1 year) | Browsers can be downgraded from HTTPS to HTTP via MITM. Set only after HTTPS is confirmed stable on your domain. Start with `86400` (1 day) for the first week. |

### 1.3 Storage — Required for document upload and serving

| Variable | Purpose | Default | Production Value | If Missing |
|----------|---------|---------|-----------------|-----------|
| `STORAGE_ENDPOINT_URL` | R2/S3 endpoint URL | `""` (AWS S3 default) | `https://<account-id>.r2.cloudflarestorage.com` | Storage uses AWS S3 instead of R2. Will fail if no AWS credentials. |
| `STORAGE_ACCESS_KEY_ID` | R2/S3 access key | `test_key` | R2 API token access key | Upload and download fail with AuthenticationError. |
| `STORAGE_SECRET_ACCESS_KEY` | R2/S3 secret key | `test_secret` | R2 API token secret | Upload and download fail with AuthenticationError. |
| `STORAGE_BUCKET_NAME` | R2/S3 bucket name | `securedoc-docs` | Your bucket name | Uploads go to wrong or non-existent bucket. |
| `STORAGE_REGION` | R2/S3 region | `us-east-1` | `auto` (for R2) | May cause signing errors with some R2 endpoints. |

### 1.4 Worker — Required for document processing performance

| Variable | Purpose | Default | Production Value | If Missing |
|----------|---------|---------|-----------------|-----------|
| `WORKER_CONCURRENCY` | Number of parallel Celery worker processes | `2` | `1` (Hobby) / `2` (Pro 4GB+) | At 2, two simultaneous large DOCX/PDF uploads can trigger OOM on containers with < 4 GB RAM. |
| `WORKER_MAX_TASKS_PER_CHILD` | Recycle worker process after N tasks | `0` (never) | `50` | Without recycling, Pillow + pdf2image + LibreOffice accumulate memory. Worker OOM-kills after ~100 documents on a typical deployment. |
| `WORKER_LOG_LEVEL` | Celery worker log verbosity | `info` | `info` | — |

### 1.5 Operational — Recommended for production visibility

| Variable | Purpose | Default | Production Value | If Missing |
|----------|---------|---------|-----------------|-----------|
| `ENABLE_JSON_LOGGING` | Emit structured JSON log lines (Grafana/Datadog/Loki) | `false` | `true` | Logs are human-readable text. Fine for pilot; switch to JSON when a log aggregator is attached. |
| `MAX_UPLOAD_MB` | Maximum document upload size in MB | `100` | `100` | — |
| `MAX_PAGES_PER_DOC` | Maximum pages rasterized per document | `500` | `500` | — |
| `MAX_DOWNLOAD_PAGES_PDF` | Maximum pages assembled in a watermarked PDF download | `100` | `100` | OOM risk for very large document downloads. |
| `RASTERIZER_TIMEOUT_SEC` | Hard timeout for pdf2image rasterization | `300` | `300` for PDF; consider `600` if serving large DOCX | Document stuck in "processing" if conversion exceeds limit. |
| `FREE_PLAN_DOC_LIMIT` | Maximum documents per free user | `10` | `10` | Pilot users have no upload limit. |
| `MAX_CONCURRENT_SESSIONS_PER_LINK` | Log warning above this many concurrent viewers | `50` | `50` | No enforcement; detection-only. |

### 1.6 Optional / Billing

| Variable | Purpose | Default |
|----------|---------|---------|
| `STRIPE_SECRET_KEY` | Stripe API key for billing | `""` — billing disabled |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification | `""` |
| `STRIPE_PRICE_ID_PRO` | Stripe Price ID for Pro plan | `""` |

### 1.7 Environment Variable Quick-Reference Card

```
# ── CRITICAL (required before first request) ──────────────────────────────────
APP_ENV=production
APP_PUBLIC_BASE_URL=https://your-domain.com
IP_HASH_SALT=<64-hex-chars — generate below>
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_ANON_KEY=<from Supabase dashboard>
DATABASE_URL=<Railway Postgres URL>
REDIS_URL=<Railway Redis URL>

# ── STORAGE ────────────────────────────────────────────────────────────────────
STORAGE_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
STORAGE_ACCESS_KEY_ID=<R2 access key>
STORAGE_SECRET_ACCESS_KEY=<R2 secret key>
STORAGE_BUCKET_NAME=securedoc-docs
STORAGE_REGION=auto

# ── SECURITY / PROXY ───────────────────────────────────────────────────────────
REAL_IP_HEADER=CF-Connecting-IP
HTTPS_REDIRECT=true
HSTS_MAX_AGE=86400

# ── WORKER ─────────────────────────────────────────────────────────────────────
WORKER_CONCURRENCY=1
WORKER_MAX_TASKS_PER_CHILD=50

# ── OBSERVABILITY ──────────────────────────────────────────────────────────────
ENABLE_JSON_LOGGING=true
```

**Generate IP_HASH_SALT:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## 2. Deployment Checklist

Work through these sections in order. Each section must be fully complete before proceeding to the next.

---

### Step 1 — Supabase Project

- [ ] **1.1** Log in to [supabase.com](https://supabase.com). Create a new project (free tier works for pilot).
- [ ] **1.2** Go to **Settings → API**. Copy:
  - `Project URL` → will become `SUPABASE_URL`
  - `anon / public` key → will become `SUPABASE_ANON_KEY`
- [ ] **1.3** Go to **Authentication → Providers**. Confirm **Email** provider is enabled. This is what users will use to log in.
- [ ] **1.4** Go to **Authentication → URL Configuration**. Set:
  - **Site URL**: `https://your-domain.com`
  - **Redirect URLs**: add `https://your-domain.com/**`
- [ ] **1.5** Note: you do NOT need Supabase Storage — TraceView uses Cloudflare R2 for document storage.

---

### Step 2 — Cloudflare R2 Storage

- [ ] **2.1** Log in to [cloudflare.com](https://cloudflare.com). Navigate to **R2 Object Storage**.
- [ ] **2.2** Create a bucket named `securedoc-docs` (or your chosen name).
- [ ] **2.3** In R2 settings, create an **API Token** with `Object Read & Write` permission scoped to your bucket.
  - Copy the **Access Key ID** → `STORAGE_ACCESS_KEY_ID`
  - Copy the **Secret Access Key** → `STORAGE_SECRET_ACCESS_KEY`
  - Copy the **Account ID** from the R2 overview page
- [ ] **2.4** Your `STORAGE_ENDPOINT_URL` will be:
  ```
  https://<your-account-id>.r2.cloudflarestorage.com
  ```
- [ ] **2.5** Set `STORAGE_REGION=auto` (not `us-east-1` — R2 uses `auto`).
- [ ] **2.6** Verify: the bucket exists and the API token has write access. You can test with `aws s3 ls s3://securedoc-docs --endpoint-url <endpoint>` using the credentials.

---

### Step 3 — Railway Project

- [ ] **3.1** Log in to [railway.app](https://railway.app). Create a new **Project**.
- [ ] **3.2** Add a **PostgreSQL** service. Railway provisions a managed Postgres database.
  - In the Postgres service, go to **Connect** → **Internal URL**. This is your `DATABASE_URL`.
  - Format: `postgresql://postgres:<password>@<host>.railway.internal:5432/railway`
- [ ] **3.3** Add a **Redis** service. Railway provisions a managed Redis instance.
  - In the Redis service, go to **Connect** → **Internal URL**. This is your `REDIS_URL`.
  - Format: `redis://default:<password>@<host>.railway.internal:6379`
- [ ] **3.4** Deploy the **API service** from the repository:
  - Select your repository and branch (`phase-d2-docx-pipeline` before merge, then `main`).
  - Railway auto-detects the `Dockerfile`.
  - **Override the start command** in Railway service settings: leave empty (the Dockerfile CMD handles it).
- [ ] **3.5** Deploy the **Worker service** from the same repository:
  - Create a second service pointing at the same repo.
  - **Override the start command** in Railway settings:
    ```
    sh -c "celery -A app.workers.celery_app worker --loglevel=info --concurrency=${WORKER_CONCURRENCY:-1} ${WORKER_MAX_TASKS_PER_CHILD:+--max-tasks-per-child=$WORKER_MAX_TASKS_PER_CHILD}"
    ```
  - This service also runs `entrypoint.sh` first (migrations) then the celery command.
- [ ] **3.6** Deploy the **Beat service** (periodic task scheduler) from the same repo:
  - **Override start command**:
    ```
    celery -A app.workers.celery_app beat --loglevel=info
    ```
  - This runs the purge-stale-sessions (every 30 min) and requeue-orphaned-uploads (every 5 min) tasks.
  - **Important:** Only one Beat instance must run. Never scale this service above 1 replica.

---

### Step 4 — Environment Variables on Railway

Set these in the Railway service settings for **both the API and Worker services** (share a Railway "Shared Variables" group if available):

- [ ] **4.1** Set all Critical variables from §1.7 above.
- [ ] **4.2** Generate and set `IP_HASH_SALT`:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
  Copy the output. Treat it as a secret — never share it.
- [ ] **4.3** Set `DATABASE_URL` to the Railway Postgres **internal** URL (not the public URL — internal is faster and free of charge).
- [ ] **4.4** Set `DATABASE_PUBLIC_URL` to the Railway Postgres **public** URL. This is used only when running migrations from your local machine.
- [ ] **4.5** Set `REDIS_URL` to the Railway Redis internal URL.
- [ ] **4.6** Confirm: Railway service → **Variables** tab shows all entries from §1.7.

---

### Step 5 — First Deployment and Migration

- [ ] **5.1** Trigger a deployment on the API service (Railway auto-deploys on push, or click **Deploy** manually).
- [ ] **5.2** Monitor the **Deployment Logs** for:
  ```
  [entrypoint] Running database migrations ...
  [entrypoint] Migrations complete.
  INFO: Application startup complete.
  ```
- [ ] **5.3** If migrations fail, check `DATABASE_URL` is correct and the Postgres service is running.
- [ ] **5.4** Once the API service shows green (healthy), open:
  ```
  https://<your-service>.railway.app/health
  ```
  Expected response:
  ```json
  {
    "status": "ok",
    "checks": {
      "db": "ok",
      "redis": "ok",
      "storage": "StorageService",
      "worker": "ok"
    },
    "version": "8.1.0"
  }
  ```
- [ ] **5.5** If `worker` shows `no_workers_detected`, the Worker service has not started yet. Wait 30 seconds and retry.
- [ ] **5.6** If `redis` shows `error`, check `REDIS_URL` in the service variables.
- [ ] **5.7** If `storage` shows `error`, check `STORAGE_*` variables.

---

### Step 6 — Custom Domain and Cloudflare DNS

- [ ] **6.1** In Railway, go to your API service → **Settings → Domains**. Add your custom domain (e.g. `secure.yourdomain.com`).
  - Railway provides a CNAME target (e.g. `<hash>.railway.app`).
- [ ] **6.2** In Cloudflare DNS, add a **CNAME record**:
  - Name: `secure` (or your chosen subdomain)
  - Target: the Railway CNAME value
  - Proxy: **Orange cloud (Proxied)** — this enables Cloudflare TLS and `CF-Connecting-IP`
- [ ] **6.3** Wait for DNS propagation (typically < 5 minutes with Cloudflare).
- [ ] **6.4** Verify the domain resolves and returns HTTPS:
  ```bash
  curl -I https://secure.yourdomain.com/health
  ```
  Expected: `HTTP/2 200`
- [ ] **6.5** Update `APP_PUBLIC_BASE_URL` in Railway environment variables:
  ```
  APP_PUBLIC_BASE_URL=https://secure.yourdomain.com
  ALLOWED_ORIGINS=https://secure.yourdomain.com
  ```
- [ ] **6.6** Redeploy the API service to apply the new `APP_PUBLIC_BASE_URL`. **This is critical** — all share links created before this change will embed the wrong URL.

---

### Step 7 — SSL Certificate Verification

- [ ] **7.1** Cloudflare issues the SSL certificate automatically when the CNAME is proxied. Verify:
  ```bash
  curl -sv https://secure.yourdomain.com/health 2>&1 | grep -E "SSL|certificate|issuer"
  ```
  Expected: certificate issued by Cloudflare, valid.
- [ ] **7.2** Confirm HTTPS enforced — set `HTTPS_REDIRECT=true` in Railway variables and redeploy.
- [ ] **7.3** Test that HTTP redirects to HTTPS:
  ```bash
  curl -I http://secure.yourdomain.com/health
  ```
  Expected: `HTTP/1.1 301 Moved Permanently` redirecting to `https://`.
- [ ] **7.4** In Cloudflare SSL/TLS settings: set **SSL/TLS encryption mode** to **Full (strict)** to prevent MITM between Cloudflare and Railway.

---

### Step 8 — Worker Verification

- [ ] **8.1** Upload a small test PDF via the frontend at `https://secure.yourdomain.com/app`.
- [ ] **8.2** Check the Worker service logs in Railway for:
  ```
  Document <uuid>: status → processing
  Document <uuid>: rasterized N page(s)
  Document <uuid>: status → ready (N pages)
  ```
- [ ] **8.3** Call the status endpoint (with a valid auth token):
  ```bash
  curl -H "Authorization: Bearer <token>" \
       https://secure.yourdomain.com/api/documents/<doc-id>/status
  ```
  Expected: `{"status": "ready", "page_count": N}`
- [ ] **8.4** If the document stays in `uploaded` or `processing`, check:
  - Worker service is running and connected to the same Redis URL.
  - Beat service is running (requeue-orphaned-uploads fires every 5 minutes).
  - Worker logs for errors.

---

### Step 9 — Storage Verification

- [ ] **9.1** After a successful document upload and processing, go to Cloudflare R2 → `securedoc-docs` bucket.
- [ ] **9.2** Confirm the following paths exist in the bucket:
  - `originals/<doc-id>.pdf` — the original upload
  - `pages/<doc-id>/0001.webp` — the first rasterized page
  - `thumbs/<doc-id>/0001.webp` — the first thumbnail
  - (For DOCX with headings) `toc/<doc-id>.json` — the heading TOC sidecar
- [ ] **9.3** Test download: in the app, create a share link with `can_download=true`, open the viewer as the recipient, and click download. A watermarked PDF should download.

---

### Step 10 — Cloudflare Security Settings

- [ ] **10.1** Cloudflare → **Security → Bot Fight Mode**: Enable **Super Bot Fight Mode** if on Pro plan, or enable standard **Bot Fight Mode** on Free.
- [ ] **10.2** Cloudflare → **Security → WAF**: No special rules needed (the app handles its own rate limiting). If you want an extra layer, add a rate-limit rule for `/api/viewer/validate` at ≥ 50 req/min/IP.
- [ ] **10.3** Cloudflare → **Caching**: Set a Page Rule or Cache Rule for `/static/*.js` → Cache Level: Standard (the app already sends appropriate `Cache-Control` headers). Leave viewer API routes (`/api/*`) with **Bypass** caching.
- [ ] **10.4** Cloudflare → **SSL/TLS → Edge Certificates**: Confirm **Always Use HTTPS** is enabled.

---

## 3. Pilot Validation Checklist

Run these tests manually before declaring the pilot open. Use two browser profiles: one as the **document owner** (Supabase authenticated) and one as the **viewer** (no account required).

---

### Test P-01 — PDF Upload and Rendering

**Steps:**
1. Log in as owner at `/app`.
2. Click **Upload Document**. Select a multi-page PDF (≥ 3 pages, < 100 MB).
3. Wait for status to change from `Processing...` to the page count.
4. Click the document to open the viewer.

**Expected:**
- Status shows "ready" within 60 seconds for a typical 10-page PDF.
- Page 1 renders as an image (not text, not a PDF embed).
- Page navigation arrows advance through pages.
- Thumbnail sidebar shows small page previews.

**Pass criteria:** All pages render, thumbnails load, no console errors.

---

### Test P-02 — DOCX Upload and Visual Fidelity

**Steps:**
1. Upload a DOCX file with text, at least one table, and at least two heading levels.
2. Wait for processing to complete.
3. Open the viewer.

**Expected:**
- Document renders as page images (same viewer as PDF).
- Table formatting is preserved in the rendered pages.
- Heading hierarchy is visible.
- Thumbnail sidebar works.

**Pass criteria:** Document renders as images. Formatting roughly matches original. No "Document processing failed" error.

---

### Test P-03 — Visible Watermark

**Steps:**
1. Open a processed document in the viewer.
2. Create a share link with no password.
3. Open the share link in an incognito browser window. Enter an email address when prompted (or enter no email if not required).
4. Navigate to page 1.

**Expected:**
- A diagonal watermark is visible across the page with format: `<email> · <date> · sess:<6 chars>`
- The watermark is different on a second session (different 6-char session prefix).
- Screenshots of the page retain the watermark.

**Pass criteria:** Watermark visible on every page. Two different sessions produce visually different watermarks.

---

### Test P-04 — DOCX TOC Navigation

**Steps:**
1. Upload a DOCX with multiple heading levels (Heading 1, Heading 2, Heading 3) on different pages.
2. Once processed, open the viewer.
3. Click the **Table of Contents** button/tab.

**Expected:**
- Heading titles appear in a hierarchical list.
- Headings with matching PDF bookmarks show page numbers and are clickable — clicking jumps to the correct page.
- Headings without page numbers (if any) appear as outline entries without navigation.

**Pass criteria:** At least one TOC entry navigates to the correct page. No page-1 fallback for all entries.

**Known limitation:** If LibreOffice does not emit PDF bookmarks for this specific DOCX (unusual heading definitions, protected document), TOC entries appear without navigation. This is graceful degradation, not a failure.

---

### Test P-05 — Share Link Creation and Access

**Steps:**
1. Open a ready document. Click **Share**.
2. Create a link with no restrictions (default settings). Copy the share URL.
3. Open the URL in a fresh browser (no login required).

**Expected:**
- Viewer loads without requiring Supabase login.
- Document renders correctly for the anonymous viewer.
- The share URL format is `https://secure.yourdomain.com/v/<token>`.

**Pass criteria:** Share link works. URL contains your production domain, not `localhost` or a Cloudflare tunnel URL.

---

### Test P-06 — Link Expiration

**Steps:**
1. Create a share link with an expiration time of 1 minute from now.
2. Open the link immediately. Verify it works.
3. Wait 2 minutes. Open the link again.

**Expected:**
- Before expiry: viewer loads normally.
- After expiry: page shows "Link expired" or HTTP 410 response.

**Pass criteria:** Link correctly expires and denies access after the expiry time.

---

### Test P-07 — Password Protection

**Steps:**
1. Create a share link with password `TestPass123!`.
2. Open the link in a fresh browser.
3. Enter an incorrect password. Then enter the correct password.

**Expected:**
- Gate page shows a password field.
- Wrong password returns an error: "Incorrect password".
- Correct password grants access to the viewer.

**Pass criteria:** Wrong password denied. Correct password accepted. Document renders after successful auth.

---

### Test P-08 — Email Restriction

**Steps:**
1. Create a share link restricted to `allowed@example.com` (email allowlist, not domain).
2. Open the link in fresh browser. Enter a different email (`other@gmail.com`).
3. Open the link again. Enter `allowed@example.com`.

**Expected:**
- Disallowed email: access denied with an appropriate message.
- Allowed email: viewer loads normally.

**Pass criteria:** Disallowed email blocked. Allowed email granted access.

---

### Test P-09 — IP Allowlist

**Steps:**
1. Find your current IP address (e.g. `curl ifconfig.me`). Note it as `YOUR_IP`.
2. Create a share link with IP allowlist set to a different IP (e.g. `192.168.99.99`).
3. Try to open the link from your current IP.

**Expected:**
- Access denied with "Access denied from this IP" or HTTP 403.

**Pass criteria:** Access blocked from non-allowlisted IP.

**Note:** Only test this if `REAL_IP_HEADER=CF-Connecting-IP` is set. Without it, IP allowlists use the Cloudflare edge IP (shared by many users) and the test is meaningless.

---

### Test P-10 — View Count Limit

**Steps:**
1. Create a share link with `max_views = 2`.
2. Open the link. Validate (1st view).
3. Open the link again. Validate (2nd view).
4. Open the link a third time.

**Expected:**
- Views 1 and 2: access granted.
- View 3: link shows as expired/max-views-reached.

**Pass criteria:** Third access denied after max_views is reached.

---

### Test P-11 — Link Revocation

**Steps:**
1. Create a share link. Open it and verify it works (viewer loads).
2. Back in the owner dashboard, revoke the link.
3. Refresh the viewer page for the revoked link.

**Expected:**
- After revocation: any new request to the revoked link returns 410 Gone.
- The revocation takes effect within 10 seconds (link cache TTL).

**Pass criteria:** Revoked link returns 410 within 10 seconds of revocation.

---

### Test P-12 — Download Controls

**Steps (download disabled):**
1. Create a share link with `can_download = false` (default).
2. Open the viewer. Try to access `/api/viewer/download/<token>?session_id=<sid>` directly.
3. Expected: HTTP 403 "Download not permitted on this link".

**Steps (download enabled):**
1. Create a share link with `can_download = true`.
2. Open the viewer. Use the download button.
3. Expected: A watermarked PDF downloads. The watermark text reads `downloaded · <date> · sess:<6 chars>`.

**Pass criteria:** Disabled download returns 403. Enabled download returns a valid watermarked PDF.

---

### Test P-13 — Analytics and Access Log

**Steps:**
1. Open a share link. Navigate to pages 1, 2, 3.
2. As the document owner, go to **Analytics → Access Log** for the document.

**Expected:**
- `opened` event appears with the viewer's email (or "anonymous") and a hashed IP.
- `page_viewed` events appear for pages 1, 2, 3.
- No raw IP addresses are logged (only SHA-256 hashes).

**Pass criteria:** Events visible in analytics. No raw IP addresses in any response.

---

### Test P-14 — Text Document (TXT)

**Steps:**
1. Upload a `.txt` file with 5+ lines.
2. Wait for processing.
3. Open the viewer.

**Expected:**
- Document displayed as text (not images).
- No thumbnail sidebar (text documents don't have page thumbnails).
- Content readable without rendering delay.

**Pass criteria:** Text content displays correctly. No 404 or 503 errors.

---

### Test P-15 — Health Endpoint

**Steps:**
1. Call `GET https://secure.yourdomain.com/health`.

**Expected:**
```json
{
  "status": "ok",
  "checks": {
    "db": "ok",
    "redis": "ok",
    "storage": "StorageService",
    "worker": "ok"
  },
  "version": "8.1.0"
}
```

**Pass criteria:** All checks show `"ok"`. If any check is `"error"` or `"no_workers_detected"`, investigate before declaring pilot open.

---

## 4. Go-Live Checklist

Complete this checklist immediately before sending the first share link to a real user.

### Infrastructure
- [ ] `GET /health` returns `{"status": "ok"}` with all checks passing.
- [ ] Upload a test PDF. Confirm processing completes in < 60 seconds.
- [ ] `APP_PUBLIC_BASE_URL` is set to the stable production domain (not localhost, not a Cloudflare tunnel URL).
- [ ] `APP_ENV=production` is confirmed in Railway variables.
- [ ] `IP_HASH_SALT` is set to a randomly generated 64-char hex string (not the default placeholder).
- [ ] `REAL_IP_HEADER=CF-Connecting-IP` is confirmed set (for Cloudflare deployments).
- [ ] `WORKER_MAX_TASKS_PER_CHILD=50` is confirmed set on the Worker service.

### Security
- [ ] HTTPS confirmed working at production domain.
- [ ] `HTTPS_REDIRECT=true` is set and HTTP requests redirect to HTTPS.
- [ ] Cloudflare proxy (orange cloud) is active on the DNS record.
- [ ] Cloudflare SSL mode is **Full (strict)**.
- [ ] `.env` file is NOT committed to git (confirm with `git ls-files | grep ".env"`).

### Access Control Validation
- [ ] IP allowlist test (P-09) passes.
- [ ] Email restriction test (P-08) passes.
- [ ] Password protection test (P-07) passes.
- [ ] Link revocation test (P-11) passes.
- [ ] Link expiration test (P-06) passes.

### Data
- [ ] Test databases (`*.db`) are not present in the deployed container (they are created locally by tests and gitignored — confirm Docker image doesn't include them).
- [ ] R2 bucket has no test documents from development. Either clear the bucket or use a dedicated production bucket.

### Limits
- [ ] `FREE_PLAN_DOC_LIMIT=10` is set to a reasonable value for the pilot.
- [ ] Upload rate limit (10/minute) is acceptable for expected pilot volume.

### Monitoring
- [ ] Railway service → **Deployments** tab is bookmarked for monitoring.
- [ ] Railway service → **Logs** tab is accessible for debugging.
- [ ] `ENABLE_JSON_LOGGING=true` is set if you have a log aggregator (optional for pilot).

---

## 5. Rollback Checklist

If the pilot encounters a critical failure and the system needs to be reverted.

### Immediate triage (first 5 minutes)

- [ ] **Check health endpoint**: `curl https://secure.yourdomain.com/health`
  - `db: error` → PostgreSQL connection lost. Check Railway Postgres service status.
  - `redis: error` → Redis connection lost. Check Railway Redis service status.
  - `worker: no_workers_detected` → Celery worker crashed. Check Worker service logs on Railway.
  - `storage: error` → R2 endpoint unreachable. Check Cloudflare R2 status.

- [ ] **Check API logs**: Railway → API service → Logs. Look for startup errors or Python exceptions.

- [ ] **Check worker logs**: Railway → Worker service → Logs. Look for task errors or OOM kills.

### Code rollback (if the issue is in the application code)

- [ ] Identify the last known-good commit (e.g. `Phase D2.6 production readiness fixes`).
  ```bash
  git log --oneline
  ```
- [ ] Deploy the known-good commit via Railway:
  - Railway → Service → **Deployments** → select the previous successful deployment → **Redeploy**.
  - OR: `git revert <bad-commit>` and push to trigger a new deployment.
- [ ] **Do not run `git reset --hard` on a shared branch without confirming with the team.**

### Configuration rollback

If the issue is caused by a bad environment variable change:
- [ ] Railway → Service → **Variables** → identify the changed variable.
- [ ] Restore the previous value.
- [ ] Railway auto-redeploys on variable change.

### Database rollback

**Only if a migration caused the failure:**
- [ ] Railway → Postgres service → connect with `psql` via the public URL.
- [ ] Identify the failed migration:
  ```sql
  SELECT version_num FROM alembic_version;
  ```
- [ ] Roll back one migration:
  ```bash
  alembic downgrade -1
  ```
  This is destructive — only perform if the migration is confirmed as the cause.
- [ ] **Note:** Alembic downgrades are not always reversible (e.g. dropped columns cannot be recovered without a backup). Check the migration's `downgrade()` function first.

### Data recovery

- [ ] Document files are stored in Cloudflare R2 and are NOT deleted by a code rollback.
- [ ] PostgreSQL data is managed by Railway's Postgres service. Enable **automatic backups** in Railway (Pro plan feature) before go-live.
- [ ] In an emergency, export the database via Railway's backup tool or:
  ```bash
  pg_dump <DATABASE_PUBLIC_URL> > backup.sql
  ```

### Communication

- [ ] Notify pilot users if the service will be unavailable for more than 5 minutes.
- [ ] Share link URLs remain valid after a code rollback (tokens are in the database, not in application code).

---

## Quick Reference

### Service URLs
| Service | URL |
|---------|-----|
| App | `https://secure.yourdomain.com/app` |
| API Docs | `https://secure.yourdomain.com/docs` |
| Health | `https://secure.yourdomain.com/health` |
| Share link | `https://secure.yourdomain.com/v/<token>` |

### Rate Limits (per IP, per minute)
| Endpoint | Limit |
|----------|-------|
| `POST /api/documents/upload` | 10/min |
| `POST /api/viewer/validate` | 20/min |
| `GET /api/viewer/page/{token}/{page}` | 120/min |
| `GET /api/viewer/thumb/{token}/{page}` | 300/min |
| `GET /api/viewer/toc/{token}` | 60/min |
| `GET /api/viewer/download/{token}` | 10/min |
| `GET /api/viewer/text/{token}/{chunk}` | 120/min |
| `POST /api/analytics/events` | 60/min |

### Supported File Formats
| Format | Pipeline | Viewer | TOC |
|--------|---------|--------|-----|
| PDF | Rasterise → WebP pages | Image viewer | PDF bookmarks |
| DOCX | LibreOffice → PDF → Rasterise | Image viewer | DOCX headings + PDF bookmarks |
| TXT / MD / LOG | Text decode | Text viewer | Heuristic headings |
| DOC | antiword → text | Text viewer | Heuristic headings |

### Free Plan Limits (pilot defaults)
| Resource | Limit |
|----------|-------|
| Documents per user | 10 |
| Max upload size | 100 MB |
| Max pages per document | 500 |
| Max download pages | 100 |
