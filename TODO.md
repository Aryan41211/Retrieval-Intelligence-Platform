# TODO

## Completed
- [x] Sprint 1: Foundation & Document Ingestion
- [x] Sprint 2: Embedding Pipeline & Vector Store
- [x] Sprint 3: Intelligent Retrieval (hybrid dense + sparse + fusion + reranking)
- [x] Sprint 4: Embedding Validation & Benchmarking
- [x] Sprint 4.5: End-to-End Integration & System Stabilization
- [x] Sprint 5: Grounded Generation (LLM gateway, citation generator, response validator, hallucination guard)
- [x] Sprint 6: Evaluation Framework (Ragas / DeepEval metrics)
- [x] Sprint 7: Experiment Tracking (MLflow / WandB)
- [x] Sprint 8: Production Engineering (Docker, CI/CD, observability, health, rate limiting)
- [x] Phase 9: Enterprise Features (auth, RBAC, workspaces, persistent chat, admin, export, audit)
- [x] Phase 10: Final Release & Portfolio (docs, visuals, benchmarks, release v1.0.0)

## Cleanup (Phase 10)
- [x] Removed dead `backend/models/` compatibility shim (re-export of `backend/data/models`)
- [x] Confirmed `backend/embeddings` already consolidated into `backend/data/embeddings`
- [x] No TODO/FIXME/debug `print` noise in shipped code (only intentional benchmark output)

## Known / Future (non-blocking)
- [ ] Run `mypy` with explicit package bases to resolve top-level namespace
      collisions (`backend.generation` vs `generation`); does not affect runtime.
- [ ] Wire `_send_email` to a real SMTP transport for password-reset/verify delivery.
- [ ] Add server-side refresh-token denylist if immediate revocation is required.
- [ ] Build frontend UI screens on top of the `enterpriseApi` service layer.
