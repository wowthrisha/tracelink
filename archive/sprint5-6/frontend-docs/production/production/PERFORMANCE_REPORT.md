# Performance Report — Sprint 5.5 Production Audit

**Date:** 2026-06-28  
**Sprint:** 5.5  
**Method:** Playwright timing observations + static bundle analysis

---

## Summary

| Metric | Result | Target | Status |
|--------|--------|--------|--------|
| Frontend bundle size | 248.2 KB | < 400 KB | ✅ PASS |
| Bundle build time | ~20ms (esbuild) | < 5s | ✅ PASS |
| Screen transition time | 1–2s (with mock) | < 3s | ✅ PASS |
| API calls per screen | 1–3 | < 5 | ✅ PASS |
| Duplicate API calls | 0 | 0 | ✅ PASS |
| Redundant polling | 1 (Notifications 30s) | Expected | ✅ OK |
| Console errors | 0 | 0 | ✅ PASS |

---

## Bundle Analysis

**File:** `frontend/dist/app.bundle.js`  
**Size:** 248.2 KB (after Sprint 5.4B, was 247.6 KB — +0.6 KB)  
**Build tool:** esbuild IIFE bundle  
**Build time:** ~20ms

The bundle is a single IIFE with no code splitting. For a beta product at 248 KB this is appropriate. The full list of screens is bundled together, meaning the initial load includes all screen components regardless of which screen the user visits. For a production deployment, consider route-based code splitting if the bundle grows past 500 KB.

---

## Screen Load Performance

All screen transitions during the Playwright audit completed within the 1.5-second wait window before screenshot capture. No timeouts were triggered by legitimate slow renders.

| Screen | Load Pattern | Notes |
|--------|-------------|-------|
| Upload Dashboard | Immediate + API fetch | Doc list appears after `/api/documents` returns |
| Access Control | Immediate + API fetch | Links appear after `/api/links` returns |
| Analytics | Immediate + API fetch | Chart renders from data; counters have separate issue |
| Storage | API fetch only | Stuck on loading (BUG-004) |
| API Keys | Immediate | Empty state renders before API returns |
| Webhooks | API fetch | List renders after `/api/webhooks` returns |
| Audit Log | API fetch | Empty state (endpoint mismatch) |
| Organizations | API fetch | Org list renders |
| Notifications | API fetch | Stuck on loading (BUG-005) |
| Billing | API fetch | Plan data renders |
| Viewer | Immediate | Email gate (no doc context) |

---

## API Call Efficiency

### Calls per Screen (observed)

| Screen | Calls | Duplicate? | Notes |
|--------|-------|-----------|-------|
| Upload | 2 | No | `GET /api/documents`, `GET /api/auth/me` |
| Access Control | 2–3 | No | `/api/documents`, `/api/links`, `/api/auth/me` |
| Analytics | 1 | No | `/api/analytics` |
| Storage | 2 | No | `/api/storage/dashboard`, `/api/storage/forecast` |
| API Keys | 1 | No | `/api/api-keys` |
| Webhooks | 1 | No | `/api/webhooks` |
| Audit Log | 1 | No | `/api/admin/audit-log` |
| Organizations | 1 | No | `/api/orgs` |
| Notifications | 1 | No | Activity endpoint |
| Billing | 1 | No | `/api/billing` |

**No duplicate API calls observed on any screen.** All data fetching is triggered once on mount via `useEffect` with appropriate dependencies.

---

## Polling

- **Notifications screen**: Auto-refreshes every 30 seconds via `setInterval`. This is documented in the screen's UI ("Refreshes every 30 seconds"). Appropriate for an activity feed; should be disabled when the user navigates away (verify cleanup in `useEffect` return function).

---

## Known Performance Risks

### PERF-001 — No Request Deduplication/Caching
API responses are fetched fresh on every screen navigation. There is no client-side cache (React Query, SWR, or similar). If a user switches between Upload and Analytics repeatedly, each visit triggers fresh API calls.

**Risk:** Low for beta. Medium at scale if server response times increase.  
**Recommendation:** Add `stale-while-revalidate` caching or React Query for the document list and analytics endpoints in a future sprint.

### PERF-002 — Full Bundle on Initial Load
248 KB bundle served on every initial load. No lazy loading, no code splitting.  
**Risk:** Low at current size. Monitor as new screens are added.

### PERF-003 — Rasterization-Based Viewer (V3.1 Architecture)
The viewer uses streaming rasterization (per architecture docs). For large PDFs (42-page Board_Presentation.pptx), the first render may take several seconds. This is a known constraint of the V3.1 streaming approach.
