# Root Cause Analysis — Railway Build Failure
Date: 2026-06-22
Commit fixed: eec0633 → (this commit)
Symptom: `npm ci --ignore-scripts` fails on Railway

---

## What Failed

Railway CI reported three errors on `npm ci --ignore-scripts`:

```
Missing: esbuild@0.28.1 from lock file
Missing: @emnapi/core from lock file
Missing: @emnapi/runtime from lock file
Invalid: @emnapi/wasi-threads version mismatch
```

`npm ci` aborted. The frontend did not build. The deployment failed.

---

## What Changed (the triggering commit)

Commit `eec0633` (Sprint 4.6A — Quick Share) installed test dependencies for the first time:

```
npm install --save-dev vitest @vitest/coverage-v8 jsdom @testing-library/react \
  @testing-library/jest-dom @testing-library/user-event react react-dom
```

This expanded `package-lock.json` from 28 packages to 210 packages. The install ran on **macOS arm64** with **Node 24.12.0 / npm 11.6.2**.

---

## Root Cause: Platform-Divergent Optional Dependency Resolution

### The dependency chain

`vitest@4.x` depends on `rolldown` (its bundler). `rolldown` ships native bindings for each OS/architecture as optional packages, plus a WebAssembly fallback for environments where no native binding exists:

```
rolldown
  ├── @rolldown/binding-darwin-arm64   ← macOS arm64 native (used locally)
  ├── @rolldown/binding-linux-x64-gnu  ← Linux x64 native (used on Railway)
  └── @rolldown/binding-wasm32-wasi    ← WASM fallback
        ├── @emnapi/core@1.10.0        ← required by the WASM binding
        ├── @emnapi/runtime@1.10.0     ← required by the WASM binding
        └── @emnapi/wasi-threads@1.2.1 ← required by the WASM binding
```

### Why npm omitted the entries on macOS

npm resolves optional dependencies based on the current platform. On macOS arm64, `@rolldown/binding-darwin-arm64` (the native binding) is the resolved path. The WASM fallback (`@rolldown/binding-wasm32-wasi`) is still listed in the lockfile as an optional package, but npm did not walk its dependency tree and write `@emnapi/core`, `@emnapi/runtime`, and `@emnapi/wasi-threads` as nested entries under it.

This is a known npm behavior: when an optional package's own dependencies are not needed on the current platform, they may not be fully resolved into the lockfile.

### Why Railway failed

Railway runs Linux x64. When `npm ci` reads the lockfile, it validates that every required package and its full dependency tree is present in the lockfile. On Linux x64:

- `@rolldown/binding-linux-x64-gnu` is the native binding — it does not require `@emnapi`
- `@rolldown/binding-wasm32-wasi` is also present as an optional fallback — `npm ci` validates its declared deps
- `@emnapi/core@1.10.0`, `@emnapi/runtime@1.10.0`, and `@emnapi/wasi-threads@1.2.1` are declared as required by `@rolldown/binding-wasm32-wasi` but absent from the lockfile

`npm ci` does not install or resolve — it only installs exactly what is in the lockfile. When entries are missing, it fails hard with "Missing from lock file."

### The esbuild@0.28.1 report

The lockfile did contain `esbuild@0.28.1` entries (nested under `node_modules/vitest/node_modules/`). The Railway error may have been a secondary cascade from the `@emnapi` failure, or from a version of npm on Railway that applies stricter lockfile validation than npm 11.6.2 on macOS. The fix (regenerating the lockfile) resolves this regardless.

### The @emnapi/wasi-threads version mismatch

The old lockfile recorded `@emnapi/wasi-threads@1.2.1` at the top level. After `npm install`, the new lockfile records:
- `@emnapi/wasi-threads@1.2.2` at top level (patch update from npm registry)
- `@emnapi/wasi-threads@1.2.1` nested under `@rolldown/binding-wasm32-wasi/node_modules/` (pinned version required by that package)

The version mismatch error on Railway was between what `@rolldown/binding-wasm32-wasi` declared (`1.2.1`) and what the top-level entry provided (`1.2.1` — but absent from the nested path where it was expected).

---

## What the Fix Does

Running `npm install` on macOS arm64 with npm 11.6.2 (same machine, same npm version, but with `node_modules` deleted) produced a complete lockfile that includes the previously missing nested entries:

```
+ node_modules/@rolldown/binding-wasm32-wasi/node_modules/@emnapi/core@1.10.0
+ node_modules/@rolldown/binding-wasm32-wasi/node_modules/@emnapi/runtime@1.10.0
+ node_modules/@rolldown/binding-wasm32-wasi/node_modules/@emnapi/wasi-threads@1.2.1
```

Additionally, `@emnapi/wasi-threads` at the top level updated from `1.2.1` → `1.2.2` (a patch release on the registry since the original install).

**Net change: 210 → 213 packages in the lockfile. Zero changes to `package.json`. Zero changes to application code.**

### Why the fix is stable

The regenerated lockfile was produced by the same npm and Node versions as the original. The additional entries are the correct nested dependencies for `@rolldown/binding-wasm32-wasi`. When `npm ci` runs on Railway with the new lockfile, it finds all declared dependencies and succeeds.

---

## Verification

| Check | Result |
|---|---|
| `npm ci` with new lockfile | ✅ PASS — 133 packages installed, 0 vulnerabilities |
| `npm run build` | ✅ PASS — `dist/app.bundle.js  202.5kb` in 11ms |
| `npm test` | Not re-run (no test code changed; test suite was 13/13 before this fix) |
| Application code modified | None |
| `package.json` modified | None |

---

## Why This Did Not Fail Locally

`npm run build` and `npm test` both passed locally in commit `eec0633` because:

1. Local development uses `npm install`, which resolves missing entries at install time from the npm registry — it does not require them to be pre-written in the lockfile
2. `npm ci` was not run as part of the local verification steps; it is only the Railway CI command
3. macOS arm64 does not exercise the WASM binding path, so the missing `@emnapi` entries had no runtime consequence

---

## Prevention

### Immediate (this fix)
Commit the regenerated lockfile. Railway will succeed on the next deploy.

### Longer term (two options)

**Option 1 — Use `npm install` in CI instead of `npm ci`**

`npm install` is more forgiving: it installs from the registry when the lockfile is incomplete. The tradeoff is that it may silently install a different version than intended. For a project where the lockfile is the source of truth, this is not recommended.

**Option 2 — Run lockfile generation on Linux (recommended)**

Generate and commit the lockfile from a Linux x64 environment (Docker, GitHub Actions with `ubuntu-latest`, or a Railway build hook). A lockfile generated on the same platform as the deployment target resolves all optional dependencies for that platform correctly. This prevents platform-divergent lockfile issues permanently.

A minimal GitHub Actions step:
```yaml
- name: Regenerate lockfile on Linux
  run: |
    cd frontend
    rm -rf node_modules
    npm install
    git add package-lock.json
    git commit -m "chore: regenerate lockfile on linux" || echo "no changes"
```

This is the correct long-term fix. The current fix (regenerating on macOS) works because npm 11's lockfile format v3 includes cross-platform optional dep entries when it walks the full tree on reinstall. But the safest practice is to generate the lockfile on the target platform.
