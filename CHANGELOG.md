# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Hardening pass following a full end-to-end audit. Nothing in the ingestion →
retrieval → generation path changed behaviourally except where it was broken.

### Added - multi-tenancy and file ingestion

- **Per-tenant knowledge bases.** Documents were written to a single
  process-wide index, so any authenticated user could retrieve any other user's
  documents. Each user now has a private namespace and each workspace a shared
  one; retrieval fans out across only the namespaces the caller may read and
  merges the results. Namespace ids are validated as filename-safe.
- **File upload.** `POST /documents/upload/file` accepts multipart uploads and
  parses them through the loader registry, making the PDF/DOCX/Markdown/TXT
  loaders reachable from the API for the first time. Enforces the configured
  extension allow-list and size limit, and neutralises directory components in
  the uploaded filename.
- `GET /documents/list` and `DELETE /documents/{id}`, derived from the vector
  store's own records so the listing cannot disagree with what retrieval finds.
- `GET /documents/supported-formats` reports the accepted extensions and limit.

### Changed

- The Documents page now uploads files, targets a workspace, shows progress and
  lists indexed documents. It previously posted `FormData` to a JSON-only
  endpoint and called `list`/`delete`/`reindex` routes that did not exist.
- `get_scoped_retrieval_service` injects the embedding provider through
  `Depends` so `app.dependency_overrides` applies to it.

### Migration note

Documents already indexed in the shared `rip-default` index are **not**
automatically migrated, and are no longer returned by retrieval. Continuing to
read that index would preserve the cross-tenant leak. Re-upload them into the
owning user's or workspace's knowledge base.

### Fixed - deployment blockers

- **A production container never became healthy.** The image `HEALTHCHECK`
  probes `http://127.0.0.1:8000/...`, and a Kubernetes kubelet probes the pod
  IP. Neither can be listed in `API_TRUSTED_HOSTS`, which production *requires*
  be set - the pod IP does not exist until the pod is scheduled - so
  `TrustedHostMiddleware` answered every probe `400`. Compose then held the
  frontend at `depends_on: service_healthy` forever and Kubernetes crash-looped
  the pod. Health paths are now exempt from Host validation, which costs
  nothing: they return a fixed body and build no URLs, so there is no Host to
  poison. Every other path is still validated.
- **`API_TRUSTED_HOSTS` could not be set for the compose `api` service.** It was
  absent from the `environment:` block, so a value in `.env` never reached the
  container and `API_ENVIRONMENT=production docker compose up` always died on
  `must list explicit hostnames in production`. Added, along with
  `API_HSTS_ENABLED` and `API_METRICS_REQUIRE_AUTH`, both of which `DEPLOYMENT.md`
  tells you to set and neither of which was forwarded either.
- **The deployment preflight passed hosts that could not deploy.**
  `bootstrap_deployment.py` gated the signing secret on length alone, and
  `.env.example`'s own placeholder is 48 characters. A fresh host was told
  "Deployment prerequisites satisfied" and then refused to boot in production.
  It now applies the same placeholder and entropy rules as the settings layer,
  and repairs an existing bad value instead of leaving it in place. The rules are
  duplicated rather than imported - `backend.enterprise.config` raises at import
  time without a secret, the very state the bootstrap repairs - and a test pins
  the copies to the originals.
- **The documented `API_TRUSTED_HOSTS` value broke every request.**
  `DEPLOYMENT.md` showed `["api.example.com"]`, but the bundled nginx forwards
  the browser's `Host` (`proxy_set_header Host $host`), so what arrives is the
  *frontend's* hostname. Health probes stayed green while all real traffic
  returned `Invalid host header`. Corrected in `DEPLOYMENT.md` and in the
  setting's own description, which `.env.example` is generated from.
- **A rejected `Host` was undiagnosable.** Starlette returns a bare
  `400 Invalid host header` and logs nothing. Rejections are now logged at
  WARNING with the offending host and the configured list, deduplicated per host
  so an attacker-controlled header cannot flood the log.

- **`cp .env.example .env` produced an application that would not start.** The
  generator rendered every `None` default as `KEY=`, and pydantic-settings reads
  that as the empty string rather than as absent. For the two optional numeric
  settings (`EMBEDDING_VALIDATION_EXPECTED_DIMENSION`,
  `RETRIEVAL_SIMILARITY_THRESHOLD`) that aborted import with
  `unable to parse string as an integer`. Optional settings are now emitted
  commented out, and four tests in `backend/tests/unit/test_config/` pin it.
- **The CI security job could never pass.** `pip-audit -r requirements.txt
  --fail-on-vuln` aborted with `unrecognized arguments: --fail-on-vuln` before
  auditing anything - pip-audit has no such flag and already exits non-zero on
  findings. The audit is now split: `requirements-runtime.txt` (what actually
  ships in the image) is blocking and currently clean; the dev-tooling set is
  advisory, so a CVE in `pytest` or `black` no longer gates a release.
