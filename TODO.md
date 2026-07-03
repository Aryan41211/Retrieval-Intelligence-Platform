# TODO - Sprint 3 Intelligent Retrieval

## Phase 1: Discovery / Setup
- [ ] Locate where `RetrievalPipeline` is instantiated and how retrieval requests are constructed (API wiring).
- [ ] Identify existing retrieval endpoint/services/tests that exercise retrieval.
- [ ] Confirm where query text can be supplied (for query expansion + cross-encoder reranking).

## Phase 2: Core Components (Modular)
- [ ] Add IntelligentRetrievalPipeline orchestrator (does not replace RetrievalPipeline).
- [ ] Add BM25 abstraction + pure-Python BM25 implementation over stored `chunk_text`.
- [ ] Add RRF fusion component with configurable parameters + duplicate removal + stable ranking.
- [ ] Add dynamic top-k selection (adaptive via score distribution/confidence + context budget).
- [ ] Add query expander (synonym expansion + query normalization + stop-word/punctuation cleanup; no LLM).
- [ ] Add CrossEncoder reranker provider abstraction; skip stage automatically if disabled/unavailable.

## Phase 3: Vector Store Capability
- [ ] Extend `FAISSVectorStore` with a capability method to expose chunk text/records needed for BM25.
- [ ] Ensure hybrid pipeline can run without mixing implementations (dense from vector store; sparse from BM25 module).

## Phase 4: Configuration + Wiring
- [ ] Add new configuration settings for BM25, RRF, CrossEncoder reranking, query expansion, dynamic top-k, and analytics.
- [ ] Add config flag to choose between semantic (`RetrievalPipeline`) and intelligent (`IntelligentRetrievalPipeline`) retrieval.
- [ ] Implement error handling + fallbacks (BM25 failure -> dense-only; missing reranker -> skip).

## Phase 5: Analytics + Logging
- [ ] Implement retrieval analytics collection: stage latencies, candidate counts, final context size.
- [ ] Add structured logging for strategy, fusion stats, latency breakdown, and ranking changes.

## Phase 6: Testing
- [ ] Run full backend test suite (`pytest`).
- [ ] Fix only confirmed regressions introduced by Sprint 3.
- [ ] Update documentation only if affected by Intelligent Retrieval subsystem.

## Phase 7: Git Workflow
- [ ] `git status`
- [ ] `git add .`
- [ ] `git commit -m "feat(intelligent-retrieval): implement modular hybrid retrieval pipeline with configurable orchestration, BM25, reciprocal rank fusion, adaptive ranking, and optional cross-encoder reranking"`
- [ ] `git push origin main`
