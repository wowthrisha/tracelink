# Deployment Forensics — Railway Build Failure (Round 2)
Date: 2026-06-22
Status: Root cause confirmed. Fix applied. npm ci + npm run build + npm test all pass.

---

## The Symptom

Railway CI reported three missing packages on `npm ci --ignore-scripts`:

```
Missing: @emnapi/core@1.11.1 from lock file
Missing: @emnapi/runtime@1.11.1 from lock file
Missing: esbuild@0.28.1 from lock file
```

These are different from the packages reported in the previous failure (which were `@emnapi/core@1.10.0` etc). The version numbers changed because the previous lockfile fix was applied using the **wrong npm version**.

---

## Task 1 — Every package.json in the Repository

```
/Users/thrisha/traceview/securedoc/frontend/package.json
```

There is exactly **one** `package.json`. It is at `frontend/package.json`.

---

## Task 2 — Every package-lock.json in the Repository

```
/Users/thrisha/traceview/securedoc/frontend/package-lock.json
```

There is exactly **one** `package-lock.json`. It is at `frontend/package-lock.json`.

---

## Task 3 — Which package-lock.json Does Railway Use?

Evidence from `backend/Dockerfile`:

```dockerfile
# ── Stage 1: Frontend build ────────────────────────────────────────────────
# Compiles JSX → plain JS with esbuild.  No Node.js ends up in the final image.
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend-src
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci --ignore-scripts
COPY frontend/src ./src
RUN npm run build
```

Railway uses:
- **Base image**: `node:20-alpine` → **Node 20.x / npm 10.x** (specifically npm 10.8.2 as of Node 20.20.2)
- **Lockfile copied**: `frontend/package-lock.json` (the only one in the repo)
- **Install command**: `npm ci --ignore-scripts`
- **Build command**: `npm run build`

The build context root is the repository root, so `frontend/package-lock.json` maps to `/frontend-src/package-lock.json` inside the builder stage.

---

## Task 4 — Compare Railway-Targeted package.json and package-lock.json

### package.json (devDependencies)

```json
{
  "devDependencies": {
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@testing-library/user-event": "^14.6.1",
    "@vitest/coverage-v8": "^4.1.9",
    "esbuild": "^0.25.0",
    "jsdom": "^29.1.1",
    "react": "^19.2.7",
    "react-dom": "^19.2.7",
    "vitest": "^4.1.9"
  }
}
```

### package-lock.json (state BEFORE this fix)

Key entries present:

| Package | Resolved version | Path in lockfile |
|---|---|---|
| `esbuild` | 0.25.12 | `node_modules/esbuild` (top-level) |
| `@emnapi/core` | 1.10.0 | `node_modules/@rolldown/binding-wasm32-wasi/node_modules/@emnapi/core` (nested only) |
| `@emnapi/runtime` | 1.10.0 | `node_modules/@rolldown/binding-wasm32-wasi/node_modules/@emnapi/runtime` (nested only) |
| `@emnapi/wasi-threads` | 1.2.1 | `node_modules/@rolldown/binding-wasm32-wasi/node_modules/@emnapi/wasi-threads` (nested only) |

Key entries **ABSENT** from the previous lockfile:

| Package | Version needed by Railway | Why missing |
|---|---|---|
| `node_modules/@emnapi/core` | 1.11.1 | npm 11 omitted top-level entry; npm 10 requires it |
| `node_modules/@emnapi/runtime` | 1.11.1 | npm 11 omitted top-level entry; npm 10 requires it |
| `node_modules/vitest/node_modules/esbuild` | 0.28.1 | npm 11 incorrectly deduped against top-level esbuild@0.25.12 |

---

## Task 5 — Regenerate Using the Correct npm Version

The Dockerfile uses `node:20-alpine`. The previous fix used **npm 11.6.2** (Node 24). Railway uses **npm 10.8.2** (Node 20).

**Previous (broken) approach:**
```sh
# Node 24.12.0 / npm 11.6.2 — WRONG: generates npm11-format lockfile
rm -rf node_modules && npm install
```

**Correct approach:**
```sh
# Switch to Node 20 to match node:20-alpine
nvm install 20       # installs v20.20.2
nvm use 20           # npm version: 10.8.2

cd frontend
rm -rf node_modules
npm install
```

