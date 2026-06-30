# Repository Inventory — Sprint 6.3

**Date:** 2026-06-30
**Version:** 8.1.0 (RC-1 / post-governance)

---

## Active Production Files

### Root
| File | Category |
|------|---------|
| `README.md` | Documentation — project entry point |
| `CHANGELOG.md` | Release docs — current version history |
| `CONTRIBUTING.md` | Documentation — contributor guide |
| `LICENSE` | Legal |
| `SECURITY.md` | Documentation — security policy |
| `CODE_OF_CONDUCT.md` | Documentation — community standards |
| `Makefile` | Deployment tooling |
| `docker-compose.yml` | Deployment — full stack definition |
| `start.sh` | Deployment tooling — convenience wrapper |
| `.gitignore` | Repository config |
| `.claude/settings.local.json` | Local tooling config (not tracked) |

### `backend/app/` — Production Source (Python)
All files in `backend/app/` are production source. Key structure:
- `auth.py`, `config.py`, `database.py`, `main.py`, `metrics.py`
- `middleware/` — HTTPS redirect, JSON logging, metrics, rate limit, request ID, security headers, trusted proxy
- `models/` — SQLAlchemy ORM models
- `routers/` — FastAPI route handlers
- `services/` — Business logic
- `workers/` — Celery tasks

### `backend/` — Backend Infrastructure
| File | Category |
|------|---------|
| `Dockerfile` | Deployment — multi-stage container build |
| `entrypoint.sh` | Deployment — container startup script |
| `migrate.py` | Deployment — advisory-lock migration runner |
| `alembic.ini` | Migration config |
| `alembic/` | Database migrations (26 total, at head) |
| `requirements.txt` | Production dependencies |
| `requirements-dev.txt` | Development dependencies |
| `pytest.ini` | Test configuration |
| `.coveragerc` | Coverage configuration |
| `.env.example` | Documentation — env var template |
| `run_demo.py` | Development tooling — local demo server |

### `backend/tests/` — Test Suite
| Path | Category |
|------|---------|
| `tests/unit/` | Tests — unit (service logic, utilities) |
| `tests/integration/` | Tests — integration (full API stack) |
| `tests/regression/` | Tests — regression (security invariants) |
| `tests/conftest.py` | Test infrastructure |

### `frontend/src/` — Frontend Source (React/JSX)
All files in `frontend/src/` are production source. Key structure:
- `app.jsx` — application entry point
- `screens/` — 13 screen components
- `components/` — 30+ shared components
- `hooks/` — 7 custom React hooks
- `constants/` — design tokens, viewer constants
- `contexts/` — toast notification context
- `utils/` — viewer and feedback utilities

### `frontend/` — Frontend Infrastructure
| File | Category |
|------|---------|
| `SecureDoc.html` | Production source — app shell |
| `api.js` | Production source — API client |
| `dist/app.bundle.js` | Generated artifact (tracked — served by backend) |
| `package.json` | Build configuration |
| `package-lock.json` | Dependency lock |
| `vitest.config.js` | Frontend test configuration |

### `tests_e2e/` — End-to-End Tests
API, service, UI, and flow tests for live environment validation.

### `scripts/` — Operations Scripts
| File | Category |
|------|---------|
| `scripts/backup.sh` | Operations — database backup |
| `scripts/restore.sh` | Operations — database restore |

### `docs/` — Active Documentation
| Path | Category |
|------|---------|
| `docs/architecture/OVERVIEW.md` | Architecture |
| `docs/architecture/adr/ADR-001` through `ADR-010` | Architecture Decision Records |
| `docs/deployment/DEPLOYMENT.md` | Deployment guide |
| `docs/release/RC1_CERTIFICATION.md` | Release docs — current certification |
| `docs/release/RC1_*.md` | Release docs — RC1 reports |
| `docs/release/MASTER_ACTION_LOG.md` | Release docs — sprint log |
| `docs/release/CHANGELOG_SPRINT61_62.md` | Release docs — sprint changelog |
| `docs/governance/` | Governance — this sprint's output |

---

## Archived Files

All historical audit reports, sprint docs, and superseded certifications are in `archive/`. Git history is preserved via `git mv`. See [`docs/governance/ARCHIVED_FILES.md`](ARCHIVED_FILES.md) for the complete list.

| Archive Folder | Contents |
|---------------|---------|
| `archive/legacy-traceview/` | Pre-SecureDoc traceview audit docs |
| `archive/root-historical/` | Early architecture and executive reviews |
| `archive/docs-sprint2-3/` | Sprint 2–3 engineering phase reports |
| `archive/sprint3-4-reports/` | Sprint 3–4 audit reports |
| `archive/sprint4-4-certification/` | Sprint 4.4 certification suite |
| `archive/sprint5-6/root-reports/` | Sprint 5–6 root-level reports (18 files) |
| `archive/sprint5-6/frontend-docs/` | Sprint 5–6 frontend docs (46+ files) |
| `archive/browser-audit-screenshots/` | Playwright screenshots from early audits |

---

## File Count Summary (Post-Governance)

| Category | Count |
|----------|-------|
| Production source (backend Python) | ~80 files |
| Production source (frontend JSX/JS) | ~50 files |
| Tests | ~40 files |
| Database migrations | 26 files |
| Active documentation | 17 files |
| Deployment/config | ~15 files |
| **Total active** | **~228 files** |
| Archived (historical reports) | 110+ files |
