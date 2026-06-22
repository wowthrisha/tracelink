# Storage Screen Root Cause Analysis
Date: 2026-06-22
Status: Fixed. Build and tests pass.
Symptoms: `0 B · undefined docs` in header, empty table, toast "Failed to construct 'URL': Invalid URL"

---

## A. Exact Line Throwing "Failed to construct 'URL': Invalid URL"

**File:** `frontend/api.js:182` (before fix)

```javascript
async getStorageDashboard(orgId = null) {
  const url = new URL(`${API_BASE}/api/storage/dashboard`);  // ← throws here
  if (orgId) url.searchParams.set('org_id', orgId);
  const r = await fetch(url, { headers: { ...authHeaders() } });
  ...
}
```

### Why it throws

`API_BASE` is determined at module load time (`api.js:18–24`):

```javascript
const API_BASE = _explicitBase || (() => {
  const port = window.location.port;
  if (port === '5500' || port === '5501') {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }
  return '';  // ← same-origin production path
})();
```

In **production** (Railway / Cloudflare), the app is served from port 443 (HTTPS). `port` is `''`, so `API_BASE = ''`.

The call becomes:
```javascript
const url = new URL('' + '/api/storage/dashboard');
// ≡ new URL('/api/storage/dashboard')
```

`new URL()` with a single argument requires a complete absolute URL. A bare path `/api/storage/dashboard` is not a valid absolute URL. The browser throws synchronously:

```
TypeError: Failed to construct 'URL': Invalid URL
```

This propagates through `Promise.all([...]).catch(e => toast(_errMsg(e, ...), 'error'))` (`StorageScreen.jsx:42`), which is why the toast shows the exact constructor error text.

### Why it only fails in production, not locally

In **local dev**, `port === '5500'` or `'5501'`, so `API_BASE = 'http://localhost:8000'`. The call becomes:
```javascript
new URL('http://localhost:8000/api/storage/dashboard')  // valid absolute URL — works fine
```

This means the storage screen has **never functioned in production**. It works in local development only.

### Why every other function is unaffected

Every other API function in `api.js` uses `fetch()` directly with a template string:
```javascript
const r = await fetch(`${API_BASE}/api/storage/forecast`, ...);
// → fetch('/api/storage/forecast', ...)  — fetch() handles relative paths fine
```

`getStorageDashboard` is the only function that used the `URL` constructor, presumably to leverage `URLSearchParams` for the optional `org_id` query parameter.

---

## B. Why document_count Becomes "undefined docs"

**File:** `frontend/src/screens/StorageScreen.jsx:74` (before fix)

```jsx
{ label: 'Total Storage', ..., sub: `${dashboard?.document_count} docs`, ... }
```

When `getStorageDashboard()` throws at the `URL` constructor, `Promise.all` rejects. The `.catch` fires and the `.finally` sets `loading = false`. Neither `dashboard` nor `forecast` state is updated — they remain `null` (their initial value from `useState(null)`).

With `dashboard = null`:
- `dashboard?.document_count` → `undefined` (optional chain on null)
- Template literal `${undefined}` → the string `"undefined"`
- Rendered text → `"undefined docs"`

Note the inconsistency with the header line (`StorageScreen.jsx:66`):
```jsx
{fmtBytes(totalBytes)} used · {dashboard?.document_count || 0} documents
```
Line 66 has a `|| 0` fallback, so it correctly shows `"0 documents"`. Line 74 has no fallback.

---

## C. Is the Backend Response Malformed or Is the Frontend Parser Incorrect?

**The backend is correct. The error never reaches the backend.**

The `URL` constructor throws **synchronously**, before any network request is made. `fetch()` is never called. The backend receives no request.

Backend response schema (from `backend/app/routers/storage.py:91–103`) is well-formed:

```json
{
  "total_bytes": 0,
  "total_mb": 0.0,
  "document_count": 0,
  "active_count": 0,
  "archived_count": 0,
  "expired_count": 0,
  "by_document": [],
  "by_org": []
}
```

All fields that `StorageScreen.jsx` reads (`total_bytes`, `document_count`, `by_document`, `by_org`) are present and correctly named. No schema mismatch exists.

---

