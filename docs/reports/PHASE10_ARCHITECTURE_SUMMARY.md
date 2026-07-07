# Architecture Summary — Phase 10

**Project:** Retrieval Intelligence Platform (RIP)
**Scope:** Concise architecture summary for the v1.0.0 release.

The full guide (with diagrams) is `docs/ARCHITECTURE.md`; the 19-part deep
dive is in `docs/architecture/`.

---

## 1. One-Paragraph Summary

RIP is a modular, async-first RAG platform: a FastAPI backend exposes
versioned REST APIs (RAG + enterprise) over an async SQLAlchemy data layer and
a FAISS vector store, while a React/TypeScript SPA consumes them. Documents
flow Loader → Preprocess → Chunk → Embed → Vector Store; queries flow Query
Expansion → Hybrid Retrieval → Rerank → Dynamic Top-K → Grounded Generation,
with citations. An enterprise layer adds JWT/OAuth auth, RBAC, workspaces,
persistent chat, admin/audit, and export — all audited and configuration-driven.

## 2. Layers

| Layer | Key Modules | Role |
|-------|-------------|------|
| Edge | `api/middleware.py` | Rate limit, security headers, CORS, correlation ID, version header |
| API | `api/routers/*`, `enterprise/routers.py` | Versioned REST surface |
| Domain | `enterprise/services.py` | Business logic (auth, workspaces, conversations, admin) |
| Pipeline | `data/{loaders,chunking,embeddings}`, `retrieval`, `generation` | RAG core |
| Storage | `vectorstore`, `enterprise/database.py` | FAISS + SQLAlchemy (SQLite/Postgres) |
| Quality | `evaluation`, `data/experiments` | Ragas/DeepEval, MLflow/WandB |
| Validation | `embedding_validation` | Benchmarking + profiling |

## 3. Data Flow (TL;DR)

```
Document → Loader → Clean → Chunk → Embed → FAISS
Query → Expand → Hybrid(Dense+BM25) → RRF → Rerank → Top-K → LLM (+citations)
```

## 4. Auth & AuthZ Model

- **Auth:** bcrypt passwords, HS256 JWT access (900s) + refresh (rotation),
  optional Google OAuth, single-use hashed reset/verify tokens.
- **AuthZ:** RBAC — `admin` (all), `member` (create/export/delete own),
  `viewer` (shared-KB read). Enforced via `get_current_active_user`,
  `require_roles`, `require_permissions` dependency factories.

## 5. Critical Design Decisions

1. **Config over convention** — env-driven, fail-fast validation.
2. **Async I/O** — FastAPI + SQLAlchemy 2.0 async; `get_db` commits on success.
3. **Audit by default** — mutating enterprise actions append `AuditLog`.
4. **Fail-closed RBAC** — unknown roles degrade to `viewer`.
5. **Swappable stages** — factories/DI for loaders, embedders, retrievers,
   providers.

## 6. Scalability Posture

- Stateless API → horizontal scale behind a LB with shared Postgres + Redis.
- FAISS in-memory indexes; serialize to disk.
- Embedding similarity is O(n²) — sample/FAISS-ANN recommended beyond ~10K
  vectors (documented; non-blocking).
- Prometheus metrics + OTLP tracing for observability.

## 7. Extensibility Hooks

- New loader → register in `LoaderFactory`.
- New embedding/LLM provider → provider factory + `GenerationSettings`.
- New retriever → `RetrievalStrategy` plug-in.
- New permission/role → extend `rbac.Permission` / `ROLE_PERMISSIONS`.
