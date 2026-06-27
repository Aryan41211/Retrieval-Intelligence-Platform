# Document Ingestion Lifecycle

## Purpose

Document ingestion transforms raw source documents into a normalized, indexed form ready for retrieval. This is the "index time" pipeline that processes documents before they can be queried.

## Sequence Diagram

```
sequenceDiagram
    participant Client as API Client
    participant API as Ingestion API
    participant Loader as DocumentLoader
    participant Preproc as Preprocessor
    participant Chunker as Chunker
    participant Embedder as EmbeddingProvider
    participant VS as VectorStore
    participant DB as MetadataDB
    
    Client->>API: POST /ingest (file/URL)
    API->>API: Validate request, generate correlation_id
    API->>Loader: load(source)
    
    Loader->>Loader: Extract text + format-specific metadata
    Loader-->>API: Document[]
    
    API->>Preproc: process(document)
    Preproc->>Preproc: Clean, normalize, detect language
    Preproc-->>API: Document[] (cleaned)
    
    API->>Chunker: chunk(document)
    Chunker->>Chunker: Split into chunks with overlap
    Chunker-->>API: Chunk[]
    
    API->>Embedder: embed_documents(chunks)
    Embedder->>Embedder: Batch encode, cache hits check
    Embedder-->>API: Chunk[] (with embeddings)
    
    API->>VS: upsert(chunks)
    VS->>VS: Store vectors + metadata
    VS-->>API: UpsertResult
    
    API->>DB: save_document_index(document, chunks)
    DB-->>API: Index mapping saved
    
    API-->>Client: IngestionResult
```

## Flowchart

```
flowchart TD
    A[Ingestion Request] --> B{Source Type}
    B -->|PDF| C[PDFLoader]
    B -->|DOCX| D[DocxLoader]
    B -->|PPTX| E[PptxLoader]
    B -->|XLSX| F[XlsxLoader]
    B -->|HTML| G[HtmlLoader]
    B -->|Markdown| H[MarkdownLoader]
    B -->|Text| I[TextLoader]
    
    C --> J[PreprocessPipeline]
    D --> J
    E --> J
    F --> J
    G --> J
    H --> J
    I --> J
    
    J --> K[ChunkerFactory.create]
    K --> L[Chunks Generated]
    
    L --> M{Embedding Cache}
    M -->|Hit| N[Return Cached]
    M -->|Miss| O[Call Provider API]
    
    N --> P[Embeddings Attached]
    O --> P
    
    P --> Q[VectorStore.upsert]
    Q --> R{BM25 Enabled?}
    R -->|Yes| S[Update Sparse Index]
    R -->|No| T[Skip]
    
    S --> U[Metadata DB Update]
    T --> U
    
    U --> V[Return IngestionResult]
```

## Inputs

| Input | Type | Description |
|-------|------|-------------|
| `source` | `DocumentSource` | Source location (file path, URL, API endpoint) |
| `source.type` | `DocumentSourceType` | FILE, URL, API, DATABASE, STREAM |
| `source.path` | `str` (optional) | Local file path |
| `source.url` | `str` (optional) | Remote URL |
| `config` | `IngestionConfig` | Chunking, embedding, vector store settings |

## Outputs

| Output | Type | Description |
|--------|------|-------------|
| `IngestionResult` | Model | `documents: int`, `chunks: int`, `vectors_upserted: int`, `failed_chunks: list[UUID]` |
| `document` | `Document` | Indexed with metadata |
| `chunks` | `Chunk[]` | Each with embedding populated |
| `vector_records` | `VectorRecord[]` | Stored in vector database |

## Processing Steps

### 1. Source Validation
```python
# Validate source exists and is readable
if source.type == DocumentSourceType.FILE:
    if not Path(source.path).exists():
        raise LoaderError("File not found")
    if Path(source.path).stat().st_size > config.max_file_size_mb * 1024 * 1024:
        raise LoaderError("File too large")
```

### 2. Document Loading
- Detect format from MIME type or extension
- Route to appropriate loader implementation
- Extract raw text and source metadata
- Compute SHA256 checksum for deduplication
- Handle multi-page documents (split into pages)

### 3. Preprocessing
- Unicode normalization (NFC form)
- Whitespace normalization (collapse, newlines)
- Remove boilerplate (headers, footers, page numbers)
- Language detection and tagging
- Extract structure (headings, tables, code blocks)
- Compute statistics (char count, word count, token estimate)

### 4. Chunking
- Apply configured strategy
- Respect boundaries (sentence, paragraph)
- Track position (start_char, end_char, chunk_index)
- Store chunking metadata (strategy, overlap)
- Preserve heading context for markdown

### 5. Embedding Generation
- Batch chunks by configured batch size
- Check embedding cache (Redis) by content hash
- Call provider API for cache misses
- Attach embeddings to chunks
- Emit cache hit/miss metrics

### 6. Vector Store Upsert
- Prepare vector records with metadata payload
- Batch upsert to vector store
- Update BM25 index if hybrid search enabled
- Update metadata database with document-chunk mapping
- Emit upsert latency metrics

## Error Cases

| Scenario | Error Type | Handling |
|----------|------------|----------|
| File not found/corrupted | `LoaderError` | Skip document, log warning, continue batch |
| Unsupported format | `LoaderError` | Return error to client with supported formats list |
| Encoding error | `PreprocessingError` | Try fallback encoding, log warning |
| Language detection fails | `PreprocessingError` | Default to "en", log warning |
| Chunking produces empty | `ChunkingError` | Skip document, log metric |
| Embedding API rate limit | `EmbeddingError` | Exponential backoff, retry with jitter |
| Provider timeout | `EmbeddingError` | Circuit breaker, fallback provider |
| Vector store unavailable | `VectorStoreError` | Queue for retry, return partial result |

## Recovery Strategy

### Per-Document Checkpointing
```python
class IngestionCheckpoint:
    document_id: UUID
    stage: IngestionStage
    completed_chunks: int
    failed_chunks: list[UUID]
    timestamp: datetime
```

### Retry Logic
- Failed chunks marked with error status
- Retry up to `max_retries` with exponential backoff
- After max retries, skip and log in `failed_chunks`
- Support resume from checkpoint for large documents

### Dead Letter Queue
- Poison pills (consistently failing) go to DLQ
- Logged to `failed_documents/` directory
- Manual inspection and reprocessing possible

## Performance Considerations

| Stage | Bottleneck | Optimization |
|-------|------------|--------------|
| Loading | I/O wait | Parallel loading, connection pooling |
| Preprocessing | Regex operations | Compiled patterns, streaming |
| Chunking | Tokenization | Cached tokenizer, batch processing |
| Embedding | API rate limits | Batching, retry with semaphore |
| Vector Store | Memory/batch size | Buffered upsert, async commit |

### Batching Strategy
```python
# Default: 32 chunks per embedding batch
# Configurable based on provider limits
# Dynamic sizing based on average token count
batch_size = min(
    config.batch_size,
    provider.max_batch_size,
    tokens_fit_in_context(avg_tokens_per_chunk)
)
```

## Future Scalability

### Streaming Ingestion (Planned)
```
Document Stream → Chunk Stream → Embedding Stream → Vector Store Stream
     │              │              │              │
     ▼              ▼              ▼              ▼
Kafka/SQS    Kafka Streams    Batch + Cache    Async Upsert
```

### Distributed Processing
- Multiple workers for parallel ingestion
- Work distribution via Redis queue or Kafka
- Shared embedding cache across workers
- Vector store handles concurrent writes

### Incremental Updates
- Track document modification time
- Re-process only changed documents
- Efficient delta updates to vector index