# Logging Strategy

## Overview

Structured logging provides visibility into pipeline operations, debugging capabilities, and audit trails for compliance.

## Structured Logging Format

All logs are JSON with consistent schema:

```json
{
  "timestamp": "2026-06-28T00:30:00.123Z",
  "level": "INFO",
  "logger": "backend.data.embeddings.openai",
  "correlation_id": "abc-123-def-456",
  "experiment_id": "exp-789",
  "message": "Embedding batch completed",
  "context": {
    "provider": "openai",
    "model": "text-embedding-3-small",
    "batch_size": 32,
    "tokens": 4096,
    "duration_ms": 150,
    "cache_hit_rate": 0.25
  }
}
```

## Log Levels

| Level | Usage | Examples |
|-------|-------|----------|
| DEBUG | Detailed debugging | Chunking boundary decisions, cache hits |
| INFO | Normal operations | Pipeline stage completed, metrics |
| WARNING | Non-critical issues | Fallback used, truncated chunk |
| ERROR | Recoverable failures | Timeout, retry triggered |
| CRITICAL | System-wide issues | Circuit breaker open |

## Correlation IDs

### Generation
- At API request: new UUIDv7
- Propagated through all stages
- Included in all log events

### Format
```
corr_<UUIDv7>
# Example: corr_018f1a2b3c4d7e8f9a0bc1d2e3f4a5b6
```

### Context Propagation
```python
# FastAPI middleware
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or f"corr_{uuid7()}"
    context.update(correlation_id=correlation_id)
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

## Experiment IDs

### Linking Logs to Experiments
- Log event includes `experiment_id`
- Query parameter `experiment_id` overrides
- Auto-generated for ad-hoc experiments

### Format
```
exp_<name>_<timestamp>
# Example: exp_chunking-test_20260628
```

## Performance Logs

### Request Timing
```
query.dense_search.duration_ms
query.rerank.duration_ms
query.generation.duration_ms
query.total.duration_ms
```

### Stage Metrics
```
chunks_processed_total{stage, status}
embedding_cache_hit_rate
vector_upsert_latency_seconds
```

### Resource Metrics
```
memory_usage_mb{stage}
gpu_memory_usage_percent
cpu_utilization_percent
active_connections
```

## Evaluation Logs

### Metric Snapshots
```json
{
  "level": "INFO",
  "message": "Evaluation completed",
  "context": {
    "dataset": "finance-qa-v1",
    "metrics": {
      "faithfulness": 0.85,
      "context_precision": 0.78,
      "answer_relevancy": 0.92
    },
    "sample_count": 100,
    "duration_seconds": 120
  }
}
```

### Per-Sample Logging
- Only in debug mode (too verbose)
- Include query, prediction, metrics
- Useful for drift detection

## Audit Logs

### Query Audit
```json
{
  "level": "INFO",
  "message": "Query processed",
  "context": {
    "query": "What was Q3 revenue?",
    "user_id": "user-123",
    "session_id": "sess-456",
    "results_returned": 5,
    "citations_generated": 3
  }
}
```

### PII Policy
- Never log query content in production
- Never log document content
- Only log metadata (counts, IDs, timing)
- Enable verbose logging in dev via feature flag

## Log Aggregation

### Development
- Console output (dev)
- Optional: Loki/Grafana (local)

### Production
- JSON → Loki
- Metrics → Prometheus
- Traces → Tempo/Jaeger

### Sampling
| Environment | Sampling Rate |
|-------------|---------------|
| Development | 100% |
| Staging | 100% |
| Production | 10% (INFO), 100% (ERROR+), 0% (DEBUG) |

## Log Fields

### Required Fields
| Field | Type | Source |
|-------|------|--------|
| `timestamp` | ISO8601 | Logger |
| `level` | string | Logger |
| `logger` | string | Code location |
| `correlation_id` | string | Request context |
| `message` | string | Log statement |

### Optional Fields
| Field | Type | Purpose |
|-------|------|---------|
| `experiment_id` | string | Track experiment runs |
| `user_id` | string | Audit trail |
| `session_id` | string | Session grouping |
| `stage` | string | Pipeline stage |
| `component` | string | Module name |
| `duration_ms` | int | Timing |
| `status` | string | success/failure |

## Log Destinations

### Primary: Application Logs
- All events to stdout
- JSON formatted
- Structured parsing by collector

### Secondary: Audit Store
- Query logs to separate index
- Required for compliance
- Retention: 7 years (configurable)

### Tertiary: Metrics Store
- Aggregated counts, latencies
- Prometheus format
- Real-time dashboards

## Configuration

```bash
# Log level
LOG_LEVEL=INFO

# Format
LOG_FORMAT=json

# Output
LOG_OUTPUT=stdout

# Audit logging
AUDIT_LOGGING=true

# PII logging
PII_LOGGING=false
```

## Future Scalability

### Log Sampling
- Adaptive sampling by volume
- Priority-based retention
- Compressed archive storage

### Log Analysis Pipelines
- Real-time anomaly detection
- Drift detection for queries
- Performance regression alerts