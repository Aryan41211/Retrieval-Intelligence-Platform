# Chunking Lifecycle

## Purpose

Chunking divides documents into semantically meaningful, retrieval-ready segments. Proper chunking is critical for retrieval quality, affecting both recall and precision of search results.

## Sequence Diagram

```
sequenceDiagram
    participant Pipeline as Ingestion Pipeline
    participant Chunker as Chunker
    participant Config as ChunkingConfig
    participant Token as Tokenizer
    participant Doc as Document
    
    Pipeline->>Chunker: chunk(document)
    Chunker->>Config: Get strategy parameters
    
    Chunker->>Chunker: Apply chunking strategy
    
    opt Fixed Strategy
        Chunker->>Chunker: Split at fixed boundaries
        Chunker->>Chunker: Apply overlap
    end
    
    opt Recursive Strategy
        Chunker->>Chunker: Split on \n\n
        Chunker->>Chunker: Recurse on \n
        Chunker->>Chunker: Recurse on ". "
        Chunker->>Chunker: Recurse on " "
    end
    
    opt Semantic Strategy
        Chunker->>Token: Count tokens
        Chunker->>Chunker: Compute embeddings for sentences
        Chunker->>Chunker: Find semantic boundaries
    end
    
    Chunker->>Token: Count tokens in each chunk
    Chunker->>Chunker: Compute positions and metadata
    
    Chunker-->>Pipeline: Chunk[]
```

## Flowchart

```
flowchart TD
    A[Document Input] --> B{Strategy}
    B -->|Fixed| C[Split at N tokens/chars]
    B -->|Recursive| D[Split on separators]
    B -->|Semantic| E[Embed sentences]
    B -->|Markdown| F[Split on headings]
    B -->|Sentence| G[Split on sentence boundaries]
    
    C --> H[Apply Overlap]
    D --> H
    E --> H
    F --> H
    G --> H
    
    H --> I[Validate Chunk Sizes]
    I --> J{Size Valid?}
    J -->|No| K[Adjust / Split Further]
    J -->|Yes| L[Compute Metadata]
    
    K --> L
    L --> M[Return Chunk[]]
```

## Inputs

| Input | Type | Description |
|-------|------|-------------|
| `document` | `Document` | Preprocessed document with clean content |
| `config.strategy` | `ChunkingStrategy` | FIXED, RECURSIVE, SEMANTIC, MARKDOWN, SENTENCE |
| `config.chunk_size` | `int` | Target size in tokens (default: 512) |
| `config.chunk_overlap` | `int` | Overlap between chunks (default: 50) |
| `config.min_chunk_size` | `int` | Minimum chunk size (default: 50) |
| `config.respect_boundaries` | `bool` | Don't split mid-sentence (default: true) |

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `chunks` | `Chunk[]` | List of chunk objects |
| `chunk.id` | `UUID` | Unique chunk identifier |
| `chunk.document_id` | `UUID` | Reference to parent document |
| `chunk.content` | `str` | Chunk text |
| `chunk.start_char` | `int` | Start position in document |
| `chunk.end_char` | `int` | End position in document |
| `chunk.metadata` | `ChunkMetadata` | Strategy, token count, overlap info |

## Chunking Strategies

### Fixed Chunker
- Split at exactly `chunk_size` tokens/characters
- Apply `chunk_overlap` between consecutive chunks
- Simple, predictable, works for uniform content
- May break mid-sentence if `respect_boundaries=false`

### Recursive Chunker
```
Split separators (in order):
1. \n\n (paragraphs)
2. \n (lines)
3. ". " (sentences)
4. " " (spaces)
```
- Recursively splits until all pieces fit
- Preferred for general purpose
- Better semantic coherence than fixed

### Semantic Chunker
- Uses embedding similarity to find boundaries
- Implements "semantic text splitting" algorithm
- Most coherent chunks, but slower
- Best for high-quality retrieval

### Markdown Chunker
- Respects heading hierarchy
- Preserves code blocks intact
- Maintains section context
- Ideal for technical documentation

### Sentence Chunker
- Uses NLTK/spaCy for sentence splitting
- Guarantees sentence boundaries
- Good for narrative text
- Requires NLP libraries

## Metadata Fields

| Field | Type | Description |
|-------|------|-------------|
| `chunking_strategy` | `str` | Strategy used (fixed, recursive, etc.) |
| `chunk_index` | `int` | Position within document (0-based) |
| `start_char` | `int` | Character offset in source |
| `end_char` | `int` | Character offset in source |
| `token_count` | `int` | Estimated tokens |
| `overlap_prev_tokens` | `int` | Tokens shared with previous |
| `overlap_next_tokens` | `int` | Tokens shared with next |
| `heading_path` | `list[str]` | Heading hierarchy for MD/docs |

## Error Cases

| Scenario | Error Type | Handling |
|----------|------------|----------|
| Document too short for chunking | `ChunkingError` | Return single chunk |
| Chunk exceeds model context | `ChunkingError` | Auto-split with warning |
| All chunks filtered by min_size | `ChunkingError` | Return error, log metric |
| Semantic chunking OOM | `ChunkingError` | Fallback to recursive |
| No valid split points found | `ChunkingError` | Return oversized chunk |

## Recovery Strategy

### Fallback Chain
1. Primary strategy fails
2. Try recursive as fallback
3. Try fixed as last resort
4. Log warning about degraded quality

### Auto-Split
```python
if chunk.token_count > config.max_chunk_size:
    # Split in half and recurse
    mid = len(chunk.content) // 2
    left = chunk.content[:mid]
    right = chunk.content[mid:]
    # Combine with overlap
    return chunk_text(left, right)
```

## Performance Considerations

| Strategy | Time Complexity | Memory | Use Case |
|----------|-----------------|--------|----------|
| Fixed | O(n) | Low | High-throughput, uniform content |
| Recursive | O(n) | Low | General purpose |
| Semantic | O(n log n) to O(n²) | High | Quality-critical, smaller docs |
| Markdown | O(n) | Low | Technical docs |
| Sentence | O(n) | Medium | Narrative text |

### Optimization Techniques
- Pre-compile regex patterns
- Cache tokenizer instances
- Batch position calculations
- Early exit for small documents

## Future Scalability

### Hierarchical Chunking
```
Parent Chunk (512 tokens)
├── Child Chunk 1 (128 tokens)
├── Child Chunk 2 (128 tokens)
└── Child Chunk 3 (128 tokens)
```
- Two-level hierarchy for multi-granularity retrieval
- Parent for coarse filtering
- Child for fine-grained matching

### Adaptive Chunking
- Different strategies per document section
- Table-aware: keep tables intact
- Figure-aware: associate captions with figures
- Dynamic chunk size based on content density

### Chunk Quality Scoring
- Compute coherence score per chunk
- Filter low-quality chunks
- Weight scoring model trained on retrieval performance