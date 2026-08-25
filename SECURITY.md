# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ |
| < 1.0   | ❌ |

## Reporting a Vulnerability

We take the security of the Retrieval Intelligence Platform seriously. If you
discover a security vulnerability, **do not** open a public issue. Instead,
report it privately to the maintainers so fixes can land before disclosure.

**To report a vulnerability:**

1. Email the maintainers (see commit history for current addresses).
2. Include a description of the vulnerability, steps to reproduce, and
   affected versions.
3. Allow up to 72 hours for an initial response.

We will acknowledge receipt, investigate, and release a fix as soon as
practical. After the fix is released, you may publicly disclose the
vulnerability if you wish.

## Security Best Practices for Deployments

| Practice | Recommendation |
|----------|----------------|
| **JWT secret** | Generate with `openssl rand -hex 32`. Never use the dev default in production. |
| **API keys** | Store in a secret manager (AWS Secrets Manager, Azure Key Vault, GitHub Secrets). Never bake into images. |
| **CORS** | Set explicit origins in production. Never use `*` with credentialed requests. |
| **HTTPS** | Enable TLS behind a reverse proxy. Set `API_HSTS_ENABLED=true`. |
| **Database** | Use a managed Postgres with TLS. Never expose the database port publicly. |
| **Redis** | Set a strong `REDIS_PASSWORD`. Use TLS when connecting over the network. |
| **Logging** | JSON structured logs shipped to a secure aggregator. Never log secrets, tokens, or PII. |

## Configuration Validation

The platform validates critical settings on startup and will refuse to start if:

- `ENTERPRISE_JWT_SECRET_KEY` is empty or set to a known-insecure default
- CORS is configured with wildcard `*` and credentials are enabled
- `API_ENVIRONMENT=production` with `API_DOCS_ENABLED=true` (auto-disabled)

This fail-fast behavior ensures configuration errors are caught before
serving traffic.

## Dependency Scanning

- CI runs `pip-audit` on every push (fails on any known vulnerability).
- `bandit` static analysis runs on every push (`-ll` severity threshold).
- Pin dependency versions in `requirements.txt` and `pyproject.toml`.

## Authentication & Authorization

- Passwords are hashed with **bcrypt** (configurable rounds).
- Access tokens are **JWT (HS256)** with configurable TTL (default 15 min).
- Refresh tokens can be rotated (default 7-day TTL).
- RBAC is enforced at the API layer via FastAPI dependency guards.
- Unknown roles degrade to the most restrictive default (`viewer`).
