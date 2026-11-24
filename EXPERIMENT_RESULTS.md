# EXPERIMENT_RESULTS.md — Retrieval Intelligence Platform

**Project:** Retrieval Intelligence Platform  
**Baseline:** 533 tests passing, Ragas not configured

## Load Test Results (Rate Limiting ENABLED — default config)

| Concurrency | Requests | Errors | Error Rate | RPS | p50 | p95 | p99 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10 | 0 | 0.0% | 166.4 | 6.57ms | 7.22ms | 7.22ms |
| 5 | 50 | 42 | 84.0% | 513.4 | 8.39ms | 19.58ms | 20.76ms |
| 10 | 100 | 99 | 99.0% | 908.1 | 9.48ms | 20.26ms | 37.62ms |
| 25 | 250 | 249 | 99.6% | 564.0 | 28.41ms | 107.93ms | 145.80ms |
| 50 | 500 | 495 | 99.0% | 241.5 | 111.38ms | 520.87ms | 899.45ms |

**Rate limiter:** 120/min per IP (~2 rps). At concurrency > 1, most requests from same IP get 429.

## Load Test Results (Rate Limiting DISABLED — for reference only)

| Concurrency | RPS | p50 | p95 | p99 | Error rate |
|---|---:|---:|---:|---:|---:|
| 1 | 229.8 | 4.1ms | 4.9ms | 10.4ms | 0.0% |
| 5 | 375.9 | 12.4ms | 18.9ms | 27.3ms | 0.0% |
| 10 | 370.6 | 25.3ms | 37.7ms | 42.5ms | 0.0% |
| 25 | 367.4 | 58.4ms | 79.6ms | 251.9ms | 0.0% |
| 50 |  | 120.3ms | 323.3ms | 334.5ms | 0.0% |

## Ragas Evaluation

| Metric | Status | Evidence |
|---|---|---|
| Faithfulness | NOT MEASURED | No API keys configured |
| Answer relevancy | NOT MEASURED | No API keys configured |
| Context precision | NOT MEASURED | No API keys configured |
| Context recall | NOT MEASURED | No API keys configured |
| Recall@k | NOT MEASURED | No eval dataset |
| Evaluation queries (N) | NOT MEASURED | No eval dataset |

**Ragas infrastructure:** Implemented but returns 501 when not configured. Endpoints correctly report "unavailable" with explanatory message. No scores fabricated.

## Grounded Generation (Chat with Fake Provider)

| Metric | Value | Evidence |
|---|---|---|
| Chat endpoint status | 200 | Tested with fake provider |
| Citations returned | Yes | CitationGenerator extracts [doc_N] markers |
| Processing time | ~25ms | Measured via processing_time_ms field |
| Retrieved chunks | Included in response | chunk_id, document_id, content, similarity_score |

## Security (Rate Limiting)

| Test | Result | Evidence |
|---|---|---|
| 15 failed login attempts | 429 triggered | Rate limiter active |
| Auth endpoints | Protected | Bearer JWT required |
| Health endpoints | Public | No auth required |
