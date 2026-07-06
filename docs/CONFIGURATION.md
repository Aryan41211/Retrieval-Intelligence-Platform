# Configuration Reference

This document describes the runtime configuration for the **API process**
(`backend.api`). Domain/pipeline configuration lives in
`backend/configs/settings.py`; this file focuses on the web/runtime layer.

All settings are read from environment variables with the `API_` prefix and
validated on startup (fail-fast). Nothing is hardcoded.

## Core

| Variable | Default | Description |
|----------|---------|-------------|
| `API_ENVIRONMENT` | `development` | `development` \| `staging` \| `production`. Drives docs/HSTS/debug defaults. |
| `API_HOST` | `0.0.0.0` | Bind host. |
| `API_PORT` | `8000` | Bind port. Overridden by `$PORT` on most PaaS. |
| `API_DOCS_ENABLED` | `true` | Expose `/docs`, `/redoc`, `/openapi.json`. Auto-disabled in `production`. |
| `API_LOG_FORMAT` | `json` | `json` (structured) or `text`. |
| `API_LOG_LEVEL` | `INFO` | `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`. |
| `API_LOG_FILE` | _(unset)_ | Optional log file; defaults to stdout. |

## CORS

| Variable | Default | Description |
|----------|---------|-------------|
| `API_CORS_ORIGINS` | `["*"]` | Allowed origins. **Must be explicit in production** (no `*` with credentials). |
| `API_CORS_CREDENTIALS` | `false` | Allow credentialed requests. |
| `API_CORS_METHODS` | common set | Allowed HTTP methods. |
| `API_CORS_HEADERS` | `["*"]` | Allowed request headers. |

> **Validation rule:** credentialed CORS (`API_CORS_CREDENTIALS=true`) together
> with a wildcard origin (`*`) raises at startup. This prevents the insecure
> browser configuration where any site can make authenticated requests.

## Rate limiting

| Variable | Default | Description |
|----------|---------|-------------|
| `API_RATE_LIMIT_PER_MINUTE` | `120` | Sustained requests per client IP per minute. |
| `API_RATE_LIMIT_BURST` | `20` | Extra burst capacity above the sustained rate. |

The in-memory token-bucket limiter is per-process. For multi-replica
deployments, swap it for a shared store (e.g. Redis) — see `backend/api/middleware.py`.

## Security & observability

| Variable | Default | Description |
|----------|---------|-------------|
| `API_SECURITY_HEADERS_ENABLED` | `true` | Emit `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy`. |
| `API_HSTS_ENABLED` | `false` | Emit `Strict-Transport-Security`. Enable only behind TLS. |
| `API_CSP_POLICY` | `default-src 'self'` | CSP value for HTML responses. |
| `API_PROMETHEUS_ENABLED` | `true` | Expose `/api/v1/metrics` in Prometheus format. |
| `API_CORRELATION_HEADER` | `X-Correlation-ID` | Header carrying the per-request correlation id. |

## Secrets

Never store secrets in `.env` committed to the repository. Provide them via
the platform's secret store (Railway/Render variables, AWS Secrets Manager,
Azure Key Vault, GitHub Actions secrets). The following are **required** in
production and must come from a secret manager, not the image:

- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `COHERE_API_KEY`, `VOYAGE_API_KEY`
- `DATABASE_URL`, `REDIS_URL`
- `SECRET_KEY`, `RAGAS_API_KEY`, `DEEPEVAL_API_KEY`, `WANDB_API_KEY`

See `.env.example` for the full list of supported variables.
