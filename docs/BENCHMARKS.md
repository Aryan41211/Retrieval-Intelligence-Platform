# Benchmarks & Evaluation Metrics — Retrieval Intelligence Platform (RIP)

This document consolidates RIP's performance, latency, evaluation, and memory
story. It is the single source for portfolio/release benchmarks.

> **How to reproduce:** every number below is produced by code that ships in
> the repo. Run the suites locally to regenerate current figures for your
> hardware.

---

## 1. Performance & Latency — Embedding Validation Framework

RIP ships a benchmark + profiler suite in `backend/embedding_validation/`:

- `EmbeddingBenchmark` — measures throughput and **latency** (p50/p95/p99) for
  embedding generation across configurable batch sizes.
- `EmbeddingProfiler` — samples **peak memory (MB)** and CPU during runs.
- `SimilarityAnalyzer` / `DuplicateDetector` — cosine similarity and duplicate
  rate across embedding sets.
- `ValidationRunner` — orchestrates a full validation pass and emits a report.

**Run it:**
```bash
python -m backend.embedding_validation.validation_runner \
    --dataset <path> --batch-size 32 --samples 1000
```
Typical outputs: `average_latency_ms`, `p95_latency_ms`, `throughput_eps`,
`peak_memory_mb`, `duplicate_rate`.

### Production Readiness Audit (Phase 4.3)

The framework was audited for production (see
`docs/reports/EMBEDDING_VALIDATION_PRODUCTION_AUDIT.md`):

| Dimension | Score |
|-----------|-------|
| Scalability | **8/10** |
| Maintainability | **9/10** |
| Reliability | **9/10** |
| Test Coverage | **84/84 tests passing** |

**Known scaling limits (documented, non-blocking):** exact similarity is
O(n²); for >10K embeddings use sampling/FAISS ANN (recommended future work).

---

## 2. Evaluation Metrics — RAG Quality

The evaluation layer (`backend/evaluation/`) integrates **Ragas** and
**DeepEval** to score generated answers:

| Metric | What it measures |
|--------|------------------|
| **Faithfulness** | Is the answer grounded in retrieved context (no hallucination)? |
| **Answer Relevancy** | Does the answer address the question? |
| **Context Precision / Recall** | Are retrieved chunks relevant/complete? |
| **Context Entity Recall** | Coverage of ground-truth entities in context. |
| **Answer Correctness** | Semantic + factual correctness vs. reference. |

These feed experiment tracking (`backend/data/experiments`, MLflow/WandB) so
quality is comparable across prompt/retriever configurations.

---

## 3. System Test Coverage

From the end-to-end acceptance run (baseline: 283 backend tests collected):

| Suite | Result |
|-------|--------|
| Backend unit + integration | **272 passed / 283 collected** (pre-API-era baseline) |
| Enterprise suite (Phase 9) | **65 passed** (auth, RBAC, workspaces, conversations, admin, services) |
| Frontend (Vitest) | passing (Chat/Dashboard component tests) |

> The historical `SYSTEM_ACCEPTANCE_REPORT.md` predates Phases 8–9. Its
> "placeholder API" findings are **superseded**: the REST API, health,
> rate-limiting, observability, and full enterprise layer are now implemented
> and tested. See the Phase 10 Final Release Report for current status.

---

## 4. Memory & Resource Profile

- **Embedding profiler** reports peak RSS/MB during batch embedding.
- **Vector store** uses FAISS in-memory indexes with on-disk serialization
  (`IndexManager`, `IndexSerializer`); memory scales with index size + cached
  similarity matrices.
- **API process** is a single ASGI worker; horizontal scale behind a load
  balancer with a shared Postgres + Redis for multi-instance deployments.

---

## 5. Representative Benchmark Table (template)

Fill this in after a local run on your target hardware:

| Scenario | p50 latency | p95 latency | Throughput | Peak Mem |
|----------|------------|------------|-----------|----------|
| Embed 1K chunks (bs=32) | _ms_ | _ms_ | _eps_ | _MB_ |
| Retrieve top-10 (hybrid) | _ms_ | _ms_ | — | — |
| Full RAG answer (GPT-class) | _ms_ | _ms_ | — | — |

Capture with the profiler + a timing wrapper around `/api/v1/chat`.

---

## 6. Methodology Notes

- Latency is measured end-to-end at the client boundary where possible
  (correlation-ID timing is also logged server-side in `X-Process-Time`).
- Throughput = successful items / wall-clock, excluding cold-start model load.
- All metrics are reproducible from committed code + pinned dependency
  versions (`requirements.txt` / `pyproject.toml`).
