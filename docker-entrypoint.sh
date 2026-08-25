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
    python - <<'VALIDATE'
import sys

# Import the real application module. Validating only backend.api.config used to
# print "configuration valid" and then let uvicorn crash on import, because the
# enterprise layer (which requires ENTERPRISE_JWT_SECRET_KEY) was never touched.
try:
    from backend.api.config import get_settings as get_api_settings
    from backend.configs.settings import get_settings as get_app_settings

    api_settings = get_api_settings()
    api_settings.validate_for_environment()

    import backend.enterprise.config  # noqa: F401 - fails fast without a JWT secret

    get_app_settings().generation.validate_for_environment(api_settings.environment)

    import backend.api.app  # noqa: F401 - proves the ASGI app imports cleanly

    print(f"configuration valid (environment={api_settings.environment})")
except Exception as exc:  # noqa: BLE001 - surface any misconfiguration clearly
    print(f"configuration validation failed: {type(exc).__name__}: {exc}")
    sys.exit(1)
VALIDATE
}

run_migrations() {
    # Alembic owns the schema. `alembic upgrade head` is idempotent and safe to
    # run on every boot; it replaces the previous create_all-on-startup, which
    # had no way to evolve an existing Postgres schema.
    if [ -f "/app/alembic.ini" ] || [ -f "./alembic.ini" ]; then
        echo "Applying database migrations..."
        alembic upgrade head
    else
        echo "No alembic.ini found; skipping migrations."
    fi
}

case "${1:-serve}" in
    serve)
        validate_config
        run_migrations
        # --forwarded-allow-ips defaults to the local peer rather than '*':
        # trusting X-Forwarded-For from any source let clients spoof their
        # address and bypass per-IP rate limiting. Set FORWARDED_ALLOW_IPS
        # to your reverse proxy's address when running behind one.
        exec uvicorn backend.api:app \
            --host "${HOST}" \
            --port "${PORT}" \
            --workers "${WORKERS}" \
            --proxy-headers \
            --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
        ;;
    migrate|setup)
        validate_config
        run_migrations
        ;;
    *)
        exec "$@"
        ;;
esac
