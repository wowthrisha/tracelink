#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# SecureDoc — Unified startup helper
#
# ONE-COMMAND STARTUP
#   ./start.sh all          Build + start full stack via Docker Compose, then run tests
#
# LOCAL DEV (native — no Docker)
#   Terminal 1: ./start.sh backend      FastAPI on :8000 (demo storage)
#   Terminal 2: ./start.sh worker       Celery PDF worker
#
# TESTING
#   ./start.sh test         Run backend unit test suite (SQLite mocks, no live services)
#   ./start.sh check        Health-check the running stack
#
# GLOBAL SHARING via Cloudflare Quick Tunnel
#   ./start.sh quicktunnel  Auto-detects public URL and updates backend/.env
#   ./start.sh set-url URL  Manually set APP_PUBLIC_BASE_URL in backend/.env
#   ./start.sh tunnel       Named Cloudflare Tunnel (needs CLOUDFLARE_TUNNEL_TOKEN)
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
ENV_FILE="$BACKEND_DIR/.env"

# ── Helpers ────────────────────────────────────────────────────────────────────
hr()       { printf '%.0s─' {1..72}; echo; }
bold()     { echo "  $*"; }

_read_env() {
  local key="$1" default="${2:-}"
  [ -f "$ENV_FILE" ] || { echo "$default"; return; }
  local val
  val=$(grep -E "^${key}=" "$ENV_FILE" | tail -1 | cut -d= -f2-)
  val="${val%\"}"; val="${val#\"}"; val="${val%\'}"; val="${val#\'}"
  echo "${val:-$default}"
}

# Update (or add) a key=value line in .env using Python for reliability
_set_env() {
  local key="$1" value="$2"
  python3 - "$ENV_FILE" "$key" "$value" <<'PYEOF'
import re, sys
env_file, key, value = sys.argv[1], sys.argv[2], sys.argv[3]
with open(env_file) as f:
    content = f.read()
pattern = rf'(?m)^{re.escape(key)}=.*'
replacement = f'{key}={value}'
if re.search(pattern, content):
    updated = re.sub(pattern, replacement, content)
else:
    updated = content.rstrip('\n') + f'\n{replacement}\n'
with open(env_file, 'w') as f:
    f.write(updated)
PYEOF
}

PUBLIC_BASE="$(_read_env APP_PUBLIC_BASE_URL http://localhost:8000)"
TUNNEL_TOKEN="$(_read_env CLOUDFLARE_TUNNEL_TOKEN)"

# ── Commands ───────────────────────────────────────────────────────────────────
cmd="${1:-help}"

