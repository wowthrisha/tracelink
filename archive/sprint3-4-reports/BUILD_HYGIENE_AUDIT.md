> **HISTORICAL ARCHIVE** — Sprint milestone record. Reflects state at time of writing. Not current state.

# Build Hygiene Audit
Sprint 4.0 — Phase 3
Date: 2026-06-18

---

## Build Script

**`package.json` build script:**
```
esbuild src/app.jsx --bundle --loader:.jsx=jsx --jsx-factory=React.createElement --jsx-fragment=React.Fragment --target=chrome80,firefox78,safari14 --outfile=dist/app.bundle.js --minify
```

**Assessment:**
- Single command, no pipeline complexity — GOOD
- `--bundle` resolves all `import` statements into one output file — correct for CDN-React UMD pattern
- `--jsx-factory=React.createElement` and `--jsx-fragment=React.Fragment` required because React is a global, not an import — correct
- `--target=chrome80,firefox78,safari14` — reasonable modern baseline
- `--minify` — correct for production output
- No `--sourcemap` — acceptable for a single-file CDN app; would help debug production issues if added

**No issues found.**

---

## dist/ Artifact — Should it be committed?

**Decision: YES — intentionally committed by design.**

Evidence from `securedoc/.gitignore`:
```
node_modules/
dist/
!frontend/dist/    # ← explicit un-ignore
```

The root `.gitignore` ignores `dist/` globally but then explicitly un-ignores `frontend/dist/`. This was a deliberate choice: the frontend is a static single-file bundle deployed directly from the repository (Railway or Cloudflare CDN). Committing `dist/app.bundle.js` means the build artifact is always present for deployment without a CI build step.

**Assessment:** Consistent with the deployment model (static CDN / direct-serve). Treat `dist/app.bundle.js` as a required tracked file, not a generated artifact to exclude.

**No change required.**

---

## .gitignore Assessment

Root `securedoc/.gitignore` exists and is comprehensive. No `frontend/.gitignore` exists — not needed since the root covers the repo.

Items in root `.gitignore` relevant to frontend:
```
node_modules/          ✅ covered
dist/                  ✅ covered (with frontend/dist/ un-ignored)
!frontend/dist/        ✅ intentional exclusion from ignore
.DS_Store              ✅
*.log                  ✅
*.webp / *.png / *.jpg ✅
```

**Assessment: CLEAN.** No missing entries.

---

## Untracked Files Assessment

Three untracked files at `securedoc/` root are hygiene issues unrelated to the build:

| File | Size | Origin | Recommendation |
|---|---|---|---|
| `].md` | 31,909 bytes | Shell redirect accident — content is "TraceView Pilot Deployment Guide Phase D2.7" | Rename to `PILOT_DEPLOYMENT_GUIDE.md` and commit, or delete if superseded |
| `200` | 0 bytes | Shell accident (likely `touch 200` or misdirected output) | Delete |
| `404` | 0 bytes | Shell accident | Delete |

**These are not build artifacts — they are malformed repository files. Phase 4 action: delete `200` and `404`; rename or preserve `].md` content at discretion.**

---

## npm Dependency Audit

| Package | Installed | Used | Status |
|---|---|---|---|
| `esbuild ^0.25.0` | Yes (devDep) | Yes — sole build tool | CLEAN |

- No unused devDependencies.
- No production dependencies — React, React-DOM, and all third-party code loaded via CDN in SecureDoc.html.
- No `node_modules/` in git (correctly ignored).

---

## Build Output Analysis

| Metric | Value | Notes |
|---|---|---|
| Output file | `dist/app.bundle.js` | Single file |
| Size (minified) | 197.4 kb (202,180 bytes) | Stable across Sprint 3.3–3.5 |
| Build time | 14ms | Extremely fast — expected for esbuild |
| Errors | 0 | Clean build |
| Warnings | 0 | Clean build |

Bundle size has remained stable since Sprint 3.3 (196.7 kb → 197.4 kb, +0.7 kb) despite extracting 32 components. This confirms esbuild's module bundling adds near-zero overhead for module extraction.

---

## Source Map Assessment

No `--sourcemap` flag in build script. Source maps would:
- Aid production debugging
- Have no security impact (maps are separate files, only loaded by DevTools)
- Add ~300–400 kb to output (separate `.map` file)

**Current assessment: ACCEPTABLE.** Single-file CDN app with fast rebuilds makes source maps a low-priority addition. Not blocking for Sprint 4.

---

## Summary

| Category | Status | Action |
|---|---|---|
| Build script | CLEAN | None |
| dist/ committed | INTENTIONAL | None |
| .gitignore | CLEAN | None |
| npm dependencies | CLEAN (1 devDep only) | None |
| Untracked root files | 3 hygiene issues | Delete `200`, `404`; decide `].md` |
| Bundle size | Stable at 197.4 kb | None |
| Source maps | Not present | Optional future addition |