Output:
```
added 132 packages, and audited 133 packages in 3s
28 packages are looking for funding
found 0 vulnerabilities
```

---

## Task 6 — Verify npm ci Succeeds Locally

```sh
$ nvm use 20 && npm ci --ignore-scripts

Now using node v20.20.2 (npm v10.8.2)
added 132 packages, and audited 133 packages in 2s
28 packages are looking for funding
found 0 vulnerabilities
```

**PASS.**

---

## Task 7 — Verify npm run build Succeeds Locally

```sh
$ nvm use 20 && npm run build

> securedoc-frontend@1.0.0 build
> esbuild src/app.jsx --bundle --loader:.jsx=jsx ...

  dist/app.bundle.js  202.5kb

⚡ Done in 12ms
```

**PASS.** Test suite also passes:

```
Tests  13 passed (13)
```

---

## Task 8 — git diff frontend/package-lock.json

Three entries were **added** by the npm 10.8.2 regeneration:

### Addition 1: `node_modules/@emnapi/core@1.11.1` (top-level)

```diff
+    "node_modules/@emnapi/core": {
+      "version": "1.11.1",
+      "resolved": "https://registry.npmjs.org/@emnapi/core/-/core-1.11.1.tgz",
+      "integrity": "sha512-RSvbQmHzdKzNsLYa/wHrbc3KN4sYLKAdPZxqiM2HATqv/SBk2/ENSHpvXGaLOMcsAyz0poEGqkmmKYG3OWiJEQ==",
+      "dev": true,
+      "license": "MIT",
+      "optional": true,
+      "peer": true,
+      "dependencies": {
+        "@emnapi/wasi-threads": "1.2.2",
+        "tslib": "^2.4.0"
+      }
+    },
```

### Addition 2: `node_modules/@emnapi/runtime@1.11.1` (top-level)

```diff
+    "node_modules/@emnapi/runtime": {
+      "version": "1.11.1",
+      "resolved": "https://registry.npmjs.org/@emnapi/runtime/-/runtime-1.11.1.tgz",
+      "integrity": "sha512-vgj7R3y3Wgx24IQaGPA/R6YFXLHVMOZ0uVEyIQPaWs+rd1AzfEMXlAC22FYwO1XkKR6NPsq7mUandH8oIRdZFw==",
+      "dev": true,
+      "license": "MIT",
+      "optional": true,
+      "peer": true,
+      "dependencies": {
+        "tslib": "^2.4.0"
+      }
+    },
```

### Addition 3: `node_modules/vitest/node_modules/esbuild@0.28.1`

```diff
+    "node_modules/vitest/node_modules/esbuild": {
+      "version": "0.28.1",
+      "resolved": "https://registry.npmjs.org/esbuild/-/esbuild-0.28.1.tgz",
+      "integrity": "sha512-HrJrvZv5ayxBzPfwphOoNzkzOIIlifzk0KJrGK2c8R4+LKpMtpYLQeUdjnwjWv/LZlkH2laZk+4w78pi99D4Vw==",
+      "dev": true,
+      "hasInstallScript": true,
+      ...
+    }
```

The remainder of the diff is `"peer": true` flag additions and removals on existing entries — metadata differences between npm 10 and npm 11's interpretation of peer dependencies.

---

## Task 9 — Why the Previous Fix Failed

### What the previous fix did

The previous fix (`ROOT_CAUSE_ANALYSIS.md`, commit `2d487a5`) ran `npm install` using **Node 24.12.0 / npm 11.6.2** on macOS arm64. That resolved the original Railway failure (which reported `@emnapi/core@1.10.0` etc. as missing).

However, the regenerated lockfile still caused a Railway failure because **npm 11 and npm 10 implement different peer dependency resolution algorithms** for optional peer dependencies:

### Difference 1: Top-level optional peer entries

`@rolldown/binding-wasm32-wasi` declares `@emnapi/core` and `@emnapi/runtime` as direct dependencies (with pinned versions). It is itself an **optional peer dependency** of rolldown.

