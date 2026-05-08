#!/usr/bin/env bash
# Run the full E2E test suite.
# Prerequisites:
#   - Backend running: cd backend && python run_demo.py
#   - Frontend served: cd frontend && python -m http.server 5500
#   - Playwright installed: playwright install chromium
#
# Usage:
#   ./run_tests.sh                  # run all layers
#   ./run_tests.sh -m api           # API contract tests only
#   ./run_tests.sh -m service       # service unit tests only
#   ./run_tests.sh -m ui            # Playwright UI tests only
#   ./run_tests.sh -m e2e           # full E2E scenario tests only

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/../backend"

export PYTHONPATH="$BACKEND_DIR:$SCRIPT_DIR"

cd "$SCRIPT_DIR"

# Install test dependencies if needed
if ! python3 -c "import httpx" 2>/dev/null; then
    pip install -r requirements-test.txt
fi

echo "=== SecureDoc E2E Test Suite ==="
echo "Backend expected at: http://localhost:8000"
echo "Frontend expected at: http://localhost:5500/SecureDoc.html"
echo ""

# Health check
if ! curl -sf http://localhost:8000/health > /dev/null; then
    echo "ERROR: Backend not running at http://localhost:8000"
    echo "Start with: cd backend && python run_demo.py"
    exit 1
fi

echo "✓ Backend health check passed"
echo ""

pytest "$@" -v --tb=short
