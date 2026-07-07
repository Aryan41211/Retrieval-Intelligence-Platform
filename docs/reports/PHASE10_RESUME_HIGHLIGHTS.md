# Resume Highlights — Phase 10

**Project:** Retrieval Intelligence Platform (RIP)
**Use:** Bullet points and a project blurb for resumes / LinkedIn.

---

## 1. Project Blurb (1–2 lines)

> Built **RIP**, a production-grade Retrieval-Augmented Generation platform: a
> modular Python/FastAPI backend with hybrid retrieval, grounded generation,
> automated evaluation, and an enterprise layer (auth, RBAC, multi-tenant
> workspaces), fully tested, type-checked, and Docker-deployed.

---

## 2. Resume Bullets (copy-paste)

- Designed and shipped an end-to-end **RAG pipeline** (ingestion → chunking →
  embeddings → FAISS vector store → hybrid dense+BM25 retrieval with RRF
  fusion → cross-encoder reranking → grounded LLM generation with citations).
- Implemented **enterprise authentication & authorization**: JWT access/refresh
  tokens, Google OAuth, password-reset/email-verify flows (bcrypt), and
  **RBAC** with `admin`/`member`/`viewer` roles and a fail-closed permission
  model.
- Built **multi-tenant collaboration**: workspaces, shared knowledge bases, and
  team membership on an async SQLAlchemy data layer.
- Added **persistent chat** (history, full-text search, rename/delete) with
  **export to JSON/Markdown/PDF** and an **admin dashboard** with analytics and
  append-only **audit/activity logs**.
- Hardened the runtime for production: **structured JSON logging + correlation
  IDs**, rate limiting, security headers, health/readiness probes, Prometheus
  metrics, and fail-fast configuration.
- Established **quality engineering**: `ruff`/`black`/`mypy` gates, **>140
  unit/integration tests** (incl. 65 enterprise API tests), and comprehensive
  docs (architecture, API, developer, contribution, benchmarks).
- Caught and fixed a **data-loss bug** in the DB session layer (flush-without-
  commit) and resolved a `mypy` package-collision during release cleanup.

---

## 3. Skills to List

- **Languages:** Python 3.11+, TypeScript, SQL
- **Backend:** FastAPI, SQLAlchemy 2.0 (async), Pydantic, PyJWT, bcrypt
- **RAG/ML:** LangChain-style loaders, sentence-transformers, FAISS, hybrid
  retrieval, RRF, cross-encoder reranking, Ragas/DeepEval, MLflow/WandB
- **Frontend:** React, Vite, TanStack Query, Axios
- **Infra/Ops:** Docker (multi-stage, non-root), Prometheus, OTLP, CI discipline
- **Practices:** TDD, type-checking, RBAC security, config validation, docs

---

## 4. Interview Prep (behavioral + technical)

- *"Tell me about a bug you found."* → the `get_db` commit bug; how you
  reproduced it and fixed it without redesigning the system.
- *"How do you secure an API?"* → JWT + refresh rotation, OAuth, bcrypt,
  rate limiting, RBAC fail-closed, audit logging, secrets via env.
- *"How would you scale this?"* → stateless API behind a LB, shared
  Postgres+Redis, FAISS ANN for >10K vectors, async pipeline.
- *"How do you ensure quality?"* → typed code, lint/type gates, >80% coverage,
  integration tests, evaluation metrics as a feedback loop.

---

## 5. LinkedIn Hook

> Shipped **RIP v1.0.0** — a modular, production-grade RAG platform with
> hybrid retrieval, grounded generation, automated evaluation, and an
> enterprise layer (auth, RBAC, workspaces, audit). 140+ tests, fully
> documented, Docker-ready. #RAG #LLM #FastAPI #MLOps
