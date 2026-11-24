# BASELINE_METRICS.md — Retrieval Intelligence Platform

**Project:** Retrieval Intelligence Platform — Enterprise RAG System  
**Baseline date:** 2026-11-24  
**Git baseline commit:** 9048912

## Test Baseline

| Metric | Value | Unit | Evidence | Confidence |
|---|---:|---|---|---|
| Tests passed | 533 | count | `pytest backend/tests` | HIGH |
| Tests failed | 0 | count | `pytest backend/tests` | HIGH |

## Functional Baseline (verified from source)

| Feature | Status | Evidence |
|---|---|---|
| Ingestion pipeline | Implemented | `backend/api/routers/documents.py` |
| Chunking | Implemented | `backend/data/chunking/` |
| Hybrid retrieval (dense+BM25+RRF) | Implemented | `backend/retrieval/intelligent_retrieval_pipeline.py` |
| Grounded generation | Implemented | `backend/api/routers/chat.py`, `backend/generation/` |
| JWT auth (access+refresh, bcrypt) | Implemented + tested | `backend/enterprise/security.py`, `rbac.py` |
| Google OAuth | Implemented (config-gated) | `backend/enterprise/oauth.py` |
| RBAC (admin/member/viewer) | Implemented + tested | `backend/enterprise/rbac.py` |
| Multi-user workspaces | Implemented + tested | `backend/enterprise/routers.py` |
| Persistent chat history | Implemented + tested | `backend/enterprise/models.py` |
| JSON export | Implemented + tested | `backend/enterprise/exporters.py` |
| Markdown export | Implemented + tested | `backend/enterprise/exporters.py` |
| PDF export | Implemented + tested | `backend/enterprise/exporters.py` |
| Ragas evaluation | NOT IMPLEMENTED | Returns 501, `evaluation/core/` empty |
| Experiment tracking | NOT IMPLEMENTED | Returns 501 |

## Load Baseline (rate limiting ENABLED - default config)

| Concurrency | Requests | Errors | Error Rate | RPS | p50 | p95 | p99 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10 | 0 | 0.0% | 166.4 | 6.57ms | 7.22ms | 7.22ms |
| 5 | 50 | 42 | 84.0% | 513.4 | 8.39ms | 19.58ms | 20.76ms |
| 10 | 100 | 99 | 99.0% | 908.1 | 9.48ms | 20.26ms | 37.62ms |
| 25 | 250 | 249 | 99.6% | 564.0 | 28.41ms | 107.93ms | 145.80ms |
| 50 | 500 | 495 | 99.0% | 241.5 | 111.38ms | 520.87ms | 899.45ms |

> **NOTE:** Rate limiting is 120/min per IP (~2 rps). At concurrency > 1, most requests from the same IP are rate-limited (429). This is expected behavior - the rate limiter protects against abuse. Previous load test (rate limiting DISABLED) showed 359 RPS at 50 concurrent users with p95=323ms.

## API Latency (with auth)

| Endpoint | p50 | p95 | p99 | n |
|---|---:|---:|---:|---:|
| /api/v1/health/live | 11.93ms | 18.24ms | 25.31ms | 30 |
| /api/v1/health/ready | 14.66ms | 26.19ms | 28.16ms | 30 |

## Ragas Baseline

| Metric | Status | Evidence |
|---|---|---|
| Faithfulness | NOT MEASURED | Ragas not configured |
| Answer relevancy | NOT MEASURED | Ragas not configured |
| Context precision | NOT MEASURED | Ragas not configured |
| Context recall | NOT MEASURED | Ragas not configured |
| Recall@k | NOT MEASURED | Ragas not configured |
| Evaluation queries (N) | NOT MEASURED | No eval dataset |

## Known Issues to Address

1. Ragas evaluation not implemented (endpoints return 501 when not configured)
2. Grounded generation needs citation correctness validation with real LLM
3. No live deployment URL
4. Load testing needs to be repeated with rate limiting enabled (DONE - see above)
