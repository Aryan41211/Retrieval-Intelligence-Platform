# Release Notes — v1.0.0

**Project:** Retrieval Intelligence Platform (RIP)
**Release:** `v1.0.0` — Production Release & Portfolio
**Date:** 2026-07-08
**Tag:** `v1.0.0`

---

## Highlights

The first production-grade release of RIP. It bundles a complete
Retrieval-Augmented Generation pipeline with an enterprise platform layer,
hardened runtime, full test coverage, and portfolio-ready documentation.

### What's in v1.0.0

- **End-to-end RAG pipeline** — document ingestion, chunking, embeddings,
  FAISS vector store, hybrid retrieval (dense + BM25 + RRF fusion),
  cross-encoder reranking, query expansion, dynamic top-k, and grounded
  generation with citations.
- **Enterprise platform** (`backend/enterprise/`)
  - JWT auth (access + refresh), optional Google OAuth, password reset,
    email verification.
  - Role-Based Access Control (`admin` / `member` / `viewer`).
  - User profiles, preferences, admin user management.
  - Multi-user workspaces with shared knowledge bases and team membership.
  - Persistent chat: history, full-text search, rename, delete, export.
  - Admin dashboard, analytics, audit & activity logs.
  - Conversation export to JSON / Markdown / PDF.
- **Production runtime** — structured JSON logging + correlation IDs,
  security headers, CORS, rate limiting, health/readiness/metrics probes,
  fail-fast configuration.
- **Evaluation & experimentation** — Ragas / DeepEval metrics, MLflow / WandB
  tracking.
- **Developer experience** — Docker multi-stage image, comprehensive docs
  (architecture, API, developer, contribution, benchmarks), Conventional
  Commits, `ruff` / `black` / `mypy` gates.

### Testing

- **65 enterprise tests** passing (unit + API integration + async service).
- Embedding validation framework: **84/84** tests.
- Full backend suite + frontend Vitest component tests.

### Cleanup (Phase 10)

- Removed the dead `backend/models/` compatibility shim (re-export of
  `backend/data/models`); this also clears a `mypy` duplicate-package
  collision.
- Confirmed `backend/embeddings` already consolidated into
  `backend/data/embeddings`.
- No `TODO`/`FIXME`/debug noise in shipped code.

---

## Upgrade / Deployment

- Containerised via the multi-stage `Dockerfile` (non-root, hardened).
- Set `API_ENVIRONMENT=production`, `ENTERPRISE_JWT_SECRET_KEY` (strong, from a
  secret manager), `DATABASE_URL`, and provider keys.
- Use `/api/v1/health/ready` as the health check.
- Full guide: [`DEPLOYMENT.md`](../DEPLOYMENT.md).

## Configuration Changes

- New `API_RATE_LIMIT_ENABLED` toggle (default on).
- Enterprise settings under `ENTERPRISE_*` (see
  [`docs/API.md`](./API.md#9-configuration)).

## Known Issues / Follow-ups

- `mypy` should be run with `--explicit-package-bases` (top-level namespace
  collisions in `backend.generation` etc.); does not affect runtime.
- Refresh tokens are stateless (no server-side revocation list yet).
- Frontend UI screens for the enterprise layer are wired at the service level
  (`enterpriseApi`); page UIs are a follow-up.
- Live benchmark numbers should be regenerated per deployment (see
  [`docs/BENCHMARKS.md`](./BENCHMARKS.md)).

## Contributors

The RIP team. See commit history for per-phase attribution.

---

**Full phase history:** Phases 1–9 (foundation → enterprise) + Phase 10
(release). Detailed reports in [`docs/reports/`](./reports/).
