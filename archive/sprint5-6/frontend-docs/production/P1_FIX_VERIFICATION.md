# P1 Fix Verification Report — Sprint 4.6E
Date: 2026-06-22
Scope: All actionable P1 items from REMAINING_BUG_BACKLOG.md and TOP_20_FIXES_BEFORE_BETA.md
Result: 3 of 5 P1 items fixed and pushed. 2 deferred by explicit user instruction.

---

## Deferred by User Instruction

| ID | Item | Reason |
|---|---|---|
| BUG-002 | No frontend for Webhooks | User: "Do not start Webhooks UI" |
| BUG-003 | No frontend for API Keys | User: "Do not start API Keys UI" |

---

## FIX-1: BUG-004 — AccessLog wrong argument order

**Commit**: `cc782c3`
**Status**: FIXED AND PUSHED

### Root Cause
`AccessLog.jsx` called `window.SecureDocAPI.getEvents(docId, 50)`.
The API signature is `getEvents(documentId, groupId, limit = 50, offset = 0)`.
The integer `50` was passed as `groupId`, not `limit`. The backend attempted
`uuid.UUID('50')`, caught the `ValueError`, set `group_uuid = None`, and returned
the last 50 events anyway (default limit). The call functioned correctly by
accident, but the groupId filter was permanently broken from this component and
the contract was silently violated.

### Files Changed
- `frontend/src/components/access/AccessLog.jsx:15`

```diff
-    window.SecureDocAPI.getEvents(docId, 50)
+    window.SecureDocAPI.getEvents(docId, null, 50)
```

- `frontend/dist/app.bundle.js` — rebuilt

### Tests Added
None — functionally benign fix. Existing 13/13 tests continue to pass.

### Risk Level
LOW — No behavior change visible to users. Enables correct groupId filtering
in future if AccessLog is extended to expose a group selector.

### Verification Evidence
- Build: `dist/app.bundle.js 202.5kb` ✅
- Tests: 13/13 passed ✅
- `grep -n "getEvents" src/components/access/AccessLog.jsx` → `getEvents(docId, null, 50)` ✅
- Backend behavior unchanged: `group_uuid = None` path no longer exercised; limit=50 applied from correct positional arg ✅

---

## FIX-2: BUG-001 — Analytics range selector non-functional

**Commit**: `4927a44`
**Status**: FIXED AND PUSHED

### Root Cause
`AnalyticsScreen.jsx` rendered four range toggle buttons (24h / 7d / 30d / 90d)
that updated local `range` state via `setRange(r)`. However:
1. The `useEffect` that fetches analytics data had empty deps `[]` — it never
   re-fired when `range` changed.
2. `getAnalyticsOverview()` accepts no `range` or `period` parameter.
3. The backend `GET /api/analytics/overview` has no range query parameter.
4. `SparkChart` receives `range` but when `sparkData` (real data) is present it
   ignores `range` entirely — data is always `views_last_7_days`.
5. The chart subtitle "Daily view count · {range}" claimed responsiveness that
   did not exist, showing "Daily view count · 90d" while displaying 7-day data.

Users were deceived into believing they were filtering a time range. They were not.

### Files Changed
- `frontend/src/screens/AnalyticsScreen.jsx`

Removed:
```diff
-import { RangeBtn } from '../components/analytics/RangeBtn.jsx';
-  const [range, setRange] = useState('7d');
-        <div style={{ display: 'flex', gap: 3 }}>
-          {analyticsTab === 'overview' && ['24h', '7d', '30d', '90d'].map(r => (
-            <RangeBtn key={r} r={r} active={range === r} onClick={() => setRange(r)} />
-          ))}
-        </div>
-                    Daily view count · {range}
-              <SparkChart range={range} sparkData={overview?.views_last_7_days} />
```

Added:
```diff
+                    Daily view count · last 7 days
+              <SparkChart range="7d" sparkData={overview?.views_last_7_days} />
```

- `frontend/dist/app.bundle.js` — rebuilt (−0.6kb dead code eliminated)

### Tests Added
None — UI-only change. Existing 13/13 tests continue to pass.

### Risk Level
LOW — No data change. The overview API call and chart data are identical.
The label is now accurate. The removed buttons had no effect on any API call.

### Verification Evidence
- Build: `dist/app.bundle.js 201.9kb` ✅ (−0.6kb vs before)
- Tests: 13/13 passed ✅
- `grep -n "RangeBtn\|setRange\|range.*useState" src/screens/AnalyticsScreen.jsx` → no output ✅
- `grep -n "SparkChart" src/screens/AnalyticsScreen.jsx` → `<SparkChart range="7d" sparkData=...` ✅
- Chart subtitle: "Daily view count · last 7 days" — matches actual data window ✅

---

## FIX-3: BUG-005 — React devDep version mismatch

**Commit**: `2026b47`
**Status**: FIXED AND PUSHED

### Root Cause
`frontend/package.json` declared `"react": "^19.2.7"` and `"react-dom": "^19.2.7"`.
npm resolved these to React 19 in `node_modules`, so `vitest` ran tests against
React 19. Production loads React 18.3.1 from unpkg CDN (hard-coded in
`SecureDoc.html:17-22` with SRI hash verification). The SRI hash locks the
production runtime to exactly React 18.3.1.

Consequence: any React 19-only behavior, hook signature change, or concurrent
mode difference exercised in tests would produce a passing test suite against
a production environment where that behavior doesn't exist. The divergence is
invisible — tests are green, production is wrong.

### Files Changed

`frontend/package.json`:
```diff
-    "react": "^19.2.7",
-    "react-dom": "^19.2.7",
+    "react": "18.3.1",
+    "react-dom": "18.3.1",
```

`frontend/package-lock.json` — regenerated with npm 10.8.2 (Node 20.20.2) to
match `node:20-alpine` in Dockerfile. Net change: react and react-dom pinned
entries updated from 19.2.7 → 18.3.1.

`frontend/dist/app.bundle.js` — unchanged (esbuild doesn't bundle react for
production; react comes from CDN).

### Compatibility Verified
`@testing-library/react@16.3.2` peerDependencies: `"react": "^18.0.0 || ^19.0.0"`
— explicitly supports React 18. No downgrade of testing library needed.

### Tests Added
None — dependency version change only. Existing 13/13 tests pass under React 18.

### Risk Level
LOW — Tests now run against the same React version as production. This eliminates
the divergence risk. No component code changed.

### Verification Evidence
- `npm ci --ignore-scripts` with npm 10.8.2: `133 packages, 0 vulnerabilities` ✅
- `node -e "require('./node_modules/react/package.json').version"` → `18.3.1` ✅
- `node -e "require('./node_modules/react-dom/package.json').version"` → `18.3.1` ✅
- Build: `dist/app.bundle.js 201.9kb` ✅
- Tests: 13/13 passed ✅

---

## Summary

| BUG | Description | Commit | Build | Tests |
|---|---|---|---|---|
| BUG-004 | AccessLog wrong arg order | cc782c3 | ✅ | 13/13 ✅ |
| BUG-001 | Analytics range buttons non-functional | 4927a44 | ✅ | 13/13 ✅ |
| BUG-005 | React 18/19 devDep mismatch | 2026b47 | ✅ | 13/13 ✅ |
| BUG-002 | Webhooks UI | — | DEFERRED | DEFERRED |
| BUG-003 | API Keys UI | — | DEFERRED | DEFERRED |