case "$cmd" in

  # ── all — one-command Docker Compose startup + test run ──────────────────────
  all)
    echo ""
    hr
    bold "SecureDoc — one-command startup"
    hr
    echo ""

    if ! command -v docker &>/dev/null; then
      echo "  ERROR: docker not found."
      echo "  Install Docker Desktop: https://docs.docker.com/get-docker/"
      exit 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
      cp "$BACKEND_DIR/.env.example" "$ENV_FILE"
      echo "  Created backend/.env from .env.example."
      echo "  Edit it with your Supabase and storage credentials, then re-run."
      echo ""
      echo "  Minimum required for demo mode (local storage, no Supabase):"
      echo "    DATABASE_URL  — already set for local postgres"
      echo "    JWT_SECRET    — generate: python3 -c \"import secrets; print(secrets.token_hex(32))\""
      echo "    APP_PUBLIC_BASE_URL — already set to http://localhost:8000"
      echo ""
      echo "  Re-run: ./start.sh all"
      exit 1
    fi

    bold "Building images and starting services ..."
    docker compose up --build -d

    echo ""
    bold "Waiting for backend to become healthy ..."
    attempts=0
    until curl -sf http://localhost:8000/health >/dev/null 2>&1; do
      sleep 3
      attempts=$((attempts + 1))
      if [ "$attempts" -ge 20 ]; then
        echo ""
        echo "  ERROR: Backend did not become healthy after 60 s."
        echo "  Check logs: docker compose logs api"
        exit 1
      fi
    done
    echo "  Backend is healthy."

    echo ""
    bold "Running unit test suite ..."
    cd "$BACKEND_DIR"
    if PYTHONPATH=. python3 -m pytest tests/ -q --tb=short; then
      echo ""
      hr
      bold "All systems go."
      bold ""
      bold "  App:        http://localhost:8000"
      bold "  API docs:   http://localhost:8000/docs"
      bold "  Logs:       docker compose logs -f"
      bold "  Stop:       docker compose down"
      bold "  Health:     ./start.sh check"
      hr
      echo ""
    else
      echo ""
      echo "  Tests FAILED. Check output above."
      echo "  Backend logs: docker compose logs api"
      exit 1
    fi
    ;;

  # ── test — unit test suite (SQLite mocks, no live services needed) ────────────
  test)
    echo ""
    echo "  Running backend unit test suite ..."
    cd "$BACKEND_DIR"
    PYTHONPATH=. python3 -m pytest tests/ -q --tb=short
    ;;

  # ── backend ──────────────────────────────────────────────────────────────────
  backend)
    PUBLIC_BASE="$(_read_env APP_PUBLIC_BASE_URL http://localhost:8000)"
    echo ""
    hr
    bold "SecureDoc backend starting on :8000"
    bold "Share links will use: ${PUBLIC_BASE}"
    hr
    echo ""
    cd "$BACKEND_DIR"
    exec python3 run_demo.py
    ;;

  # ── worker ───────────────────────────────────────────────────────────────────
  worker)
    echo "Starting Celery PDF worker …"
    cd "$BACKEND_DIR"
    exec python3 -m celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
    ;;

  # ── quicktunnel ──────────────────────────────────────────────────────────────
  quicktunnel)
    if ! command -v cloudflared &>/dev/null; then
      echo "ERROR: cloudflared not installed."
      echo "Install with:  brew install cloudflared"
      exit 1
    fi

    echo ""
    hr
    bold "Cloudflare Quick Tunnel — no card, no login, no DNS needed"
    hr
    echo ""
    echo "  Starting tunnel to http://localhost:8000 …"
    echo "  A public URL will appear below (e.g. https://random-words.trycloudflare.com)"
    echo "  When detected, backend/.env is updated automatically."
    echo "  Then start (or restart) the backend: ./start.sh backend"
    echo ""

    # Run cloudflared, echo every line, and act on the URL when it appears.
    cloudflared tunnel --url http://localhost:8000 2>&1 | while IFS= read -r line; do
      echo "  cloudflared | $line"

      # Extract trycloudflare.com URL from the log line
      if [[ "$line" =~ (https://[a-zA-Z0-9-]+\.trycloudflare\.com) ]]; then
        DETECTED_URL="${BASH_REMATCH[1]}"

        # Auto-update backend/.env
        _set_env APP_PUBLIC_BASE_URL "$DETECTED_URL"

        echo ""
        hr
        bold "Public URL detected and saved to backend/.env:"
        bold ""
        bold "  ${DETECTED_URL}"
        bold ""
        bold "Share links will now be:  ${DETECTED_URL}/v/<token>"
        bold ""
        bold "Next step — restart the backend to apply:"
        bold "  ./start.sh backend"
        hr
        echo ""
      fi
    done
    ;;

  # ── set-url ──────────────────────────────────────────────────────────────────
  set-url)
    NEW_URL="${2:-}"
    if [ -z "$NEW_URL" ]; then
      echo "Usage: ./start.sh set-url <url>"
      echo "Example: ./start.sh set-url https://abc123.trycloudflare.com"
      exit 1
    fi
    _set_env APP_PUBLIC_BASE_URL "$NEW_URL"
    echo ""
    echo "  APP_PUBLIC_BASE_URL → $NEW_URL"
    echo "  Restart backend to apply: ./start.sh backend"
    echo ""
    ;;

  # ── tunnel (named — needs Zero Trust token) ───────────────────────────────────
  tunnel)
    if [ -z "$TUNNEL_TOKEN" ]; then
      echo ""
      echo "  NOTE: For quick sharing without any setup, use:"
      echo "    ./start.sh quicktunnel"
      echo ""
      echo "  For a named tunnel with a custom domain:"
      echo "    1. Go to https://one.dash.cloudflare.com/ → Networks → Tunnels"
      echo "    2. Create tunnel 'securedoc', copy the token"
      echo "    3. Add to backend/.env:  CLOUDFLARE_TUNNEL_TOKEN=<token>"
      echo "    4. Re-run: ./start.sh tunnel"
      exit 1
    fi
    echo "Starting named Cloudflare Tunnel …"
    echo "Public URL: ${PUBLIC_BASE}"
    exec cloudflared tunnel run --token "$TUNNEL_TOKEN"
    ;;

  # ── check ────────────────────────────────────────────────────────────────────
  check)
    PUBLIC_BASE="$(_read_env APP_PUBLIC_BASE_URL http://localhost:8000)"
    echo ""
    echo "  Stack health"
    echo "  ────────────"
    if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
      echo "  Backend  :8000   ✓"
    else
      echo "  Backend  :8000   ✗  (run: ./start.sh backend)"
    fi
    if redis-cli ping >/dev/null 2>&1; then
      echo "  Redis            ✓"
    else
      echo "  Redis            ✗  (run: brew services start redis)"
    fi
    echo ""
    echo "  APP_PUBLIC_BASE_URL = ${PUBLIC_BASE}"
    if [[ "$PUBLIC_BASE" == *"trycloudflare.com"* ]]; then
      echo "  Mode: Cloudflare Quick Tunnel (globally shareable)"
    elif [[ "$PUBLIC_BASE" == "http://localhost"* ]]; then
      echo "  Mode: Local only (run ./start.sh quicktunnel for global sharing)"
    else
      echo "  Mode: Custom domain"
    fi
    echo "  Share URL: ${PUBLIC_BASE}/v/<token>"
    echo ""
    ;;

  # ── help ─────────────────────────────────────────────────────────────────────
  *)
    PUBLIC_BASE="$(_read_env APP_PUBLIC_BASE_URL http://localhost:8000)"
    echo ""
    hr
    bold "SecureDoc startup helper"
    hr
    echo ""
    bold "ONE-COMMAND STARTUP (Docker)"
    echo "    ./start.sh all           Build + start everything, then run tests"
    echo "    make up                  Same via Makefile"
    echo ""
    bold "LOCAL DEV (native, separate terminals)"
    echo "    ./start.sh backend       FastAPI on :8000 (demo storage)"
    echo "    ./start.sh worker        Celery PDF worker"
    echo ""
    bold "TESTING"
    echo "    ./start.sh test          Unit test suite (SQLite mocks)"
    echo "    make test                Same via Makefile"
    echo ""
    bold "GLOBAL SHARING"
    echo "    ./start.sh quicktunnel   Free public URL via trycloudflare.com"
    echo "    ./start.sh set-url URL   Manually set APP_PUBLIC_BASE_URL"
    echo "    ./start.sh tunnel        Named Cloudflare Tunnel (needs token)"
    echo "    ./start.sh check         Health-check the stack"
    echo ""
    bold "CURRENT CONFIG"
    echo "    APP_PUBLIC_BASE_URL = ${PUBLIC_BASE}"
    if [[ "$PUBLIC_BASE" == *"trycloudflare.com"* ]]; then
      echo "    Mode: Cloudflare Quick Tunnel (globally shareable)"
    elif [[ "$PUBLIC_BASE" == "http://localhost"* ]]; then
      echo "    Mode: local only — run './start.sh quicktunnel' for global sharing"
    else
      echo "    Mode: custom domain"
    fi
    echo "    Share URL: ${PUBLIC_BASE}/v/<token>"
    echo ""
    hr
    ;;

esac
