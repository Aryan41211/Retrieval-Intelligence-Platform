#!/usr/bin/env sh
# Container entrypoint for the Retrieval Intelligence Platform API.
#
# Responsibilities:
#   1. Validate configuration early (fail fast before serving traffic).
#   2. Apply sane defaults for the managed runtime.
#   3. Launch uvicorn with a non-root, single-worker ASGI server.
set -eu

# Resolve the bind port (container platforms inject $PORT).
PORT="${PORT:-${API_PORT:-8000}}"
HOST="${API_HOST:-0.0.0.0}"
WORKERS="${API_WORKERS:-1}"

validate_config() {
    python - <<'PY'
import sys
try:
    from backend.api.config import get_settings
    get_settings().validate_for_environment()
    print("configuration valid")
except Exception as exc:  # noqa: BLE001 - surface any misconfiguration clearly
    print(f"configuration validation failed: {exc}")
    sys.exit(1)
PY
}

case "${1:-serve}" in
    serve)
        validate_config
        exec uvicorn backend.api:app \
            --host "${HOST}" \
            --port "${PORT}" \
            --workers "${WORKERS}" \
            --proxy-headers \
            --forwarded-allow-ips '*'
        ;;
    migrate|setup)
        validate_config
        echo "No schema migrations required for the default SQLite/vector store backend."
        ;;
    *)
        exec "$@"
        ;;
esac
