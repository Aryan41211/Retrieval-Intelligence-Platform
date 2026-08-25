<h1 align="center">Retrieval Intelligence Platform</h1>

<p align="center">
  Production-grade <strong>R</strong>etrieval-<strong>A</strong>ugmented <strong>G</strong>eneration —
  ingest, retrieve, generate, evaluate, repeat.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11%2B-blue" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
  <img src="https://img.shields.io/badge/code%20style-black-000000" alt="Code Style: Black">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen" alt="PRs Welcome">
</p>

---

## Overview

The Retrieval Intelligence Platform (RIP) is a **modular, enterprise-ready RAG system** that connects large language models to your documents. It handles the full pipeline — from raw document ingestion through chunking, embedding, hybrid retrieval, grounded generation, and automated evaluation — with experiment tracking for every configuration.

## Key Features

- **Hybrid Retrieval** — Dense (FAISS) + sparse (BM25) with RRF fusion and optional
  cross-encoder reranking. Opt in with `INTELLIGENT_RETRIEVAL_ENABLED=true`;
  dense-only is the default.
- **Multi-Provider LLM** — OpenAI, Anthropic, Ollama, NVIDIA NIM and any
  OpenAI-compatible endpoint, selected by `GENERATION_PROVIDER`.
- **Enterprise Auth** — JWT access/refresh tokens, RBAC, OAuth 2.0 (Google),
  password reset and email verification.
- **Collaborative Workspaces** — Multi-user shared knowledge bases with role-based access.
- **Persistent Chat** — History, search and export (JSON/Markdown/PDF).
- **Admin Dashboard** — Usage analytics, audit logs and health probes.
- **Observability** — Prometheus metrics, structured JSON logs, correlation IDs.
- **Config-Driven** — Every setting is an environment variable, validated on startup.

### Not yet implemented

These are scaffolded but **not** wired up; the endpoints return `501` rather
than simulated results:

- **Evaluation suite** (Ragas / DeepEval) — `/evaluation/*`
- **Experiment tracking** (MLflow / WandB) — `/experiments/*`

Chat responses are delivered over SSE, but the answer is generated in full
before the frame is emitted — this is not yet token-by-token streaming.

## Architecture

```
Ingestion → Chunking → Embedding → Vector Store
                                         ↓
Query → Expansion → Hybrid Retrieval → Reranker → LLM → Grounded Answer
                                         ↓
                              Evaluation → Metrics → Experiment Log
```

The system is built on a **clean modular architecture** with a FastAPI backend,
async SQLAlchemy data layer, and React/TypeScript frontend. See the
[Architecture Guide](docs/ARCHITECTURE.md) for detailed diagrams.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **API** | FastAPI, Pydantic v2, Starlette |
| **Auth** | JWT (HS256), bcrypt, OAuth 2.0 |
| **Database** | SQLAlchemy 2.0 async, SQLite/PostgreSQL |
| **Embeddings** | Sentence-Transformers (local), batch processing, caching |
| **Vector Store** | FAISS, HNSW, IVF indexes |
| **LLM Providers** | OpenAI, Anthropic, Ollama, NVIDIA NIM |
| **Retrieval** | BM25 (rank-bm25), RRF fusion, Cross-Encoder reranking |
| **Evaluation** | Ragas, DeepEval, MLflow, WandB *(scaffolded, not wired up)* |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Vite |
| **Observability** | Prometheus metrics, structured JSON logging, correlation IDs |
| **Infrastructure** | Docker, Railway/Render/AWS/Azure ready |

## Quick Start

### Backend

```bash
git clone https://github.com/user/rip.git
cd rip
pip install -e ".[dev]"

# Configure. Generates .env with a valid ENTERPRISE_JWT_SECRET_KEY, which is
# REQUIRED - the app will not import without it - and must be >= 32 characters.
python scripts/bootstrap_deployment.py

# Run (module path is backend.api, not backend.api.main)
uvicorn backend.api:app --reload

# Open http://localhost:8000/docs
```

To use a real LLM instead of the built-in development stub, set both:

```bash
GENERATION_PROVIDER=anthropic     # or openai / ollama / nim
GENERATION_API_KEY=sk-...
```

The stub provider (`fake`) is rejected outright in a production environment.

Optional settings are shipped **commented out** in `.env.example`. Leave them
that way to use the built-in default — assigning an empty value is not the same
as leaving one unset, and the numeric settings reject it at startup.

### Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies /api to localhost:8000
```

Register an account on first load; every API route except the health probes
requires a bearer token.

See the [Developer Guide](docs/DEVELOPER.md) for full setup instructions.

## Documentation

| Guide | Description |
|-------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System overview, data flows, auth, module map (with Mermaid diagrams) |
| [API Reference](API_REFERENCE.md) | Full endpoint contract — request/response schemas, streaming, error codes |
| [Developer Guide](docs/DEVELOPER.md) | Local setup, running, testing, and conventions |
| [Contributing](docs/CONTRIBUTING.md) | Branching, commit format, PR checklist, code of conduct |
| [Deployment](DEPLOYMENT.md) | Docker, Railway, Render, AWS, Azure |
| [Configuration](docs/CONFIGURATION.md) | All environment variables with defaults and descriptions |
| [Benchmarks](docs/BENCHMARKS.md) | Latency, memory, evaluation metrics and methodology |
| [Architecture Deep-Dive](docs/architecture/) | 19-part component reference |

## Screenshots

<!--
  Add screenshots here before publishing:
  ![Chat Interface](docs/screenshots/chat.png)
  ![Dashboard](docs/screenshots/dashboard.png)
  ![Admin Panel](docs/screenshots/admin.png)
-->

## Roadmap

The ingestion → retrieval → generation path is complete and covered by tests.
Next up:

- **Evaluation and experiment tracking** — wire Ragas/DeepEval and MLflow to the API
- **Token-by-token streaming** — stream from the provider through to the SSE channel
- **Shared-state scaling** — move rate limiting and OAuth state to Redis for multi-instance
- **Streaming agentic capabilities** — tool use, multi-step reasoning
- **On-premise LLM support** — vLLM, llama.cpp integrations
- **Advanced RAG patterns** — self-RAG, FLARE, CRAG
- **Multi-modal RAG** — image, audio, video understanding
- **Kubernetes helm chart** — production-grade orchestration

See the full [Release Notes](docs/RELEASE_NOTES_v1.0.0.md) for v1.0.0 details.

## License

MIT — see [LICENSE](LICENSE).
