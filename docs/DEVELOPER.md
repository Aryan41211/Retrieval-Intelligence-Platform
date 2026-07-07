# Developer Guide — Retrieval Intelligence Platform (RIP)

This guide gets you from clone to a running, testable RIP instance.

---

## 1. Prerequisites

- Python **3.11+**
- Node.js **18+** (frontend)
- Access to an LLM provider key (OpenAI/Anthropic/etc.) for live generation
- Optional: PostgreSQL, Redis (defaults use SQLite / in-memory for local dev)

## 2. Backend Setup

```bash
# Clone
git clone <repo> && cd "Retrieval Intelligence Platform"

# Create a virtual environment
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install (editable, with dev tools)
pip install -e ".[dev]"

# Configure
cp .env.example .env        # then fill in secrets (never commit .env)
```

Key environment variables (see `.env.example`):

```bash
API_ENVIRONMENT=development
DATABASE_URL=sqlite+aiosqlite:///./rip.db
ENTERPRISE_JWT_SECRET_KEY=change-me-to-a-long-random-string
OPENAI_API_KEY=sk-...        # for live generation
```

## 3. Run the API

```bash
uvicorn backend.api.app:app --reload --port 8000
# Docs: http://localhost:8000/docs
```

## 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev          # Vite dev server (default http://localhost:5173)
```

The SPA talks to the API via `VITE_API_URL` (defaults to `/api/v1`).

## 5. Testing

```bash
# All backend tests
pytest

# Enterprise suite only (isolated SQLite + TestClient)
pytest backend/tests/enterprise -q

# Quality gates
ruff check backend
mypy backend --explicit-package-bases
black --check backend
```

> **Note:** run `mypy` with `--explicit-package-bases` so the `backend.*`
> packages resolve correctly (the repo has same-named sub-packages that
> otherwise collide as top-level module names).

Frontend:

```bash
cd frontend
npm test               # vitest
npm run build          # tsc + vite build
```

## 6. Project Layout

```
backend/
  api/            # FastAPI app, routers, middleware, observability
  enterprise/     # Auth, RBAC, workspaces, conversations, admin, export
  data/           # loaders, preprocessing, chunking, embeddings, vectorstore,
                  # retrieval, generation, evaluation, experiments, models
  vectorstore/    # FAISS index management
  embedding_validation/  # Benchmarking + profiling
  tests/          # unit + integration + enterprise
frontend/
  src/services/   # API clients (incl. enterpriseApi)
  src/types/      # shared TypeScript types
  src/pages/      # React pages
docs/             # architecture, reports, guides
```

## 7. Adding an Enterprise Endpoint

1. Define the Pydantic schema in `backend/enterprise/schemas.py`.
2. Implement the logic in `backend/enterprise/services.py` (async, session param).
3. Add the route in `backend/enterprise/routers.py`, guarding with
   `get_current_active_user` / `require_permissions(...)`.
4. The router is auto-included by `backend/api/app.py` — no manual wiring.
5. Add unit + API tests under `backend/tests/enterprise/`.

## 8. Conventions

Follow [`CLAUDE.md`](../CLAUDE.md): type hints everywhere, Google docstrings,
`ruff` + `black` + `mypy`, >80% test coverage on public APIs, no hardcoded
secrets, fail-fast config validation.