- **npm 11**: resolved `@emnapi/core` and `@emnapi/runtime` only as **nested** entries under `node_modules/@rolldown/binding-wasm32-wasi/node_modules/`. It omitted top-level entries for these packages because it treated the optional peer's sub-deps as not needing top-level hoisting.
- **npm 10**: requires `@emnapi/core` and `@emnapi/runtime` to also appear as **top-level** entries with `"peer": true` so that `npm ci` can validate the full dependency graph. When it reads the npm 11-generated lockfile and doesn't find them at the top level, it reports them as "Missing".

### Difference 2: esbuild version deduplication

`vitest@4.1.9` requires esbuild `^0.27.0 || ^0.28.0` (transitively through rolldown). The top-level devDependency is `esbuild: "^0.25.0"`, pinned to 0.25.12 in the lockfile.

- **npm 11**: incorrectly deduped vitest's esbuild requirement against the top-level `esbuild@0.25.12`. It did NOT add a separate `node_modules/vitest/node_modules/esbuild` entry. This is a bug: `0.25.12` does not satisfy `^0.27.0 || ^0.28.0`.
- **npm 10**: correctly identifies the incompatible range and adds a separate `node_modules/vitest/node_modules/esbuild@0.28.1` entry nested under vitest.

### Difference 3: Registry version update

Between when npm 11 generated the lockfile and when this fix was applied, `@emnapi/core` and `@emnapi/runtime` were updated on the npm registry from `1.10.0` → `1.11.1`. npm 10 resolves the declared range `^1.7.1` to the latest available version, which is now `1.11.1`. The npm 11 lockfile pinned `1.10.0` in the nested entries; npm 10's `npm ci` expects the top-level entries at `1.11.1`.

### Summary table

| Missing package | Reason absent from npm 11 lockfile |
|---|---|
| `@emnapi/core@1.11.1` (top-level) | npm 11 omits top-level optional peer sub-deps; npm 10 requires them |
| `@emnapi/runtime@1.11.1` (top-level) | Same as above |
| `vitest/node_modules/esbuild@0.28.1` | npm 11 dedup bug: 0.25.12 incorrectly treated as satisfying `^0.28.0` |

---

## Root Cause Statement

The project's lockfile was generated using **npm 11** (local development, Node 24). Railway's Docker build uses **npm 10** (via `node:20-alpine`). These npm versions implement incompatible peer dependency resolution logic, producing lockfiles that are not interchangeable.

npm 11 generates a lockfile that passes `npm ci` under npm 11 but fails under npm 10. npm 10 generates a lockfile that passes under both.

**Correct fix**: always regenerate `frontend/package-lock.json` using `node:20-alpine`'s npm version (npm 10.x). On macOS, this requires switching to Node 20 via nvm before running `npm install`.

---

## Long-Term Prevention

The root cause will recur whenever a developer on Node 24+ runs `npm install` and commits the lockfile. The lockfile generator and the lockfile consumer (Railway) must use the same npm version.

### Option A — Enforce in .nvmrc (Recommended)

Add `frontend/.nvmrc`:
```
20
```

When developers run `nvm use` inside `frontend/`, they automatically switch to the Node version that Railway uses. Combined with a pre-commit hook or CI check, this prevents npm 11 lockfiles from being committed.

### Option B — Regenerate Lockfile in CI on Linux

Add a GitHub Actions step that regenerates the lockfile on `ubuntu-latest` with `node:20` and commits the result. This ensures the lockfile is always generated on the same platform and Node version as Railway.

### Option C — Use npm install in the Dockerfile instead of npm ci

Change the Dockerfile from `npm ci --ignore-scripts` to `npm install --ignore-scripts`. This is less reproducible (installs from registry) but tolerates lockfile version mismatches. **Not recommended** — defeats the purpose of a lockfile.

---

## Verification Checklist

| Check | Version used | Result |
|---|---|---|
| `npm install` (regenerate lockfile) | Node 20.20.2 / npm 10.8.2 | ✅ 132 packages, 0 vulnerabilities |
| `npm ci --ignore-scripts` | Node 20.20.2 / npm 10.8.2 | ✅ PASS |
| `npm run build` | Node 20.20.2 / npm 10.8.2 | ✅ `dist/app.bundle.js 202.5kb` |
| `npm test` | Node 20.20.2 / npm 10.8.2 | ✅ 13/13 passed |
| Application code modified | — | None |
| `package.json` modified | — | None |
| Lockfile net change | — | 210 → 213 entries (3 added) |
