# Archive

Historical documentation preserved for audit trail purposes.

Files here are **not active**. They document the project at a specific point in time and have been superseded by current documentation in the repository root or `docs/`.

All files were moved (not deleted) via `git mv` where the source was tracked, preserving full git history; a handful of long-lived scratch reports that were never committed in the first place were moved and committed here for the first time (see `docs/governance/ARCHIVED_FILES.md` for which).

## Directories

| Directory | Contents | Era |
|-----------|----------|-----|
| `legacy-traceview/` | Documents from when the project was named "TraceView" | Pre-SecureDoc rename |
| `root-historical/` | Root-level reports superseded by Sprint 5.x production docs | Pre-Sprint 5 |
| `browser-audit-screenshots/` | PNG screenshots from a browser UI audit session | Sprint 4.x |
| `docs-sprint2-3/` | Sprint 2–3 era engineering and audit notes | Sprint 2–3 |
| `sprint4-4-certification/` | Sprint 4.4 certification snapshots | Sprint 4.4 |
| `sprint3-4-reports/` | Sprint 3–4 implementation and review reports | Sprint 3–4 |
| `sprint5-6/` | Root-level and `frontend/docs/` reports superseded by Sprint 6.3's RC1 certification (`root-reports/`, `root-reports2/`, `frontend-docs/`) | Sprint 5–6 |
| `sprint7-18/` | Root-level sprint/certification reports superseded by the canonical `ENGINEERING_BACKLOG.md`/`docs/engineering/ISSUE_DATABASE.md` (`root-reports/`) | Sprint 7–18 |

## Authoritative Current Documentation

- `docs/` — the live documentation tree (api, architecture, deployment, development, engineering, governance, operations, product-review, reading_analytics, release, security, ui-audit). `frontend/docs/` no longer exists — it was an empty 3-level directory tree deleted during Sprint V6.0 (see `docs/engineering/FIX_LOG.md`'s "Dead code removed" entry for that sprint); this file's prior references to it were stale and are corrected here.
- Security: `SECURITY.md` (root). `RISK_REGISTER.md`/`ARCHITECTURE_DECISIONS.md` no longer exist at root — both were themselves archived in an earlier sprint (see `docs/governance/ARCHIVED_FILES.md`); this file's prior references to them were stale and are corrected here.
- Canonical outstanding-work backlog: `ENGINEERING_BACKLOG.md` (root)
