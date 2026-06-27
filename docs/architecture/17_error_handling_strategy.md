# Error Handling Strategy

## Overview

Error handling provides predictable failure modes, clear error messages, and graceful degradation across all pipeline stages.

## Custom Exceptions

### Exception Hierarchy
```
RipError (base exception)
├── ConfigurationError
│   ├── InvalidSettingError
│   └── MissingSecretError
├── DataError
│   ├── LoaderError
│   ├── PreprocessingError
│   ├── ChunkingError
│   └── EmbeddingError
├── RetrievalError
│   ├── VectorStoreError
│   ├── SearchError
│   └── RerankError
├── GenerationError
│   ├── LLMError
│   ├── PromptError
│   └── CitationError
├── EvaluationError
│   ├── DatasetError
│   └── MetricError
└── ExperimentError
    ├── TrackerError
    └── ArtifactError
```

### Exception Structure
```python
class RipError(Exception):
    code: str                    # Unique error code
    details: dict[str, Any]       # Structured error info
    correlation_id: str          # Request tracking
    timestamp: datetime          # When error occurred
    
    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            error={
                "code": self.code,
                "message": str(self),
                "details": self.details,
                "correlation_id": self.correlation_id,
                "timestamp": self.timestamp.isoformat()
            }
        )
```

## Error Codes

| Category | Code Pattern | Examples |
|----------|--------------|----------|
| Loader | `LOADER_*` | `LOADER_FORMAT_UNSUPPORTED`, `LOADER_FILE_CORRUPT` |
| Preprocessor | `PREPROCESS_*` | `PREPROCESS_ENCODING_ERROR`, `PREPROCESS_TOO_LONG` |
| Chunker | `CHUNKING_*` | `CHUNKING_SIZE_EXCEEDED`, `CHUNKING_NO_VALID_CHUNKS` |
| Embedding | `EMBEDDING_*` | `EMBEDDING_RATE_LIMIT`, `EMBEDDING_INVALID_KEY` |
| Vector Store | `VECTOR_*` | `VECTOR_UPsert_FAILED`, `VECTOR_SEARCH_TIMEOUT` |
| Retrieval | `RETRIEVAL_*` | `RETRIEVAL_NO_RESULTS`, `RETRIEVAL_FILTER_TOO_STRICT` |
| Rerank | `RERANK_*` | `RERANK_TIMEOUT`, `RERANK_QUOTA_EXCEEDED` |
| Generation | `GENERATION_*` | `GENERATION_CONTEXT_EXCEEDED`, `GENERATION_SAFETY_FILTER` |
| Evaluation | `EVALUATION_*` | `EVALUATION_DATASET_NOT_FOUND`, `EVALUATION_METRIC_FAILED` |
| Experiment | `EXPERIMENT_*` | `EXPERIMENT_TRACKER_UNAVAILABLE`, `EXPERIMENT_QUOTA_EXCEEDED` |

## Logging Policy

### Log on Error
- Log error with full context before raising
- Include correlation ID
- Include relevant config values (no secrets)
- Use structured JSON format

```python
logger.error(
    "Embedding API timeout",
    extra={
        "correlation_id": correlation_id,
        "provider": "openai",
        "model": "text-embedding-3-small",
        "batch_size": 32,
        "timeout_ms": 5000,
        "retry_count": 3
    }
)
```

### No Silent Failures
- All exceptions logged
- All handled exceptions return structured response
- Health checks report error rates

## Retry Strategy

### Exponential Backoff
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type(
        (EmbeddingError, LLMError, VectorStoreError)
    ),
    after=after_log(logger, logging.WARNING)
)
async def call_external_api(...):
    ...
```

### Jitter for Distributed Retries
- Add randomness to backoff times
- Prevent thundering herd
- Configured via `tenacity` or custom

### Retry Budget
- Total time budget: 30s default
- Per-retry max: 30s
- Circuit breaker after budget exhausted

## Graceful Failures

### Optional Stages
| Stage | Failure Behavior |
|-------|-----------------|
| Query Expander | Return original query |
| Reranker | Return unranked results |
| Citations | Generate answer without citations |
| Grounding Check | Log warning, don't block |
| PII Redaction | Continue without redaction |

### Partial Results
```python
# Vector store search times out
# Return whatever we have
if results:
    return partial_results
else:
    raise SearchError("No results within timeout")
```

### Degradation Chain
```
Full Pipeline (Dense + Sparse + Rerank)
        │
        ▼
Dense Only (Embedding fails)
        │
        ▼
Sparse Only (Vector store fails)
        │
        ▼
No Results (All fail)
```

## Validation Strategy

### Input Validation
- Pydantic models at API boundaries
- Type hints throughout
- Fail fast on invalid input

### Config Validation
- Validate all settings at startup
- Cross-field validation
- Fail before serving requests

### Data Validation
- Validate between stages
- Check embedding dimensions
- Verify chunk boundaries

## Circuit Breaker Pattern

```python
class CircuitBreaker:
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    expected_exception: type[Exception]
    
    def call(self, func, *args):
        if self._is_open():
            raise CircuitBreakerOpen()
        try:
            result = func(*args)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure(e)
            raise
```

### Provider Circuit Breakers
- Embedding providers: 3 failures, 30s cooldown
- LLM providers: 5 failures, 60s cooldown
- Vector stores: 3 failures, 30s cooldown

## Health Checks

### Liveness Probe
- Process running check
- Always returns OK

### Readiness Probe
- Database connection check
- Vector store accessible
- Embedding API responding
- LLM API responding (if used)

### Metrics Endpoint
- Error rates per component
- Latency percentiles
- Health status map

## Error Response Format

```json
{
  "error": {
    "code": "EMBEDDING_RATE_LIMIT",
    "message": "OpenAI API rate limit exceeded",
    "details": {
      "provider": "openai",
      "model": "text-embedding-3-small",
      "quota_remaining": 0,
      "retry_after_seconds": 60
    },
    "correlation_id": "abc-123-def-456",
    "timestamp": "2026-06-28T00:30:00Z"
  }
}
```

## Recovery Strategy

### At Startup
- Validate all required settings
- Test external connections
- Fail fast if unconfigured

### At Runtime
- Circuit breakers for external services
- Fallback implementations
- Queued retries for transient errors

### For Batch Operations
- Checkpoint every N items
- Resume on restart
- DLQ for permanent failures

## Monitoring

### Error Metrics
```
errors_total{component, error_code, severity}
error_duration_seconds{component}
errors_by_stage{stage}
circuit_breaker_state{component}
```

### Alerting Thresholds
- 5xx errors > 10/min → PagerDuty
- 429 rate limits > 100/min → Slack
- Circuit breaker open > 5min → PagerDuty