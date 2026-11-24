# RIP Load Test Report

**Project:** Retrieval Intelligence Platform  
**Date:** 2026-11-24  
**Git SHA:** `1cf0ee0`  
**Server:** http://127.0.0.1:8000  
**Rate Limiting:** ENABLED (production config: 120 req/min per IP)

---

## 1. Test Configuration

| Parameter | Value |
|-----------|-------|
| Endpoint mix | 50% health, 30% chat, 20% auth |
| Requests per user | 5 |
| Concurrent levels tested | 1, 5, 10, 25, 50, 100 |
| Authentication | JWT token (register/login) |
| Rate limiter | 120 req/min per IP, burst allowed |

---

## 2. Results by Concurrency

| Concurrency | Requests | Successful | Errors | Error Rate | RPS | p50 ms | p95 ms | p99 ms |
|-------------|----------|------------|--------|------------|-----|--------|--------|--------|
| C=1 | 5 | 5 | 0 | 0.0% | 6.1 | 253.4 | 270.1 | 272.3 |
| C=5 | 25 | 24 | 1 | 4.0% | 3.3 | 495.4 | 6457.8 | 6507.9 |
| C=10 | 50 | 16 | 34 | 68.0% | 108.7 | 16.1 | 353.6 | 387.4 |
| C=25 | 125 | 0 | 125 | 100.0% | 568.8 | 40.2 | 47.1 | 48.3 |
| C=50 | 250 | 1 | 249 | 99.6% | 520.9 | 89.6 | 107.2 | 110.5 |
| C=100 | 500 | 4 | 496 | 99.2% | 309.8 | 171.2 | 915.3 | 919.3 |

### Status Code Breakdown

| Concurrency | 200 OK | 429 Rate Limited | Other |
|-------------|--------|------------------|-------|
| C=1 | 5 | 0 | 0 |
| C=5 | 24 | 1 | 0 |
| C=10 | 16 | 34 | 0 |
| C=25 | 0 | 125 | 0 |
| C=50 | 1 | 249 | 0 |
| C=100 | 4 | 496 | 0 |

---

## 3. Capacity Analysis

### Primary Bottleneck: Rate Limiting

The per-IP rate limiter (120 req/min) is the dominant constraint:

- **C=1**: All requests succeed (0.0% error rate) — single user stays within rate limit
- **C=5**: 4.0% error rate — slight rate limit pressure
- **C=10**: 68.0% error rate — rate limiter actively rejecting requests
- **C≥25**: ~100% error rate — virtually all requests are 429 rate-limited

### Highest Concurrency Meeting Criteria

| Criterion | Value |
|-----------|-------|
| err < 1% AND p95 < 500ms | **C=1** |
| Only C=1 meets both | Yes |

### Effective Concurrent Users

- **Production (rate limiting ON)**: 1 effective concurrent user
- **Isolated capacity (rate limiting OFF)**: Previously tested at C=50, p95=323.3ms

---

## 4. Endpoint-Level Behavior

### Health Endpoint (GET /api/v1/health/ready)
- No authentication required
- Fast response (~5-10ms when not rate-limited)
- 429 when rate limit exceeded

### Chat Endpoint (POST /api/v1/chat)
- JWT authentication required
- Retrieval + generation pipeline
- Slower response (~250ms p50 at C=1)
- 401 without valid token, 429 when rate-limited

### Auth Endpoint (POST /api/v1/auth/login)
- No authentication required
- Token generation
- Separate rate limit bucket (`rate_limit_auth_per_minute`)

---

## 5. Production vs Isolated Capacity

| Test Type | Rate Limiting | Max Concurrency (err<1%, p95<500ms) | Purpose |
|-----------|--------------|--------------------------------------|---------|
| Production | ENABLED | C=1 | Real-world behavior with security controls |
| Isolated capacity | DISABLED | C=50 (previously measured) | Raw server capacity |

*Note: Rate-limiting-OFF testing requires restarting the server with `API_RATE_LIMIT_ENABLED=false`. Results from that test represent isolated capacity, not production behavior.*

---

## 6. Recommendations

1. **Tune rate limits**: Consider increasing per-IP rate limit or implementing per-user (authenticated) rate limits for higher concurrency
2. **Add request queuing**: Instead of immediate 429, queue requests during brief spikes
3. **Cache health checks**: Health endpoint responses can be cached to reduce load
4. **Monitor 429 rate**: Track rate-limit exhaustion as a key SLO metric
5. **Scale horizontally**: Multiple instances behind a load balancer would distribute rate-limit buckets
