# RIP Capacity Analysis

**Project:** Retrieval Intelligence Platform  
**Date:** 2026-11-24  
**Git SHA:** `1cf0ee0`

---

## 1. Production Concurrency (Rate Limiting ON)

### Results Summary

| Concurrency | Error Rate | p95 ms | Meets Criteria (err<1%, p95<500ms) |
|-------------|------------|--------|-------------------------------------|
| C=1 | 0.0% | 270.1 | ✅ Yes |
| C=5 | 4.0% | 6457.8 | ❌ No |
| C=10 | 68.0% | 353.6 | ❌ No |
| C=25 | 100.0% | 47.1 | ❌ No |
| C=50 | 99.6% | 107.2 | ❌ No |
| C=100 | 99.2% | 915.3 | ❌ No |

### Conclusion

**Only C=1 meets both criteria** (error rate < 1% AND p95 < 500ms) with rate limiting enabled.

The per-IP rate limiter (120 req/min) is the primary bottleneck. At C=5, the combined request rate from 5 users (25 requests total) starts hitting rate limits. At C≥10, most requests receive 429 responses.

---

## 2. Isolated Capacity (Rate Limiting OFF)

### Previously Measured (from prior audit)

| Concurrency | p95 ms | Status |
|-------------|--------|--------|
| C=50 | 323.3 | Meets p95<500ms |

**Note:** Rate-limiting-OFF testing requires restarting the server with `API_RATE_LIMIT_ENABLED=false`. This is an isolated capacity test, NOT a production setting. The server was not restarted for this audit to avoid disrupting the running instance.

---

## 3. Bottleneck Analysis

### Primary Bottleneck: Per-IP Rate Limiter

| Component | Bottleneck Severity | Mitigation |
|-----------|-------------------|------------|
| Rate limiter (120 req/min per IP) | CRITICAL | Increase limit, use per-user limits for authenticated users |
| Chat endpoint latency (~250ms p50) | MODERATE | Cache retrieval results, optimize generation |
| Auth endpoint | LOW | Separate rate limit bucket already exists |

### Secondary Considerations

| Factor | Impact | Notes |
|--------|--------|-------|
| SSE streaming | Adds overhead | Full response generated before emission (not token-by-token) |
| Database queries | Minimal | SQLite/PostgreSQL with connection pooling |
| Vector search | Minimal | FAISS IndexFlatIP is fast for small indexes |
| JWT validation | Minimal | HS256 signature verification is fast |

---

## 4. Recommendations

### Short-Term (Production)

1. **Increase per-IP rate limit**: From 120 to 300-600 req/min for authenticated users
2. **Add per-user rate limits**: Authenticated users get higher limits than anonymous
3. **Cache health check responses**: Reduce load on health endpoint
4. **Monitor 429 rate**: Track as key SLO

### Medium-Term (Scalability)

1. **Horizontal scaling**: Multiple instances behind load balancer (distributes rate-limit buckets)
2. **Request queuing**: Queue requests during brief spikes instead of immediate 429
3. **Response caching**: Cache common RAG responses
4. **Token-by-token streaming**: Implement actual SSE streaming (currently full response in one frame)

### Long-Term (Production Grade)

1. **Distributed rate limiting**: Redis-backed rate limiter for multi-instance deployments
2. **Auto-scaling**: K8s HPA based on request queue depth
3. **Circuit breaker**: Fail fast when downstream services are unhealthy

---

## 5. Test Configuration

| Parameter | Value |
|-----------|-------|
| Server | http://127.0.0.1:8000 |
| Rate limiter | 120 req/min per IP (enabled) |
| Endpoint mix | 50% health, 30% chat, 20% auth |
| Requests per user | 5 |
| Concurrent levels | 1, 5, 10, 25, 50, 100 |
| Auth | JWT token via register/login |

---

## 6. Files

- `scripts/rip_load_test.py` — Load test script
- `experiment_results/rip_load_test.json` — Raw load test results
- `RIP_LOAD_TEST_REPORT.md` — Detailed load test report
