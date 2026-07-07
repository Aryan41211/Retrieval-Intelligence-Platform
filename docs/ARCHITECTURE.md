# Architecture Guide — Retrieval Intelligence Platform (RIP)

This guide is the single entry point to RIP's architecture. Detailed,
per-component write-ups live in [`docs/architecture/`](./architecture/); this
document provides the maps and the mental model. All diagrams are
[Mermaid](https://mermaid.js.org/) and render natively on GitHub.

---

## 1. System Overview

RIP is a modular Retrieval-Augmented Generation (RAG) platform. A FastAPI
backend exposes versioned REST APIs (RAG + enterprise) and an async SQLAlchemy
data layer; a React/TypeScript frontend consumes them. Configuration is
environment-driven and validated on startup.

```mermaid
flowchart TB
    subgraph Client["Client"]
        FE["React + TypeScript SPA"]
    end
    subgraph Edge["API Edge"]
        RL["Rate Limiter"]
        SEC["Security Headers + CORS"]
        CORR["Correlation ID / Logging"]
        VER["X-API-Version"]
    end
    subgraph API["FastAPI App (/api/v1)"]
        AUTH["Auth / Users / Workspaces"]
        CONV["Conversations"]
        ADMIN["Admin / Audit"]
        RAG["Chat / Retrieval / Documents"]
        EVAL["Evaluation / Experiments"]
        HLTH["Health / Metrics"]
    end
    subgraph Core["Domain Core"]
        LOAD["Loaders / Preprocess"]
        CHUNK["Chunking"]
        EMB["Embeddings"]
        VS["Vector Store (FAISS)"]
        RET["Retrieval (Hybrid + Rerank)"]
        GEN["Generation (LLM Gateway)"]
        EVALC["Evaluation (Ragas/DeepEval)"]
        EXP["Experiments (MLflow/WandB)"]
    end
    subgraph Ent["Enterprise"]
        AUTHDB[("Users / Workspaces\nConversations / Audit")]
    end
    subgraph Infra["Infrastructure"]
        DB[("Postgres / SQLite")]
        CACHE[("Redis")]
        OBS["Prometheus / OTLP"]
    end

    FE --> RL
    RL --> SEC --> CORR --> VER --> API
    AUTH --> AUTHDB --> DB
    CONV --> AUTHDB
    ADMIN --> AUTHDB
    RAG --> Core
    EVAL --> EVALC
    LOAD --> CHUNK --> EMB --> VS
    VS --> RET --> GEN
    Core --> CACHE
    API --> OBS
```

---

## 2. Request Lifecycle

Every request flows through the middleware stack (outer → inner) before
reaching a router, and back out through logging/headers.

```mermaid
sequenceDiagram
    participant C as Client
    participant RL as Rate Limiter
    participant MW as Security/CORS
    participant CR as Correlation/Logging
    participant R as Router
    participant D as get_db (Async Session)
    participant S as Services
    participant DB as Database

    C->>RL: HTTP request
    RL->>MW: allowed?
    MW->>CR: attach X-Correlation-ID
    CR->>R: dispatch
    R->>D: dependency (AsyncSession)
    D->>S: business logic
    S->>DB: SQL (commit on success)
    DB-->>S: rows
    S-->>R: response model
    R-->>CR: 200 + latency
    CR->>C: JSON + headers
```

---

## 3. RAG Data Flow

```mermaid
flowchart LR
    DOC["Document"] --> L["LoaderFactory"]
    L --> PC["Text Cleaner"]
    PC --> CH["Chunker"]
    CH --> EM["Embedder"]
    EM --> VS[("Vector Store")]
    Q["Query"] --> QE["Query Expansion"]
    QE --> RET["Hybrid Retrieval\n(Dense + Sparse)"]
    VS --> RET
    RET --> RR["Reranker (Cross-Encoder)"]
    RR --> DK["Dynamic Top-K"]
    DK --> GEN["LLM Generation\n(+ Citations)"]
    GEN --> OUT["Grounded Answer"]
```

---

## 4. Enterprise Authentication Flow

```mermaid
flowchart TD
    U["User"] -->|email+password| LOGIN["POST /auth/login"]
    LOGIN -->|bcrypt verify| OK{"Valid?"}
    OK -->|yes| ISSUE["Issue Access + Refresh JWT"]
    OK -->|no| ERR["401"]
    ISSUE --> API["Authenticated API call\nBearer <access_token>"]
    API --> AUTHZ{"RBAC\nrole + permissions"}
    AUTHZ -->|allowed| SVC["Service layer"]
    AUTHZ -->|denied| F403["403"]
    REFRESH["POST /auth/refresh"] --> ROT["Rotate token pair"]
    RESET["password-reset / email-verify"] --> TOK["single-use hashed token"]
```

Roles: `admin` (all perms), `member` (create/export/delete own), `viewer`
(shared-KB read). See `docs/reports/PHASE9_AUTHORIZATION.md`.

---

## 5. Key Design Principles

1. **Configuration over convention** — every setting is an env var, validated
   fail-fast on startup (`backend/api/config.py`, `backend/enterprise/config.py`).
2. **Composition over duplication** — pipeline stages are swappable via
   factories/dependency injection.
3. **Async everywhere for I/O** — FastAPI + SQLAlchemy 2.0 async; `get_db`
   commits on success, rolls back on error.
4. **Audit by default** — mutating enterprise actions append `AuditLog` rows.
5. **Fail-closed authorization** — unknown roles degrade to `viewer`.

---

## 6. Module Map

| Layer | Location | Responsibility |
|-------|----------|----------------|
| API | `backend/api/` | App factory, routers, middleware, observability |
| Enterprise | `backend/enterprise/` | Auth, RBAC, workspaces, conversations, admin, export |
| Ingestion | `backend/data/loaders`, `preprocessing`, `chunking` | Document → chunks |
| Embeddings | `backend/data/embeddings` | Vector generation + caching |
| Vector store | `backend/vectorstore` | FAISS index management |
| Retrieval | `backend/retrieval` | Hybrid, fusion, rerank, expansion |
| Generation | `backend/generation` | LLM gateway, citations, validation |
| Evaluation | `backend/evaluation` | Ragas / DeepEval metrics |
| Experiments | `backend/data/experiments` | MLflow / WandB tracking |
| Validation | `backend/embedding_validation` | Benchmarking + profiling |

See [`docs/architecture/`](./architecture/) for the full 19-part deep dive and
[`docs/API.md`](./API.md) for the endpoint contract.
