# Deployment

How to run the Retrieval Intelligence Platform in a real environment.

---

## Required configuration

The application **will not start** without these. Both are validated at boot —
misconfiguration fails fast rather than surfacing later as a broken request.

| Variable | Why |
|---|---|
| `ENTERPRISE_JWT_SECRET_KEY` | Signs access/refresh tokens. Minimum 32 characters, and rejected outright if it has too little variety. In `production` a value that *looks* like a copied placeholder (contains `change-in-production`, `dev-secret`, `example`, `ci-only`, ...) is refused too, because a guessable HS256 key means forgeable admin tokens. Generate with `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `GENERATION_PROVIDER` + `GENERATION_API_KEY` | The default provider is `fake`, a development stub that returns canned text. It is **refused outright** when `API_ENVIRONMENT=production`. |

Additionally, in `production` the following are rejected:

- `API_CORS_ORIGINS=["*"]` — list your real frontend origins.
- `API_TRUSTED_HOSTS=["*"]` — list your real hostnames.

Every supported variable is documented in [`.env.example`](.env.example), which
is **generated from the settings classes**:

```bash
python scripts/generate_env_example.py          # regenerate
python scripts/generate_env_example.py --check  # CI drift check
```

---

## Docker Compose (recommended for a single host)

```bash
python scripts/bootstrap_deployment.py    # writes .env + deploy/metrics_token
docker compose up --build
```

`bootstrap_deployment.py` creates `.env` from `.env.example`, generates
`ENTERPRISE_JWT_SECRET_KEY` and `API_METRICS_TOKEN`, and writes the metrics
token to `deploy/metrics_token` so the API and Prometheus agree on it. Re-running
it only fills in what is missing; `--force` rotates both secrets, and `--check`
verifies a host without writing anything.

To do it by hand instead:

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"   # -> ENTERPRISE_JWT_SECRET_KEY
```

Keys that are **commented out** in `.env.example` are optional — leave them
commented. Assigning an empty value is not the same as leaving one unset, and
for the numeric settings it fails validation at startup.

| Service | Port | Purpose |
|---|---|---|
| `frontend` | 3000 | React SPA on nginx; proxies `/api` to the API |
| `api` | 8000 | FastAPI application |
| `postgres` | — | Conversations, users, workspaces, audit log |
| `redis` | — | Reserved for shared rate limiting |
| `prometheus` | 9090 | Scrapes `/api/v1/metrics` |

Open <http://localhost:3000> and register an account.

**Persistence.** The `apidata` volume holds the FAISS index (and the SQLite
database if you are not using Postgres). Without it, the knowledge base is lost
on every restart.

**Compose refuses to start** if `ENTERPRISE_JWT_SECRET_KEY` is unset — that is
deliberate, not a bug.

---

## Database migrations

Alembic owns the schema.

```bash
alembic upgrade head                       # apply
alembic current                            # inspect
alembic revision --autogenerate -m "..."   # after changing models.py
```

The container entrypoint runs `alembic upgrade head` on every start (idempotent),
and the image sets `DB_AUTO_CREATE=false` so the app does not also run
`create_all`. Local development leaves `DB_AUTO_CREATE` unset, which creates
tables directly from the models.

`DATABASE_URL` must reach an **async** driver. A synchronous URL is upgraded
automatically (`postgresql://` → `postgresql+asyncpg://`), and an unsupported
scheme fails immediately with a clear message.

---

## Running behind a reverse proxy

Per-IP rate limiting is only as trustworthy as the client address, so proxy
headers are **not** trusted by default.

```bash
API_TRUST_PROXY_HEADERS=true
API_TRUSTED_PROXY_COUNT=1        # hops between the client and this app
FORWARDED_ALLOW_IPS=10.0.0.5     # uvicorn: your proxy's address, not '*'
```

