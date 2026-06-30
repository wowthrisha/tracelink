# Final Repository Structure — Sprint 6.3

**Date:** 2026-06-30

---

```
securedoc/
│
├── README.md                      ← Project overview, quick start, architecture
├── CHANGELOG.md                   ← Version history (v7.x–v8.1.0)
├── CONTRIBUTING.md                ← Dev setup, code standards, PR checklist
├── LICENSE                        ← MIT
├── SECURITY.md                    ← Security policy, vulnerability reporting
├── CODE_OF_CONDUCT.md             ← Contributor Covenant v2.1
├── Makefile                       ← Common dev/ops commands
├── docker-compose.yml             ← Full local stack (db, redis, api, worker, beat, backup)
├── start.sh                       ← Convenience wrapper script
│
├── docs/
│   ├── architecture/
│   │   ├── OVERVIEW.md            ← System diagram, data flows, security model
│   │   └── adr/
│   │       ├── ADR-001-hsts-default.md
│   │       ├── ADR-002-atomic-max-views.md
│   │       ├── ADR-003-viewer-forensic-stamp.md
│   │       ├── ADR-004-session-cache.md
│   │       ├── ADR-005-json-logging.md
│   │       ├── ADR-006-cdn-thumbnails-only.md
│   │       ├── ADR-007-streaming-download.md
│   │       ├── ADR-008-prometheus.md
│   │       ├── ADR-009-pptx-libreoffice.md
│   │       └── ADR-010-sso-supabase-saml.md
│   ├── deployment/
│   │   └── DEPLOYMENT.md          ← Docker, env vars, Railway, migrations, scaling
│   ├── release/
│   │   ├── RC1_CERTIFICATION.md   ← Current release certification
│   │   ├── RC1_RELEASE_REPORT.md
│   │   ├── RC1_DEPLOYMENT_REPORT.md
│   │   ├── RC1_REGRESSION_REPORT.md
│   │   ├── RC1_RUNTIME_REPORT.md
│   │   ├── MASTER_ACTION_LOG.md
│   │   └── CHANGELOG_SPRINT61_62.md
│   └── governance/
│       ├── REPOSITORY_INVENTORY.md
│       ├── ARCHIVED_FILES.md
│       ├── FINAL_REPOSITORY_STRUCTURE.md  ← This file
│       ├── CLEANUP_LOG.md
│       └── REPOSITORY_GOVERNANCE_REPORT.md
│
├── backend/
│   ├── Dockerfile                 ← Multi-stage build (frontend → python runtime)
│   ├── entrypoint.sh              ← Container startup (migrate then exec)
│   ├── migrate.py                 ← Advisory-lock migration runner
│   ├── run_demo.py                ← Local demo server
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── pytest.ini
│   ├── .coveragerc
│   ├── .env.example
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/              ← 26 migrations (001–025 + initial)
│   ├── app/
│   │   ├── auth.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── main.py
│   │   ├── metrics.py
│   │   ├── middleware/            ← 7 middleware modules
│   │   ├── models/                ← SQLAlchemy ORM models
│   │   ├── routers/               ← FastAPI route handlers
│   │   ├── services/              ← Business logic services
│   │   └── workers/               ← Celery tasks
│   └── tests/
│       ├── unit/                  ← 23 unit test files
│       ├── integration/           ← 21 integration test files
│       └── regression/            ← 4 regression test files
│
├── frontend/
│   ├── SecureDoc.html             ← App shell
│   ├── api.js                     ← API client (auto-detects environment)
│   ├── dist/app.bundle.js         ← Built bundle (249.3 KB, tracked)
│   ├── package.json
│   ├── vitest.config.js
│   └── src/
│       ├── app.jsx                ← Application entry point
│       ├── screens/               ← 13 screen components
│       ├── components/            ← 30+ shared components
│       ├── hooks/                 ← 7 custom React hooks
│       ├── constants/             ← Design tokens, viewer constants
│       ├── contexts/              ← Toast context
│       └── utils/                 ← Viewer and feedback utilities
│
├── scripts/
│   ├── backup.sh                  ← Database backup
│   └── restore.sh                 ← Database restore
│
├── tests_e2e/
│   ├── api/                       ← API endpoint tests
│   ├── e2e/                       ← End-to-end flow tests
│   ├── services/                  ← Service-level tests
│   └── ui/                        ← UI automation tests
│
└── archive/                       ← Historical sprint docs (git mv, history preserved)
    ├── legacy-traceview/          ← Pre-SecureDoc origin
    ├── root-historical/           ← Early architecture docs
    ├── docs-sprint2-3/            ← Sprint 2–3 phase reports
    ├── sprint3-4-reports/         ← Sprint 3–4 audit reports
    ├── sprint4-4-certification/   ← Sprint 4.4 certification
    ├── sprint5-6/                 ← Sprint 5–6 reports (this sprint)
    │   ├── root-reports/          ← 18 former root-level reports
    │   └── frontend-docs/         ← 46 former frontend/docs/ files
    └── browser-audit-screenshots/ ← Playwright screenshots
```

## Active Document Count

| Category | Count |
|----------|-------|
| Root governance | 6 |
| Architecture docs | 11 (1 overview + 10 ADRs) |
| Deployment docs | 1 |
| Release docs | 7 |
| Governance docs (this sprint) | 5 |
| **Total active docs** | **30** |

This is the target state for a maintainable production repository. Future sprints should add to `docs/` for architecture or deployment changes, add to `CHANGELOG.md` for releases, and move obsolete sprint reports to `archive/`.
