# Embedding Lifecycle

## Purpose

Embedding generation converts text chunks into dense vector representations for similarity search. This lifecycle handles provider communication, caching, batching, and error recovery.

## Sequence Diagram

```
sequenceDiagram
    participant Pipeline as Ingestion Pipeline
    participant Embedder as EmbeddingProvider
    participant Cache as EmbeddingCache
    participant Provider as API Provider
    participant Batch as Batch Queue
    
    Pipeline->>Embedder: embed_chunks(chunks)
    Embedder->>Cache: Check cache for content hashes
    Cache-->>Embedder: cached_embeddings
    
    Embedder->>Batch: Queue uncached chunks
    Batch->>Provider: Call embed_documents(batch)
    
    alt Cache Miss
        Provider-->>Batch: vectors
        Batch->>Cache: Store vectors
    end
    
    Embedder-->>Pipeline: chunks with embeddings
```

## Flowchart

```
flowchart TD
    A[Chunk Input] --> B[Compute Content Hash]
    B --> C{Cache Check}
    C -->|Hit| D[Return Cached Vector]
    C -->|Miss| E[Add to Batch Queue]
    
    E --> F{Batch Full?}
    F -->|No| G[Wait for More Chunks]
    F -->|Yes| H[Call Provider API]
    
    G --> F
    H --> I{API Success?}
    I -->|Yes| J[Store in Cache]
    I -->|No| K[Retry with Backoff]
    
    K --> L{Retry Count < Max?}
    L -->|Yes| H
    L -->|No| M[Fallback Provider]
    
    M --> N[CIRCUIT BREAKER]
    N -->|Open| O[Use Fallback]
    N -->|Closed| P[Raise Error]
    
    J --> Q[Attach Vectors to Chunks]
    D --> Q
    O --> Q
    
    Q --> R[Return Chunks with Embeddings]
```

## Inputs

| Input | Type | Description |
|-------|------|-------------|
| `chunks` | `Chunk[]` | Chunks with text content |
| `config.provider` | `EmbeddingProvider` | OPENAI, COHERE, VOYAGE, SENTENCE_TRANSFORMERS |
| `config.model` | `str` | Model identifier (e.g., "text-embedding-3-small") |
| `config.batch_size` | `int` | Batch size for API calls (default: 32) |
| `config.cache_enabled` | `bool` | Enable embedding cache |
| `config.cache_ttl` | `int` | Cache TTL in seconds |

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `chunks` | `Chunk[]` | Same chunks with `embedding` field populated |
| `embedding` | `Vector` | Dense vector on each chunk |
| `dimension` | `int` | Vector dimension (propagated to metadata) |

## Provider Interfaces

### OpenAI
- Models: `text-embedding-3-small` (1536), `text-embedding-3-large` (3072)
- Rate limits: 3000 RPM, 1M TPM
- Cost: $0.00002 per 1K tokens (small), $0.00013 (large)

### Cohere
- Models: `embed-english-v3.0` (1024), `embed-multilingual-v3.0` (1024)
- Rate limits: 100 RPM, 50K TPM
- Cost: $0.000075 per 1K tokens

### Voyage AI
- Models: `voyage-3` (1024), `voyage-3-large` (2048)
- Rate limits: 1000 RPM
- Cost: $0.000045 per 1K tokens

### Sentence Transformers
- Models: `BAAI/bge-small-en-v1.5`, `intfloat/e5-large-v2`, etc.
- No rate limits (local inference)
- GPU memory bottleneck

## Caching Strategy

### Cache Key Composition (current implementation)
The cache key is designed to be provider-agnostic and future-proof.

```
key = sha256(
  chunk_checksum
  + model_name + model_version
  + stable_json(configuration_snapshot)
)
```

- `chunk_checksum`: sha256 of the chunk content (`sha256(chunk.text)`), computed during pipeline execution.
- `model_name` / `model_version`: taken from `provider.model_info`.
- `configuration_snapshot`: a stable JSON snapshot that includes pipeline runtime knobs (e.g., `batch_size`, `max_workers`, `show_progress`) plus any additional per-call `config`.

### Cache Persistence
When `EmbeddingCache(persist_path=...)` is configured, the cache is persisted to disk as a best-effort JSON file:
- Loads on startup (corrupt cache is ignored)
- Writes on `set()` and `clear()` (bounded by `max_size`)

This satisfies the “persist embeddings” requirement without introducing a vector database.

### Cache Metrics
- `hits`, `misses`, `hit_rate` (from `EmbeddingCache.get_stats()`)

## Error Cases

| Scenario | Error Type | Handling |
|----------|------------|----------|
| Rate limit exceeded | `EmbeddingError` | Exponential backoff, retry |
| Invalid API key | `EmbeddingError` | Fail fast, circuit breaker open |
| Token limit exceeded | `EmbeddingError` | Auto-truncate with warning |
| Provider timeout | `EmbeddingError` | Retry, then fallback |
| Dimension mismatch | `EmbeddingError` | Fail at startup validation |
| Model not found | `EmbeddingError` | Fail fast |
| GPU out of memory | `EmbeddingError` | Fallback to CPU, log |

## Recovery Strategy

### Retry with Exponential Backoff
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(EmbeddingError)
)
async def embed_with_retry(texts: list[str]) -> list[Vector]:
    ...
```

### Circuit Breaker Pattern
```python
# After 5 consecutive failures, open for 30s
@circuit_breaker(failure_threshold=5, recovery_timeout=30)
async def call_embedding_api(...) -> ...:
    ...
```

### Fallback Provider
```python
# Primary: OpenAI
# Fallback: Sentence Transformers (local)
if primary_fails:
    use_fallback_if_configured()
```

## Performance Considerations

### Batching Optimization
- Provider max batch size varies (OpenAI: 2048, Cohere: 96)
- Optimal batch size balances throughput and latency
- Dynamic sizing based on text length

### Parallelization
```python
# Process multiple batches concurrently
semaphore = asyncio.Semaphore(config.max_concurrency)
results = await asyncio.gather(*[
    embed_batch(batch) for batch in batches
])
```

### Memory Management
- Stream embeddings directly to vector store
- Don't hold all embeddings in memory
- Use generator pattern for large batches

## Future Scalability

### Asynchronous Processing
```
Embedding Queue (Redis/Celery)
        │
        ▼
Worker Pool (GPU/CPU workers)
        │
        ▼
Result Cache
        │
        ▼
Vector Store
```

### Multi-Vector Embeddings
- ColBERT: Token-level embeddings
- SPLADE: Sparse + dense combination
- Late interaction for better retrieval

### Quantization
- INT8 quantization for storage
- Binary embeddings for speed
- Product quantization (PQ) for compression