With `TRUSTED_PROXY_COUNT=1` the client IP is read one hop from the right of
`X-Forwarded-For`, which a spoofed prefix cannot reach. Leaving these unset
means the direct peer address is used — correct for a directly exposed service.

Also set:

```bash
API_HSTS_ENABLED=true            # only behind TLS
API_TRUSTED_HOSTS=["app.example.com"]
API_CORS_ORIGINS=["https://app.example.com"]
```

**`API_TRUSTED_HOSTS` lists the hostnames browsers use, not the API's.** The
bundled nginx forwards the original `Host` header (`proxy_set_header Host
$host`), so what reaches the API is whatever the browser typed — the *frontend's*
hostname. Listing `api.example.com` while users visit `app.example.com` leaves
the health probes green and 400s every real request with `Invalid host header`.
Include every hostname the app is reached by, and the API's own if it is also
exposed directly:

```bash
API_TRUSTED_HOSTS=["app.example.com","api.example.com"]
```

A rejected Host is logged at WARNING with the offending value and the configured
list, so check the API logs first if requests 400 while `/health/ready` is fine.

The health endpoints are deliberately exempt from this check. Orchestrators
probe by address — the image `HEALTHCHECK` uses `127.0.0.1` and a Kubernetes
kubelet uses the pod IP, which cannot be known in advance — and those endpoints
reflect no `Host` anywhere, so validating it there only ever broke deployments.

---

## Metrics

`/api/v1/metrics` requires authentication. Prometheus cannot log in, so give it
a dedicated token:

```bash
python scripts/bootstrap_deployment.py    # sets both sides consistently
```

The API reads the token from `API_METRICS_TOKEN`; Prometheus presents the
contents of `deploy/metrics_token`. **The two must match** or every scrape
returns 401. Compose mounts the whole `./deploy` directory at `/etc/prometheus`,
so the token file is picked up alongside `prometheus.yml`.

A normal user access token is also accepted. On a fully private network you may
set `API_METRICS_REQUIRE_AUTH=false` and drop the `authorization` block from
`deploy/prometheus.yml`.

`deploy/metrics_token` is git-ignored — it is a generated credential, not
configuration.

---

## Scaling

Single-instance deployments work as shipped. Before running multiple replicas,
be aware of two **per-process** stores:

| Component | Consequence of replicas |
|---|---|
| Rate limiter buckets | Effective limit multiplies by replica count |
| OAuth `state` store | A callback may land on a replica that never issued the state |

Both need a shared backend (Redis) first. The `redis` service and `REDIS_URL`
are already provisioned for this.

The FAISS index is also process-local and guarded by an in-process write lock,
so concurrent ingestion is safe **within** one instance. Multi-instance writes
need an external vector store.

---

## Health probes

| Endpoint | Meaning | Use for |
|---|---|---|
| `/api/v1/health/live` | Process is up | Liveness probe |
| `/api/v1/health/ready` | Database reachable, vector store writable | Readiness probe |
| `/api/v1/health` | Version and uptime | Dashboards |

`/health/ready` returns **503** when a dependency is down and reports each check
individually, so an orchestrator stops routing traffic to a broken instance.

Allow a generous start period: the embedding model is loaded at startup
(deliberately, so the first request does not pay for it). The compose
healthcheck uses `start_period: 90s`.

---

## Platform notes

**Kubernetes.** Use `/health/live` and `/health/ready` as the probes, mount a
PVC at `/app/data`, and supply `ENTERPRISE_JWT_SECRET_KEY` from a Secret. Run
migrations as an init container: `docker-entrypoint.sh migrate`.

**Railway / Render.** Both inject `$PORT`, which the entrypoint honours. Set the
required variables above; use a managed Postgres and set `DATABASE_URL`.

**Workers.** `API_WORKERS` defaults to 1. CPU-bound work (embedding, indexing)
runs in a thread pool so the event loop stays responsive, but each worker holds
its own embedding model and FAISS index — size memory accordingly, and do not
run multiple workers while the vector store is process-local.
