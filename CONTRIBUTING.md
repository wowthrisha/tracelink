# Contributing to SecureDoc

## Getting Started

1. Fork the repository and create a branch from `main`
2. Set up your local environment (see `README.md`)
3. Run the test suite: `cd backend && python -m pytest tests/ -q`
4. Make your changes
5. Ensure tests still pass and add tests for new behaviour
6. Open a pull request

## Development Setup

```bash
cp backend/.env.example backend/.env   # fill in your credentials
cd backend && pip install -r requirements.txt -r requirements-dev.txt
alembic upgrade head
USE_DEMO_STORAGE=1 python run_demo.py
```

Frontend:
```bash
cd frontend && npm ci && npm run build
```

## Code Standards

- **Python:** Follow existing patterns; async/await throughout; SQLAlchemy async ORM
- **Frontend:** JSX with React hooks; no class components; design tokens from `constants/tokens.js`
- **Tests:** Add integration tests for new API endpoints; unit tests for pure logic
- **Commits:** One logical change per commit; descriptive message in the present tense

## Pull Request Checklist

- [ ] Tests pass (`python -m pytest tests/ -q` — expect 1624+ passed, 0 failed)
- [ ] No new `console.log`, `print()`, `pdb`, or `breakpoint()` in production paths
- [ ] No secrets or credentials committed
- [ ] New API endpoints documented in the PR description
- [ ] Database migrations included if schema changed (`alembic revision --autogenerate`)
- [ ] ADR added to `docs/architecture/adr/` if an architectural decision was made

## Reporting Issues

Open a GitHub issue with:
- Steps to reproduce
- Expected vs actual behaviour
- Backend version (`GET /health` → `version`)
- Browser and OS (for frontend issues)

## Security Issues

Do not open public issues for security vulnerabilities. See [SECURITY.md](SECURITY.md).
