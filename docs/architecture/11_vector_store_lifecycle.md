# Vector Store Lifecycle

## Purpose

Vector stores persist and enable efficient similarity search over embedding vectors. This lifecycle manages indexing, storage, retrieval configuration, and hybrid search support.

## Sequence Diagram

```
sequenceDiagram
    participant Pipeline as Ingestion/Query Pipeline
    participant VS as VectorStore
    participant Index as Vector Index
    participant BM25 as BM25 Index
    participant DB as Metadata DB
    
    Pipeline->>VS: upsert(chunks)
    VS->>Index: Store vectors
    Index-->>VS: acknowledgment
    
    alt Hybrid Search Enabled
        VS->>DB: Get chunk content
        VS->>BM25: Update sparse index
        BM25-->>VS: index updated
    end
    
    VS->>DB: Update metadata mapping
    VS-->>Pipeline: UpsertResult
    
    Pipeline->>VS: search(query, top_k, filter)
    VS->>Index: similarity_search
    Index-->>VS: candidate_chunks
    VS-->>Pipeline: Chunk[]
```

## Flowchart

```
flowchart TD
    A[Upsert Request] --> B[Validate Input]
    B --> C[Prepare Vector Records]
    C --> D{Provider}
    
    D -->|FAISS| E[FAISS Index]
    D -->|Chroma| F[Chroma Collection]
    D -->|Pinecone| G[Pinecone Index]
    D -->|Weaviate| H[Weaviate Classes]
    D -->|Qdrant| I[Qdrant Collection]
    
    E --> J[Store Vectors + Metadata]
    F --> J
    G --> J
    H --> J
    I --> J
    
    J --> K{BM25 Enabled?}
    K -->|Yes| L[Update Sparse Index]
    K -->|No| M[Skip Sparse]
    
    L --> N[Update Metadata DB]
    M --> N
    
    N --> O[Return UpsertResult]
    
    A2[Search Request] --> B2[Embed Query]
    B2 --> C2{Search Mode}
    C2 -->|Dense| D2[Dense Search]
    C2 -->|Sparse| E2[BM25 Search]
    C2 -->|Hybrid| F2[Dense + Sparse + Fusion]
    
    D2 --> G2[Return Results]
    E2 --> G2
    F2 --> G2
```

## Inputs

| Operation | Input | Type |
|-----------|-------|------|
| Upsert | `chunks` | `Chunk[]` |
| Search | `query` | `Vector` (embedded query) |
| Search | `top_k` | `int` |
| Search | `filter` | `MetadataFilter` (optional) |
| Delete | `ids` | `UUID[]` |

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `upsert` | `UpsertResult` | `success_count`, `failed_ids` |
| `search` | `Chunk[]` | Retrieved chunks with scores |
| `delete` | `DeleteResult` | `deleted_count` |
| `count` | `int` | Total vectors matching filter |

## Vector Store Providers

### FAISS
- **Type**: In-memory, file-backed
- **Hybrid**: Manual BM25 management
- **Scale**: 10M+ vectors
- **Features**: IVF, HNSW, PQ indexes
- **Limitations**: Single node, no built-in filtering

### Chroma
- **Type**: Embedded
- **Hybrid**: Native sparse support
- **Scale**: 1M+ vectors
- **Features**: Metadata filtering, persistence
- **Limitations**: SQLite backend

### Pinecone
- **Type**: Managed cloud
- **Hybrid**: Native sparse support
- **Scale**: 100M+ vectors
- **Features**: Namespace, pod scaling
- **Limitations**: Cost, external dependency

### Weaviate
- **Type**: Managed/self-hosted
- **Hybrid**: Native sparse support
- **Scale**: 100M+ vectors
- **Features**: GraphQL API, multi-tenancy
- **Limitations**: Resource intensive

### Qdrant
- **Type**: Self-hosted/managed
- **Hybrid**: Native sparse support
- **Scale**: 100M+ vectors
- **Features**: Payload indexing, distributed
- **Limitations**: Newer ecosystem

## Hybrid Search Flow

```
Query Embedding
        │
        ▼
┌─────────────────┐
│  Dense Search   │
│  (Vector Index) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Sparse Search  │
│  (BM25 Index)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Fusion        │
│  (RRF/Weighted) │
└────────┬────────┘
         │
         ▼
    Ranked Results
```

## Metadata Schema (Stored with Vectors)

| Field | Type | Description |
|-------|------|-------------|
| `chunk_id` | `str` (UUID) | Primary identifier |
| `document_id` | `str` (UUID) | Parent document |
| `document_title` | `str` | For display |
| `content` | `str` | Chunk text (for BM25) |
| `source_type` | `str` | Filterable |
| `language` | `str` | Filterable |
| `tags` | `list[str]` | Filterable |
| `sensitivity` | `str` | Filterable |
| `created_at` | `ISO8601` | Filterable (time range) |

## Error Cases

| Scenario | Error Type | Handling |
|----------|------------|----------|
| Dimension mismatch | `VectorStoreError` | Fail at startup validation |
| Index full | `VectorStoreError` | Auto-resize (FAISS) or alert |
| Metadata too large | `VectorStoreError` | Truncate, log warning |
| Write timeout | `VectorStoreError` | Retry with backoff |
| Read timeout | `SearchError` | Return partial results |
| Duplicate ID | `VectorStoreError` | Upsert (replace) |
| Filter yields no results | `SearchError` | Empty result set |

## Recovery Strategy

### Retry Logic
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(),
    retry=retry_if_exception_type(VectorStoreError)
)
async def upsert_with_retry(chunks: list[Chunk]) -> UpsertResult:
    ...
```

### Graceful Degradation
- If vector store fails, circuit breaker opens
- Optional: Read from stale replica
- Optional: Return cached recent results

### Index Management
- Monitor index size, auto-resize thresholds
- Periodic compaction for FAISS
- Backup before major operations

## Performance Considerations

### Index Selection
| Provider | Best For | Considerations |
|----------|----------|----------------|
| FAISS | Development, small-medium scale | Memory, no built-in sparse |
| Chroma | Embedded apps | SQLite bottleneck |
| Pinecone | Production scale | Cost |
| Weaviate | Multi-tenancy | Resources |
| Qdrant | Self-hosted | Setup complexity |

### Query Optimization
- Pre-filtering pushdown (where supported)
- Result caching for repeated queries
- ANN tuning (nlist, nprobe for IVF)
- Metadata index on filterable fields

## Future Scalability

### Sharding Strategy
```
Shard by document_id hash:
Shard 0: hash % 4 == 0
Shard 1: hash % 4 == 1
Shard 2: hash % 4 == 2
Shard 3: hash % 4 == 3
```

### Index Versioning
- Version vectors by embedding model
- Atomic swap on re-indexing
- Rollback capability

### Compression
- Product Quantization (PQ): 96% size reduction
- Scalar Quantization (SQ): 90% size reduction
- Binary embeddings: 99% size reduction