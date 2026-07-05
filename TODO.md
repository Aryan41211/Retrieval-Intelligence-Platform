# TODO

## Completed
- [x] Sprint 1: Foundation & Document Ingestion
- [x] Sprint 2: Embedding Pipeline & Vector Store
- [x] Sprint 3: Intelligent Retrieval (hybrid dense + sparse + fusion + reranking)
- [x] Sprint 4: Embedding Validation & Benchmarking
- [x] Sprint 4.5: End-to-End Integration & System Stabilization

## Sprint 4.5 — Completed
- [x] Fix critical generation pipeline breakages (missing llm_gateway, citation_generator, response_validator, hallucination_guard)
- [x] Implement missing LLM provider stubs (OpenAICompatible, Ollama, NIM)
- [x] Add `GenerationSettings` to application configuration
- [x] Fix `ProviderFactory` to read settings correctly
- [x] Unify exception hierarchy (`VectorStoreError` now inherits `RipError`)
- [x] Create `RAGPipeline` end-to-end orchestrator
- [x] Create integration test suite covering all 8 validation scenarios
- [x] Verify existing tests still pass (no regressions)
- [x] Run linting and fix all issues

## Remaining / Future
- [ ] Add FastAPI API layer (`backend/api/`)
- [ ] Complete ingestion pipeline orchestrator
- [ ] Add evaluation and experiment tracking modules
- [ ] Implement async variants for all pipeline stages
- [ ] Centralize filter matching into shared utility
- [ ] Add `upsert()` method to `BaseVectorStore`
- [ ] Consolidate duplicate `backend/embeddings/` and `backend/data/embeddings/`
