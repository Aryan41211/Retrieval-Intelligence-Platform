# OPTIMIZATION_STRATEGY.md — Retrieval Intelligence Platform

**Project:** Retrieval Intelligence Platform — Enterprise RAG System  
**Strategy date:** 2026-11-24  
**Priority order:** Ragas evaluation > RAG quality > Latency/cost > Security

## Priority 1: Ragas Evaluation Implementation (Phase R2)

**Current state:** Ragas evaluation endpoints return 501 when not configured. No evaluation dataset exists.  
**Goal:** Implement reproducible Ragas evaluation pipeline with faithfulness, answer relevancy, context precision, context recall metrics.  
**Constraint:** Cannot run Ragas without API keys (no cost incurred during this audit).

### Planned actions:
1. Create labeled evaluation dataset (questions, ground-truth answers, retrieved contexts, reference documents)
2. Wire Ragas evaluator to accept and process labeled samples
3. Report metrics when Ragas is configured; report "not available" when not
4. Create experiment tracking for chunk size, overlap, model, k, index type, scores

### Success criteria:
- Ragas pipeline is executable when configured
- Evaluation dataset schema is documented
- Metrics are reported honestly (no fabrication when not configured)

## Priority 2: RAG Quality Optimization (Phase R3-R4)

**Current state:** Hybrid retrieval (dense+BM25+RRF), grounded generation with citations, hallucination guard  
**Goal:** Improve grounded generation quality and citation correctness  
**Constraint:** Do not claim quality improvements without Ragas validation

### Planned actions:
1. Evaluate chunking strategies (recursive, semantic, fixed-size)
2. Test hybrid retrieval with weighted fusion (vs RRF)
3. Evaluate cross-encoder reranking on top candidates
4. Validate citation-to-claim alignment
5. Test unknown-answer handling (when context is insufficient)

### Success criteria:
- Each technique tested via ablation
- Citation correctness verified against source references
- No fabricated citations in responses

## Priority 3: Latency & Cost Optimization (Phase R6)

**Current state:** p95=26ms at concurrency 1 (with rate limiting), p95=323ms at concurrency 50 (rate limiting disabled)  
**Goal:** Measure and optimize component-level latency  
**Constraint:** Do not claim production readiness without measured evidence

### Planned actions:
1. Component-level latency breakdown (ingestion, embedding, retrieval, generation, export)
2. Token consumption and cost estimation per query
3. Embedding caching evaluation
4. Connection reuse and async optimization

### Success criteria:
- Component-level latencies documented
- Cost per query estimated (when real LLM provider configured)

## Priority 4: Load Testing & Scalability (Phase R7)

**Current state:** Load tested with rate limiting ENABLED and DISABLED  
**Goal:** Document realistic capacity under production configuration  
**Constraint:** Do not compare rate-limited results with unrate-limited results

### Planned actions:
1. Run load tests with rate limiting ENABLED (DONE - see BASELINE_METRICS.md)
2. Run load tests with rate limiting DISABLED (DONE - see BASELINE_METRICS.md)
3. Test with authentication enabled
4. Separate lightweight vs full RAG workloads

### Success criteria:
- Realistic capacity numbers documented
- Rate limiting behavior verified

## Priority 5: Security & Multi-tenancy (Phase R8)

**Current state:** JWT auth, RBAC, OAuth, workspace isolation implemented and tested  
**Goal:** Validate security boundaries  
**Constraint:** Do not claim security without testing

### Planned actions:
1. Test workspace isolation (cross-user access prevention)
2. Test RBAC enforcement (viewer cannot access admin operations)
3. Test export authorization
4. Test prompt injection resistance

### Success criteria:
- All security boundaries verified with tests
- No cross-tenant data leakage

## Experiment Tracking

All experiments recorded per Section 8 of the master prompt.

## Acceptance Criteria

- Executable Ragas evaluation
- Real measured RAG scores (when API keys available)
- Reproducible retrieval benchmarks
- Citation correctness evaluation
- Grounded generation
- Measured cost
- Realistic load testing
- Security validation