## D. Has This Screen Ever Worked?

**No, not in production. Yes, in local development.**

The screen renders correctly in any environment where `API_BASE` is a full URL (local dev with `port === '5500'` or `'5501'`). It has never functioned in any production deployment where `API_BASE = ''` (same-origin mode).

The `getStorageForecast` call (`StorageScreen.jsx:40`) also fails as a secondary consequence: `Promise.all` rejects on the first rejection, so the forecast fetch is also abandoned (or its result is discarded). The error message shown in the toast comes from the `URL` constructor throw.

---

## Verification

### Actual API response payload

Not receivable in production because the request is never sent. In local dev, `GET /api/storage/dashboard` returns:

```json
{
  "total_bytes": <sum of storage_bytes_computed or file_size_bytes>,
  "total_mb": <rounded>,
  "document_count": <count of non-deleted documents>,
  "active_count": <count>,
  "archived_count": <count>,
  "expired_count": <count>,
  "by_document": [{ "id", "filename", "lifecycle_state", "retention_policy", "expires_at", "storage_bytes", ... }],
  "by_org": [{ "org_id", "total_bytes", "total_mb" }]
}
```

### Actual frontend state after fetch (production, before fix)

```
dashboard: null     (never set — Promise.all rejected before setState)
forecast:  null     (same reason)
loading:   false    (set by finally())
```

### Exact failing stack trace

```
TypeError: Failed to construct 'URL': Invalid URL
    at new URL (<anonymous>)
    at Object.getStorageDashboard (api.js:182)
    at StorageScreen.jsx:39   [Promise.all([getStorageDashboard(), ...])]
```

The error is caught by `.catch(e => toast(_errMsg(e, 'Failed to load storage data'), 'error'))` at `StorageScreen.jsx:42`. `_errMsg` receives a `TypeError` object — since `TypeError` has no `.detail` property, `_errMsg` falls back to `e.message`, which is the browser's constructor error string.

---

## The Fix

### Fix 1 — api.js:181–188 (critical — crash)

**Before:**
```javascript
async getStorageDashboard(orgId = null) {
  const url = new URL(`${API_BASE}/api/storage/dashboard`);
  if (orgId) url.searchParams.set('org_id', orgId);
  const r = await fetch(url, { headers: { ...authHeaders() } });
  if (r.status === 401) { _clearAndReload(); return; }
  if (!r.ok) throw await r.json();
  return r.json();
},
```

**After:**
```javascript
async getStorageDashboard(orgId = null) {
  const qs = orgId ? `?org_id=${encodeURIComponent(orgId)}` : '';
  const r = await fetch(`${API_BASE}/api/storage/dashboard${qs}`, { headers: { ...authHeaders() } });
  if (r.status === 401) { _clearAndReload(); return; }
  if (!r.ok) throw await r.json();
  return r.json();
},
```

Replaces `new URL()` with the same `fetch(template-string)` pattern used by every other function in api.js. `encodeURIComponent` handles the `org_id` query parameter. The `URL` constructor is no longer used anywhere in api.js.

### Fix 2 — StorageScreen.jsx:74 (secondary — display)

**Before:**
```jsx
sub: `${dashboard?.document_count} docs`
```

**After:**
```jsx
sub: `${dashboard?.document_count ?? 0} docs`
```

Adds `?? 0` fallback so any future error state (or a zero-doc account) renders `"0 docs"` instead of `"undefined docs"`. Uses `??` (nullish coalescing) rather than `||` so an explicit `0` document count is not coerced.

---

## Verification Checklist (after fix)

| Check | Result |
|---|---|
| `npm run build` | ✅ `dist/app.bundle.js  202.5kb` (11ms) |
| `npm test` | ✅ 13/13 passed |
| `new URL()` usage in api.js | ✅ Zero — confirmed with `grep -n "new URL(" api.js` (no output) |
| `getStorageForecast` pattern | ✅ Already correct — uses `fetch(template-string)` |
| `updateRetention` pattern | ✅ Already correct — uses `fetch(template-string)` |
| Backend storage router registered | ✅ `app.include_router(storage_router.router)` at `main.py:237` |
| Backend response schema match | ✅ All fields consumed by StorageScreen are present in response |
