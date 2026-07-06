# Deployment Guide

The Retrieval Intelligence Platform (RIP) API is a single FastAPI/ASGI process.
It is containerised via a multi-stage `Dockerfile` (non-root, hardened, with
health checks) and can be deployed to Railway, Render, AWS or Azure.

> **Prerequisites**
> - A container image built from the `Dockerfile`, or direct Python execution
>   (`uvicorn backend.api:app`).
> - Set `API_ENVIRONMENT=production` and supply secrets via the platform secret
>   store (never bake secrets into the image).
> - Bind to `0.0.0.0` on the platform-provided `$PORT`.

## Endpoints

| Path | Purpose |
|------|---------|
| `/api/v1/health/live` | Liveness probe. |
| `/api/v1/health/ready` | Readiness probe (dependency checks). |
| `/api/v1/health` | Service info (env, version, uptime). |
| `/api/v1/metrics` | Prometheus metrics. |
| `/docs`, `/redoc` | Interactive docs (auto-disabled in production). |

---

## Railway

Railway supports Dockerfile-based deployments directly.

1. Create a new project and link the Git repository.
2. Add a service from the repo root; Railway auto-detects the `Dockerfile`.
3. Set environment variables (Variables tab):
   - `API_ENVIRONMENT=production`
   - `API_DOCS_ENABLED=false`
   - `API_HSTS_ENABLED=true`
   - `API_CORS_ORIGINS=["https://your-frontend.example.com"]`
   - `OPENAI_API_KEY`, `DATABASE_URL`, `REDIS_URL`, etc. (mark as secret).
4. Railway assigns a `$PORT`; the container reads it automatically.
5. Use the generated `/api/v1/health/ready` endpoint as the health check URL.

Railway automatically provides `REDIS_URL` if you add a Redis plugin; wire it
to `REDIS_URL`.

---

## Render

Render supports Docker and also a direct Python web service.

**Option A — Docker (recommended):**

1. New → Web Service → connect repo, select "Docker".
2. Set `API_ENVIRONMENT=production` and other vars in the Environment section
   (use the "Secret" toggle for keys).
3. Render exposes `$PORT`; the entrypoint binds to it.
4. Health check path: `/api/v1/health/ready`.

**Option B — Python (no Docker):**

1. Runtime: `Python 3.12`; Build command: `pip install -r requirements.txt`.
2. Start command:
   `uvicorn backend.api:app --host 0.0.0.0 --port $PORT --workers 1`
3. Add the same environment variables.

---

## AWS

### Elastic Container Service (Fargate) + Application Load Balancer

1. Push the image to **Amazon ECR** (`aws ecr create-repository`, `docker push`).
2. Create a **Fargate** task definition:
   - Container port `8000`, `essential: true`.
   - `healthCheck` → `CMD-SHELL`, `python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/live').status==200 else 1)"`.
   - `logConfiguration` → `awslogs` to CloudWatch (JSON logs are parsed).
3. ALB target group health check: `/api/v1/health/ready` (HTTP 200).
4. Store secrets in **AWS Secrets Manager** and inject as env vars via task
   definitions (`valueFrom` ARN).
5. (Optional) Scale with an Auto Scaling policy on request count.

### Alternatives

- **App Runner:** Point at the ECR image; set `API_PORT`/`$PORT` and env vars.
- **ECS + Copilot:** `copilot svc init` using the Dockerfile.

---

## Azure

### Container Apps (recommended)

1. `az containerapp up` (or Bicep) referencing the built image in ACR.
2. Ingress: external, target port `8000`.
3. Set `API_ENVIRONMENT=production` and secrets as **secret** env vars.
4. Health probes:
   - Liveness: `GET /api/v1/health/live`
   - Readiness: `GET /api/v1/health/ready`
5. Mount Azure Key Vault secrets as env vars via the managed identity.

### Alternatives

- **App Service (Containers):** set `WEBSITES_PORT=8000`, `API_ENVIRONMENT=production`,
  and configure health check path `/api/v1/health/ready`.
- **AKS:** deploy the image with a `Deployment` + `Service` + `Ingress`, using
  the supplied `docker-compose.yml` as a reference topology (api + redis +
  postgres + prometheus).

---

## Observability in production

- Scrape `/api/v1/metrics` with Prometheus (see `deploy/prometheus.yml`).
- Ship JSON stdout logs to your aggregator (CloudWatch, Log Analytics, Loki).
- Correlation IDs are echoed in every response under `X-Correlation-ID` and
  attached to every structured log line for end-to-end tracing.

## Notes on image size

The runtime image installs the full ML dependency set (PyTorch CPU,
`sentence-transformers`, `chromadb`, `mlflow`, `wandb`, etc.). Expect a large
image. To reduce size you can:
- Move optional providers (MLflow/W&B, DeepEval) to optional extras.
- Use a GPU/base image only where embeddings run in-process.
- Pre-bake the image in a registry and pull by digest.