- **Prometheus could never authenticate.** `deploy/prometheus.yml` reads its
  bearer token from `/etc/prometheus/metrics_token` and `DEPLOYMENT.md` told you
  to write `deploy/metrics_token`, but compose only ever mounted
  `prometheus.yml`. Compose now mounts the whole `./deploy` directory, avoiding
  the single-file bind that silently creates a directory when the path is absent.
- **The frontend image had no `.dockerignore`.** `COPY . .` after `npm ci`
  overwrote the container's dependencies with the host's `node_modules`,
  shipping platform-native binaries into a linux image.
- Runtime state (`data/`) and `.env` were excluded from neither `.gitignore` nor
  `.dockerignore`, so a local FAISS index was one `git add` away from being
  committed and shipped.
- Three `run:` blocks in `ci.yml` had lost their line continuations and had run
  together into single lines.
- `scripts/` was never linted; it had a real ruff error and formatting drift.
  CI now covers it.

- **Production accepted placeholder signing secrets.** `FORBIDDEN_SECRETS`
  matched six exact strings, so the shapes people actually paste -
  `dev-secret-key-change-in-production-32chars-long`,
  `test-secret-key-not-for-prod-use-...` - cleared every length and entropy
  check. A guessable HS256 key means anyone can mint an admin token.
  `API_ENVIRONMENT=production` now refuses to start on a placeholder-shaped
  secret; non-production keeps accepting throwaway values, which is where they
  belong. DEPLOYMENT.md previously claimed this protection existed.
- **The API image shipped the CUDA build of torch.** `pip install torch` from
  PyPI dragged ~2.5 GB of `nvidia_*` wheels (cuBLAS, cuDNN, cuFFT, NCCL, ...)
  into an image with no GPU runtime that pairs torch with `faiss-cpu`. The
  builder now installs the CPU wheel from PyTorch's index first; override
  `TORCH_INDEX_URL` to build a GPU image.
- **`asyncpg` was missing from `pyproject.toml`.** It was listed in both
  requirements files, so containers were fine, but `pip install -e .` - the
  install path the README documents - could not open any Postgres
  `DATABASE_URL`, which is what the compose stack defaults to.

### Added - deployment

- `scripts/bootstrap_deployment.py` generates `ENTERPRISE_JWT_SECRET_KEY` and
  `API_METRICS_TOKEN`, writes `deploy/metrics_token` so the API and Prometheus
  agree, and offers `--check` (verify a host, change nothing) and `--force`
  (rotate). The two secrets that have no safe default are the two things a first
  deployment reliably gets wrong.

### Fixed - critical

- **CI ran zero tests.** `-m unit` / `-m integration` filtered on markers no
  test carried, so all 292 tests were deselected while the job reported success.
  Markers are now applied automatically by directory.
- **`mypy` could not run at all** (`Source file found twice under different
  module names`) and blocked every other job via `needs:`. Added the 10 missing
  `__init__.py` files; type checking is now a separate advisory job.
- **`asyncio_mode` was in a section pytest never reads**, silently skipping 10
  async integration tests. Enabling them immediately surfaced a real defect.
- **No LLM provider could authenticate.** `ProviderFactory` built every provider
  with only a model name — no API key, and OpenAI defaulting to localhost. Added
  `GENERATION_API_KEY` / `GENERATION_BASE_URL` and per-provider endpoints.
- **A typo in `GENERATION_PROVIDER` silently served fabricated answers**, because
  any unrecognised value fell back to the development stub. Unknown providers now
  raise, and the stub is rejected in production.
- **Provider outages returned HTTP 500** instead of a graceful "I don't know":
  `llm_latency_ms` was referenced before assignment in the error handler.
- **`DATABASE_URL` named a synchronous driver** in `.env`, `.env.example` and
  `docker-compose.yml`, so every database-backed request failed against the async
  engine. URLs are now normalised, with a clear error for unsupported schemes.
- **The container started without its mandatory JWT secret**: the pre-flight
  check validated a module that never touched the enterprise settings, printed
  "configuration valid", then crashed on import.
- **The frontend could not authenticate to its own backend** — no token storage,
  no `Authorization` header, no login page. Every request returned 401.
- **Prometheus label cardinality was unbounded**: metrics were labelled with the
  raw request path, so every path parameter value allocated new time series.
- **Concurrent uploads could discard each other's embeddings** — the shared FAISS
  index was mutated with no mutual exclusion.

### Fixed - security

- Added the missing authorization check on `GET /workspaces/{id}/members`; any
  authenticated user could enumerate any workspace's membership.
- OAuth `state` is now validated and single-use (was generated, then ignored).
- OAuth logins require the provider's `email_verified` claim, closing an account
  takeover against existing local accounts.
