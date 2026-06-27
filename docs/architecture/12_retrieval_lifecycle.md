# Retrieval Lifecycle

## Purpose

Retrieval finds the most relevant chunks for a query using dense vector search, sparse keyword search, or hybrid fusion. This lifecycle transforms a user query into ranked candidate chunks.

## Sequence Diagram

```
sequenceDiagram
    participant API as Query API
    participant Expander as QueryExpander
    participant Retriever as Retriever
    participant Embedder as EmbeddingProvider
    participant VS as VectorStore
    participant Fusion as HybridFusion
    participant Reranker as Reranker
    
    API->>Expander: expand(query)
    Expander-->>API: ExpandedQuery
    
    API->>Retriever: retrieve(expanded_query)
    
    alt Dense Search Enabled
        Retriever->>Embedder: embed_query(expanded_query)
        Embedder-->>Retriever: query_vector
        Retriever->>VS: search(query_vector, top_k)
        VS-->>Retriever: dense_results
    end
    
    alt Sparse Search Enabled
        Retriever->>VS: search_bm25(expanded_query.text, top_k)
        VS-->>Retriever: sparse_results
    end
    
    Retriever->>Fusion: fuse(dense_results, sparse_results)
    Fusion-->>API: final_results
    
    API->>Reranker: rerank(query, results, top_n)
    Reranker-->>API: reranked_results
```

## Flowchart

```
flowchart TD
    A[Query Request] --> B{Query Expansion}
    B -->|Enabled| C[Expand Query]
    B -->|Disabled| D[Use Original]
    C --> E[HyDE Generate]
    C --> F[LLM Rewrite]
    C --> G[Decompose]
    
    D --> H[Retrieve]
    E --> H
    F --> H
    G --> H
    
    H --> I{Dense Search}
    I -->|Enabled| J[Embed Query]
    I -->|Disabled| K[Skip Dense]
    J --> L[Vector Search]
    
    H --> M{Sparse Search}
    M -->|Enabled| N[BM25 Search]
    M -->|Disabled| O[Skip Sparse]
    
    L --> P{Fusion}
    N --> P
    O --> P
    K --> P
    
    P -->|RRF| Q[Reciprocal Rank Fusion]
    P -->|Weighted| R[Weighted Score Fusion]
    P -->|Single| S[Use Single Result]
    
    Q --> T[Rerank]
    R --> T
    S --> T
    
    T -->|Enabled| U[Apply Reranker]
    T -->|Disabled| V[Skip Reranking]
    
    U --> W[Return Ranked Results]
    V --> W
```

## Inputs

| Input | Type | Description |
|-------|------|-------------|
| `query` | `str` | User query string |
| `expanded_query` | `ExpandedQuery` | Original + rewrite + sub-queries + HyDE |
| `config.dense_enabled` | `bool` | Enable dense search |
| `config.sparse_enabled` | `bool` | Enable BM25 search |
| `config.top_k` | `int` | Number of candidates (default: 20) |
| `config.hybrid_fusion` | `HybridFusion` | RRF, WEIGHTED, DBSF |

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `results` | `RetrievalResult[]` | Ranked chunks |
| `result.rank` | `int` | 1-based rank |
| `result.score` | `float` | Normalized 0-1 score |
| `result.retrieval_method` | `str` | DENSE, SPARSE, HYBRID_RRF |
| `result.dense_score` | `float` | Component score (hybrid) |
| `result.sparse_score` | `float` | Component score (hybrid) |

## Query Expansion Methods

### LLM Rewrite
```
Input: "What's the revenue last year?"
Output: "What was the company's revenue in the fiscal year 2023?"
```

### Query Decomposition
```
Input: "Compare product features and pricing"
Output: [
    "What are the key product features?",
    "What is the pricing for each product?"
]
```

### HyDE (Hypothetical Document Embeddings)
```
Input: "How to install Python?"
LLM Generates Hypothetical Document → Embed → Search
```

## Hybrid Fusion Algorithms

### RRF (Reciprocal Rank Fusion)
```python
def rrf_score(rank_dense: int, rank_sparse: int, k: int = 60) -> float:
    return 1 / (k + rank_dense + 1) + 1 / (k + rank_sparse + 1)
```

### Weighted Fusion
```python
def weighted_score(dense: float, sparse: float, w_dense: float, w_sparse: float) -> float:
    # Normalize both scores to [0,1]
    dense_norm = (dense - min_d) / (max_d - min_d)
    sparse_norm = (sparse - min_s) / (max_s - min_s)
    return w_dense * dense_norm + w_sparse * sparse_norm
```

## Retrieval Methods

| Method | Description | When to Use |
|--------|-------------|-------------|
| Dense | Vector similarity (cosine/dot/L2) | Semantic queries |
| Sparse | BM25 keyword matching | Exact term queries |
| Hybrid RRF | Combine dense + sparse | Best overall |
| Hybrid Weighted | Configurable weights | Domain-tuned |
| Multi-Vector | ColBERT style | Fine-grained matching |

## Error Cases

| Scenario | Error Type | Handling |
|----------|------------|----------|
| No results | `SearchError` | Return empty, log metric |
| Vector store timeout | `SearchError` | Return partial, degrade |
| Embedding failure | `SearchError` | Fallback to sparse only |
| Filter too restrictive | `SearchError` | Relax filter, log warning |
| Reranker timeout | `RerankError` | Return original ranking |
| Query too long | `SearchError` | Truncate with warning |

## Recovery Strategy

### Fallback to Sparse Only
```python
if dense_search_fails:
    log_warning("Dense search failed, using sparse only")
    return sparse_results
```

### Partial Results
```python
if timeout_before_completion:
    return whatever_we_have_with_lowest_scores
```

### Circuit Breaker Pattern
```python
# Open after 5 failures
# 30s recovery window
# Fallback to in-memory index for critical queries
```

## Performance Considerations

| Method | Latency | Recall | Precision |
|--------|---------|---------|-----------|
| Dense Only | Low | Medium | Medium |
| Sparse Only | Low | High (keywords) | High (keywords) |
| Hybrid RRF | Med | High | High |
| Hybrid Weighted | Med | High | High (tuned) |

### Optimization Techniques
- Query embedding caching
- ANN tuning (nprobe, ef_search)
- Pre-filtering pushdown
- Result caching for common queries

## Future Scalability

### Multi-Vector Retrieval
```
Query Tokens → Multiple Vector Searches
     │
     ▼
┌─────────────────┐
│  MaxSim Score   │
│  (ColBERT)      │
└─────────────────┘
```

### Learned Sparse Retrieval
- SPLADE embeddings
- Expansion terms learned
- No separate BM25 index needed

### Adaptive Retrieval
- Query intent classification
- Select strategy based on query type
- A/B test different approaches