# TODO - Phase 3 Embedding Pipeline

## Step 1: Audit (done)
- [x] Read CLAUDE.md completely
- [x] Read all docs/architecture/* through chunking lifecycle
- [x] Audit existing embedding modules and unit tests under backend/data/embeddings and backend/tests/unit/test_embeddings

## Step 2: Identify gaps vs Phase 3 requirements (done)
- [x] Cache key must include chunk checksum, model, model version, configuration snapshot (current pipeline uses sha256(text))
- [x] Cache persistence is required (persist_path currently unused)
- [x] Validation gaps (duplicate embeddings, corrupted vectors, dimension mismatch handling)
- [x] Provider abstraction defaults / configurability gaps (batch/device/max workers/timeout/max retries integration)
- [x] Ensure metadata richness matches Phase 3 spec (model/version/chunk/document ids, dimension, latency, hash, config snapshot)

## Step 3: Implement Phase 3 embedding modules (next)
- [x] Add required modules under backend/embeddings/ as wrappers/aliases to the existing backend/data/embeddings implementation
- [x] Create/adjust backend/models/embedding.py to match the Phase 3 Embedding domain model contract
- [x] Fix EmbeddingPipeline to use chunk checksum (sha256(text)), incorporate correct cache key inputs, and produce/attach required metadata
- [x] Upgrade EmbeddingCache to support persistence (persist_path: save/load) and correct key handling
- [x] Upgrade EmbeddingValidator to implement required checks (empty, NaN/Inf, dimension mismatch, duplicates) with meaningful exceptions
- [ ] Ensure batch processor respects configurable batching, retry policy, timeouts, and (where feasible) device selection / worker controls
- [x] Add/adjust unit tests for: provider swapping, batch generation, cache hit/miss, dimension validation, invalid embeddings, large corpus, GPU fallback (mock), configuration loading, and persistence
- [x] Persist embeddings to disk after generation (no vector DB) (via EmbeddingCache persistence)

## Step 4: Documentation + self-audit (after code passes)
- [x] Update embedding architecture docs (at minimum docs/architecture/10_embedding_lifecycle.md) describing provider abstraction, caching, metadata, performance metrics
- [x] Produce Embedding Pipeline Review Report and review all touched files
- [x] Run pytest and ensure embeddings-related tests pass

## Phase 4: Embedding Validation & Benchmarking Framework (next)
- [ ] Create `backend/embedding_validation/` package + module skeleton
- [ ] Implement validation workflow (dimensions, normalization, NaN/Inf, zero vectors, duplicates/near-duplicates, consistency)
- [ ] Implement benchmarking/profiling (latency percentiles, throughput, cache hit rate, CPU/GPU best-effort)
- [ ] Implement similarity analysis (top-K, distribution, outliers/nearest-neighbor distribution)
- [ ] Implement reporting (Markdown + JSON exports)
- [ ] Implement optional visualization (lightweight, lazy imports)
- [ ] Add unit tests for stats/validation/benchmark/report/profiler
- [ ] Self-audit + produce `EMBEDDING_VALIDATION_REVIEW_REPORT.md`