- Login now performs an equivalent bcrypt verification for unknown identifiers,
  removing a timing oracle for user enumeration.
- `/metrics` requires a bearer token (previously public).
- Rate-limiter buckets are bounded with LRU eviction; authentication endpoints
  have their own stricter budget.
- `X-Forwarded-For` is honoured only when explicitly configured, and read from a
  trusted hop, so clients can no longer spoof their address past the limiter.
- CORS moved to the outermost middleware layer so 429/413 responses carry CORS
  headers instead of surfacing as opaque browser errors.
- The pickled index sidecar is checksum-verified before deserialization.
- JWT secrets must be ≥32 characters with sufficient variety.
- All user-supplied inputs are length/range bounded; role fields are enums.
- Debug logging no longer emits SQL bind parameters; client errors carry a
  correlation id rather than raw exception text.

### Added

- Hybrid retrieval (BM25 + RRF + optional cross-encoder rerank) wired into the
  API behind `INTELLIGENT_RETRIEVAL_ENABLED`; previously unreachable dead code.
- Full authentication UI: login/registration, session restore, transparent token
  refresh with request replay, route guards, role-gated admin page, user menu.
- Persistent chat history backed by the conversations API, with SSE parsing that
  matches what the endpoint actually returns.
- Alembic migrations with a baseline revision; the entrypoint applies them.
- Frontend container (nginx) and a full-stack `docker-compose` including volumes.
- `scripts/generate_env_example.py` — `.env.example` is generated from the
  settings classes and drift-checked in CI.
- `EmbeddingSettings`: the embedding model and device are configurable rather
  than hardcoded.
- Startup cache warm-up so the first request does not pay the model load.
- Readiness probe now checks the database and returns 503 when unhealthy.

### Changed

- Ingestion and retrieval run in a worker thread; the event loop no longer
  blocks for the duration of every embed/index/search.
- Dependencies pinned with upper bounds and split into optional extras. Core
  runtime dropped from 50 to 25 packages; ragas, deepeval, mlflow, wandb,
  chromadb, langchain and friends were never imported.
- Added the missing `email-validator` (via `pydantic[email]`), without which
  `pip install -e .` produced an unimportable package.
- Frontend bundle split: main chunk 1152 KB → 103 KB.
- README corrected: the quick-start command was wrong, and the evaluation,
  experiment-tracking and token-streaming features are now marked as not
  implemented rather than advertised as shipping.

## [1.0.0] - 2026-07-08

### Added
- Phase 9: Enterprise features — authentication (JWT/OAuth/refresh/password-reset/email-verify), RBAC authorization, user management, multi-user workspaces with shared knowledge bases, persistent collaborative chat (history/search/rename/delete), admin dashboard with analytics and audit/activity logs, and conversation export (JSON/Markdown/PDF)
- Frontend `enterpriseApi` service client and typed enterprise models
- Comprehensive enterprise test suite (65 tests)
- Config-driven rate-limit toggle (`API_RATE_LIMIT_ENABLED`) for the API middleware
- Sprint 4: Embedding validation framework with profiling, benchmarking, and duplicate detection
- Sprint 3: Intelligent retrieval pipeline with BM25, RRF fusion, cross-encoder reranking, query expansion, and dynamic top-k selection
- Sprint 2: Embedding pipeline with batch processing, caching, and validation
- Sprint 1: Document loading, preprocessing, chunking, and vector store infrastructure
- End-to-end RAG pipeline orchestrator (`RAGPipeline`) integrating retrieval and generation
- Integration test suite covering 8 validation scenarios for the RAG pipeline
- Missing generation pipeline components: `LLMGateway`, `CitationGenerator`, `ResponseValidator`, `HallucinationGuard`
- Missing LLM provider stubs: `OpenAICompatibleProvider`, `OllamaProvider`, `NIMProvider`
- `GenerationSettings` configuration class and provider factory wiring

### Changed
- `enterprise.database.get_db` now commits on success and rolls back on error so writes persist (previously flushed but never committed)
- Enterprise settings validated fail-fast; JWT secret is mandatory in production
- Unified exception hierarchy: `VectorStoreError` now inherits from `RipError`
- `ProviderFactory.create()` now reads from unified `GenerationSettings` instead of nested provider config
- Enhanced `GenerationPipeline.from_config()` to build complete pipeline with all components

### Fixed
- Critical data-loss bug: `get_db` discarded all writes on session close
- Critical import failures in `generation_pipeline.py` caused by missing pipeline component modules
- `ProviderFactory` broken configuration reads for `settings.generation.provider.provider_type`
- Standardized exception base classes across vector store and embedding modules

## [0.1.0] - 2026-06-27

### Added
- Project initialization with clean architecture
- Directory structure following modular design principles
- Core configuration infrastructure
- Development environment setup
- Code quality tooling
- Testing framework configuration
